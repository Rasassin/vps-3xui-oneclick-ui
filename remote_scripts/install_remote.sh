#!/usr/bin/env bash
set -Eeuo pipefail

RESULT_DIR="/root/3xui-oneclick-result"
RESULT_JSON="$RESULT_DIR/result.json"

NODE_NAME="${ONECLICK_NODE_NAME:-auto-reality}"
REALITY_PORT="${ONECLICK_REALITY_PORT:-443}"
SNI="${ONECLICK_SNI:-www.microsoft.com}"
TARGET="${ONECLICK_TARGET:-www.microsoft.com:443}"
FINGERPRINT="${ONECLICK_FINGERPRINT:-chrome}"
PANEL_PORT="${ONECLICK_PANEL_PORT:-2053}"
REQUESTED_PANEL_PORT="$PANEL_PORT"
GENERATE_SSH_KEY="${ONECLICK_GENERATE_SSH_KEY:-1}"
RUN_HARDENING="${ONECLICK_RUN_HARDENING:-0}"
PUBLIC_HOST="${ONECLICK_PUBLIC_HOST:-}"

STATUS="running"
ERROR_CODE=""
ERROR_MESSAGE=""
SUBSCRIPTION_WARNING=""

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

json_write() {
  local status="$1"
  local error_code="${2:-}"
  local error_message="${3:-}"
  jq -n \
    --arg status "$status" \
    --arg error_code "$error_code" \
    --arg error_message "$error_message" \
    --arg node_name "${NODE_NAME}" \
    --arg public_host "${PUBLIC_HOST}" \
    --arg panel_url "${PANEL_PUBLIC_URL:-}" \
    --arg panel_username "${PANEL_USER:-}" \
    --arg panel_password "${PANEL_PASS:-}" \
    --arg vless_link "${VLESS_LINK:-}" \
    --arg subscription_link "${SUBSCRIPTION_LINK:-}" \
    --arg subscription_warning "${SUBSCRIPTION_WARNING:-}" \
    --arg reality_port "${REALITY_PORT}" \
    --arg sni "${SNI}" \
    --arg target "${TARGET}" \
    --arg fingerprint "${FINGERPRINT}" \
    '{
      status: $status,
      error_code: $error_code,
      error_message: $error_message,
      node_name: $node_name,
      public_host: $public_host,
      panel_url: $panel_url,
      panel_username: $panel_username,
      panel_password: $panel_password,
      vless_link: $vless_link,
      subscription_link: $subscription_link,
      subscription_warning: $subscription_warning,
      reality_port: ($reality_port | tonumber? // $reality_port),
      sni: $sni,
      target: $target,
      fingerprint: $fingerprint
    }' > "$RESULT_JSON"
  chmod 600 "$RESULT_JSON"
}

json_escape_no_jq() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

fail() {
  ERROR_CODE="$1"
  ERROR_MESSAGE="$2"
  STATUS="failed"
  log "ERROR [$ERROR_CODE] $ERROR_MESSAGE"
  if command -v jq >/dev/null 2>&1; then
    json_write "failed" "$ERROR_CODE" "$ERROR_MESSAGE"
  else
    {
      printf '{\n'
      printf '  "status": "failed",\n'
      printf '  "error_code": "%s",\n' "$(json_escape_no_jq "$ERROR_CODE")"
      printf '  "error_message": "%s"\n' "$(json_escape_no_jq "$ERROR_MESSAGE")"
      printf '}\n'
    } > "$RESULT_JSON"
    chmod 600 "$RESULT_JSON"
  fi
  write_report || true
  exit 1
}

