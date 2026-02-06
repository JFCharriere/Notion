"""Helpers pour construire les propriétés Notion.

Chaque fonction retourne un dict compatible avec l'API Notion, utilisable
directement dans les payloads de création/mise à jour de pages ou de databases.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


# =============================================================================
# Propriétés de PAGE (valeurs)
# =============================================================================


def title(text: str) -> dict[str, Any]:
    """Propriété titre."""
    return {"title": [{"type": "text", "text": {"content": text}}]}


def rich_text(text: str) -> dict[str, Any]:
    """Propriété texte enrichi."""
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


def number(value: int | float) -> dict[str, Any]:
    return {"number": value}


def checkbox(value: bool) -> dict[str, Any]:
    return {"checkbox": value}


def select(name: str) -> dict[str, Any]:
    return {"select": {"name": name}}


def multi_select(*names: str) -> dict[str, Any]:
    return {"multi_select": [{"name": n} for n in names]}


def status(name: str) -> dict[str, Any]:
    return {"status": {"name": name}}


def date_prop(
    start: str | date | datetime,
    end: str | date | datetime | None = None,
) -> dict[str, Any]:
    """Propriété date. Accepte des chaînes ISO ou des objets date/datetime."""
    d: dict[str, Any] = {"start": str(start)}
    if end:
        d["end"] = str(end)
    return {"date": d}


def url(value: str) -> dict[str, Any]:
    return {"url": value}


def email(value: str) -> dict[str, Any]:
    return {"email": value}


def phone_number(value: str) -> dict[str, Any]:
    return {"phone_number": value}


def relation(*page_ids: str) -> dict[str, Any]:
    return {"relation": [{"id": pid} for pid in page_ids]}


def people(*user_ids: str) -> dict[str, Any]:
    return {"people": [{"object": "user", "id": uid} for uid in user_ids]}


# =============================================================================
# Schémas de propriétés pour DATABASES
# =============================================================================


def schema_title(name: str) -> dict[str, Any]:
    """Colonne titre pour un schéma de base de données."""
    return {name: {"title": {}}}


def schema_rich_text(name: str) -> dict[str, Any]:
    return {name: {"rich_text": {}}}


def schema_number(name: str, fmt: str = "number") -> dict[str, Any]:
    return {name: {"number": {"format": fmt}}}


def schema_select(name: str, options: list[str] | None = None) -> dict[str, Any]:
    prop: dict[str, Any] = {"select": {}}
    if options:
        prop["select"]["options"] = [{"name": o} for o in options]
    return {name: prop}


def schema_multi_select(
    name: str, options: list[str] | None = None
) -> dict[str, Any]:
    prop: dict[str, Any] = {"multi_select": {}}
    if options:
        prop["multi_select"]["options"] = [{"name": o} for o in options]
    return {name: prop}


def schema_status(name: str) -> dict[str, Any]:
    return {name: {"status": {}}}


def schema_date(name: str) -> dict[str, Any]:
    return {name: {"date": {}}}


def schema_checkbox(name: str) -> dict[str, Any]:
    return {name: {"checkbox": {}}}


def schema_url(name: str) -> dict[str, Any]:
    return {name: {"url": {}}}


def schema_email(name: str) -> dict[str, Any]:
    return {name: {"email": {}}}


def schema_phone(name: str) -> dict[str, Any]:
    return {name: {"phone_number": {}}}


def schema_relation(name: str, database_id: str) -> dict[str, Any]:
    return {name: {"relation": {"database_id": database_id}}}


# =============================================================================
# Utilitaires de lecture
# =============================================================================


def extract_plain_text(prop: dict[str, Any]) -> str:
    """Extrait le texte brut d'une propriété title ou rich_text."""
    ptype = prop.get("type", "")
    items = prop.get(ptype, [])
    if isinstance(items, list):
        return "".join(item.get("plain_text", "") for item in items)
    return str(items) if items is not None else ""


def extract_property_value(prop: dict[str, Any]) -> Any:
    """Extrait la valeur Python d'une propriété Notion (tout type)."""
    ptype = prop.get("type", "")

    if ptype in ("title", "rich_text"):
        return extract_plain_text(prop)
    if ptype == "number":
        return prop.get("number")
    if ptype == "checkbox":
        return prop.get("checkbox")
    if ptype == "select":
        sel = prop.get("select")
        return sel["name"] if sel else None
    if ptype == "multi_select":
        return [o["name"] for o in prop.get("multi_select", [])]
    if ptype == "status":
        st = prop.get("status")
        return st["name"] if st else None
    if ptype == "date":
        d = prop.get("date")
        return d if d else None
    if ptype == "url":
        return prop.get("url")
    if ptype == "email":
        return prop.get("email")
    if ptype == "phone_number":
        return prop.get("phone_number")
    if ptype == "relation":
        return [r["id"] for r in prop.get("relation", [])]
    if ptype == "people":
        return [p["id"] for p in prop.get("people", [])]
    if ptype == "formula":
        formula = prop.get("formula", {})
        return formula.get(formula.get("type", ""))
    if ptype == "rollup":
        rollup = prop.get("rollup", {})
        return rollup.get(rollup.get("type", ""))
    if ptype == "created_time":
        return prop.get("created_time")
    if ptype == "last_edited_time":
        return prop.get("last_edited_time")

    return prop.get(ptype)
