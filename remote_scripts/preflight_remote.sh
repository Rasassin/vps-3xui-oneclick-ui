#!/usr/bin/env bash
set -Eeuo pipefail

RESULT_DIR="/root/3xui-oneclick-result"
RESULT_JSON="$RESULT_DIR/preflight-result.json"
RESULT_REPORT="$RESULT_DIR/preflight-report.txt"
REALITY_PORT="${ONECLICK_REALITY_PORT:-443}"
PANEL_PORT="${ONECLICK_PANEL_PORT:-2053}"

mkdir -p "$RESULT_DIR"
chmod 700 "$RESULT_DIR"

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

write_json() {
  local overall="$1"
  local os_name="$2"
  local os_supported="$3"
  local is_root="$4"
  local port_status="$5"
  local xui_status="$6"
  local github_status="$7"
  local notes="$8"
  {
    printf '{\n'
    printf '  "status": "%s",\n' "$(json_escape "$overall")"
    printf '  "os_name": "%s",\n' "$(json_escape "$os_name")"
    printf '  "os_supported": %s,\n' "$os_supported"
    printf '  "is_root": %s,\n' "$is_root"
    printf '  "reality_port": %s,\n' "$REALITY_PORT"
    printf '  "reality_port_status": "%s",\n' "$(json_escape "$port_status")"
    printf '  "panel_port": %s,\n' "$PANEL_PORT"
    printf '  "xui_status": "%s",\n' "$(json_escape "$xui_status")"
    printf '  "github_status": "%s",\n' "$(json_escape "$github_status")"
    printf '  "notes": "%s"\n' "$(json_escape "$notes")"
    printf '}\n'
  } > "$RESULT_JSON"
  chmod 600 "$RESULT_JSON"
}

write_report() {
  {
    echo "VPS 3x-ui 部署前检测报告"
    echo "生成时间：$(date '+%F %T')"
    echo
    echo "系统：$OS_NAME"
    echo "系统支持：$OS_SUPPORTED"
    echo "root 用户：$IS_ROOT"
    echo "Reality 端口：$REALITY_PORT"
    echo "Reality 端口状态：$PORT_STATUS"
    echo "3x-ui 状态：$XUI_STATUS"
    echo "GitHub 连通性：$GITHUB_STATUS"
    echo
    echo "提示：检测只读取服务器状态，不安装软件、不修改配置。"
    [[ -n "$NOTES" ]] && echo "备注：$NOTES"
  } > "$RESULT_REPORT"
  chmod 600 "$RESULT_REPORT"
}

IS_ROOT=false
if [[ "${EUID}" -eq 0 ]]; then
  IS_ROOT=true
fi

OS_NAME="unknown"
OS_SUPPORTED=false
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  OS_NAME="${PRETTY_NAME:-${ID:-unknown} ${VERSION_ID:-}}"
  if [[ "${ID:-}" == "ubuntu" && ( "${VERSION_ID:-}" == "22.04" || "${VERSION_ID:-}" == "24.04" ) ]]; then
    OS_SUPPORTED=true
  elif [[ "${ID:-}" == "debian" && "${VERSION_ID:-}" == "12" ]]; then
    OS_SUPPORTED=true
  fi
fi

PORT_STATUS="unknown"
if command -v ss >/dev/null 2>&1; then
  if ss -ltnH "( sport = :${REALITY_PORT} )" | grep -q .; then
    PORT_STATUS="in_use"
  else
    PORT_STATUS="available"
  fi
elif command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:"${REALITY_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    PORT_STATUS="in_use"
  else
    PORT_STATUS="available"
  fi
fi

XUI_STATUS="not_installed"
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files x-ui.service >/dev/null 2>&1; then
  if systemctl is-active --quiet x-ui; then
    XUI_STATUS="running"
  else
    XUI_STATUS="installed_not_running"
  fi
elif [[ -x /usr/local/x-ui/x-ui ]] || command -v x-ui >/dev/null 2>&1; then
  XUI_STATUS="installed"
fi

GITHUB_STATUS="unknown"
if command -v curl >/dev/null 2>&1; then
  if curl -fsSL --connect-timeout 8 --max-time 12 https://raw.githubusercontent.com/MHSanaei/3x-ui/master/install.sh >/dev/null; then
    GITHUB_STATUS="reachable"
  else
    GITHUB_STATUS="unreachable"
  fi
fi

NOTES=""
STATUS="ok"
if [[ "$IS_ROOT" != true ]]; then
  STATUS="blocked"
  NOTES="请使用 root 用户部署。"
elif [[ "$OS_SUPPORTED" != true ]]; then
  STATUS="blocked"
  NOTES="仅支持 Ubuntu 22.04 / Ubuntu 24.04 / Debian 12。"
elif [[ "$PORT_STATUS" == "in_use" ]]; then
  STATUS="warning"
  NOTES="Reality 端口已被占用，继续部署可能失败；可以换端口。"
elif [[ "$GITHUB_STATUS" == "unreachable" ]]; then
  STATUS="warning"
  NOTES="VPS 到 GitHub 连接失败，安装 3x-ui 可能失败。"
fi

write_json "$STATUS" "$OS_NAME" "$OS_SUPPORTED" "$IS_ROOT" "$PORT_STATUS" "$XUI_STATUS" "$GITHUB_STATUS" "$NOTES"
write_report
cat "$RESULT_JSON"
