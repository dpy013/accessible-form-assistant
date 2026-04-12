from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image

from src.core.utils import (
    allocate_project_number,
    allocate_unique_project_number,
    ensure_directory,
    normalize_project_number,
)


PROJECT_FILENAME = "project.json"


@dataclass(slots=True)
class ProjectMeta:
    project_number: str
    created_time: str
    scenario: str
    template: str
    project_name: str = ""


@dataclass(slots=True)
class ProjectItem:
    id: str
    content: str
    status: str = "pending"
    description: str = ""
    image_path: str = ""
    priority: str = "medium"
    deleted: bool = False


@dataclass(slots=True)
class ProjectData:
    meta: ProjectMeta
    items: list[ProjectItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "meta": asdict(self.meta),
            "items": [asdict(item) for item in self.items],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ProjectData":
        meta = ProjectMeta(**payload["meta"])
        items = [ProjectItem(**item) for item in payload.get("items", [])]
        return cls(meta=meta, items=items)


@dataclass(slots=True)
class ProjectSession:
    root: Path
    data: ProjectData

    @property
    def project_file(self) -> Path:
        return self.root / PROJECT_FILENAME


class ProjectManager:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def create_project(
        self,
        scenario: str,
        template_name: str,
        items: Iterable[ProjectItem],
        project_name: str = "",
    ) -> ProjectSession:
        project_number = allocate_project_number(self.workspace)
        root = ensure_directory(self.workspace / project_number)
        ensure_directory(root / "assets")
        ensure_directory(root / "backup")

        data = ProjectData(
            meta=ProjectMeta(
                project_number=project_number,
                created_time=datetime.now().strftime("%Y-%m-%d"),
                scenario=scenario,
                template=template_name,
                project_name=project_name,
            ),
            items=list(items),
        )
        session = ProjectSession(root=root, data=data)
        self.save_project(session)
        return session

    def save_project(self, session: ProjectSession) -> None:
        session.project_file.write_text(
            json.dumps(session.data.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_project(self, project_root: Path) -> ProjectSession:
        payload = json.loads(
            (project_root / PROJECT_FILENAME).read_text(encoding="utf-8")
        )
        session = ProjectSession(root=project_root, data=ProjectData.from_dict(payload))
        self._normalize_project_session(session)
        return session

    def list_projects(self) -> list[Path]:
        projects: list[Path] = []
        for entry in self.workspace.iterdir():
            if entry.is_dir() and (entry / PROJECT_FILENAME).exists():
                projects.append(entry)
        return sorted(projects, key=lambda item: item.stat().st_mtime, reverse=True)

    def backup_project(self, session: ProjectSession) -> Path:
        self.save_project(session)
        backup_name = datetime.now().strftime("project_%Y%m%d_%H%M%S.json")
        target = session.root / "backup" / backup_name
        shutil.copy2(session.project_file, target)
        return target

    def clean_project_directory(self, session: ProjectSession) -> list[str]:
        keep_names = {PROJECT_FILENAME, "assets", "backup"}
        removed: list[str] = []
        for entry in session.root.iterdir():
            if entry.name in keep_names:
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            removed.append(entry.name)
        return removed

    def save_bitmap_asset(self, session: ProjectSession, bitmap) -> str:
        timestamp = datetime.now().strftime("%H%M%S_%f")
        relative_path = Path("assets") / f"screenshot_{timestamp}.jpg"
        destination = session.root / relative_path

        image = bitmap.ConvertToImage()
        width, height = image.GetSize()
        if width > 1600:
            ratio = 1600 / width
            image = image.Scale(1600, int(height * ratio))

        pil_image = Image.frombytes("RGB", image.GetSize(), image.GetData())
        pil_image.save(destination, format="JPEG", quality=85, optimize=True)
        return relative_path.as_posix()

    def _normalize_project_session(self, session: ProjectSession) -> None:
        current_number = session.data.meta.project_number or session.root.name
        normalized_number = normalize_project_number(current_number)
        if not normalized_number:
            return

        changed = session.data.meta.project_number != normalized_number
        session.data.meta.project_number = normalized_number

        if session.root.parent == self.workspace:
            target_number = allocate_unique_project_number(
                self.workspace, normalized_number, current_root=session.root
            )
            if target_number != session.root.name:
                target_root = session.root.with_name(target_number)
                session.root.rename(target_root)
                session.root = target_root
                session.data.meta.project_number = target_number
                changed = True

        if changed:
            self.save_project(session)
