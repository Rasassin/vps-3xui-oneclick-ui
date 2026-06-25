from __future__ import annotations

import html
import secrets
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from deployer.config import NodeConfig, OUTPUT_DIR, VPSLogin
from deployer.deploy_service import (
    ERROR_HINTS,
    clear_output,
    deploy,
    download_remote_results,
    preflight,
    reset_remote_oneclick,
)
from deployer.result_parser import load_results
from deployer.ssh_runner import DeploymentError, redact


st.set_page_config(page_title="VPS 3x-ui Oneclick", page_icon="◉", layout="centered")


def init_state() -> None:
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("last_results", load_results(OUTPUT_DIR))
    st.session_state.setdefault("is_running", False)
    st.session_state.setdefault("host_value", "")
    st.session_state.setdefault("ssh_port_value", 22)
    st.session_state.setdefault("ssh_user_value", "root")
    st.session_state.setdefault("node_name_value", "auto-reality")
    st.session_state.setdefault("reality_port_value", 443)
    st.session_state.setdefault("sni_value", "www.microsoft.com")
    st.session_state.setdefault("target_value", "www.microsoft.com:443")
    st.session_state.setdefault("fingerprint_value", "chrome")
    st.session_state.setdefault("panel_port_value", 2053)
    st.session_state.setdefault("generate_ssh_key_value", True)
    st.session_state.setdefault("run_hardening_value", False)
    st.session_state.setdefault("confirm_redeploy", False)
    st.session_state.setdefault("reset_confirm_phrase", "")
    st.session_state.setdefault("reset_uninstall_xui", False)
    st.session_state.setdefault("last_preflight", load_results(OUTPUT_DIR).get("preflight", {}))


def append_log(message: str, password: str = "") -> None:
    clean = redact(message, password)
    st.session_state.logs.append(clean)


def render_logs(target=st) -> None:
    log_text = "\n".join(st.session_state.logs[-1000:])
    target.text_area("技术日志", value=log_text, height=260, disabled=True, key="technical_logs_area")


def apply_product_style() -> None:
    st.markdown(
        """
<style>
  :root {
    color-scheme: light;
  }
  .stApp {
    background:
      radial-gradient(circle at 50% -10%, rgba(255,255,255,0.98), rgba(246,247,249,0.98) 46%, rgba(241,243,246,1) 100%);
  }
  [data-testid="stHeader"] {
    background: transparent;
  }
  [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
    display: none !important;
    visibility: hidden !important;
  }
  .block-container {
    max-width: 980px;
    padding-top: 38px;
    padding-bottom: 72px;
  }
  h1, h2, h3 {
    letter-spacing: 0;
  }
  h1 {
    font-size: 40px !important;
    line-height: 1.08 !important;
    font-weight: 700 !important;
    margin-bottom: 8px !important;
  }
  h2 {
    font-size: 24px !important;
    font-weight: 650 !important;
  }
  h3 {
    font-size: 18px !important;
    font-weight: 650 !important;
  }
  [data-testid="stMetric"] {
    background: rgba(255,255,255,0.72);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 14px;
    padding: 14px 16px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.04);
  }
  [data-testid="stForm"], [data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 18px !important;
  }
  div.stButton > button, div[data-testid="stFormSubmitButton"] button, .stDownloadButton button, .stLinkButton a {
    border-radius: 999px !important;
    min-height: 42px;
    font-weight: 600;
  }
  button[data-testid="stBaseButton-primary"],
  button[data-testid="stBaseButton-primaryFormSubmit"],
  div[data-testid="stFormSubmitButton"] button {
    min-height: 52px;
    font-size: 17px;
    background: #0071e3 !important;
    border: 1px solid #0071e3 !important;
    color: white !important;
    box-shadow: 0 14px 28px rgba(0, 113, 227, 0.20);
  }
  button[data-testid="stBaseButton-primary"]:hover,
  button[data-testid="stBaseButton-primaryFormSubmit"]:hover,
  div[data-testid="stFormSubmitButton"] button:hover {
    background: #0077ed !important;
    border-color: #0077ed !important;
    color: white !important;
  }
  button[data-testid="stBaseButton-primary"]:active,
  button[data-testid="stBaseButton-primaryFormSubmit"]:active,
  div[data-testid="stFormSubmitButton"] button:active {
    background: #006edb !important;
    border-color: #006edb !important;
    color: white !important;
  }
  input, textarea, [data-baseweb="select"] > div {
    border-radius: 12px !important;
  }
  .product-hero {
    text-align: center;
    margin: 4px auto 26px;
  }
  .product-hero p {
    color: #667085;
    font-size: 17px;
    line-height: 1.6;
    margin: 0 auto;
    max-width: 680px;
  }
  .quiet-note {
    color: #667085;
    font-size: 14px;
    line-height: 1.6;
  }
  .status-pill {
    width: fit-content;
    margin: 0 auto 24px;
    padding: 7px 13px;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 999px;
    background: rgba(255,255,255,0.74);
    color: #475467;
    font-size: 14px;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.05);
  }
  .status-pill strong {
    color: #111827;
    font-weight: 650;
  }
  .result-note {
    color: #667085;
    font-size: 13px;
  }
</style>
""",
        unsafe_allow_html=True,
    )


