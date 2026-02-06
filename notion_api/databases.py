"""Opérations sur les bases de données Notion."""

from __future__ import annotations

from typing import Any

from notion_api.client import NotionClient
from notion_api.models import extract_property_value


class DatabaseManager:
    """Gère les opérations CRUD sur les bases de données Notion."""

    def __init__(self, client: NotionClient | None = None):
        self.client = client or NotionClient()

    # -- Lecture ----------------------------------------------------------------

    def get(self, database_id: str) -> dict[str, Any]:
        """Récupère les métadonnées d'une base de données."""
        return self.client.get(f"databases/{database_id}")

    def get_schema(self, database_id: str) -> dict[str, Any]:
        """Retourne le schéma (propriétés) d'une base de données."""
        db = self.get(database_id)
        return db.get("properties", {})

    def query(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Interroge une base de données avec filtres et tri optionnels."""
        body: dict[str, Any] = {}
        if filter:
            body["filter"] = filter
        if sorts:
            body["sorts"] = sorts
        return self.client.paginated_post(
            f"databases/{database_id}/query", body
        )

    def query_as_dicts(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, str | Any]]:
        """Interroge une DB et retourne les résultats comme liste de dicts Python."""
        pages = self.query(database_id, filter=filter, sorts=sorts)
        rows = []
        for page in pages:
            row: dict[str, Any] = {"id": page["id"]}
            for name, prop in page.get("properties", {}).items():
                row[name] = extract_property_value(prop)
            rows.append(row)
        return rows

    # -- Création ---------------------------------------------------------------

    def create(
        self,
        parent_page_id: str,
        title: str,
        properties: dict[str, Any] | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Crée une nouvelle base de données dans une page parente.

        Args:
            parent_page_id: ID de la page parente.
            title: Titre de la base de données.
            properties: Schéma des propriétés. Doit contenir au moins une
                propriété de type ``title``. Si omis, une colonne "Nom" est
                créée automatiquement.
            icon: Emoji optionnel pour l'icône.
        """
        if properties is None:
            properties = {"Nom": {"title": {}}}

        body: dict[str, Any] = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": [{"type": "text", "text": {"content": title}}],
            "properties": properties,
        }
        if icon:
            body["icon"] = {"type": "emoji", "emoji": icon}

        return self.client.post("databases", json=body)

    # -- Mise à jour ------------------------------------------------------------

    def update(
        self,
        database_id: str,
        title: str | None = None,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Met à jour le titre ou le schéma d'une base de données."""
        body: dict[str, Any] = {}
        if title is not None:
            body["title"] = [{"type": "text", "text": {"content": title}}]
        if properties is not None:
            body["properties"] = properties
        return self.client.patch(f"databases/{database_id}", json=body)

    def add_column(
        self, database_id: str, column_schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Ajoute une ou plusieurs colonnes à une base de données existante."""
        return self.update(database_id, properties=column_schema)

    # -- Insertion de données ---------------------------------------------------

    def insert_row(
        self, database_id: str, properties: dict[str, Any]
    ) -> dict[str, Any]:
        """Insère une ligne (page) dans une base de données."""
        body = {
            "parent": {"database_id": database_id},
            "properties": properties,
        }
        return self.client.post("pages", json=body)

    def insert_rows(
        self,
        database_id: str,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Insère plusieurs lignes dans une base de données.

        Chaque élément de ``rows`` est un dict de propriétés au format Notion.
        """
        results = []
        for row_props in rows:
            result = self.insert_row(database_id, row_props)
            results.append(result)
        return results

    # -- Filtres helpers --------------------------------------------------------

    @staticmethod
    def filter_equals(property_name: str, property_type: str, value: Any) -> dict:
        """Construit un filtre d'égalité simple."""
        return {"property": property_name, property_type: {"equals": value}}

    @staticmethod
    def filter_contains(property_name: str, value: str) -> dict:
        """Construit un filtre 'contient' pour les propriétés texte."""
        return {
            "property": property_name,
            "rich_text": {"contains": value},
        }

    @staticmethod
    def filter_and(*filters: dict) -> dict:
        return {"and": list(filters)}

    @staticmethod
    def filter_or(*filters: dict) -> dict:
        return {"or": list(filters)}

    @staticmethod
    def sort_ascending(property_name: str) -> dict:
        return {"property": property_name, "direction": "ascending"}

    @staticmethod
    def sort_descending(property_name: str) -> dict:
        return {"property": property_name, "direction": "descending"}
