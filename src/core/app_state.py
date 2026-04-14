from __future__ import annotations

import json
from json import JSONDecodeError
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
        try:
            payload = json.loads(self.state_file.read_text(encoding="utf-8"))
        except JSONDecodeError as exc:
            raise RuntimeError(f"应用状态文件损坏：{self.state_file}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError(f"应用状态文件格式无效：{self.state_file}")

        recent_projects = payload.get("recent_projects", [])
        if not isinstance(recent_projects, list) or any(
            not isinstance(item, str) for item in recent_projects
        ):
            raise RuntimeError(f"应用状态文件格式无效：{self.state_file}")
        return AppState(recent_projects=recent_projects)

    def save(self, state: AppState) -> None:
        self.state_file.write_text(
            json.dumps(
                {"recent_projects": state.recent_projects}, ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )

    def remember_project(self, project_root: Path) -> None:
        state = self._load_for_update()
        project_value = str(project_root.resolve())
        recent = [project_value, *state.recent_projects]
        deduplicated: list[str] = []
        for item in recent:
            if item not in deduplicated:
                deduplicated.append(item)
        state.recent_projects = deduplicated[:10]
        self.save(state)

    def forget_project(self, project_root: Path) -> None:
        state = self._load_for_update()
        project_value = str(project_root.resolve())
        state.recent_projects = [
            item for item in state.recent_projects if item != project_value
        ]
        self.save(state)

    def recent_projects(self, *, strict: bool = False) -> list[Path]:
        state = self.load() if strict else self._load_for_update()
        existing = [
            Path(entry) for entry in state.recent_projects if Path(entry).exists()
        ]
        if len(existing) != len(state.recent_projects):
            state.recent_projects = [str(path) for path in existing]
            self.save(state)
        return existing

    def latest_project(self, *, strict: bool = False) -> Path | None:
        projects = self.recent_projects(strict=strict)
        return projects[0] if projects else None

    def _load_for_update(self) -> AppState:
        try:
            return self.load()
        except RuntimeError:
            state = AppState()
            self.save(state)
            return state
