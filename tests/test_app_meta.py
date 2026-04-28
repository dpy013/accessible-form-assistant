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


class GitHubActionsArtifactNameTests(unittest.TestCase):
    def test_artifact_name_uses_run_id(self) -> None:
        artifact_name = app_meta.github_actions_artifact_name(
            run_id=25067180150,
            run_attempt=1,
        )

        self.assertEqual(artifact_name, f"{app_meta.APP_DIST_NAME}-run25067180150")

    def test_artifact_name_includes_rerun_attempt(self) -> None:
        artifact_name = app_meta.github_actions_artifact_name(
            run_id=25067180150,
            run_attempt=2,
        )

        self.assertEqual(artifact_name, f"{app_meta.APP_DIST_NAME}-run25067180150-a2")


class ReleaseNameTests(unittest.TestCase):
    def test_release_name_uses_explicit_build_label(self) -> None:
        with patch.dict(os.environ, {"BUILD_LABEL": "260429r57"}):
            self.assertEqual(
                app_meta.release_name(),
                f"{app_meta.APP_DIST_NAME}-{app_meta.package_version()}-260429r57",
            )


if __name__ == "__main__":
    unittest.main()