write_report() {
  {
    echo "VPS 3x-ui 一键部署报告"
    echo "生成时间：$(date '+%F %T')"
    echo
    echo "状态：${STATUS}"
    [[ -n "$ERROR_CODE" ]] && echo "错误代码：$ERROR_CODE"
    [[ -n "$ERROR_MESSAGE" ]] && echo "错误信息：$ERROR_MESSAGE"
    echo
    echo "节点名称：$NODE_NAME"
    echo "Reality 端口：$REALITY_PORT"
    echo "SNI：$SNI"
    echo "Target：$TARGET"
    echo "Fingerprint：$FINGERPRINT"
    echo
    echo "面板地址：${PANEL_PUBLIC_URL:-}"
    echo "面板账号：${PANEL_USER:-}"
    echo "面板密码：${PANEL_PASS:-}"
    echo
    echo "订阅链接：${SUBSCRIPTION_LINK:-未生成}"
    [[ -n "$SUBSCRIPTION_WARNING" ]] && echo "订阅警告：$SUBSCRIPTION_WARNING"
    echo
    echo "安全提示：请尽快修改 VPS root 密码，或切换为 SSH key 登录。第一版不会默认关闭 root 登录、密码登录或 ping。"
  } > "$RESULT_DIR/deploy-report.txt"
  chmod 600 "$RESULT_DIR/deploy-report.txt"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "请使用 root 用户运行远程脚本。"
    exit 1
  fi
}

prepare_result_dir() {
  mkdir -p "$RESULT_DIR"
  chmod 700 "$RESULT_DIR"
}

check_os() {
  [[ -f /etc/os-release ]] || fail "UNSUPPORTED_OS" "无法识别系统版本。"
  # shellcheck disable=SC1091
  source /etc/os-release
  local os_id="${ID:-}"
  local version_id="${VERSION_ID:-}"
  if [[ "$os_id" == "ubuntu" && ( "$version_id" == "22.04" || "$version_id" == "24.04" ) ]]; then
    log "系统检查通过：Ubuntu $version_id"
    return
  fi
  if [[ "$os_id" == "debian" && "$version_id" == "12" ]]; then
    log "系统检查通过：Debian $version_id"
    return
  fi
  fail "UNSUPPORTED_OS" "仅支持 Ubuntu 22.04 / Ubuntu 24.04 / Debian 12，当前系统：${PRETTY_NAME:-unknown}"
}

install_dependencies() {
  log "安装基础依赖。"
  export DEBIAN_FRONTEND=noninteractive
  export APT_LISTCHANGES_FRONTEND=none
  export NEEDRESTART_MODE=a
  apt-get \
    -o Acquire::Retries=3 \
    -o Acquire::ForceIPv4=true \
    -o Acquire::http::Timeout=30 \
    -o Acquire::https::Timeout=30 \
    -o Dpkg::Progress-Fancy=0 \
    update || fail "APT_INSTALL_FAILED" "apt-get update 失败，请检查 VPS 到 Ubuntu/Debian 软件源的网络。"
  apt-get install -y \
    -o Acquire::Retries=3 \
    -o Acquire::ForceIPv4=true \
    -o Acquire::http::Timeout=30 \
    -o Acquire::https::Timeout=30 \
    -o Dpkg::Options::=--force-confdef \
    -o Dpkg::Options::=--force-confold \
    -o Dpkg::Progress-Fancy=0 \
    curl \
    jq \
    qrencode \
    openssl \
    uuid-runtime \
    ca-certificates \
    python3 \
    iproute2 \
    procps \
    lsof \
    sqlite3 || fail "APT_INSTALL_FAILED" "基础依赖安装失败，请检查 VPS 软件源和网络。"
}

verify_dependencies() {
  log "校验基础依赖命令。"
  for cmd in curl jq qrencode openssl uuidgen ss python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "缺少依赖命令: $cmd"
      exit 1
    fi
  done
}

enable_bbr() {
  log "开启 BBR。"
  cat >/etc/sysctl.d/99-3xui-oneclick-bbr.conf <<'EOF'
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
  sysctl --system >/dev/null || true
}

check_port() {
  log "检查 Reality 入站端口 ${REALITY_PORT} 是否被占用。"
  if ss -ltnH "( sport = :${REALITY_PORT} )" | grep -q .; then
    fail "PORT_IN_USE" "Reality 入站端口 ${REALITY_PORT} 已被占用。"
  fi
}

random_string() {
  openssl rand -hex 32 | cut -c "1-${1:-16}"
}

