from __future__ import annotations

import argparse
import logging
from pathlib import Path

import wx

from src.app_meta import APP_DISPLAY_NAME
from src.core.parser import TemplateRepository
from src.ui.main_frame import MainFrame

APP_LOG_FILENAME = ".accessible_form_assist.log"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=APP_DISPLAY_NAME)
    parser.add_argument(
        "--workspace",
        default=str(Path.cwd()),
        help="工程工作目录，默认使用当前目录。",
    )
    return parser


def configure_logging(workspace: Path) -> None:
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler()],
        force=True,
    )

    log_file = workspace / APP_LOG_FILENAME
    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
    except OSError:
        logging.getLogger(__name__).exception(
            "Failed to open application log file %s.", log_file
        )
        return

    file_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(file_handler)


def main() -> int:
    args = build_parser().parse_args()
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    configure_logging(workspace)

    app = wx.App(False)
    repository = TemplateRepository.load_builtin()
    frame = MainFrame(workspace=workspace, template_repository=repository)
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
