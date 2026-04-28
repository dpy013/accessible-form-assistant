from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from src import app_meta


class GitHubActionsBuildLabelTests(unittest.TestCase):
    def test_uses_run_number_for_unique_build_label(self) -> None:
        label = app_meta.github_actions_build_label(
            now=datetime(2026, 4, 29, tzinfo=UTC),
            run_number=57,
            run_attempt=1,
        )

        self.assertEqual(label, "260429r57")

    def test_includes_attempt_for_rerun_labels(self) -> None:
        label = app_meta.github_actions_build_label(
            now=datetime(2026, 4, 29, tzinfo=UTC),
            run_number=57,
            run_attempt=3,
        )

        self.assertEqual(label, "260429r57a3")

    def test_release_name_uses_explicit_build_label(self) -> None:
        with patch.dict(os.environ, {"BUILD_LABEL": "260429r57"}):
            self.assertEqual(
                app_meta.release_name(), "accessible-form-assistant-0.1.0-260429r57"
            )


if __name__ == "__main__":
    unittest.main()
