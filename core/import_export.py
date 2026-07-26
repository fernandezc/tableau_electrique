from __future__ import annotations


def _normalize_project_entry(project, default_name):
    if not isinstance(project, dict) or "circuits" not in project:
        raise ValueError("Format projet invalide")
    return {
        "name": project.get("name") or default_name,
        "circuits": project.get("circuits", []),
        "metadata": project.get("metadata") or {},
    }


def normalize_imported_projects(payload, default_name="Projet importé"):
    """Normalise les formats JSON supportés vers une liste de projets."""
    if isinstance(payload, dict):
        if isinstance(payload.get("projects"), list):
            return [
                _normalize_project_entry(project, default_name)
                for project in payload["projects"]
            ]
        if "circuits" in payload:
            return [_normalize_project_entry(payload, default_name)]
        raise ValueError("Format JSON non reconnu")

    if isinstance(payload, list):
        if not payload:
            return []
        if all(isinstance(item, dict) and "circuits" in item for item in payload):
            return [
                _normalize_project_entry(project, default_name)
                for project in payload
            ]
        if all(isinstance(item, dict) for item in payload):
            return [{
                "name": default_name,
                "circuits": payload,
                "metadata": {},
            }]

    raise ValueError("Format JSON non reconnu")
