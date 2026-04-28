from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.core.app_state import (
    APP_STATE_FILENAME,
    MAX_RECENT_PROJECTS,
    AppState,
    AppStateManager,
)


class AppStateManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.manager = AppStateManager(self.workspace)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_save_writes_state_without_leaving_temp_files(self) -> None:
        self.manager.save(AppState(recent_projects=["C:\\demo\\one"]))

        self.assertEqual(
            json.loads(
                (self.workspace / APP_STATE_FILENAME).read_text(encoding="utf-8")
            ),
            {"recent_projects": ["C:\\demo\\one"]},
        )
        self.assertEqual(
            sorted(path.name for path in self.workspace.iterdir()),
            [APP_STATE_FILENAME],
        )

    def test_remember_project_limits_recent_projects_with_named_constant(self) -> None:
        overflow_count = 3
        for index in range(MAX_RECENT_PROJECTS + overflow_count):
            project_root = self.workspace / f"project-{index:02d}"
            project_root.mkdir()
            self.manager.remember_project(project_root)

        state = self.manager.load()
        expected_newest_index = MAX_RECENT_PROJECTS + overflow_count - 1
        expected_oldest_index = overflow_count

        self.assertEqual(len(state.recent_projects), MAX_RECENT_PROJECTS)
        self.assertTrue(
            state.recent_projects[0].endswith(f"project-{expected_newest_index:02d}")
        )
        self.assertTrue(
            state.recent_projects[-1].endswith(f"project-{expected_oldest_index:02d}")
        )

    def test_load_resets_invalid_state_payload(self) -> None:
        (self.workspace / APP_STATE_FILENAME).write_text(
            '{"recent_projects":"invalid"}',
            encoding="utf-8",
        )

        state = self.manager.load()

        self.assertEqual(state.recent_projects, [])
        self.assertEqual(
            json.loads(
                (self.workspace / APP_STATE_FILENAME).read_text(encoding="utf-8")
            ),
            {"recent_projects": []},
        )


if __name__ == "__main__":
    unittest.main()
