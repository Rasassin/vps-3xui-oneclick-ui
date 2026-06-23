#!/usr/bin/env bash
set -Eeuo pipefail

RESULT_DIR="/root/3xui-oneclick-result"
BACKUP_DIR="/root/3xui-oneclick-backups"
RESET_JSON="$RESULT_DIR/reset-result.json"
RESET_REPORT="$RESULT_DIR/reset-report.txt"
CONFIRM="${ONECLICK_RESET_CONFIRM:-}"
UNINSTALL_XUI="${ONECLICK_RESET_UNINSTALL_XUI:-0}"
STAMP="$(date +%Y%m%d-%H%M%S)"

json_escape() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  printf '%s' "$value"
}

write_result() {
  local status="$1"
  local error_code="$2"
  local error_message="$3"
  local backup_path="$4"
  local xui_action="$5"
  local removed_files="$6"
  mkdir -p "$RESULT_DIR"
  chmod 700 "$RESULT_DIR"
  {
    printf '{\n'
    printf '  "status": "%s",\n' "$(json_escape "$status")"
    printf '  "error_code": "%s",\n' "$(json_escape "$error_code")"
    printf '  "error_message": "%s",\n' "$(json_escape "$error_message")"
    printf '  "backup_path": "%s",\n' "$(json_escape "$backup_path")"
    printf '  "xui_action": "%s",\n' "$(json_escape "$xui_action")"
    printf '  "removed_files": "%s",\n' "$(json_escape "$removed_files")"
    printf '  "generated_at": "%s"\n' "$(date '+%F %T')"
    printf '}\n'
  } > "$RESET_JSON"
  chmod 600 "$RESET_JSON"

  {
    echo "VPS 3x-ui oneclick 远程重置报告"
    echo "生成时间：$(date '+%F %T')"
    echo
    echo "状态：$status"
    [[ -n "$error_code" ]] && echo "错误代码：$error_code"
    [[ -n "$error_message" ]] && echo "错误信息：$error_message"
    [[ -n "$backup_path" ]] && echo "备份位置：$backup_path"
    echo "3x-ui 操作：$xui_action"
    echo "已清理文件：$removed_files"
    echo
    echo "说明：本脚本不会修改 VPS root 密码，不会关闭 root 登录、密码登录或 ping。"
  } > "$RESET_REPORT"
  chmod 600 "$RESET_REPORT"
}

fail() {
  local code="$1"
  local message="$2"
  write_result "failed" "$code" "$message" "" "not_requested" ""
  echo "$message"
  exit 1
}

[[ "${EUID}" -eq 0 ]] || fail "NOT_ROOT" "请使用 root 用户执行远程重置。"
[[ "$CONFIRM" == "RESET_3XUI_ONECLICK" ]] || fail "BAD_CONFIRM" "确认短语不正确，远程重置已取消。"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

BACKUP_PATH=""
if [[ -d "$RESULT_DIR" ]]; then
  BACKUP_PATH="$BACKUP_DIR/reset-before-$STAMP.tgz"
  tar -C /root -czf "$BACKUP_PATH" "$(basename "$RESULT_DIR")"
  chmod 600 "$BACKUP_PATH"
  rm -rf "$RESULT_DIR"
fi
mkdir -p "$RESULT_DIR"
chmod 700 "$RESULT_DIR"

REMOVED_FILES=""
for path in /root/install_remote.sh /root/preflight_3xui_oneclick.sh /root/harden_after_success.sh /root/reset_3xui_oneclick.sh; do
  if [[ -e "$path" ]]; then
    rm -f "$path"
    REMOVED_FILES="${REMOVED_FILES}${path} "
  fi
done
REMOVED_FILES="${REMOVED_FILES%% }"

XUI_ACTION="not_requested"
if [[ "$UNINSTALL_XUI" == "1" ]]; then
  XUI_BACKUP="$BACKUP_DIR/x-ui-before-reset-$STAMP.tgz"
  XUI_PATHS=()
  [[ -d /etc/x-ui ]] && XUI_PATHS+=("/etc/x-ui")
  [[ -d /usr/local/x-ui ]] && XUI_PATHS+=("/usr/local/x-ui")
  [[ -f /etc/systemd/system/x-ui.service ]] && XUI_PATHS+=("/etc/systemd/system/x-ui.service")

  if command -v systemctl >/dev/null 2>&1; then
    systemctl stop x-ui >/dev/null 2>&1 || true
    systemctl disable x-ui >/dev/null 2>&1 || true
  fi

  if [[ "${#XUI_PATHS[@]}" -gt 0 ]]; then
    tar -czf "$XUI_BACKUP" "${XUI_PATHS[@]}"
    chmod 600 "$XUI_BACKUP"
    for path in "${XUI_PATHS[@]}"; do
      if [[ -e "$path" ]]; then
        mv "$path" "${path}.disabled-$STAMP"
      fi
    done
    if command -v systemctl >/dev/null 2>&1; then
      systemctl daemon-reload >/dev/null 2>&1 || true
    fi
    XUI_ACTION="disabled_and_archived:$XUI_BACKUP"
  else
    XUI_ACTION="not_found"
  fi
fi

write_result "success" "" "" "$BACKUP_PATH" "$XUI_ACTION" "$REMOVED_FILES"
cat "$RESET_JSON"
