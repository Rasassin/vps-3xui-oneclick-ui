from __future__ import annotations

import html
import secrets
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from deployer.config import APP_VERSION, NodeConfig, OUTPUT_DIR, VPSLogin
from deployer.diagnostics_service import build_public_diagnostics_zip, collect_local_diagnostics
from deployer.deploy_service import (
    ERROR_HINTS,
    backup_remote_results,
    clear_output,
    deploy,
    download_remote_results,
    preflight,
    reset_remote_oneclick,
)
from deployer.export_service import build_export_zip
from deployer.profile_service import delete_profile, load_profiles, upsert_profile
from deployer.qr_service import regenerate_output_qrs
from deployer.release_status import collect_release_artifacts, load_release_source_summary, release_artifacts_ready
from deployer.result_parser import load_results
from deployer.ssh_runner import DeploymentError, redact
from deployer.update_service import check_latest_release


st.set_page_config(page_title="VPS 3x-ui 一键部署器", page_icon="🚀", layout="wide")


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
    st.session_state.setdefault("export_zip_path", "")
    st.session_state.setdefault("last_remote_backup", "")
    st.session_state.setdefault("local_diagnostics", {})
    st.session_state.setdefault("diagnostics_zip_path", "")
    st.session_state.setdefault("update_status", {})
    st.session_state.setdefault("profile_name_input", "")
    st.session_state.setdefault("selected_profile_name", "")


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


def has_failed_result(results: dict) -> bool:
    return bool(results.get("error_code")) or results.get("status") == "failed"


def render_readiness_summary(results: dict, existing_success: bool) -> None:
    st.subheader("当前状态")
    cols = st.columns(4)
    if existing_success:
        cols[0].metric("本地结果", "已有可用节点")
        cols[1].metric("Reality 端口", results.get("reality_port", "未知"))
        cols[2].metric("订阅", "已生成" if results.get("subscription_link") else "单节点可用")
        cols[3].metric("建议操作", "查看结果")
    elif has_failed_result(results):
        cols[0].metric("本地结果", "上次失败")
        cols[1].metric("错误代码", results.get("error_code", "unknown"))
        cols[2].metric("VLESS", "有链接" if results.get("vless_link") else "未生成")
        cols[3].metric("建议操作", "看恢复提示")
    else:
        cols[0].metric("本地结果", "未部署")
        cols[1].metric("输入", "IP + 密码")
        cols[2].metric("预检", "建议先跑")
        cols[3].metric("下一步", "开始部署")


def render_first_run_guide(existing_success: bool) -> None:
    if existing_success:
        return
    with st.expander("部署前快速确认", expanded=True):
        st.markdown(
            """
- 你只需要填写 VPS IP 和 VPS 密码；密码不会保存到项目文件、日志或 output。
- 建议先点“刷新远程状态”，它只读取服务器状态，不会安装软件或修改配置。
- Reality 端口默认 443；如果被占用，可以点“随机 Reality 端口”，并在 VPS 服务商安全组放行对应 TCP 端口。
- 服务器加固默认不执行；只有你主动勾选时才会运行。
"""
        )


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


