# fmt: off
from __future__ import annotations

import os
import re
import sys
import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version as installed_version
from pathlib import Path

APP_PACKAGE_NAME = "accessible-form-assist"
APP_DIST_NAME = "accessible-form-assistant"
APP_DISPLAY_NAME = "信息无障碍表格填写助手"
DEFAULT_BUILD_SUFFIX = "s"
DEFAULT_PACKAGE_VERSION = "0.0.0"


def _version_file_candidates() -> tuple[Path, ...]:
    candidates = [Path(__file__).resolve().parents[1] / "pyproject.toml"]

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "pyproject.toml")

    return tuple(candidates)


def _version_from_pyproject() -> str | None:
    for pyproject_path in _version_file_candidates():
        try:
            with pyproject_path.open("rb") as file:
                return str(tomllib.load(file)["project"]["version"])
        except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError):
            continue
    return None


@lru_cache
def package_version() -> str:
    try:
        return installed_version(APP_PACKAGE_NAME)
    except PackageNotFoundError:
        return _version_from_pyproject() or DEFAULT_PACKAGE_VERSION


def build_label() -> str | None:
    explicit_label = os.getenv("BUILD_LABEL", "").strip()
    if explicit_label:
        return explicit_label

    build_stamp = os.getenv("BUILD_STAMP", "").strip()
    if not build_stamp:
        return None

    build_suffix = os.getenv("BUILD_SUFFIX", "").strip() or DEFAULT_BUILD_SUFFIX
    return f"{build_stamp}{build_suffix}"


def display_version() -> str:
    current_build_label = build_label()
    version = package_version()
    if not current_build_label:
        return version
    return f"{version}+{current_build_label}"


def release_name() -> str:
    current_build_label = build_label()
    version = package_version()
    if not current_build_label:
        return f"{APP_DIST_NAME}-{version}"
    return f"{APP_DIST_NAME}-{version}-{current_build_label}"


def executable_filename() -> str:
    return f"{release_name()}.exe"


def window_title_suffix() -> str:
    return f"{APP_DISPLAY_NAME} {display_version()}"


def numeric_version_tuple() -> tuple[int, int, int, int]:
    numeric_parts: list[int] = []
    for part in package_version().split("."):
        match = re.match(r"(\d+)", part)
        if match:
            numeric_parts.append(int(match.group(1)))
        if len(numeric_parts) == 4:
            break

    numeric_parts.extend([0] * (4 - len(numeric_parts)))
    return tuple(numeric_parts[:4])
# fmt: on
