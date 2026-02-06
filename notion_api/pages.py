"""Opérations sur les pages Notion."""

from __future__ import annotations

from typing import Any

from notion_api.client import NotionClient
from notion_api.models import extract_plain_text


class PageManager:
    """Gère les opérations CRUD sur les pages Notion."""

    def __init__(self, client: NotionClient | None = None):
        self.client = client or NotionClient()

    # -- Lecture ----------------------------------------------------------------

    def get(self, page_id: str) -> dict[str, Any]:
        """Récupère une page par son ID."""
        return self.client.get(f"pages/{page_id}")

    def get_properties(self, page_id: str) -> dict[str, Any]:
        """Retourne les propriétés d'une page."""
        page = self.get(page_id)
        return page.get("properties", {})

    def get_title(self, page_id: str) -> str:
        """Retourne le titre d'une page."""
        props = self.get_properties(page_id)
        for prop in props.values():
            if prop.get("type") == "title":
                return extract_plain_text(prop)
        return ""

    def get_content(self, page_id: str) -> list[dict[str, Any]]:
        """Récupère tous les blocs enfants (contenu) d'une page."""
        return self.client.paginated_post(
            f"blocks/{page_id}/children",
            body={},
        )

    # -- Création ---------------------------------------------------------------

    def create(
        self,
        parent_page_id: str | None = None,
        parent_database_id: str | None = None,
        properties: dict[str, Any] | None = None,
        children: list[dict[str, Any]] | None = None,
        icon: str | None = None,
        cover_url: str | None = None,
    ) -> dict[str, Any]:
        """Crée une nouvelle page.

        La page peut être enfant d'une autre page ou d'une base de données.
        """
        if not parent_page_id and not parent_database_id:
            raise ValueError(
                "Spécifiez parent_page_id ou parent_database_id."
            )

        body: dict[str, Any] = {}

        if parent_page_id:
            body["parent"] = {"type": "page_id", "page_id": parent_page_id}
            if properties is None:
                properties = {
                    "title": {
                        "title": [
                            {"type": "text", "text": {"content": "Sans titre"}}
                        ]
                    }
                }
        else:
            body["parent"] = {
                "type": "database_id",
                "database_id": parent_database_id,
            }

        if properties:
            body["properties"] = properties
        if children:
            body["children"] = children
        if icon:
            body["icon"] = {"type": "emoji", "emoji": icon}
        if cover_url:
            body["cover"] = {"type": "external", "external": {"url": cover_url}}

        return self.client.post("pages", json=body)

    # -- Mise à jour ------------------------------------------------------------

    def update(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Met à jour les propriétés d'une page."""
        body: dict[str, Any] = {}
        if properties is not None:
            body["properties"] = properties
        if archived is not None:
            body["archived"] = archived
        if icon is not None:
            body["icon"] = {"type": "emoji", "emoji": icon}
        return self.client.patch(f"pages/{page_id}", json=body)

    def archive(self, page_id: str) -> dict[str, Any]:
        """Archive (supprime) une page."""
        return self.update(page_id, archived=True)

    def restore(self, page_id: str) -> dict[str, Any]:
        """Restaure une page archivée."""
        return self.update(page_id, archived=False)

    # -- Blocs (contenu de page) ------------------------------------------------

    def append_blocks(
        self, page_id: str, children: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Ajoute des blocs au contenu d'une page."""
        return self.client.patch(
            f"blocks/{page_id}/children", json={"children": children}
        )
