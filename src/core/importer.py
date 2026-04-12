from __future__ import annotations

import csv
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from docx import Document
from docx.table import Table
from openpyxl import load_workbook

from src.core.project_manager import ProjectData, ProjectItem, ProjectMeta

STATUS_MAP = {
    "pending": "pending",
    "待处理": "pending",
    "passed": "passed",
    "通过": "passed",
    "failed": "failed",
    "失败": "failed",
    "not_applicable": "not_applicable",
    "不适用": "not_applicable",
}

PRIORITY_MAP = {
    "low": "low",
    "低": "low",
    "medium": "medium",
    "中": "medium",
    "high": "high",
    "高": "high",
}


@dataclass(slots=True)
class ImportedProject:
    data: ProjectData
    source_format: str


class _ReportHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_paragraph = False
        self.in_body_row = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.paragraphs: list[str] = []
        self.rows: list[list[str]] = []
        self._cell_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "p":
            self.in_paragraph = True
        elif tag == "tr":
            attrs_dict = dict(attrs)
            self.in_body_row = "status-" in attrs_dict.get("class", "")
            if self.in_body_row:
                self.current_row = []
        elif tag == "td" and self.in_body_row:
            self._cell_depth += 1
            self.current_cell = []
        elif tag == "br" and self._cell_depth:
            self.current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self.in_paragraph = False
        elif tag == "td" and self._cell_depth:
            self._cell_depth -= 1
            self.current_row.append("".join(self.current_cell).strip())
            self.current_cell = []
        elif tag == "tr" and self.in_body_row:
            self.rows.append(self.current_row)
            self.current_row = []
            self.in_body_row = False

    def handle_data(self, data: str) -> None:
        text = html.unescape(data)
        if self.in_paragraph and text.strip():
            if self.paragraphs and not self.paragraphs[-1].endswith("\n"):
                self.paragraphs[-1] += text
            else:
                self.paragraphs.append(text)
        elif self._cell_depth:
            self.current_cell.append(text)


