"""Constructeur de dashboards Notion.

Permet de créer des pages « dashboard » composées de bases de données
liées, de résumés, de métriques et de mises en page structurées.
"""

from __future__ import annotations

from typing import Any

from notion_api.blocks import BlockBuilder
from notion_api.client import NotionClient
from notion_api.databases import DatabaseManager
from notion_api.models import extract_property_value
from notion_api.pages import PageManager


class DashboardBuilder:
    """Crée des dashboards structurés dans Notion."""

    def __init__(self, client: NotionClient | None = None):
        self.client = client or NotionClient()
        self.pages = PageManager(self.client)
        self.databases = DatabaseManager(self.client)
        self.blocks = BlockBuilder()

    def create_dashboard_page(
        self,
        parent_page_id: str,
        title: str,
        icon: str = "📊",
        cover_url: str | None = None,
    ) -> dict[str, Any]:
        """Crée une page de dashboard vide."""
        return self.pages.create(
            parent_page_id=parent_page_id,
            properties={
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
            icon=icon,
            cover_url=cover_url,
        )

    def add_metric_section(
        self,
        page_id: str,
        title: str,
        metrics: dict[str, str | int | float],
    ) -> dict[str, Any]:
        """Ajoute une section de métriques clés au dashboard.

        Args:
            page_id: ID de la page dashboard.
            title: Titre de la section.
            metrics: Dict {nom_métrique: valeur}.
        """
        children = [self.blocks.heading_2(title)]
        children.append(self.blocks.divider())

        # Affichage sous forme de callouts
        for name, value in metrics.items():
            children.append(
                self.blocks.callout(f"{name}: {value}", icon="📈")
            )

        children.append(self.blocks.divider())
        return self.pages.append_blocks(page_id, children)

    def add_summary_table(
        self,
        page_id: str,
        title: str,
        headers: list[str],
        rows: list[list[str]],
    ) -> dict[str, Any]:
        """Ajoute un tableau de synthèse au dashboard."""
        children = [
            self.blocks.heading_2(title),
            self.blocks.table([headers, *rows], has_column_header=True),
        ]
        return self.pages.append_blocks(page_id, children)

    def add_linked_database(
        self,
        page_id: str,
        database_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Ajoute une vue liée à une base de données existante (linked database)."""
        children: list[dict[str, Any]] = []
        if title:
            children.append(self.blocks.heading_2(title))

        # Bloc "linked database" (non documenté officiellement mais supporté)
        # On utilise un embed de la DB via son URL publique ou un child_database
        # L'API ne supporte pas les linked databases nativement, on crée donc
        # un callout avec un lien + un résumé des données
        db_info = self.databases.get(database_id)
        db_title = ""
        for t in db_info.get("title", []):
            db_title += t.get("plain_text", "")
        db_url = db_info.get("url", "")

        children.append(
            self.blocks.callout(f"Base de données : {db_title}", icon="🗄️")
        )
        if db_url:
            children.append(self.blocks.bookmark(db_url, caption=db_title))

        return self.pages.append_blocks(page_id, children)

    def add_database_summary(
        self,
        page_id: str,
        database_id: str,
        title: str,
        group_by: str | None = None,
        count_label: str = "Total",
    ) -> dict[str, Any]:
        """Ajoute un résumé agrégé d'une base de données.

        Si ``group_by`` est fourni, affiche le compte par catégorie.
        Sinon, affiche simplement le nombre total d'entrées.
        """
        rows = self.databases.query_as_dicts(database_id)
        children = [self.blocks.heading_2(title)]

        if group_by:
            counts: dict[str, int] = {}
            for row in rows:
                key = str(row.get(group_by, "N/A"))
                counts[key] = counts.get(key, 0) + 1

            table_rows = [[cat, str(count)] for cat, count in counts.items()]
            children.append(
                self.blocks.table(
                    [[group_by, count_label], *table_rows],
                    has_column_header=True,
                )
            )
        else:
            children.append(
                self.blocks.callout(
                    f"{count_label} : {len(rows)} entrées", icon="📊"
                )
            )

        return self.pages.append_blocks(page_id, children)

    def create_full_dashboard(
        self,
        parent_page_id: str,
        title: str,
        database_ids: list[str],
        metrics: dict[str, str | int | float] | None = None,
        icon: str = "📊",
    ) -> dict[str, Any]:
        """Crée un dashboard complet avec métriques et résumés de bases de données.

        Args:
            parent_page_id: Page parente du dashboard.
            title: Titre du dashboard.
            database_ids: IDs des bases de données à inclure.
            metrics: Métriques clés à afficher en haut.
            icon: Emoji pour l'icône.

        Returns:
            La page dashboard créée.
        """
        dashboard = self.create_dashboard_page(
            parent_page_id, title, icon=icon
        )
        dashboard_id = dashboard["id"]

        if metrics:
            self.add_metric_section(dashboard_id, "Métriques clés", metrics)

        for db_id in database_ids:
            db_info = self.databases.get(db_id)
            db_title = ""
            for t in db_info.get("title", []):
                db_title += t.get("plain_text", "")

            self.add_database_summary(
                dashboard_id,
                db_id,
                title=db_title or "Base de données",
            )

        return dashboard
