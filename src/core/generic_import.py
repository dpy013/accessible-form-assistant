from __future__ import annotations

import re
from collections.abc import Sequence

from src.core.project_manager import ProjectItem


def items_from_text_blocks(
    blocks: Sequence[str], prefix: str = "DOC"
) -> list[ProjectItem]:
    normalized_blocks = _normalize_blocks(blocks)
    if not normalized_blocks:
        return []

    sections = _group_blocks(normalized_blocks)
    items: list[ProjectItem] = []
    for index, section in enumerate(sections, start=1):
        heading = section["heading"]
        body = section["body"]
        if body:
            description = "\n\n".join(body)
            content = heading
        else:
            description = ""
            content = heading
        items.append(
            ProjectItem(
                id=f"{prefix}_{index:03d}",
                content=_truncate(content),
                description=description,
            )
        )
    return items


def items_from_rows(
    rows: Sequence[Sequence[str]], prefix: str = "ROW"
) -> list[ProjectItem]:
    normalized_rows = [
        [str(value).strip() for value in row if str(value).strip()]
        for row in rows
    ]
    normalized_rows = [row for row in normalized_rows if row]
    if not normalized_rows:
        return []

    header, data_rows = _extract_header(normalized_rows)
    items: list[ProjectItem] = []
    for index, row in enumerate(data_rows, start=1):
        if header:
            pairs = list(zip(header, row))
            content = next(
                (f"{label}：{value}" for label, value in pairs if value),
                "导入内容",
            )
            description = "\n".join(
                f"{label}：{value}" for label, value in pairs if value
            )
        else:
            content = row[0]
            description = "\n".join(row[1:])
        items.append(
            ProjectItem(
                id=f"{prefix}_{index:03d}",
                content=_truncate(content),
                description=description,
            )
        )
    return items


def _normalize_blocks(blocks: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    previous = ""
    for block in blocks:
        text = re.sub(r"[ \t]+", " ", block).strip()
        if not text or _looks_like_noise(text):
            continue
        if text == previous and len(text) <= 40:
            continue
        normalized.append(text)
        previous = text
    return normalized


def _group_blocks(blocks: Sequence[str]) -> list[dict[str, list[str] | str]]:
    sections: list[dict[str, list[str] | str]] = []
    current_heading = ""
    current_body: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_body
        if current_heading or current_body:
            heading = current_heading or _truncate(current_body[0])
            body = current_body if current_heading else current_body[1:]
            sections.append({"heading": heading, "body": body})
        current_heading = ""
        current_body = []

    for block in blocks:
        if _is_heading(block):
            flush()
            current_heading = block
            continue
        if not current_heading and not current_body and len(block) <= 60:
            current_heading = block
            continue
        current_body.append(block)

    flush()
    return sections


def _extract_header(
    rows: Sequence[Sequence[str]],
) -> tuple[list[str] | None, list[list[str]]]:
    if len(rows) < 2:
        return None, [list(row) for row in rows]

    first_row = list(rows[0])
    second_row = list(rows[1])
    if _looks_like_header(first_row, second_row):
        max_length = len(first_row)
        data_rows = [list(row[:max_length]) for row in rows[1:]]
        return first_row, data_rows
    return None, [list(row) for row in rows]


def _looks_like_header(first_row: Sequence[str], second_row: Sequence[str]) -> bool:
    if not first_row or any(not cell for cell in first_row):
        return False
    if len(first_row) < 2:
        return False
    if len(set(first_row)) != len(first_row):
        return False
    if all(_looks_like_label(cell) for cell in first_row) and first_row != list(second_row):
        return True
    if all(_looks_like_data(cell) for cell in first_row):
        return False
    return any(_looks_like_data(cell) for cell in second_row)


def _looks_like_data(value: str) -> bool:
    return bool(
        re.search(r"\d", value) or len(value) > 20 or "：" in value or ":" in value
    )


def _looks_like_label(value: str) -> bool:
    return len(value) <= 20 and not re.search(r"[。；]", value)


def _looks_like_noise(value: str) -> bool:
    if re.fullmatch(r"\d+", value):
        return True
    return bool(re.fullmatch(r"GB[\\/A-ZTz+\-\s0-9.]+", value))


def _is_heading(value: str) -> bool:
    if value in {"前言", "引言", "范围", "术语和定义", "参考文献"}:
        return True
    if re.match(r"^(附录|附件)[A-Z]?", value):
        return True
    if re.match(r"^\d+(\.\d+)*\s*\S+", value):
        return True
    return len(value) <= 30 and not re.search(r"[。；，：]", value)


def _truncate(value: str, limit: int = 80) -> str:
    compact = value.replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"
