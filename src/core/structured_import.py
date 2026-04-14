from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from src.core.project_manager import ProjectItem

RowMapping = Mapping[str, str]
RowFactory = Callable[[RowMapping, int], ProjectItem | None]


@dataclass(frozen=True, slots=True)
class TableSchema:
    name: str
    required_headers: tuple[str, ...]
    row_factory: RowFactory
    template_name: str | None = None


def parse_tables_with_schema(
    tables: Sequence[Sequence[Sequence[str]]],
    schema: TableSchema,
    start_index: int = 1,
) -> list[ProjectItem]:
    items: list[ProjectItem] = []
    next_index = start_index
    for table in tables:
        header_row_index = _find_header_row_index(table, schema.required_headers)
        if header_row_index is None:
            continue

        headers = [_normalize_cell(value) for value in table[header_row_index]]
        for row in table[header_row_index + 1 :]:
            mapping = _row_mapping(headers, row)
            item = schema.row_factory(mapping, next_index)
            next_index += 1
            if item:
                items.append(item)
    return items


def _find_header_row_index(
    rows: Sequence[Sequence[str]], required_headers: Sequence[str]
) -> int | None:
    required = {header.strip() for header in required_headers}
    for index, row in enumerate(rows):
        row_headers = {_normalize_cell(value) for value in row}
        if required.issubset(row_headers):
            return index
    return None


def _row_mapping(headers: Sequence[str], row: Sequence[str]) -> dict[str, str]:
    values = [_normalize_cell(value) for value in row]
    mapping: dict[str, str] = {}
    for index, header in enumerate(headers):
        if not header:
            continue
        mapping[header] = values[index] if index < len(values) else ""
    return mapping


def _normalize_cell(value: str | None) -> str:
    return "" if value is None else str(value).strip()