def render_sidebar() -> None:
    with st.sidebar:
        st.subheader("产品信息")
        st.caption(f"版本：v{APP_VERSION}")
        st.link_button("GitHub 仓库", "https://github.com/Rasassin/vps-3xui-oneclick-ui", use_container_width=True)
        update_cols = st.columns([1, 1])
        if update_cols[0].button("检查更新", use_container_width=True):
            st.session_state.update_status = check_latest_release().to_dict()
        update_cols[1].caption("只访问 GitHub，不连接 VPS。")
        update_status = st.session_state.get("update_status", {})
        if update_status:
            if update_status.get("error"):
                st.warning(update_status["error"])
            elif update_status.get("is_newer"):
                st.success(f"发现新版本：{update_status.get('latest_version')}")
                release_url = update_status.get("release_url", "")
                if release_url:
                    st.link_button("打开最新版 Release", release_url, use_container_width=True)
            else:
                latest = update_status.get("latest_version") or f"v{APP_VERSION}"
                st.info(f"当前已是最新版本：{latest}")
        with st.expander("隐私与数据边界"):
            st.markdown(
                """
- VPS 密码只保存在当前页面会话内存，不写入日志、配置档、诊断包或 output。
- `output/` 可能包含节点链接、二维码、订阅链接和面板信息，请当作敏感文件。
- 本地配置档只保存常用参数，不保存 VPS 密码。
- 公开诊断包会排除节点链接、二维码、订阅链接、面板账号密码和 VPS root 密码。
- “检查更新”只访问 GitHub Release 信息，不连接 VPS，也不上传本地诊断。
- 只有点击部署、预检、重新下载或远程备份这类按钮时，才会通过 SSH 连接 VPS。
"""
            )
            st.caption("完整说明见 docs/privacy.md。")
        with st.expander("发布包状态"):
            artifacts = collect_release_artifacts()
            if release_artifacts_ready():
                st.success("当前版本发布产物已生成。")
            else:
                st.info("需要发布时运行：python3 scripts/prepare_release.py --allow-dirty")
            source = load_release_source_summary()
            if source:
                st.caption(
                    f"来源：{source.git_branch} · {source.short_commit} · 工作区{source.dirty_label}"
                )
                if source.is_dirty:
                    st.warning("当前发布产物来自未提交工作区，只建议本地测试，不建议作为正式 GitHub Release 发布。")
                if source.is_stale:
                    st.warning(
                        "当前发布产物来自旧代码："
                        f"{source.short_commit}，本地当前代码是 {source.current_short_commit}。"
                        "正式发布前请重新运行 python3 scripts/prepare_release.py --allow-dirty。"
                    )
            for artifact in artifacts:
                status = "已生成" if artifact.exists else "未生成"
                st.caption(f"{status} · {artifact.label} · {artifact.display_size}")
                if artifact.exists:
                    st.download_button(
                        f"下载{artifact.label}",
                        data=artifact.path.read_bytes(),
                        file_name=artifact.path.name,
                        mime=artifact.mime_type,
                        key=f"release_artifact_{artifact.path.name}",
                        use_container_width=True,
                    )
        st.divider()
        render_profiles_sidebar()
        st.divider()
        st.subheader("本地诊断")
        if st.button("运行本地自检", use_container_width=True):
            st.session_state.local_diagnostics = collect_local_diagnostics(OUTPUT_DIR)
        if st.button("生成公开诊断包", use_container_width=True):
            zip_path = build_public_diagnostics_zip(OUTPUT_DIR)
            st.session_state.diagnostics_zip_path = str(zip_path)
            st.session_state.local_diagnostics = collect_local_diagnostics(OUTPUT_DIR)
            st.toast("公开诊断包已生成。")

        diagnostics = st.session_state.get("local_diagnostics", {})
        if diagnostics:
            deps = diagnostics.get("dependencies", {})
            files = diagnostics.get("files", {})
            missing_deps = [name for name, ok in deps.items() if not ok]
            missing_files = [name for name, info in files.items() if not info.get("exists")]
            if missing_deps or missing_files:
                st.warning("本地自检发现问题。")
                if missing_deps:
                    st.caption(f"缺少依赖：{', '.join(missing_deps)}")
                if missing_files:
                    st.caption(f"缺少文件：{', '.join(missing_files)}")
            else:
                st.success("本地自检通过。")

        diagnostics_zip_path = st.session_state.get("diagnostics_zip_path", "")
        if diagnostics_zip_path and Path(diagnostics_zip_path).exists():
            st.caption("公开诊断包不包含节点链接、二维码、订阅链接、面板账号密码或 VPS root 密码。")
            st.download_button(
                "下载公开诊断包",
                data=Path(diagnostics_zip_path).read_bytes(),
                file_name=Path(diagnostics_zip_path).name,
                mime="application/zip",
                use_container_width=True,
            )


