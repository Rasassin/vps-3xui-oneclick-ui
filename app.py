from __future__ import annotations

import html
import secrets
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from deployer.config import NodeConfig, OUTPUT_DIR, VPSLogin
from deployer.deploy_service import ERROR_HINTS, clear_output, deploy
from deployer.result_parser import load_results
from deployer.ssh_runner import DeploymentError, redact


st.set_page_config(page_title="VPS 3x-ui 一键部署器", page_icon="🚀", layout="wide")


def init_state() -> None:
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("last_results", load_results(OUTPUT_DIR))
    st.session_state.setdefault("is_running", False)
    st.session_state.setdefault("reality_port_value", 443)
    st.session_state.setdefault("confirm_redeploy", False)


def append_log(message: str, password: str = "") -> None:
    clean = redact(message, password)
    st.session_state.logs.append(clean)


def render_logs(target=st) -> None:
    log_text = "\n".join(st.session_state.logs[-1000:])
    target.text_area("部署进度", value=log_text, height=320, disabled=True)


def image_exists(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def generate_random_reality_port() -> int:
    return 20_000 + secrets.randbelow(30_001)


def has_success_result(results: dict) -> bool:
    return results.get("status") == "success" and bool(results.get("vless_link"))


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

    st.subheader("3x-ui 面板")
    if panel_url:
        st.link_button("打开 3x-ui 面板", panel_url)
        copy_inline("面板地址", panel_url)
    copy_inline("面板账号", panel_username)
    copy_inline("面板密码", panel_password)
    if panel_username and panel_password:
        copy_box("面板登录信息", f"账号：{panel_username}\n密码：{panel_password}", height=70)
    if panel_login and not (panel_username and panel_password):
        copy_box("3x-ui 面板信息", panel_login, height=130)
    st.caption("浏览器出于跨站安全限制，不能可靠地从本地页面自动填入远程 3x-ui 登录框；请打开面板后复制账号和密码登录。")


def render_results(results: dict) -> None:
    st.subheader("结果")
    vless_link = results.get("vless_link", "")
    subscription_link = results.get("subscription_link", "")
    vless_qr_path = Path(results.get("vless_qr_path", OUTPUT_DIR / "vless-qr.png"))
    subscription_qr_path = Path(results.get("subscription_qr_path", OUTPUT_DIR / "subscription-qr.png"))

    if image_exists(vless_qr_path):
        st.image(str(vless_qr_path), caption="VLESS Reality 节点二维码", width=260)
    elif vless_link:
        st.warning("VLESS 链接已生成，但本地二维码图片不存在。")

    copy_box("vless:// 链接", vless_link, height=100)

    if subscription_link:
        copy_box("订阅链接", subscription_link, height=72)
        if image_exists(subscription_qr_path):
            st.image(str(subscription_qr_path), caption="订阅二维码", width=260)
        else:
            st.warning("订阅链接已生成，但订阅二维码图片不存在。")
    elif vless_link:
        st.info("订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。")

    render_panel_access(results)

    deploy_report = results.get("deploy_report", "")
    if deploy_report:
        st.text_area("部署报告", value=deploy_report, height=260, disabled=True, key="deploy_report_area")

    local_output_dir = results.get("local_output_dir") or str(OUTPUT_DIR)
    st.caption(f"本地结果已保存到：{local_output_dir}")
    st.warning("安全提示：部署完成后请尽快修改 VPS root 密码，或切换为 SSH key 登录。第一版不会默认关闭 root 登录、密码登录或 ping。")


def main() -> None:
    init_state()
    st.title("VPS 3x-ui 一键部署器")
    current_results = st.session_state.last_results or load_results(OUTPUT_DIR)
    existing_success = has_success_result(current_results)
    existing_port = current_results.get("reality_port", "")

    if existing_success:
        st.info(
            f"检测到已有成功部署结果，Reality 端口：{existing_port or '未知'}。"
            "如果只是查看二维码、订阅链接或面板信息，不需要再次点击部署。"
        )

    with st.container(border=True):
        st.subheader("快捷优化")
        port_col, action_col = st.columns([2, 1])
        port_col.caption(
            "Reality 入站端口不一定必须是 443。443 更像普通 HTTPS；如果 443 已被占用，"
            "可以换成随机高位端口，但需要在 VPS 服务商安全组放行对应 TCP 端口。"
        )
        if action_col.button("随机 Reality 端口", disabled=st.session_state.is_running):
            st.session_state.reality_port_value = generate_random_reality_port()
            st.toast(f"已生成端口：{st.session_state.reality_port_value}")
            st.rerun()

    confirm_redeploy = True
    if existing_success:
        confirm_redeploy = st.checkbox(
            "我确认要重新部署。重复使用同一个 Reality 端口可能会因为端口已占用而失败。",
            key="confirm_redeploy",
            disabled=st.session_state.is_running,
        )

    with st.form("deploy_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("VPS 登录信息")
            host = st.text_input("VPS IP", placeholder="例如：1.2.3.4")
            ssh_port = st.number_input("SSH 端口", min_value=1, max_value=65535, value=22, step=1)
            ssh_user = st.text_input("SSH 用户", value="root")
            ssh_password = st.text_input("VPS 密码", type="password")
        with col2:
            st.subheader("节点配置")
            node_name = st.text_input("节点名称", value="auto-reality")
            reality_port = st.number_input(
                "Reality 入站端口",
                min_value=1,
                max_value=65535,
                step=1,
                key="reality_port_value",
            )
            st.caption("如果使用随机端口，请确认 VPS 服务商安全组已放行该 TCP 端口。")
            sni = st.text_input("SNI", value="www.microsoft.com")
            target = st.text_input("Target", value="www.microsoft.com:443")
            fingerprint = st.selectbox("Fingerprint", ["chrome", "firefox", "safari", "ios", "android", "edge", "random"], index=0)

        with st.expander("高级选项", expanded=True):
            panel_port = st.number_input("3x-ui 面板端口", min_value=1, max_value=65535, value=2053, step=1)
            generate_ssh_key = st.checkbox("安装完成后生成 SSH key", value=True)
            run_hardening = st.checkbox("执行服务器加固", value=False)
            st.caption("服务器加固脚本默认不会执行；只有主动勾选时才会运行。第一版不会默认关闭 root 登录、密码登录或 ping。")

        col_a, col_b = st.columns([1, 1])
        start_disabled = st.session_state.is_running or (existing_success and not confirm_redeploy)
        start = col_a.form_submit_button("开始一键部署", type="primary", disabled=start_disabled)
        clear = col_b.form_submit_button("清空本地输出", disabled=st.session_state.is_running)

    if clear:
        clear_output()
        st.session_state.logs = []
        st.session_state.last_results = load_results(OUTPUT_DIR)
        st.success("本地 output/ 已清空。")

    log_placeholder = st.empty()
    render_logs(log_placeholder)

    if start:
        if existing_success and int(reality_port) == int(existing_port or 0):
            st.warning("你正在使用上一轮成功部署相同的 Reality 端口，若服务器上已有入站监听，可能会提示端口占用。")
        st.session_state.is_running = True
        st.session_state.logs = []
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

        def ui_log(line: str) -> None:
            append_log(line, ssh_password)
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

    results = st.session_state.last_results or load_results(OUTPUT_DIR)
    if results.get("vless_link") or results.get("panel_login") or (OUTPUT_DIR / "result.json").exists():
        render_results(results)
    else:
        st.info("填写 VPS IP 和 root 密码后，点击“开始一键部署”。完成后这里会直接显示二维码、链接和面板信息。")


if __name__ == "__main__":
    main()
