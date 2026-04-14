from __future__ import annotations

import re
from datetime import date
from pathlib import Path


def normalize_project_number(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    match = re.fullmatch(r"#0*(\d+)(?:-0*(\d+))?", raw)
    if not match:
        return raw

    number = str(int(match.group(1)))
    suffix = match.group(2)
    if suffix is None:
        return f"#{number}"
    return f"#{number}-{int(suffix)}"


def generate_project_number(today: date | None = None) -> str:
    current = today or date.today()
    return f"#{int(current.strftime('%m%d'))}"


def allocate_unique_project_number(
    base_dir: Path, base_number: str, current_root: Path | None = None
) -> str:
    base_number = normalize_project_number(base_number)
    candidate = base_number
    index = 2

    while (base_dir / candidate).exists() and (
        current_root is None or (base_dir / candidate) != current_root
    ):
        candidate = f"{base_number}-{index}"
        index += 1

    return candidate


def allocate_project_number(base_dir: Path, today: date | None = None) -> str:
    return allocate_unique_project_number(
        base_dir, generate_project_number(today=today)
    )


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