def current_profile_from_state() -> dict:
    return {
        "host": st.session_state.get("host_value", "").strip(),
        "ssh_port": int(st.session_state.get("ssh_port_value", 22)),
        "ssh_user": st.session_state.get("ssh_user_value", "root").strip(),
        "node_name": st.session_state.get("node_name_value", "auto-reality").strip() or "auto-reality",
        "reality_port": int(st.session_state.get("reality_port_value", 443)),
        "sni": st.session_state.get("sni_value", "www.microsoft.com").strip(),
        "target": st.session_state.get("target_value", "www.microsoft.com:443").strip(),
        "fingerprint": st.session_state.get("fingerprint_value", "chrome"),
        "panel_port": int(st.session_state.get("panel_port_value", 2053)),
        "generate_ssh_key": bool(st.session_state.get("generate_ssh_key_value", True)),
        "run_hardening": bool(st.session_state.get("run_hardening_value", False)),
    }


def apply_profile_to_state(profile: dict) -> None:
    field_to_key = {
        "host": "host_value",
        "ssh_port": "ssh_port_value",
        "ssh_user": "ssh_user_value",
        "node_name": "node_name_value",
        "reality_port": "reality_port_value",
        "sni": "sni_value",
        "target": "target_value",
        "fingerprint": "fingerprint_value",
        "panel_port": "panel_port_value",
        "generate_ssh_key": "generate_ssh_key_value",
        "run_hardening": "run_hardening_value",
    }
    for field, state_key in field_to_key.items():
        if field in profile:
            st.session_state[state_key] = profile[field]


def render_profiles_sidebar() -> None:
    st.subheader("本地配置档")
    profiles = load_profiles()
    profile_names = sorted(profiles)
    options = [""] + profile_names
    if st.session_state.selected_profile_name not in options:
        st.session_state.selected_profile_name = ""
    selected = st.selectbox(
        "选择配置档",
        options,
        format_func=lambda item: item or "未选择",
        key="selected_profile_name",
    )

    col_load, col_delete = st.columns(2)
    if col_load.button("载入", disabled=not selected, use_container_width=True):
        apply_profile_to_state(profiles[selected])
        st.toast(f"已载入配置档：{selected}")
        st.rerun()
    if col_delete.button("删除", disabled=not selected, use_container_width=True):
        delete_profile(selected)
        st.session_state.selected_profile_name = ""
        st.toast(f"已删除配置档：{selected}")
        st.rerun()

    st.text_input("配置档名称", key="profile_name_input", placeholder="例如：my-vps")
    if st.button("保存当前配置", use_container_width=True):
        try:
            upsert_profile(st.session_state.profile_name_input, current_profile_from_state())
            st.session_state.selected_profile_name = st.session_state.profile_name_input.strip()
            st.success("配置档已保存，不包含 VPS 密码。")
        except ValueError as exc:
            st.error(str(exc))
    st.caption("配置档只保存在本机 data/，不会保存 VPS 密码；VPS IP 等环境信息也不会提交到 GitHub。")


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


def render_management_mode(results: dict) -> None:
    if not has_success_result(results):
        return
    st.subheader("管理模式")
    status_cols = st.columns(4)
    status_cols[0].metric("部署状态", "可用")
    status_cols[1].metric("Reality 端口", results.get("reality_port", "未知"))
    status_cols[2].metric("节点名称", results.get("node_name", "auto-reality"))
    status_cols[3].metric("订阅", "已生成" if results.get("subscription_link") else "单节点")

    actions = st.columns(4)
    panel_url = results.get("panel_url", "")
    if panel_url:
        actions[0].link_button("打开 3x-ui 面板", panel_url, use_container_width=True)
    else:
        actions[0].button("打开 3x-ui 面板", disabled=True, use_container_width=True)
    if actions[1].button("生成导出配置包", use_container_width=True):
        zip_path = build_export_zip(OUTPUT_DIR)
        st.session_state.export_zip_path = str(zip_path)
        st.toast("导出配置包已生成。")
    if actions[2].button("重建本地二维码", use_container_width=True):
        regenerated = regenerate_output_qrs(OUTPUT_DIR)
        st.session_state.last_results = load_results(OUTPUT_DIR)
        if regenerated:
            st.toast(f"已重建 {len(regenerated)} 个二维码。")
        else:
            st.warning("没有可用于重建二维码的链接。")
    actions[3].button("远程重置/卸载", disabled=True, use_container_width=True)
    st.caption("远程重置/卸载属于危险操作，请在下方表单的“高级选项”里输入确认短语后执行。")

    export_zip_path = st.session_state.get("export_zip_path", "")
    if export_zip_path and Path(export_zip_path).exists():
        st.warning("导出配置包包含节点链接、订阅链接和面板信息，请只保存在你信任的位置。")
        st.download_button(
            "下载导出配置包",
            data=Path(export_zip_path).read_bytes(),
            file_name=Path(export_zip_path).name,
            mime="application/zip",
            use_container_width=True,
        )
    if st.session_state.get("last_remote_backup"):
        st.info(f"最近一次远程备份位置：{st.session_state.last_remote_backup}")