install_3xui() {
  log "准备安装 3x-ui。"
  PANEL_USER="admin$(random_string 6)"
  PANEL_PASS="$(random_string 20)"
  PANEL_PATH_NAME="$(random_string 18)"
  INSTALLER="/tmp/3x-ui-install.sh"
  if ! curl -fsSL https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh -o "$INSTALLER"; then
    fail "GITHUB_DOWNLOAD_FAILED" "无法从 GitHub 下载 MHSanaei/3x-ui 官方 install.sh。"
  fi
  chmod 700 "$INSTALLER"

  log "执行 3x-ui 官方安装脚本。"
  if ! XUI_NONINTERACTIVE=1 \
       XUI_USERNAME="$PANEL_USER" \
       XUI_PASSWORD="$PANEL_PASS" \
       XUI_WEB_BASE_PATH="$PANEL_PATH_NAME" \
       XUI_PORT="$REQUESTED_PANEL_PORT" \
       XUI_PANEL_PORT="$REQUESTED_PANEL_PORT" \
       bash "$INSTALLER"; then
    fail "XUI_INSTALL_FAILED" "3x-ui 安装脚本执行失败。"
  fi

  force_panel_settings
  recover_panel_info
  systemctl enable x-ui >/dev/null 2>&1 || true
  systemctl restart x-ui >/dev/null 2>&1 || true
  sleep 3
}

find_xui_bin() {
  if [[ -x /usr/local/x-ui/x-ui ]]; then
    printf '%s\n' "/usr/local/x-ui/x-ui"
    return
  fi
  command -v x-ui || true
}

force_panel_settings() {
  local xui_bin
  xui_bin="$(find_xui_bin)"
  if [[ -z "$xui_bin" ]]; then
    log "未找到 x-ui CLI，跳过强制写入面板配置。"
    return
  fi
  log "写入本次部署使用的 3x-ui 面板账号、密码、端口和路径。"
  "$xui_bin" setting \
    -username "$PANEL_USER" \
    -password "$PANEL_PASS" \
    -port "$REQUESTED_PANEL_PORT" \
    -webBasePath "$PANEL_PATH_NAME" >/dev/null 2>&1 || fail "XUI_API_FAILED" "无法通过 x-ui CLI 写入面板配置。"
}

