from __future__ import annotations

import unittest

from src.core.importer import ProjectImporter
from src.core.structured_import import TableSchema, parse_tables_with_schema


class ReportImportFallbackIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.importer = ProjectImporter()

    def test_report_rows_without_id_get_indexed_fallback_id(self) -> None:
        first = self.importer._report_item_from_mapping(  # noqa: SLF001
            {"检查项": "缺少标签"}, 1
        )
        second = self.importer._report_item_from_mapping(  # noqa: SLF001
            {"内容": "按钮无名称"}, 2
        )

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, "IMPORT_001")
        self.assertEqual(second.id, "IMPORT_002")

    def test_report_rows_preserve_existing_id(self) -> None:
        item = self.importer._report_item_from_mapping(  # noqa: SLF001
            {"ID": "A11Y_007", "检查项": "颜色对比度不足"},
            3,
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.id, "A11Y_007")

    def test_parse_tables_assigns_unique_fallback_ids_across_tables(self) -> None:
        schema = TableSchema(
            name="report-check-item",
            required_headers=("ID", "检查项", "状态", "优先级", "描述"),
            row_factory=self.importer._report_item_from_mapping,  # noqa: SLF001
        )
        tables = [
            [
                ["ID", "检查项", "状态", "优先级", "描述"],
                ["", "第一个问题", "待处理", "高", ""],
                ["", "", "", "", ""],
            ],
            [
                ["ID", "检查项", "状态", "优先级", "描述"],
                ["", "第二个问题", "待处理", "中", ""],
            ],
        ]

        items = parse_tables_with_schema(tables, schema)

        self.assertEqual([item.id for item in items], ["IMPORT_001", "IMPORT_003"])


if __name__ == "__main__":
    unittest.main()