def render_preflight(preflight_result: dict) -> None:
    if not preflight_result:
        return
    status = preflight_result.get("status", "unknown")
    status_text = {
        "ok": "通过",
        "warning": "有提醒",
        "blocked": "阻塞",
    }.get(status, status)
    st.subheader("部署前检测")
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
    st.subheader("结果")
    vless_link = results.get("vless_link", "")
    subscription_link = results.get("subscription_link", "")
    vless_qr_path = Path(results.get("vless_qr_path", OUTPUT_DIR / "vless-qr.png"))
    subscription_qr_path = Path(results.get("subscription_qr_path", OUTPUT_DIR / "subscription-qr.png"))

    node_col, sub_col = st.columns(2)
    with node_col:
        with st.container(border=True):
            st.markdown("**VLESS Reality 节点**")
            if image_exists(vless_qr_path):
                st.image(str(vless_qr_path), caption="VLESS Reality 节点二维码", width=260)
            elif vless_link:
                st.warning("VLESS 链接已生成，但本地二维码图片不存在。")
            copy_box("vless:// 链接", vless_link, height=100)

    with sub_col:
        with st.container(border=True):
            st.markdown("**订阅**")
            if subscription_link:
                copy_box("订阅链接", subscription_link, height=72)
                if image_exists(subscription_qr_path):
                    st.image(str(subscription_qr_path), caption="订阅二维码", width=260)
                else:
                    st.warning("订阅链接已生成，但订阅二维码图片不存在。")
            elif vless_link:
                st.info("订阅链接生成失败，但单节点 VLESS 二维码已经生成，可直接扫码使用。")

    with st.container(border=True):
        render_panel_access(results)

    deploy_report = results.get("deploy_report", "")
    if deploy_report:
        st.text_area("部署报告", value=deploy_report, height=260, disabled=True, key="deploy_report_area")

    local_output_dir = results.get("local_output_dir") or str(OUTPUT_DIR)
    st.caption(f"本地结果已保存到：{local_output_dir}")
    st.warning("安全提示：部署完成后请尽快修改 VPS root 密码，或切换为 SSH key 登录。第一版不会默认关闭 root 登录、密码登录或 ping。")