recover_panel_info() {
  log "读取或恢复 3x-ui 面板信息。"
  PANEL_PATH="/"
  PANEL_SCHEME="http"
  PANEL_API_TOKEN=""
  if [[ -f /etc/x-ui/install-result.env ]]; then
    # shellcheck disable=SC1091
    source /etc/x-ui/install-result.env || true
    PANEL_PORT="${XUI_PANEL_PORT:-${PORT:-${XUI_PORT:-$PANEL_PORT}}}"
    PANEL_USER="${PANEL_USER:-${USERNAME:-${XUI_USERNAME:-}}}"
    PANEL_PASS="${PANEL_PASS:-${PASSWORD:-${XUI_PASSWORD:-}}}"
    PANEL_API_TOKEN="${XUI_API_TOKEN:-${API_TOKEN:-${PANEL_API_TOKEN:-}}}"
    PANEL_PATH="${WEB_BASE_PATH:-${WEBBASEPATH:-${XUI_WEB_BASE_PATH:-${XUI_WEBBASEPATH:-${PANEL_PATH}}}}}"
    if [[ "${XUI_ACCESS_URL:-}" == https://* ]]; then
      PANEL_SCHEME="https"
    fi
  fi

  local db="/etc/x-ui/x-ui.db"
  if [[ -f "$db" ]]; then
    local db_user db_port db_path
    db_user="$(sqlite3 "$db" "select username from users limit 1;" 2>/dev/null || true)"
    db_port="$(sqlite3 "$db" "select value from settings where key='webPort' limit 1;" 2>/dev/null || true)"
    db_path="$(sqlite3 "$db" "select value from settings where key='webBasePath' limit 1;" 2>/dev/null || true)"
    [[ -n "$db_user" ]] && PANEL_USER="${PANEL_USER:-$db_user}"
    [[ -n "$db_port" ]] && PANEL_PORT="$db_port"
    [[ -n "$db_path" ]] && PANEL_PATH="$db_path"
  fi

  local xui_bin settings cert_info cli_port cli_path cli_cert cli_key
  xui_bin="$(find_xui_bin)"
  if [[ -n "$xui_bin" ]]; then
    settings="$("$xui_bin" setting -show true 2>/dev/null || true)"
    cli_port="$(echo "$settings" | awk -F': ' '/^port:/ {print $2; exit}' | tr -d '[:space:]')"
    cli_path="$(echo "$settings" | awk -F': ' '/^webBasePath:/ {print $2; exit}' | tr -d '[:space:]')"
    [[ -n "$cli_port" ]] && PANEL_PORT="$cli_port"
    [[ -n "$cli_path" ]] && PANEL_PATH="$cli_path"

    cert_info="$("$xui_bin" setting -getCert true 2>/dev/null || true)"
    cli_cert="$(echo "$cert_info" | awk -F': ' '/^cert:/ {print $2; exit}' | tr -d '[:space:]')"
    cli_key="$(echo "$cert_info" | awk -F': ' '/^key:/ {print $2; exit}' | tr -d '[:space:]')"
    if [[ -n "$cli_cert" && -n "$cli_key" ]]; then
      PANEL_SCHEME="https"
    fi
  fi

  [[ -n "${PANEL_USER:-}" ]] || PANEL_USER="admin"
  [[ -n "${PANEL_PASS:-}" ]] || log "未能从配置恢复面板密码，将继续尝试使用安装前生成的密码。"
  [[ "$PANEL_PATH" == /* ]] || PANEL_PATH="/$PANEL_PATH"
  [[ "$PANEL_PATH" == */ ]] || PANEL_PATH="$PANEL_PATH/"
  PANEL_LOCAL_URL="${PANEL_SCHEME}://127.0.0.1:${PANEL_PORT}${PANEL_PATH%/}"
  PANEL_PUBLIC_URL="${PANEL_SCHEME}://${PUBLIC_HOST}:${PANEL_PORT}${PANEL_PATH%/}"

  if [[ -z "$PANEL_API_TOKEN" && -n "$xui_bin" ]]; then
    PANEL_API_TOKEN="$("$xui_bin" setting -getApiToken true 2>/dev/null | awk -F': ' '/apiToken:/ {print $2; exit}' | tr -d '[:space:]' || true)"
  fi
}

curl_api_get() {
  local url="$1"
  if [[ -n "${PANEL_API_TOKEN:-}" ]]; then
    curl -k -sS --connect-timeout 10 --max-time 30 \
      -H "Authorization: Bearer ${PANEL_API_TOKEN}" \
      -H 'Accept: application/json' \
      "$url"
  else
    curl -k -sS --connect-timeout 10 --max-time 30 \
      -b "$COOKIE_JAR" \
      -H 'X-Requested-With: XMLHttpRequest' \
      -H 'Accept: application/json' \
      "$url"
  fi
}

curl_api_post_json() {
  local url="$1"
  local payload="$2"
  if [[ -n "${PANEL_API_TOKEN:-}" ]]; then
    curl -k -sS --connect-timeout 10 --max-time 30 \
      -H "Authorization: Bearer ${PANEL_API_TOKEN}" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json' \
      -X POST "$url" -d "$payload"
  else
    curl -k -sS --connect-timeout 10 --max-time 30 \
      -b "$COOKIE_JAR" \
      -H 'Content-Type: application/json' \
      -H 'X-Requested-With: XMLHttpRequest' \
      -H 'Accept: application/json' \
      -X POST "$url" -d "$payload"
  fi
}

wait_for_panel() {
  log "等待 3x-ui 面板启动。"
  local code
  for _ in $(seq 1 30); do
    code="$(curl -k -sS --connect-timeout 3 --max-time 5 -o /tmp/oneclick-panel-probe.txt -w '%{http_code}' "${PANEL_LOCAL_URL}/" || true)"
    if [[ "$code" =~ ^(200|301|302|307|308|401|403|404)$ ]]; then
      return 0
    fi
    sleep 2
  done
  fail "XUI_API_FAILED" "3x-ui 面板未在预期时间内启动，无法访问：${PANEL_LOCAL_URL}/"
}

api_login_or_token() {
  COOKIE_JAR="/tmp/3xui-oneclick-cookie.txt"
  rm -f "$COOKIE_JAR"
  wait_for_panel
  if [[ -n "${PANEL_API_TOKEN:-}" ]]; then
    log "使用 3x-ui API Token 调用面板 API。"
    local code
    code="$(curl -k -sS --connect-timeout 10 --max-time 30 -o /tmp/oneclick-api-auth-test.txt -w '%{http_code}' \
      -H "Authorization: Bearer ${PANEL_API_TOKEN}" \
      -H 'Accept: application/json' \
      "${PANEL_LOCAL_URL}/panel/api/inbounds/list" || true)"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    log "API Token 探测未成功，HTTP 状态：$code，将尝试旧版 cookie 登录。"
    PANEL_API_TOKEN=""
  fi

  log "登录 3x-ui API。"
  local csrf response
  csrf="$(curl -k -sS -c "$COOKIE_JAR" "${PANEL_LOCAL_URL}/csrf-token" | jq -r '.csrfToken // .token // empty' 2>/dev/null || true)"
  if [[ -n "$csrf" ]]; then
    response="$(curl -k -sS -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "${PANEL_LOCAL_URL}/login" \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      -H "X-CSRF-Token: ${csrf}" \
      --data-urlencode "username=${PANEL_USER}" \
      --data-urlencode "password=${PANEL_PASS}" || true)"
  else
    response="$(curl -k -sS -b "$COOKIE_JAR" -c "$COOKIE_JAR" -X POST "${PANEL_LOCAL_URL}/login" \
      -H 'Content-Type: application/x-www-form-urlencoded' \
      --data-urlencode "username=${PANEL_USER}" \
      --data-urlencode "password=${PANEL_PASS}" || true)"
  fi
  if ! echo "$response" | jq -e '.success == true or .obj != null' >/dev/null 2>&1; then
    fail "XUI_API_FAILED" "3x-ui API 登录失败，可能是面板账号密码恢复失败或面板尚未启动。响应：$response"
  fi
}

get_x25519_from_api() {
  log "尝试通过 3x-ui API 生成 Reality X25519 密钥。"
  local response private_key public_key
  response="$(curl_api_get "${PANEL_LOCAL_URL}/panel/api/server/getNewX25519Cert" || true)"
  private_key="$(echo "$response" | jq -r '.obj.privateKey // .obj.private_key // .privateKey // .private_key // empty' 2>/dev/null || true)"
  public_key="$(echo "$response" | jq -r '.obj.publicKey // .obj.public_key // .publicKey // .public_key // empty' 2>/dev/null || true)"
  if [[ -n "$private_key" && -n "$public_key" ]]; then
    REALITY_PRIVATE_KEY="$private_key"
    REALITY_PUBLIC_KEY="$public_key"
    return 0
  fi
  return 1
}

get_x25519_from_xray() {
  log "API 生成密钥失败，尝试使用 xray 命令生成 Reality X25519 密钥。"
  local xray_bin output private_key public_key
  xray_bin="$(command -v xray || true)"
  [[ -z "$xray_bin" && -x /usr/local/x-ui/bin/xray-linux-amd64 ]] && xray_bin="/usr/local/x-ui/bin/xray-linux-amd64"
  [[ -z "$xray_bin" && -x /usr/local/x-ui/bin/xray ]] && xray_bin="/usr/local/x-ui/bin/xray"
  [[ -n "$xray_bin" ]] || return 1
  output="$("$xray_bin" x25519 2>/dev/null || true)"
  private_key="$(echo "$output" | awk -F': ' '/Private key/ {print $2; exit}')"
  public_key="$(echo "$output" | awk -F': ' '/Public key/ {print $2; exit}')"
  if [[ -n "$private_key" && -n "$public_key" ]]; then
    REALITY_PRIVATE_KEY="$private_key"
    REALITY_PUBLIC_KEY="$public_key"
    return 0
  fi
  return 1
}

build_vless_link() {
  local encoded_name encoded_sni encoded_pbk encoded_sid encoded_fp
  encoded_name="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$NODE_NAME")"
  encoded_sni="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$SNI")"
  encoded_pbk="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$REALITY_PUBLIC_KEY")"
  encoded_sid="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$SHORT_ID")"
  encoded_fp="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$FINGERPRINT")"
  VLESS_LINK="vless://${CLIENT_UUID}@${PUBLIC_HOST}:${REALITY_PORT}?type=tcp&security=reality&pbk=${encoded_pbk}&fp=${encoded_fp}&sni=${encoded_sni}&sid=${encoded_sid}&spx=%2F&flow=xtls-rprx-vision&encryption=none#${encoded_name}"
}

