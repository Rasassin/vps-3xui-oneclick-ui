const { app, BrowserWindow, Menu, shell } = require("electron");
const fs = require("fs");
const http = require("http");
const net = require("net");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const APP_NAME = "VPS 3x-ui Oneclick";
const SAFETY_NOTE = "The Electron shell starts only local Streamlit and does not connect to a VPS.";
const DEFAULT_HOST = "127.0.0.1";
const DEFAULT_PORT = 18520;
const START_TIMEOUT_MS = 120000;
const STREAMLIT_CHILD_FLAG = "--vps-3xui-streamlit-child";
const CHILD_HOST_ENV = "VPS_3XUI_CHILD_HOST";
const CHILD_PORT_ENV = "VPS_3XUI_CHILD_PORT";

let mainWindow = null;
let streamlitProcess = null;
let streamlitUrl = null;
let logStream = null;

function runtimeRoot() {
  if (!app.isPackaged) {
    return path.resolve(__dirname, "..");
  }
  return path.join(process.resourcesPath, "app");
}

function bundledSidecarExecutable() {
  if (!app.isPackaged) {
    return null;
  }
  const candidates = [];
  if (process.platform === "darwin") {
    candidates.push(path.join(
      process.resourcesPath,
      "streamlit-server",
      "streamlit-sidecar",
      "Contents",
      "MacOS",
      "VPS 3x-ui Oneclick",
    ));
  } else if (process.platform === "win32") {
    candidates.push(path.join(process.resourcesPath, "streamlit-server", "VPS 3x-ui Oneclick.exe"));
  } else {
    candidates.push(path.join(process.resourcesPath, "streamlit-server", "VPS 3x-ui Oneclick"));
  }
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function supportDir() {
  return path.join(app.getPath("userData"));
}

function logPath() {
  const dir = path.join(supportDir(), "logs");
  fs.mkdirSync(dir, { recursive: true });
  return path.join(dir, "electron-launcher.log");
}

function writeLog(message) {
  const line = `[${new Date().toISOString()}] ${message}\n`;
  if (!logStream) {
    logStream = fs.createWriteStream(logPath(), { flags: "a" });
  }
  logStream.write(line);
}

function pythonExecutable(root) {
  const candidates = [];
  if (process.platform === "win32") {
    candidates.push(path.join(root, ".venv", "Scripts", "python.exe"));
    candidates.push("python");
    candidates.push("py");
  } else {
    candidates.push(path.join(root, ".venv", "bin", "python"));
    candidates.push("python3");
    candidates.push("python");
  }
  return candidates.find((candidate) => {
    if (candidate.includes(path.sep)) {
      return fs.existsSync(candidate);
    }
    return true;
  });
}

function portAvailable(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, host);
  });
}

async function findFreePort(host, startPort) {
  for (let port = startPort; port < startPort + 120; port += 1) {
    if (await portAvailable(host, port)) {
      return port;
    }
  }
  throw new Error("无法找到可用的本地端口。");
}