class ProjectImporter:
    def import_file(self, path: Path, format_name: str) -> ImportedProject:
        handlers = {
            "html": self._import_html,
            "word": self._import_word,
            "excel": self._import_excel,
            "jira_csv": self._import_jira_csv,
            "markdown": self._import_markdown,
        }
        try:
            handler = handlers[format_name]
        except KeyError as exc:
            raise RuntimeError(f"暂不支持的导入格式：{format_name}") from exc
        return handler(path)

    def _import_html(self, path: Path) -> ImportedProject:
        parser = _ReportHtmlParser()
        parser.feed(path.read_text(encoding="utf-8"))
        meta = self._meta_from_paragraphs(parser.paragraphs, path)
        items = [self._item_from_row(row) for row in parser.rows if len(row) >= 6]
        return ImportedProject(ProjectData(meta=meta, items=items), "html")

    def _import_word(self, path: Path) -> ImportedProject:
        document = Document(path)
        title_paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        meta = self._meta_from_paragraphs(title_paragraphs, path)
        report_items: list[ProjectItem] = []
        standard_items: list[ProjectItem] = []
        for table in document.tables:
            if self._is_word_report_table(table):
                report_items.extend(self._report_items_from_word_table(table))
                continue
            if self._is_word_standard_table(table):
                start_index = len(standard_items) + 1
                standard_items.extend(
                    self._standard_items_from_word_table(table, start_index)
                )

        items = report_items or standard_items
        if standard_items and meta.template == f"{path.suffix} 导入":
            meta.template = "GB/T 37668 指标导入"
        return ImportedProject(ProjectData(meta=meta, items=items), "word")

    def _import_excel(self, path: Path) -> ImportedProject:
        workbook = load_workbook(path)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        items: list[ProjectItem] = []
        for row in rows[1:]:
            if not row or not row[0]:
                continue
            values = [self._string(value) for value in row]
            while len(values) < 6:
                values.append("")
            items.append(
                ProjectItem(
                    id=values[0],
                    content=values[1],
                    status=self._normalize_status(values[2]),
                    priority=self._normalize_priority(values[3]),
                    description=self._normalize_empty(values[4]),
                    image_path=self._normalize_empty(values[5]),
                )
            )

        meta = ProjectMeta(
            project_number="",
            created_time="",
            scenario="导入",
            template="Excel 导入",
            project_name=path.stem,
        )
        return ImportedProject(ProjectData(meta=meta, items=items), "excel")

    def _import_jira_csv(self, path: Path) -> ImportedProject:
        items: list[ProjectItem] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for index, row in enumerate(reader, start=1):
                summary = (row.get("Summary") or "").strip()
                description = (row.get("Description") or "").strip()
                priority = self._normalize_priority((row.get("Priority") or "").strip())
                item_id, content = self._parse_jira_summary(summary, index)
                items.append(
                    ProjectItem(
                        id=item_id,
                        content=content,
                        status="failed",
                        priority=priority,
                        description=description,
                    )
                )

        meta = ProjectMeta(
            project_number="",
            created_time="",
            scenario="导入",
            template="Jira CSV 导入",
            project_name=path.stem,
        )
        return ImportedProject(ProjectData(meta=meta, items=items), "jira_csv")

    def _import_markdown(self, path: Path) -> ImportedProject:
        text = path.read_text(encoding="utf-8")
        lines = [line.rstrip() for line in text.splitlines()]
        meta = self._meta_from_markdown(lines, path)
        items: list[ProjectItem] = []
        for line in lines:
            if not line.startswith("|") or line.startswith("| ---"):
                continue
            columns = [column.strip() for column in line.strip("|").split("|")]
            if columns[:2] == ["ID", "内容"] or len(columns) < 6:
                continue
            items.append(
                ProjectItem(
                    id=columns[0],
                    content=columns[1],
                    status=self._normalize_status(columns[2]),
                    priority=self._normalize_priority(columns[3]),
                    description=self._normalize_empty(columns[4]),
                    image_path=self._normalize_empty(columns[5]),
                )
            )
        return ImportedProject(ProjectData(meta=meta, items=items), "markdown")

    def _meta_from_paragraphs(self, paragraphs: list[str], path: Path) -> ProjectMeta:
        merged = "\n".join(paragraphs)
        return ProjectMeta(
            project_number=self._extract_value(merged, "项目编号"),
            created_time=self._extract_value(merged, "创建时间"),
            scenario=self._extract_value(merged, "场景") or "导入",
            template=self._extract_value(merged, "模板") or f"{path.suffix} 导入",
            project_name=self._extract_value(merged, "工程名称") or path.stem,
        )

    def _meta_from_markdown(self, lines: list[str], path: Path) -> ProjectMeta:
        content = "\n".join(lines)
        return ProjectMeta(
            project_number=self._extract_value(content, "项目编号"),
            created_time="",
            scenario=self._extract_value(content, "场景") or "导入",
            template=self._extract_value(content, "模板") or "Markdown 导入",
            project_name=self._extract_value(content, "名称") or path.stem,
        )

    def _extract_value(self, text: str, label: str) -> str:
        match = re.search(rf"{re.escape(label)}[:：]\s*([^\n｜|]+)", text)
        return match.group(1).strip() if match else ""

    def _item_from_row(self, row: list[str]) -> ProjectItem:
        return ProjectItem(
            id=row[0],
            content=row[1],
            status=self._normalize_status(row[2]),
            priority=self._normalize_priority(row[3]),
            description=self._normalize_empty(row[4]),
            image_path=self._normalize_empty(row[5]),
        )

    def _parse_jira_summary(self, summary: str, index: int) -> tuple[str, str]:
        cleaned = summary.replace("[A11Y]", "", 1).strip()
        match = re.match(r"([A-Za-z0-9_:-]+)\s+(.*)", cleaned)
        if match:
            return match.group(1), match.group(2).strip()
        return f"IMPORT_{index:03d}", cleaned or f"导入问题 {index}"

    def _is_word_report_table(self, table: Table) -> bool:
        if not table.rows:
            return False
        header = self._row_values(table.rows[0])
        return len(header) >= 5 and header[:5] == [
            "ID",
            "检查项",
            "状态",
            "优先级",
            "描述",
        ]

    def _is_word_standard_table(self, table: Table) -> bool:
        if len(table.rows) < 2:
            return False
        header = self._row_values(table.rows[1])
        return len(header) >= 6 and header[:6] == [
            "原则",
            "准则",
            "指标",
            "一级",
            "二级",
            "三级",
        ]

    def _report_items_from_word_table(self, table: Table) -> list[ProjectItem]:
        items: list[ProjectItem] = []
        for row in table.rows[1:]:
            values = self._row_values(row)
            while len(values) < 5:
                values.append("")
            if not any(values[:5]):
                continue
            items.append(
                ProjectItem(
                    id=values[0],
                    content=values[1],
                    status=self._normalize_status(values[2]),
                    priority=self._normalize_priority(values[3]),
                    description=self._normalize_empty(values[4]),
                )
            )
        return items

    def _standard_items_from_word_table(
        self, table: Table, start_index: int
    ) -> list[ProjectItem]:
        items: list[ProjectItem] = []
        for offset, row in enumerate(table.rows[2:]):
            values = self._row_values(row)
            while len(values) < 6:
                values.append("")
            if not any(values[:3]) or not values[2]:
                continue
            items.append(self._word_standard_item_from_row(values, start_index + offset))
        return items

    def _word_standard_item_from_row(
        self, row: list[str], index: int
    ) -> ProjectItem:
        principle, guideline, indicator = row[:3]
        level_labels = ["一级", "二级", "三级"]
        level_markers = [value.strip() for value in row[3:6]]
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
            priority=self._priority_from_level_markers(level_markers),
            description="\n".join(description_lines),
        )

    def _priority_from_level_markers(self, markers: list[str]) -> str:
        if len(markers) >= 1 and markers[0]:
            return "high"
        if len(markers) >= 2 and markers[1]:
            return "medium"
        if len(markers) >= 3 and markers[2]:
            return "low"
        return "medium"

    def _normalize_status(self, value: str) -> str:
        return STATUS_MAP.get(value.strip(), "pending")

    def _normalize_priority(self, value: str) -> str:
        return PRIORITY_MAP.get(
            value.strip().lower(), PRIORITY_MAP.get(value.strip(), "medium")
        )

    def _normalize_empty(self, value: str) -> str:
        cleaned = self._string(value).strip()
        return "" if cleaned in {"", "-"} else cleaned

    def _row_values(self, row) -> list[str]:
        return [self._string(cell.text).strip() for cell in row.cells]

    def _string(self, value) -> str:
        return "" if value is None else str(value)