create_inbound() {
  log "创建 VLESS + TCP + Reality 入站。"
  CLIENT_UUID="$(uuidgen)"
  SHORT_ID="$(openssl rand -hex 8)"
  if ! get_x25519_from_api; then
    get_x25519_from_xray || fail "XUI_API_FAILED" "Reality X25519 密钥生成失败。"
  fi

  local payload response success
  payload="$(jq -n \
    --arg remark "$NODE_NAME" \
    --argjson port "$REALITY_PORT" \
    --arg uuid "$CLIENT_UUID" \
    --arg email "$NODE_NAME" \
    --arg sub_id "$SHORT_ID" \
    --arg target "$TARGET" \
    --arg sni "$SNI" \
    --arg fingerprint "$FINGERPRINT" \
    --arg private_key "$REALITY_PRIVATE_KEY" \
    --arg short_id "$SHORT_ID" \
    '{
      up: 0,
      down: 0,
      total: 0,
      remark: $remark,
      enable: true,
      expiryTime: 0,
      listen: "",
      port: $port,
      protocol: "vless",
      settings: ({
        clients: [{
          id: $uuid,
          flow: "xtls-rprx-vision",
          email: $email,
          limitIp: 0,
          totalGB: 0,
          expiryTime: 0,
          enable: true,
          tgId: "",
          subId: $sub_id
        }],
        decryption: "none",
        fallbacks: []
      } | tostring),
      streamSettings: ({
        network: "tcp",
        security: "reality",
        tcpSettings: {
          acceptProxyProtocol: false,
          header: {type: "none"}
        },
        realitySettings: {
          show: false,
          xver: 0,
          dest: $target,
          serverNames: [$sni],
          privateKey: $private_key,
          minClient: "",
          maxClient: "",
          maxTimediff: 0,
          shortIds: [$short_id],
          settings: {
            publicKey: "",
            fingerprint: $fingerprint,
            serverName: "",
            spiderX: "/"
          }
        }
      } | tostring),
      sniffing: ({
        enabled: true,
        destOverride: ["http", "tls", "quic", "fakedns"],
        metadataOnly: false,
        routeOnly: false
      } | tostring)
    }')"

  response="$(curl_api_post_json "${PANEL_LOCAL_URL}/panel/api/inbounds/add" "$payload" || true)"
  success="$(echo "$response" | jq -r '.success // false' 2>/dev/null || echo false)"
  if [[ "$success" != "true" ]]; then
    fail "INBOUND_CREATE_FAILED" "Reality inbound 创建失败。响应：$response"
  fi
  build_vless_link
  systemctl restart x-ui >/dev/null 2>&1 || true
  sleep 2
}