function healthCheck(host, port) {
  return new Promise((resolve) => {
    const request = http.get(
      {
        host,
        port,
        path: "/_stcore/health",
        timeout: 2000,
      },
      (response) => {
        let body = "";
        response.setEncoding("utf8");
        response.on("data", (chunk) => {
          body += chunk;
        });
        response.on("end", () => {
          resolve(response.statusCode === 200 && body.trim() === "ok");
        });
      },
    );
    request.on("timeout", () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

async function waitForStreamlit(host, port) {
  const deadline = Date.now() + START_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await healthCheck(host, port)) {
      return true;
    }
    if (streamlitProcess && streamlitProcess.exitCode !== null) {
      throw new Error(`Streamlit 已退出，退出码：${streamlitProcess.exitCode}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

function createWindow() {
  Menu.setApplicationMenu(null);
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 1080,
    minHeight: 720,
    title: APP_NAME,
    backgroundColor: "#f7f8fb",
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (streamlitUrl && url.startsWith(streamlitUrl)) {
      return { action: "allow" };
    }
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (streamlitUrl && url.startsWith(streamlitUrl)) {
      return;
    }
    event.preventDefault();
    shell.openExternal(url);
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function loadSplash(text) {
  const escaped = text.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
  mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(`
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <title>${APP_NAME}</title>
    <style>
      body { margin: 0; height: 100vh; display: grid; place-items: center; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #20242c; background: #f7f8fb; }
      main { width: min(520px, calc(100vw - 48px)); }
      h1 { font-size: 24px; margin: 0 0 12px; }
      p { margin: 0; color: #667085; line-height: 1.6; }
    </style>
  </head>
  <body><main><h1>${APP_NAME}</h1><p>${escaped}</p></main></body>
</html>
`)}`);
}

async function startStreamlit() {
  const root = runtimeRoot();
  const appPath = path.join(root, "app.py");
  const sidecar = bundledSidecarExecutable();
  if (!sidecar && !fs.existsSync(appPath)) {
    throw new Error(`找不到 app.py：${appPath}`);
  }

  const host = DEFAULT_HOST;
  const port = await findFreePort(host, Number(process.env.VPS_3XUI_ELECTRON_PORT || DEFAULT_PORT));
  const env = {
    ...process.env,
    PYTHONPATH: [root, process.env.PYTHONPATH || ""].filter(Boolean).join(path.delimiter),
    STREAMLIT_BROWSER_GATHER_USAGE_STATS: "false",
    VPS_3XUI_OPEN_BROWSER: "0",
    [CHILD_HOST_ENV]: host,
    [CHILD_PORT_ENV]: String(port),
  };
  const command = sidecar || pythonExecutable(root);
  const args = sidecar
    ? [STREAMLIT_CHILD_FLAG]
    : [
      "-m",
      "streamlit",
      "run",
      appPath,
      "--server.address",
      host,
      "--server.port",
      String(port),
      "--server.headless",
      "true",
      "--server.fileWatcherType",
      "none",
      "--browser.gatherUsageStats",
      "false",
    ];

  writeLog(`starting Streamlit with ${command} on ${host}:${port}`);
  streamlitProcess = spawn(command, args, {
    cwd: root,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });
  streamlitProcess.stdout.on("data", (chunk) => writeLog(chunk.toString()));
  streamlitProcess.stderr.on("data", (chunk) => writeLog(chunk.toString()));
  streamlitProcess.on("exit", (code, signal) => writeLog(`Streamlit exited code=${code} signal=${signal}`));

  const ready = await waitForStreamlit(host, port);
  if (!ready) {
    throw new Error(`Streamlit 启动超时，请查看日志：${logPath()}`);
  }
  streamlitUrl = `http://${host}:${port}`;
  return streamlitUrl;
}

function stopStreamlit() {
  if (!streamlitProcess || streamlitProcess.exitCode !== null) {
    return;
  }
  streamlitProcess.kill("SIGTERM");
  setTimeout(() => {
    if (streamlitProcess && streamlitProcess.exitCode === null) {
      streamlitProcess.kill("SIGKILL");
    }
  }, 5000);
}

app.whenReady().then(async () => {
  createWindow();
  loadSplash("正在启动本地部署界面。这个桌面壳只启动本机服务，不会连接 VPS。");
  try {
    const url = await startStreamlit();
    writeLog(`loading ${url}`);
    await mainWindow.loadURL(url);
  } catch (error) {
    writeLog(error.stack || String(error));
    loadSplash(`${error.message}\n日志位置：${logPath()}`);
  }
});

app.on("window-all-closed", () => {
  stopStreamlit();
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopStreamlit();
  if (logStream) {
    logStream.end();
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
    if (streamlitUrl) {
      mainWindow.loadURL(streamlitUrl);
    }
  }
});
