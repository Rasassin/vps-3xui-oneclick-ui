# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).resolve().parent
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all("streamlit")

datas = [
    (str(ROOT / "app.py"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "requirements.txt"), "."),
    (str(ROOT / "deployer"), "deployer"),
    (str(ROOT / "remote_scripts"), "remote_scripts"),
    (str(ROOT / "output" / ".gitkeep"), "output"),
    (str(ROOT / "data" / ".gitkeep"), "data"),
]
datas += streamlit_datas

binaries = streamlit_binaries

hiddenimports = streamlit_hiddenimports + [
    "paramiko",
    "qrcode",
    "PIL",
]


a = Analysis(
    [str(ROOT / "desktop_launcher.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VPS 3x-ui Oneclick",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VPS 3x-ui Oneclick",
)

app = BUNDLE(
    coll,
    name="VPS 3x-ui Oneclick.app",
    icon=None,
    bundle_identifier="com.vps3xui.oneclick",
)