generate_qr_files() {
  log "生成二维码。"
  echo "$VLESS_LINK" > "$RESULT_DIR/vless-link.txt"
  chmod 600 "$RESULT_DIR/vless-link.txt"
  if ! qrencode -o "$RESULT_DIR/vless-qr.png" "$VLESS_LINK"; then
    fail "QR_FAILED" "VLESS 二维码生成失败。"
  fi
  chmod 600 "$RESULT_DIR/vless-qr.png"
}

try_subscription() {
  log "尝试生成 3x-ui 订阅链接。"
  SUBSCRIPTION_LINK=""
  local sub_port sub_path sub_cert sub_key sub_uri sub_scheme candidate response_code
  sub_port="2096"
  sub_path="/sub/"
  sub_scheme="http"
  sub_uri=""

  if [[ -f /etc/x-ui/x-ui.db ]]; then
    sub_port="$(sqlite3 /etc/x-ui/x-ui.db "select value from settings where key='subPort' limit 1;" 2>/dev/null || true)"
    sub_path="$(sqlite3 /etc/x-ui/x-ui.db "select value from settings where key='subPath' limit 1;" 2>/dev/null || true)"
    sub_cert="$(sqlite3 /etc/x-ui/x-ui.db "select value from settings where key='subCertFile' limit 1;" 2>/dev/null || true)"
    sub_key="$(sqlite3 /etc/x-ui/x-ui.db "select value from settings where key='subKeyFile' limit 1;" 2>/dev/null || true)"
    sub_uri="$(sqlite3 /etc/x-ui/x-ui.db "select value from settings where key='subURI' limit 1;" 2>/dev/null || true)"
  fi

  [[ -n "$sub_port" ]] || sub_port="2096"
  [[ -n "$sub_path" ]] || sub_path="/sub/"
  [[ "$sub_path" == /* ]] || sub_path="/$sub_path"
  [[ "$sub_path" == */ ]] || sub_path="$sub_path/"
  if [[ -n "${sub_cert:-}" && -n "${sub_key:-}" ]]; then
    sub_scheme="https"
  fi

  local candidates=()
  if [[ -n "$sub_uri" ]]; then
    [[ "$sub_uri" == */ ]] || sub_uri="$sub_uri/"
    candidates+=("${sub_uri}${SHORT_ID}")
  fi
  candidates+=(
    "${sub_scheme}://${PUBLIC_HOST}:${sub_port}${sub_path}${SHORT_ID}"
    "https://${PUBLIC_HOST}:${sub_port}${sub_path}${SHORT_ID}"
    "http://${PUBLIC_HOST}:${sub_port}${sub_path}${SHORT_ID}"
    "${PANEL_PUBLIC_URL}/panel/api/clients/subLinks/${SHORT_ID}"
  )

  for candidate in "${candidates[@]}"; do
    response_code="$(curl -k -L -sS -o /tmp/oneclick-sub-test.txt -w '%{http_code}' "$candidate" || true)"
    if [[ "$response_code" =~ ^2 && -s /tmp/oneclick-sub-test.txt ]]; then
      SUBSCRIPTION_LINK="$candidate"
      break
    fi
  done

  if [[ -n "$SUBSCRIPTION_LINK" ]]; then
    echo "$SUBSCRIPTION_LINK" > "$RESULT_DIR/subscription-link.txt"
    chmod 600 "$RESULT_DIR/subscription-link.txt"
    if qrencode -o "$RESULT_DIR/subscription-qr.png" "$SUBSCRIPTION_LINK"; then
      chmod 600 "$RESULT_DIR/subscription-qr.png"
    else
      SUBSCRIPTION_WARNING="订阅链接已生成，但订阅二维码生成失败。"
      rm -f "$RESULT_DIR/subscription-qr.png"
    fi
  else
    SUBSCRIPTION_WARNING="订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。"
    : > "$RESULT_DIR/subscription-link.txt"
    chmod 600 "$RESULT_DIR/subscription-link.txt"
    rm -f "$RESULT_DIR/subscription-qr.png"
  fi
}

