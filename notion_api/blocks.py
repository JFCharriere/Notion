"""Constructeur de blocs Notion.

Fournit des méthodes simples pour créer les différents types de blocs
utilisables dans les pages Notion.
"""

from __future__ import annotations

from typing import Any


class BlockBuilder:
    """Fabrique de blocs Notion prêts à être insérés dans une page."""

    @staticmethod
    def _text_objects(text: str) -> list[dict[str, Any]]:
        return [{"type": "text", "text": {"content": text}}]

    # -- Texte ------------------------------------------------------------------

    @staticmethod
    def paragraph(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def heading_1(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def heading_2(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def heading_3(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    # -- Listes -----------------------------------------------------------------

    @staticmethod
    def bulleted_list_item(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def numbered_list_item(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def to_do(text: str, checked: bool = False) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "to_do",
            "to_do": {
                "rich_text": BlockBuilder._text_objects(text),
                "checked": checked,
            },
        }

    # -- Mise en forme ----------------------------------------------------------

    @staticmethod
    def toggle(text: str, children: list[dict] | None = None) -> dict[str, Any]:
        block: dict[str, Any] = {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }
        if children:
            block["toggle"]["children"] = children
        return block

    @staticmethod
    def callout(
        text: str, icon: str = "💡", color: str = "default"
    ) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": BlockBuilder._text_objects(text),
                "icon": {"type": "emoji", "emoji": icon},
                "color": color,
            },
        }

    @staticmethod
    def quote(text: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "quote",
            "quote": {
                "rich_text": BlockBuilder._text_objects(text),
            },
        }

    @staticmethod
    def divider() -> dict[str, Any]:
        return {"object": "block", "type": "divider", "divider": {}}

    @staticmethod
    def code(text: str, language: str = "python") -> dict[str, Any]:
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": BlockBuilder._text_objects(text),
                "language": language,
            },
        }

    # -- Médias -----------------------------------------------------------------

    @staticmethod
    def image(url: str, caption: str = "") -> dict[str, Any]:
        block: dict[str, Any] = {
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": url},
            },
        }
        if caption:
            block["image"]["caption"] = BlockBuilder._text_objects(caption)
        return block

    @staticmethod
    def bookmark(url: str, caption: str = "") -> dict[str, Any]:
        block: dict[str, Any] = {
            "object": "block",
            "type": "bookmark",
            "bookmark": {"url": url},
        }
        if caption:
            block["bookmark"]["caption"] = BlockBuilder._text_objects(caption)
        return block

    @staticmethod
    def embed(url: str) -> dict[str, Any]:
        return {
            "object": "block",
            "type": "embed",
            "embed": {"url": url},
        }

    # -- Table simple -----------------------------------------------------------

    @staticmethod
    def table(
        rows: list[list[str]],
        has_column_header: bool = True,
        has_row_header: bool = False,
    ) -> dict[str, Any]:
        """Crée un bloc tableau.

        Args:
            rows: Liste de lignes. Chaque ligne est une liste de chaînes.
            has_column_header: La première ligne est un en-tête.
            has_row_header: La première colonne est un en-tête.
        """
        if not rows:
            raise ValueError("Le tableau doit avoir au moins une ligne.")
        width = len(rows[0])

        table_rows = []
        for row in rows:
            cells = [
                [{"type": "text", "text": {"content": cell}}] for cell in row
            ]
            table_rows.append(
                {
                    "type": "table_row",
                    "table_row": {"cells": cells},
                }
            )

        return {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": width,
                "has_column_header": has_column_header,
                "has_row_header": has_row_header,
                "children": table_rows,
            },
        }
