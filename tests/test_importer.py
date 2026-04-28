from __future__ import annotations

import unittest

from src.core.importer import ProjectImporter


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


if __name__ == "__main__":
    unittest.main()
