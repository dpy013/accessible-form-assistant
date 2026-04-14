from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.core.project_manager import ProjectItem

GBT37668_HEADERS = ["原则", "准则", "指标", "一级", "二级", "三级"]
GBT37668_TEMPLATE_NAME = "GB/T 37668 指标导入"


def item_from_gbt37668_mapping(
    row: Mapping[str, str | None], index: int
) -> ProjectItem | None:
    values = [_normalize_cell(row.get(header, "")) for header in GBT37668_HEADERS]
    return item_from_gbt37668_values(values, index)


def item_from_gbt37668_values(
    values: Sequence[str | None], index: int
) -> ProjectItem | None:
    normalized = [_normalize_cell(value) for value in values]
    while len(normalized) < len(GBT37668_HEADERS):
        normalized.append("")

    if not any(normalized[:3]) or not normalized[2]:
        return None

    principle, guideline, indicator = normalized[:3]
    level_labels = ["一级", "二级", "三级"]
    level_markers = [value.strip() for value in normalized[3:6]]
    applicable_levels = [
        label for label, marker in zip(level_labels, level_markers) if marker
    ]
    raw_level_marks = [
        f"{label}={marker}"
        for label, marker in zip(level_labels, level_markers)
        if marker
    ]

    description_lines = []
    if principle:
        description_lines.append(f"原则：{principle}")
    if guideline:
        description_lines.append(f"准则：{guideline}")
    if applicable_levels:
        description_lines.append(f"适用等级：{'、'.join(applicable_levels)}")
    if raw_level_marks:
        description_lines.append(f"等级标记：{'；'.join(raw_level_marks)}")

    return ProjectItem(
        id=f"GBT37668_{index:03d}",
        content=f"{indicator}（{principle} / {guideline}）",
        status="pending",
        priority=_priority_from_level_markers(level_markers),
        description="\n".join(description_lines),
    )


def _priority_from_level_markers(markers: Sequence[str]) -> str:
    if len(markers) >= 1 and markers[0]:
        return "high"
    if len(markers) >= 2 and markers[1]:
        return "medium"
    if len(markers) >= 3 and markers[2]:
        return "low"
    return "medium"


def _normalize_cell(value: str | None) -> str:
    return "" if value is None else str(value).strip()
