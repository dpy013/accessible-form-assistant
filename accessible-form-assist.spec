# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

project_root = Path(SPECPATH)
sys.path.insert(0, str(project_root))

from src.app_meta import (
    APP_DISPLAY_NAME,
    APP_DIST_NAME,
    display_version,
    executable_filename,
    numeric_version_tuple,
    release_name,
)

templates_dir = project_root / "src" / "templates"
build_dir = project_root / "build"
build_dir.mkdir(exist_ok=True)
version_file = build_dir / "pyinstaller-version-info.txt"
version_numbers = numeric_version_tuple()
version_literal = ", ".join(str(part) for part in version_numbers)
bundle_name = release_name()
exe_name = Path(executable_filename()).stem
display_build_version = display_version()
version_file.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({version_literal}),
    prodvers=({version_literal}),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', ''),
            StringStruct('FileDescription', '{APP_DISPLAY_NAME}'),
            StringStruct('FileVersion', '{display_build_version}'),
            StringStruct('InternalName', '{APP_DIST_NAME}'),
            StringStruct('OriginalFilename', '{exe_name}.exe'),
            StringStruct('ProductName', '{APP_DISPLAY_NAME}'),
            StringStruct('ProductVersion', '{display_build_version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
    encoding="utf-8",
)
datas = [
    (str(path), "src/templates")
    for path in templates_dir.iterdir()
    if path.is_file()
]
datas.append((str(project_root / "pyproject.toml"), "."))


a = Analysis(
    ["src\\main.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
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
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(version_file),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=bundle_name,
)

