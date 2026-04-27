from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files

from src.core.project_manager import ProjectItem


@dataclass(frozen=True, slots=True)
class TemplateDefinition:
    id: str
    name: str
    scenario: str
    items: tuple[ProjectItem, ...]


class TemplateRepository:
    def __init__(self, templates: dict[str, list[TemplateDefinition]]) -> None:
        self.templates = templates

    @classmethod
    def load_builtin(cls) -> "TemplateRepository":
        payload = json.loads(
            files("src.templates")
            .joinpath("project_templates.json")
            .read_text(encoding="utf-8")
        )
        templates: dict[str, list[TemplateDefinition]] = {}

        for scenario, entries in payload.items():
            templates[scenario] = [
                TemplateDefinition(
                    id=entry["id"],
                    name=entry["name"],
                    scenario=scenario,
                    items=tuple(ProjectItem(**item) for item in entry["items"]),
                )
                for entry in entries
            ]
        return cls(templates=templates)

    def list_scenarios(self) -> list[str]:
        return sorted(self.templates.keys())

    def list_templates(self, scenario: str) -> list[TemplateDefinition]:
        return list(self.templates.get(scenario, []))

    def get_template(self, scenario: str, template_id: str) -> TemplateDefinition:
        for template in self.list_templates(scenario):
            if template.id == template_id:
                return template
        raise KeyError(f"Template not found: {scenario}/{template_id}")
