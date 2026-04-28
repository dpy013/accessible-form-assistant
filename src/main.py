from __future__ import annotations

import argparse
from pathlib import Path

import wx

from src.app_meta import APP_DISPLAY_NAME
from src.core.parser import TemplateRepository
from src.ui.main_frame import MainFrame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--workspace",
        default=str(Path.cwd()),
        help="工程工作目录，默认使用当前目录。",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    app = wx.App(False)
    repository = TemplateRepository.load_builtin()
    frame = MainFrame(workspace=workspace, template_repository=repository)
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
