# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = Path(SPECPATH)

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("starlette")
    + collect_submodules("anyio")
    + collect_submodules("httpx")
    + collect_submodules("pydantic")
    + collect_submodules("pydantic_settings")
    + collect_submodules("aiosqlite")
    + collect_submodules("structlog")
    + [
        "uvicorn",
        "uvicorn.main",
        "uvicorn.config",
        "uvicorn.importer",
        "multipart",
        "python_multipart",
        "socksio",
    ]
)

a = Analysis(
    [str(root / "kie_sidecar" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "kie_sidecar" / "models" / "registry"), "kie_sidecar/models/registry"),
        (str(root / "kie_sidecar" / "db" / "schema.sql"), "kie_sidecar/db"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="kie-sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
