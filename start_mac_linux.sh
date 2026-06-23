#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")"

echo "VPS 3x-ui 一键部署器启动器"

if ! command -v python3 >/dev/null 2>&1; then
  echo "启动失败：未找到 python3。请先安装 Python 3.9 或更高版本。"
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "正在创建本地虚拟环境 .venv ..."
  if ! python3 -m venv .venv; then
    echo "启动失败：创建 .venv 失败。请确认 Python venv 模块可用。"
    exit 1
  fi
fi

source .venv/bin/activate
if ! python -m pip install --upgrade pip; then
  echo "启动失败：升级 pip 失败。请检查本机网络或 Python 安装。"
  exit 1
fi
if ! pip install -r requirements.txt; then
  echo "启动失败：安装 requirements.txt 依赖失败。请检查本机网络。"
  exit 1
fi

echo "正在运行本地产品启动前自检，不会连接 VPS ..."
if ! python scripts/check_product_readiness.py; then
  echo "启动失败：产品启动前自检未通过。"
  exit 1
fi

echo "正在启动本地页面 ..."
streamlit run app.py
