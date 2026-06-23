@echo off
setlocal
cd /d "%~dp0"

echo VPS 3x-ui 一键部署器启动器

where py >nul 2>nul
if errorlevel 1 (
  where python >nul 2>nul
  if errorlevel 1 (
    echo 启动失败：未找到 Python。请先安装 Python 3.9 或更高版本。
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo 正在创建本地虚拟环境 .venv ...
  py -3 -m venv .venv
  if errorlevel 1 (
    python -m venv .venv
    if errorlevel 1 (
      echo 启动失败：创建 .venv 失败。请确认 Python venv 模块可用。
      pause
      exit /b 1
    )
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 (
  echo 启动失败：升级 pip 失败。请检查本机网络或 Python 安装。
  pause
  exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
  echo 启动失败：安装 requirements.txt 依赖失败。请检查本机网络。
  pause
  exit /b 1
)

echo 正在运行本地产品启动前自检，不会连接 VPS ...
python scripts\check_product_readiness.py
if errorlevel 1 (
  echo 启动失败：产品启动前自检未通过。
  pause
  exit /b 1
)

echo 正在启动本地页面 ...
streamlit run app.py
