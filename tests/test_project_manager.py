from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from src.core.project_manager import CONFIG_FILENAME, PROJECT_FILENAME, ProjectManager


class ProjectManagerConfigRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.project_root = self.workspace / "#0504"
        self.project_root.mkdir()
        self.manager = ProjectManager(self.workspace)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_load_project_recovers_from_invalid_config_xml(self) -> None:
        (self.project_root / PROJECT_FILENAME).write_text(
            json.dumps(
                {
                    "meta": {
                        "project_number": "#0504",
                        "created_time": "2026-05-04",
                        "scenario": "桌面端",
                        "template": "默认模板",
                        "project_name": "示例工程",
                    },
                    "items": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (self.project_root / CONFIG_FILENAME).write_text(
            "<config><tool-settings><hide-completed>true</hide-completed>",
            encoding="utf-8",
        )

        session = self.manager.load_project(self.project_root)

        self.assertEqual(session.data.meta.project_name, "示例工程")
        self.assertFalse(session.config.tool_settings.hide_completed)
        self.assertFalse(session.config.tool_settings.show_trash)
        self.assertEqual(session.config.custom_settings, {})

        invalid_configs = sorted(session.root.glob("config.invalid_*.xml"))
        self.assertEqual(len(invalid_configs), 1)
        self.assertIn("<tool-settings>", invalid_configs[0].read_text(encoding="utf-8"))

        config_root = ET.parse(session.root / CONFIG_FILENAME).getroot()
        self.assertEqual(config_root.tag, "config")
        self.assertEqual(config_root.findtext("./tool-settings/hide-completed"), "false")
        self.assertEqual(config_root.findtext("./tool-settings/show-trash"), "false")


if __name__ == "__main__":
    unittest.main()