def render_product_hero(existing_success: bool) -> None:
    subtitle = (
        "节点已经就绪。你可以直接扫码、复制链接，或在需要时重新部署。"
        if existing_success
        else "输入 VPS IP 和 root 密码，其余配置可以保持默认。部署完成后直接扫码导入客户端。"
    )
    st.markdown(
        f"""
<div class="product-hero">
  <h1>VPS 3x-ui Oneclick</h1>
  <p>{html.escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_product_status(results: dict, existing_success: bool) -> None:
    if existing_success:
        text = f"已部署 · Reality {html.escape(str(results.get('reality_port', '未知')))}"
        if results.get("subscription_link"):
            text += " · 订阅可用"
        else:
            text += " · 单节点可用"
    elif has_failed_result(results):
        text = f"上次未完成 · {html.escape(str(results.get('error_code', 'UNKNOWN')))}"
    else:
        text = "准备就绪 · 填写 VPS IP 和 root 密码即可开始"
    st.markdown(f'<div class="status-pill"><strong>{text}</strong></div>', unsafe_allow_html=True)


def image_exists(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def generate_random_reality_port() -> int:
    return 20_000 + secrets.randbelow(30_001)


def has_success_result(results: dict) -> bool:
    return results.get("status") == "success" and bool(results.get("vless_link"))


def has_failed_result(results: dict) -> bool:
    return bool(results.get("error_code")) or results.get("status") == "failed"


def recovery_hint(error_code: str) -> str:
    hints = {
        "PORT_IN_USE": "换一个 Reality 入站端口，然后重新部署；如果使用随机端口，记得在 VPS 服务商安全组放行对应 TCP 端口。",
        "SSH_SESSION_LOST": "先不要反复点部署。通常是 VPS 网络到软件源不稳定或 SSH 会话中断；可稍后重试，或先点“重新下载结果”确认远程是否已经生成结果。",
        "XUI_API_FAILED": "3x-ui 已可能安装成功但 API 未完成配置。建议先点“刷新远程状态”，再尝试“重新下载结果”；仍失败时再重新部署。",
        "INBOUND_CREATE_FAILED": "Reality 入站创建失败。可换 Reality 端口，确认 SNI/Target 没有带 http:// 或 https://，再重新部署。",
        "DOWNLOAD_FAILED": "远程可能部署完成但本地下载失败。请点“重新下载结果”，不会重新安装或修改服务器。",
        "GITHUB_DOWNLOAD_FAILED": "VPS 到 GitHub 网络不稳定。稍后重试，或换 VPS 网络环境。",
        "APT_INSTALL_FAILED": "VPS 到 Ubuntu/Debian 软件源网络不稳定。稍后重试，或换软件源/镜像质量更好的 VPS。",
        "UNSUPPORTED_OS": "当前 VPS 系统不在支持范围；只支持 Ubuntu 22.04、Ubuntu 24.04、Debian 12。",
    }
    return hints.get(error_code, "先查看部署报告和实时日志；如果远程可能已生成结果，可以先点“重新下载结果”，避免不必要的重复部署。")


def render_failure_recovery(results: dict) -> None:
    if not has_failed_result(results):
        return
    error_code = str(results.get("error_code") or "UNKNOWN")
    error_message = str(results.get("error_message") or ERROR_HINTS.get(error_code, "上次部署没有完成。"))
    with st.container(border=True):
        st.subheader("失败恢复")
        st.error(f"{error_code}：{error_message}")
        st.info(recovery_hint(error_code))
        action_cols = st.columns(3)
        if action_cols[0].button("为下一次部署随机端口", use_container_width=True, disabled=st.session_state.is_running):
            st.session_state.reality_port_value = generate_random_reality_port()
            st.toast(f"已生成端口：{st.session_state.reality_port_value}")
            st.rerun()
        action_cols[1].caption("可在表单里点“刷新远程状态”，只读检测服务器。")
        action_cols[2].caption("可在表单里点“重新下载结果”，不会重新部署。")


def validate_form_ready(host: str, ssh_user: str, ssh_password: str, action: str) -> bool:
    missing = []
    if not host.strip():
        missing.append("VPS IP")
    if not ssh_user.strip():
        missing.append("SSH 用户")
    if not ssh_password:
        missing.append("VPS 密码")
    if missing:
        st.error(f"{action}前请先填写：{', '.join(missing)}。")
        return False
    return True


def build_login_and_config(
    host: str,
    ssh_port: int,
    ssh_user: str,
    ssh_password: str,
    node_name: str,
    reality_port: int,
    sni: str,
    target: str,
    fingerprint: str,
    panel_port: int,
    generate_ssh_key: bool,
    run_hardening: bool,
) -> tuple[VPSLogin, NodeConfig]:
    login = VPSLogin(host=host.strip(), port=int(ssh_port), username=ssh_user.strip(), password=ssh_password)
    config = NodeConfig(
        node_name=node_name.strip() or "auto-reality",
        reality_port=int(reality_port),
        sni=sni.strip(),
        target=target.strip(),
        fingerprint=fingerprint.strip(),
        panel_port=int(panel_port),
        generate_ssh_key=bool(generate_ssh_key),
        run_hardening=bool(run_hardening),
    )
    return login, config


def copy_box(label: str, value: str, height: int = 120) -> None:
    if not value:
        return
    escaped_value = html.escape(value)
    button_id = f"copy_{abs(hash((label, value))) % 10_000_000}"
    components.html(
        f"""
        <div style="font-family: sans-serif;">
          <label style="font-size: 0.9rem; font-weight: 600;">{html.escape(label)}</label>
          <textarea id="{button_id}_text" readonly style="width: 100%; height: {height}px; margin-top: 6px; border: 1px solid #d7dce2; border-radius: 6px; padding: 8px; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">{escaped_value}</textarea>
          <button id="{button_id}" style="margin-top: 8px; padding: 6px 10px; border: 1px solid #c8d0d9; border-radius: 6px; background: #fff; cursor: pointer;">复制</button>
          <span id="{button_id}_ok" style="margin-left: 8px; color: #18794e;"></span>
          <script>
            const btn = document.getElementById("{button_id}");
            btn.onclick = async () => {{
              const text = document.getElementById("{button_id}_text").value;
              await navigator.clipboard.writeText(text);
              document.getElementById("{button_id}_ok").innerText = "已复制";
              setTimeout(() => document.getElementById("{button_id}_ok").innerText = "", 1600);
            }};
          </script>
        </div>
        """,
        height=height + 80,
    )


def copy_inline(label: str, value: str) -> None:
    if not value:
        return
    button_id = f"copy_inline_{abs(hash((label, value))) % 10_000_000}"
    components.html(
        f"""
        <div style="display:flex; align-items:center; gap:8px; font-family:sans-serif; margin:4px 0;">
          <span style="min-width:86px; font-weight:600;">{html.escape(label)}</span>
          <code style="flex:1; padding:6px 8px; border:1px solid #d7dce2; border-radius:6px; overflow:auto;">{html.escape(value)}</code>
          <button id="{button_id}" style="padding:6px 10px; border:1px solid #c8d0d9; border-radius:6px; background:#fff; cursor:pointer;">复制</button>
          <span id="{button_id}_ok" style="color:#18794e;"></span>
          <script>
            document.getElementById("{button_id}").onclick = async () => {{
              await navigator.clipboard.writeText({value!r});
              document.getElementById("{button_id}_ok").innerText = "已复制";
              setTimeout(() => document.getElementById("{button_id}_ok").innerText = "", 1600);
            }};
          </script>
        </div>
        """,
        height=48,
    )


def render_preflight(preflight_result: dict) -> None:
    if not preflight_result:
        return
    status = preflight_result.get("status", "unknown")
    status_text = {
        "ok": "通过",
        "warning": "有提醒",
        "blocked": "阻塞",
    }.get(status, status)
    st.markdown("**服务器检测结果**")
    cols = st.columns(5)
    cols[0].metric("检测状态", status_text)
    cols[1].metric("系统", preflight_result.get("os_name", "unknown"))
    cols[2].metric("Reality 端口", preflight_result.get("reality_port_status", "unknown"))
    cols[3].metric("3x-ui", preflight_result.get("xui_status", "unknown"))
    cols[4].metric("GitHub", preflight_result.get("github_status", "unknown"))
    notes = preflight_result.get("notes", "")
    if status == "blocked":
        st.error(notes or "检测发现阻塞项，请先处理后再部署。")
    elif status == "warning":
        st.warning(notes or "检测发现提醒项，继续部署前建议确认。")
    else:
        st.success("检测通过，可以继续部署。")


def render_panel_access(results: dict) -> None:
    panel_url = results.get("panel_url", "")
    panel_username = results.get("panel_username", "")
    panel_password = results.get("panel_password", "")
    panel_login = results.get("panel_login", "")

    if not panel_url and panel_login:
        for line in panel_login.splitlines():
            if "面板地址：" in line:
                panel_url = line.split("面板地址：", 1)[1].strip()
            elif "面板账号：" in line:
                panel_username = line.split("面板账号：", 1)[1].strip()
            elif "面板密码：" in line:
                panel_password = line.split("面板密码：", 1)[1].strip()

    if not (panel_url or panel_username or panel_password or panel_login):
        return

    st.markdown("**3x-ui 面板**")
    if panel_url:
        st.link_button("打开 3x-ui 面板", panel_url, use_container_width=True)
        copy_inline("面板地址", panel_url)
    copy_inline("面板账号", panel_username)
    copy_inline("面板密码", panel_password)
    if panel_username and panel_password:
        copy_box("面板登录信息", f"账号：{panel_username}\n密码：{panel_password}", height=70)
    if panel_login and not (panel_username and panel_password):
        copy_box("3x-ui 面板信息", panel_login, height=130)
    st.caption("浏览器出于跨站安全限制，不能可靠地从本地页面自动填入远程 3x-ui 登录框；请打开面板后复制账号和密码登录。")


def render_reset_result(results: dict) -> None:
    reset_result = results.get("reset", {})
    reset_report = results.get("reset_report", "")
    if not reset_result and not reset_report:
        return
    st.subheader("远程重置结果")
    status = reset_result.get("status", "unknown")
    if status == "success":
        st.success("远程重置已完成。")
    else:
        st.error(reset_result.get("error_message") or "远程重置没有完成。")
    backup_path = reset_result.get("backup_path", "")
    xui_action = reset_result.get("xui_action", "")
    cols = st.columns(3)
    cols[0].metric("状态", status)
    cols[1].metric("远程备份", "已生成" if backup_path else "无")
    cols[2].metric("3x-ui", xui_action or "not_requested")
    if backup_path:
        st.info(f"远程备份位置：{backup_path}")
    if reset_report:
        st.text_area("远程重置报告", value=reset_report, height=220, disabled=True, key="reset_report_area")


def render_results(results: dict) -> None:
    render_reset_result(results)
    if not (results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists()):
        return
    st.subheader("连接")
    vless_link = results.get("vless_link", "")
    subscription_link = results.get("subscription_link", "")
    vless_qr_path = Path(results.get("vless_qr_path", OUTPUT_DIR / "vless-qr.png"))
    subscription_qr_path = Path(results.get("subscription_qr_path", OUTPUT_DIR / "subscription-qr.png"))

    primary_col, secondary_col = st.columns([1, 1], vertical_alignment="top")
    with primary_col:
        with st.container(border=True):
            st.markdown("**推荐订阅**")
            if subscription_link:
                if image_exists(subscription_qr_path):
                    st.image(str(subscription_qr_path), caption="订阅二维码", width=240)
                else:
                    st.warning("订阅链接已生成，但订阅二维码图片不存在。")
                copy_box("订阅链接", subscription_link, height=76)
            elif vless_link:
                st.info("订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。")
                if image_exists(vless_qr_path):
                    st.image(str(vless_qr_path), caption="VLESS Reality 节点二维码", width=240)
                copy_box("vless:// 链接", vless_link, height=100)

    with secondary_col:
        with st.container(border=True):
            st.markdown("**单节点备用**")
            if image_exists(vless_qr_path):
                st.image(str(vless_qr_path), caption="VLESS Reality 节点二维码", width=240)
            elif vless_link:
                st.warning("VLESS 链接已生成，但本地二维码图片不存在。")
            copy_box("vless:// 链接", vless_link, height=100)

    with st.expander("面板登录信息", expanded=False):
        render_panel_access(results)

    deploy_report = results.get("deploy_report", "")
    if deploy_report:
        with st.expander("部署报告", expanded=False):
            st.text_area("部署报告", value=deploy_report, height=260, disabled=True, key="deploy_report_area")

    local_output_dir = results.get("local_output_dir") or str(OUTPUT_DIR)
    st.markdown(f'<p class="result-note">结果已自动保存到本机：{html.escape(local_output_dir)}</p>', unsafe_allow_html=True)
    st.warning("部署完成后请尽快修改 VPS root 密码，或切换为 SSH key 登录。")


def main() -> None:
    init_state()
    apply_product_style()
    current_results = st.session_state.last_results or load_results(OUTPUT_DIR)
    existing_success = has_success_result(current_results)
    existing_port = current_results.get("reality_port", "")

    render_product_hero(existing_success)
    render_product_status(current_results, existing_success)
    if has_failed_result(current_results):
        render_failure_recovery(current_results)

    confirm_redeploy = True
    with st.form("deploy_form"):
        st.subheader("部署")
        host = st.text_input("VPS IP", placeholder="例如：1.2.3.4", key="host_value")
        ssh_password = st.text_input("root 密码", type="password", help="只保存在当前页面会话内存，不写入日志或文件。")

        with st.expander("高级设置", expanded=False):
            top_cols = st.columns(3)
            with top_cols[0]:
                ssh_port = st.number_input("SSH 端口", min_value=1, max_value=65535, step=1, key="ssh_port_value")
            with top_cols[1]:
                ssh_user = st.text_input("SSH 用户", key="ssh_user_value")
            with top_cols[2]:
                panel_port = st.number_input("3x-ui 面板端口", min_value=1, max_value=65535, step=1, key="panel_port_value")
            config_cols = st.columns(2)
            with config_cols[0]:
                node_name = st.text_input("节点名称", key="node_name_value")
                reality_port = st.number_input(
                    "Reality 入站端口",
                    min_value=1,
                    max_value=65535,
                    step=1,
                    key="reality_port_value",
                )
            with config_cols[1]:
                sni = st.text_input("SNI", key="sni_value")
                target = st.text_input("Target", key="target_value")
            fingerprint = st.selectbox(
                "Fingerprint",
                ["chrome", "firefox", "safari", "ios", "android", "edge", "random"],
                key="fingerprint_value",
            )
            setting_cols = st.columns(2)
            with setting_cols[0]:
                generate_ssh_key = st.checkbox("安装完成后生成 SSH key", key="generate_ssh_key_value")
            with setting_cols[1]:
                run_hardening = st.checkbox("执行服务器加固", key="run_hardening_value")
            st.caption("默认值适合第一次使用。若 443 被占用，可换高位端口，并在 VPS 服务商安全组放行对应 TCP 端口。")

        if existing_success:
            confirm_redeploy = st.checkbox(
                "重新部署",
                key="confirm_redeploy",
                disabled=st.session_state.is_running,
            )

        start_disabled = st.session_state.is_running or (existing_success and not confirm_redeploy)
        start = st.form_submit_button("开始一键部署", type="primary", disabled=start_disabled, use_container_width=True)

        with st.expander("更多操作", expanded=False):
            st.caption("只在需要排错、换端口或重新整理结果时使用。")
            maintenance_cols = st.columns(4)
            check = maintenance_cols[0].form_submit_button("检测服务器", disabled=st.session_state.is_running)
            redownload = maintenance_cols[1].form_submit_button("重新下载结果", disabled=st.session_state.is_running)
            clear = maintenance_cols[2].form_submit_button("清空本机结果", disabled=st.session_state.is_running)
            random_port = maintenance_cols[3].form_submit_button("随机端口", disabled=st.session_state.is_running)
            st.divider()
            st.caption("危险操作：远程重置只在需要清理 oneclick 结果或停用 3x-ui 时使用。")
            reset_confirm_phrase = st.text_input(
                "远程重置确认短语",
                key="reset_confirm_phrase",
                placeholder="输入 RESET_3XUI_ONECLICK 才能执行",
            )
            reset_uninstall_xui = st.checkbox(
                "同时停用并归档 3x-ui",
                key="reset_uninstall_xui",
            )
            remote_reset = st.form_submit_button("执行远程重置", disabled=st.session_state.is_running)

        if "ssh_port" not in locals():
            ssh_port = st.session_state.ssh_port_value
        if "ssh_user" not in locals():
            ssh_user = st.session_state.ssh_user_value
        if "panel_port" not in locals():
            panel_port = st.session_state.panel_port_value
        if "node_name" not in locals():
            node_name = st.session_state.node_name_value
        if "reality_port" not in locals():
            reality_port = st.session_state.reality_port_value
        if "sni" not in locals():
            sni = st.session_state.sni_value
        if "target" not in locals():
            target = st.session_state.target_value
        if "fingerprint" not in locals():
            fingerprint = st.session_state.fingerprint_value
        if "generate_ssh_key" not in locals():
            generate_ssh_key = st.session_state.generate_ssh_key_value
        if "run_hardening" not in locals():
            run_hardening = st.session_state.run_hardening_value
        if "reset_confirm_phrase" not in locals():
            reset_confirm_phrase = st.session_state.reset_confirm_phrase
        if "reset_uninstall_xui" not in locals():
            reset_uninstall_xui = st.session_state.reset_uninstall_xui
        if "remote_reset" not in locals():
            remote_reset = False
        if "random_port" not in locals():
            random_port = False

    if random_port:
        st.session_state.reality_port_value = generate_random_reality_port()
        st.toast(f"已生成端口：{st.session_state.reality_port_value}")
        st.rerun()

    if clear:
        clear_output()
        st.session_state.logs = []
        st.session_state.last_results = load_results(OUTPUT_DIR)
        st.session_state.last_preflight = {}
        st.success("本机结果已清空。")

    log_placeholder = st.empty()
    if st.session_state.logs:
        with st.expander("开发者日志", expanded=False):
            log_placeholder = st.empty()
            render_logs(log_placeholder)

    if check:
        if not validate_form_ready(host, ssh_user, ssh_password, "刷新远程状态"):
            render_preflight(st.session_state.last_preflight or (st.session_state.last_results or {}).get("preflight", {}))
            results = st.session_state.last_results or load_results(OUTPUT_DIR)
            if results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists():
                render_results(results)
            return
        st.session_state.is_running = True
        st.session_state.logs = []
        login, config = build_login_and_config(
            host,
            int(ssh_port),
            ssh_user,
            ssh_password,
            node_name,
            int(reality_port),
            sni,
            target,
            fingerprint,
            int(panel_port),
            bool(generate_ssh_key),
            bool(run_hardening),
        )

        def ui_log(line: str) -> None:
            append_log(line, ssh_password)

        try:
            ui_log("开始部署前检测。检测只读取服务器状态，不安装软件、不修改配置。")
            preflight_result = preflight(login, config, ui_log)
            st.session_state.last_preflight = preflight_result
            st.session_state.last_results = load_results(OUTPUT_DIR)
            ui_log("部署前检测完成。")
            st.success("部署前检测完成。")
        except DeploymentError as exc:
            append_log(f"错误：{exc.message}", ssh_password)
            hint = ERROR_HINTS.get(exc.code, exc.message)
            st.error(hint)
        except Exception as exc:  # noqa: BLE001
            append_log(f"未知错误：{exc}", ssh_password)
            st.error(f"检测失败：{exc}")
        finally:
            st.session_state.is_running = False

    if redownload:
        if not validate_form_ready(host, ssh_user, ssh_password, "重新下载结果"):
            render_preflight(st.session_state.last_preflight or (st.session_state.last_results or {}).get("preflight", {}))
            results = st.session_state.last_results or load_results(OUTPUT_DIR)
            if results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists():
                render_results(results)
            return
        st.session_state.is_running = True
        st.session_state.logs = []
        login = VPSLogin(host=host.strip(), port=int(ssh_port), username=ssh_user.strip(), password=ssh_password)

        def ui_log(line: str) -> None:
            append_log(line, ssh_password)

        try:
            ui_log("开始从远程重新下载结果文件。不会重新部署，也不会修改 3x-ui 配置。")
            results = download_remote_results(login, ui_log)
            st.session_state.last_results = results
            st.session_state.last_preflight = results.get("preflight", {})
            ui_log("远程结果文件已重新下载到本地 output/。")
            st.success("远程结果已重新下载。")
        except DeploymentError as exc:
            append_log(f"错误：{exc.message}", ssh_password)
            hint = ERROR_HINTS.get(exc.code, exc.message)
            st.error(hint)
        except Exception as exc:  # noqa: BLE001
            append_log(f"未知错误：{exc}", ssh_password)
            st.error(f"重新下载失败：{exc}")
        finally:
            st.session_state.is_running = False

    if remote_reset:
        if not validate_form_ready(host, ssh_user, ssh_password, "远程重置"):
            render_preflight(st.session_state.last_preflight or (st.session_state.last_results or {}).get("preflight", {}))
            results = st.session_state.last_results or load_results(OUTPUT_DIR)
            if results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists():
                render_results(results)
            return
        st.session_state.is_running = True
        st.session_state.logs = []
        login = VPSLogin(host=host.strip(), port=int(ssh_port), username=ssh_user.strip(), password=ssh_password)

        def ui_log(line: str) -> None:
            append_log(line, ssh_password)

        try:
            ui_log("开始远程重置。将先备份远程结果目录，再执行清理；不会修改 VPS root 密码。")
            results = reset_remote_oneclick(
                login,
                confirm_phrase=reset_confirm_phrase,
                uninstall_xui=bool(reset_uninstall_xui),
                log=ui_log,
            )
            st.session_state.last_results = results
            st.session_state.last_preflight = {}
            ui_log("远程重置完成。本地旧二维码和链接已清空。")
            st.success("远程重置完成。")
        except DeploymentError as exc:
            append_log(f"错误：{exc.message}", ssh_password)
            st.session_state.last_results = load_results(OUTPUT_DIR)
            hint = ERROR_HINTS.get(exc.code, exc.message)
            st.error(hint)
        except Exception as exc:  # noqa: BLE001
            append_log(f"未知错误：{exc}", ssh_password)
            st.session_state.last_results = load_results(OUTPUT_DIR)
            st.error(f"远程重置失败：{exc}")
        finally:
            st.session_state.is_running = False

    if start:
        if not validate_form_ready(host, ssh_user, ssh_password, "开始部署"):
            render_preflight(st.session_state.last_preflight or (st.session_state.last_results or {}).get("preflight", {}))
            results = st.session_state.last_results or load_results(OUTPUT_DIR)
            if results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists():
                render_results(results)
            return
        if existing_success and int(reality_port) == int(existing_port or 0):
            st.warning("你正在使用上一轮成功部署相同的 Reality 端口，若服务器上已有入站监听，可能会提示端口占用。")
        st.session_state.is_running = True
        st.session_state.logs = []
        login, config = build_login_and_config(
            host,
            int(ssh_port),
            ssh_user,
            ssh_password,
            node_name,
            int(reality_port),
            sni,
            target,
            fingerprint,
            int(panel_port),
            bool(generate_ssh_key),
            bool(run_hardening),
        )

        def ui_log(line: str) -> None:
            append_log(line, ssh_password)

        try:
            ui_log("开始部署。VPS 密码只保存在当前页面会话内存，不会写入日志或 output。")
            results = deploy(login, config, ui_log)
            st.session_state.last_results = results
            ui_log("部署完成，结果已下载到本地 output/。")
            st.success("部署完成。")
        except DeploymentError as exc:
            append_log(f"错误：{exc.message}", ssh_password)
            st.session_state.last_results = load_results(OUTPUT_DIR)
            hint = ERROR_HINTS.get(exc.code, exc.message)
            st.error(hint)
        except Exception as exc:  # noqa: BLE001
            append_log(f"未知错误：{exc}", ssh_password)
            st.session_state.last_results = load_results(OUTPUT_DIR)
            st.error(f"部署失败：{exc}")
        finally:
            st.session_state.is_running = False

    results = st.session_state.last_results or load_results(OUTPUT_DIR)
    preflight_data = st.session_state.last_preflight or results.get("preflight", {})
    if preflight_data:
        with st.expander("服务器检测结果", expanded=False):
            render_preflight(preflight_data)
    if (
        results.get("vless_link")
        or results.get("panel_login")
        or results.get("reset")
        or (OUTPUT_DIR / "result.json").exists()
    ):
        render_results(results)


if __name__ == "__main__":
    main()
