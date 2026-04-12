from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


APP_STATE_FILENAME = ".accessible_form_assist.json"


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
        payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        return AppState(recent_projects=payload.get("recent_projects", []))

    def save(self, state: AppState) -> None:
        self.state_file.write_text(
            json.dumps(
                {"recent_projects": state.recent_projects}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )

    def remember_project(self, project_root: Path) -> None:
        state = self.load()
        project_value = str(project_root.resolve())
        recent = [project_value, *state.recent_projects]
        deduplicated: list[str] = []
        for item in recent:
            if item not in deduplicated:
                deduplicated.append(item)
        state.recent_projects = deduplicated[:10]
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