def main() -> None:
    init_state()
    render_sidebar()
    st.title("VPS 3x-ui 一键部署器")
    current_results = st.session_state.last_results or load_results(OUTPUT_DIR)
    existing_success = has_success_result(current_results)
    existing_port = current_results.get("reality_port", "")

    render_readiness_summary(current_results, existing_success)
    render_first_run_guide(existing_success)
    render_failure_recovery(current_results)

    if existing_success:
        st.info(
            f"检测到已有成功部署结果，Reality 端口：{existing_port or '未知'}。"
            "如果只是查看二维码、订阅链接或面板信息，不需要再次点击部署。"
        )
        render_management_mode(current_results)

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
            host = st.text_input("VPS IP", placeholder="例如：1.2.3.4", key="host_value")
            ssh_port = st.number_input("SSH 端口", min_value=1, max_value=65535, step=1, key="ssh_port_value")
            ssh_user = st.text_input("SSH 用户", key="ssh_user_value")
            ssh_password = st.text_input("VPS 密码", type="password")
        with col2:
            st.subheader("节点配置")
            node_name = st.text_input("节点名称", key="node_name_value")
            reality_port = st.number_input(
                "Reality 入站端口",
                min_value=1,
                max_value=65535,
                step=1,
                key="reality_port_value",
            )
            st.caption("如果使用随机端口，请确认 VPS 服务商安全组已放行该 TCP 端口。")
            sni = st.text_input("SNI", key="sni_value")
            target = st.text_input("Target", key="target_value")
            fingerprint = st.selectbox(
                "Fingerprint",
                ["chrome", "firefox", "safari", "ios", "android", "edge", "random"],
                key="fingerprint_value",
            )

        with st.expander("高级选项", expanded=True):
            panel_port = st.number_input("3x-ui 面板端口", min_value=1, max_value=65535, step=1, key="panel_port_value")
            generate_ssh_key = st.checkbox("安装完成后生成 SSH key", key="generate_ssh_key_value")
            run_hardening = st.checkbox("执行服务器加固", key="run_hardening_value")
            st.caption("服务器加固脚本默认不会执行；只有主动勾选时才会运行。第一版不会默认关闭 root 登录、密码登录或 ping。")
            st.divider()
            st.markdown("**危险操作：远程重置 / 卸载**")
            reset_confirm_phrase = st.text_input(
                "远程重置确认短语",
                key="reset_confirm_phrase",
                placeholder="输入 RESET_3XUI_ONECLICK 才能执行",
            )
            reset_uninstall_xui = st.checkbox(
                "同时停用并归档 3x-ui",
                key="reset_uninstall_xui",
            )
            st.caption(
                "远程重置会先备份 /root/3xui-oneclick-result，再清理 oneclick 结果和临时脚本。"
                "只有勾选“同时停用并归档 3x-ui”时，才会停止 x-ui 服务并把 3x-ui 目录归档后改名停用。"
            )

        col_a, col_b, col_c, col_d, col_e, col_f = st.columns([1, 1, 1, 1, 1, 1])
        start_disabled = st.session_state.is_running or (existing_success and not confirm_redeploy)
        check = col_a.form_submit_button("刷新远程状态", disabled=st.session_state.is_running)
        redownload = col_b.form_submit_button("重新下载结果", disabled=st.session_state.is_running)
        backup_remote = col_c.form_submit_button("远程备份结果", disabled=st.session_state.is_running)
        start = col_d.form_submit_button("开始一键部署", type="primary", disabled=start_disabled)
        clear = col_e.form_submit_button("清空本地输出", disabled=st.session_state.is_running)
        remote_reset = col_f.form_submit_button("远程重置/卸载", disabled=st.session_state.is_running)

    if clear:
        clear_output()
        st.session_state.logs = []
        st.session_state.last_results = load_results(OUTPUT_DIR)
        st.session_state.last_preflight = {}
        st.session_state.export_zip_path = ""
        st.session_state.last_remote_backup = ""
        st.success("本地 output/ 已清空。")

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
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

    if backup_remote:
        if not validate_form_ready(host, ssh_user, ssh_password, "远程备份结果"):
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
            render_logs(log_placeholder)

        try:
            ui_log("开始备份远程结果目录。备份只保存到 VPS，不下载到本地。")
            backup_hint = backup_remote_results(login, ui_log)
            st.session_state.last_remote_backup = backup_hint
            ui_log(f"远程备份完成：{backup_hint}")
            st.success("远程结果目录已备份。")
        except DeploymentError as exc:
            append_log(f"错误：{exc.message}", ssh_password)
            hint = ERROR_HINTS.get(exc.code, exc.message)
            st.error(hint)
        except Exception as exc:  # noqa: BLE001
            append_log(f"未知错误：{exc}", ssh_password)
            st.error(f"远程备份失败：{exc}")
        finally:
            st.session_state.is_running = False
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

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
            render_logs(log_placeholder)

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
    render_preflight(st.session_state.last_preflight or results.get("preflight", {}))
    if (
        results.get("vless_link")
        or results.get("panel_login")
        or results.get("reset")
        or (OUTPUT_DIR / "result.json").exists()
    ):
        render_results(results)
    else:
        st.info("填写 VPS IP 和 root 密码后，点击“开始一键部署”。完成后这里会直接显示二维码、链接和面板信息。")


if __name__ == "__main__":
    main()
