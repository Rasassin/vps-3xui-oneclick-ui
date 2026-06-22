#!/usr/bin/env bash
set -Eeuo pipefail

REALITY_PORT="${1:-443}"
PANEL_PORT="${2:-2053}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ufw fail2ban unattended-upgrades

ufw allow OpenSSH
ufw allow "${REALITY_PORT}/tcp"
ufw allow "${PANEL_PORT}/tcp"
ufw --force enable

cat >/etc/sysctl.d/98-3xui-oneclick-hardening.conf <<'EOF'
net.ipv4.tcp_syncookies=1
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.default.rp_filter=1
EOF
sysctl --system >/dev/null || true

systemctl enable --now fail2ban >/dev/null 2>&1 || true
systemctl enable unattended-upgrades >/dev/null 2>&1 || true

echo "服务器加固已执行：已启用 ufw、fail2ban、unattended-upgrades。未关闭 root 登录、密码登录或 ping。"

