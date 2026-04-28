from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


APP_STATE_FILENAME = ".accessible_form_assist.json"
MAX_RECENT_PROJECTS = 10
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppState:
    recent_projects: list[str] = field(default_factory=list)


class AppStateManager:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.state_file = workspace / APP_STATE_FILENAME

    def load(self) -> AppState:
        if not self.state_file.exists():
            return AppState()
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except OSError:
            logger.exception(
                "Failed to read app state from %s; resetting state.", self.state_file
            )
            return self._reset_state()
        except UnicodeDecodeError:
            logger.exception(
                "App state file %s is not valid UTF-8; resetting state.",
                self.state_file,
            )
            return self._reset_state()
        except json.JSONDecodeError:
            logger.exception(
                "App state file %s is not valid JSON; resetting state.",
                self.state_file,
            )
            return self._reset_state()
        if not isinstance(payload, dict):
            logger.warning(
                "App state file %s has invalid root type %s; resetting state.",
                self.state_file,
                type(payload).__name__,
            )
            return self._reset_state()
        recent_projects = payload.get("recent_projects", [])
        if not isinstance(recent_projects, list):
            logger.warning(
                "App state file %s has invalid recent_projects type %s; resetting state.",
                self.state_file,
                type(recent_projects).__name__,
            )
            return self._reset_state()
        return AppState(recent_projects=[str(item) for item in recent_projects if item])

    def save(self, state: AppState) -> None:
        payload = json.dumps(
            {"recent_projects": state.recent_projects}, ensure_ascii=False, indent=2
        )
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.workspace,
                prefix=f"{self.state_file.stem}_",
                suffix=".tmp",
                delete=False,
            ) as handle:
                handle.write(payload)
                temp_path = Path(handle.name)
            temp_path.replace(self.state_file)
        except OSError:
            logger.exception("Failed to save app state to %s.", self.state_file)
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise

    def remember_project(self, project_root: Path) -> None:
        state = self.load()
        project_value = str(project_root.resolve())
        recent = [project_value, *state.recent_projects]
        deduplicated: list[str] = []
        for item in recent:
            if item not in deduplicated:
                deduplicated.append(item)
        state.recent_projects = deduplicated[:MAX_RECENT_PROJECTS]
        self.save(state)

    def forget_project(self, project_root: Path) -> None:
        state = self.load()
        project_value = str(project_root.resolve())
        state.recent_projects = [
            item for item in state.recent_projects if item != project_value
        ]
        self.save(state)

    def recent_projects(self) -> list[Path]:
        state = self.load()
        existing = [
            Path(entry) for entry in state.recent_projects if Path(entry).exists()
        ]
        if len(existing) != len(state.recent_projects):
            state.recent_projects = [str(path) for path in existing]
            self.save(state)
        return existing

    def latest_project(self) -> Path | None:
        projects = self.recent_projects()
        return projects[0] if projects else None

    def _reset_state(self) -> AppState:
        state = AppState()
        try:
            self.save(state)
        except OSError:
            logger.exception("Failed to reset app state at %s.", self.state_file)
        return state