write_panel_login() {
  {
    echo "3x-ui 面板地址：$PANEL_PUBLIC_URL"
    echo "3x-ui 面板账号：$PANEL_USER"
    echo "3x-ui 面板密码：$PANEL_PASS"
    echo
    echo "安全提示：面板地址、账号和密码只保存到本地 output 与远程结果目录，请及时修改默认部署后的 root 密码或切换 SSH key。"
  } > "$RESULT_DIR/panel-login.txt"
  chmod 600 "$RESULT_DIR/panel-login.txt"
}

maybe_generate_ssh_key() {
  if [[ "$GENERATE_SSH_KEY" == "1" && ! -f /root/.ssh/id_ed25519 ]]; then
    log "生成 root SSH key。"
    mkdir -p /root/.ssh
    chmod 700 /root/.ssh
    ssh-keygen -t ed25519 -N "" -f /root/.ssh/id_ed25519 -C "3xui-oneclick-$(date +%Y%m%d)" >/dev/null
    chmod 600 /root/.ssh/id_ed25519
    chmod 644 /root/.ssh/id_ed25519.pub
  fi
}

maybe_run_hardening() {
  if [[ "$RUN_HARDENING" != "1" ]]; then
    log "未勾选服务器加固，跳过 harden_after_success.sh。"
    return
  fi
  if [[ -f /root/harden_after_success.sh ]]; then
    log "执行用户主动勾选的服务器加固脚本。"
    bash /root/harden_after_success.sh "$REALITY_PORT" "$PANEL_PORT" || log "服务器加固脚本执行失败，请稍后人工检查。"
  fi
}

main() {
  require_root
  prepare_result_dir
  check_os
  install_dependencies
  verify_dependencies
  json_write "running" "" ""
  enable_bbr
  check_port
  install_3xui
  api_login_or_token
  create_inbound
  generate_qr_files
  try_subscription
  write_panel_login
  maybe_generate_ssh_key
  maybe_run_hardening
  STATUS="success"
  write_report
  json_write "success" "" ""
  log "部署完成。"
}

main "$@"
