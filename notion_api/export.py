"""Export et extraction de données depuis Notion."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from notion_api.client import NotionClient
from notion_api.databases import DatabaseManager
from notion_api.models import extract_plain_text, extract_property_value


class DataExporter:
    """Exporte des données depuis Notion vers différents formats."""

    def __init__(self, client: NotionClient | None = None):
        self.client = client or NotionClient()
        self.databases = DatabaseManager(self.client)

    # -- Extraction brute -------------------------------------------------------

    def extract_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Extrait toutes les données d'une base de données sous forme de dicts."""
        return self.databases.query_as_dicts(
            database_id, filter=filter, sorts=sorts
        )

    def extract_page_content(self, page_id: str) -> list[dict[str, Any]]:
        """Extrait le contenu brut (blocs) d'une page."""
        return self.client.paginated_post(
            f"blocks/{page_id}/children", body={}
        )

    def extract_page_as_text(self, page_id: str) -> str:
        """Extrait le contenu d'une page sous forme de texte brut."""
        blocks = self.extract_page_content(page_id)
        lines = []
        for block in blocks:
            btype = block.get("type", "")
            content = block.get(btype, {})

            if btype == "divider":
                lines.append("---")
                continue

            rich_text = content.get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)

            if btype == "heading_1":
                lines.append(f"# {text}")
            elif btype == "heading_2":
                lines.append(f"## {text}")
            elif btype == "heading_3":
                lines.append(f"### {text}")
            elif btype == "bulleted_list_item":
                lines.append(f"- {text}")
            elif btype == "numbered_list_item":
                lines.append(f"1. {text}")
            elif btype == "to_do":
                checked = "x" if content.get("checked") else " "
                lines.append(f"- [{checked}] {text}")
            elif btype == "code":
                lang = content.get("language", "")
                lines.append(f"```{lang}\n{text}\n```")
            elif btype == "quote":
                lines.append(f"> {text}")
            elif text:
                lines.append(text)

        return "\n".join(lines)

    # -- Export CSV -------------------------------------------------------------

    def to_csv(
        self,
        database_id: str,
        output_path: str | Path | None = None,
        filter: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> str:
        """Exporte une base de données au format CSV.

        Args:
            database_id: ID de la base de données.
            output_path: Chemin du fichier de sortie. Si None, retourne le CSV
                sous forme de chaîne.
            filter: Filtre Notion optionnel.
            columns: Colonnes à inclure. Si None, inclut toutes les colonnes.

        Returns:
            Le contenu CSV sous forme de chaîne.
        """
        rows = self.extract_database(database_id, filter=filter)
        if not rows:
            return ""

        if columns:
            fieldnames = ["id"] + columns
        else:
            all_keys: list[str] = []
            for row in rows:
                for key in row:
                    if key not in all_keys:
                        all_keys.append(key)
            fieldnames = all_keys

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            clean_row = {}
            for key in fieldnames:
                val = row.get(key, "")
                if isinstance(val, list):
                    clean_row[key] = ", ".join(str(v) for v in val)
                elif isinstance(val, dict):
                    clean_row[key] = json.dumps(val, ensure_ascii=False)
                else:
                    clean_row[key] = val
            writer.writerow(clean_row)

        csv_content = output.getvalue()

        if output_path:
            Path(output_path).write_text(csv_content, encoding="utf-8")

        return csv_content

    # -- Export JSON -------------------------------------------------------------

    def to_json(
        self,
        database_id: str,
        output_path: str | Path | None = None,
        filter: dict[str, Any] | None = None,
        indent: int = 2,
    ) -> str:
        """Exporte une base de données au format JSON.

        Args:
            database_id: ID de la base de données.
            output_path: Chemin du fichier de sortie.
            filter: Filtre Notion optionnel.
            indent: Indentation du JSON.

        Returns:
            Le contenu JSON sous forme de chaîne.
        """
        rows = self.extract_database(database_id, filter=filter)
        json_content = json.dumps(rows, ensure_ascii=False, indent=indent, default=str)

        if output_path:
            Path(output_path).write_text(json_content, encoding="utf-8")

        return json_content

    # -- Export Markdown --------------------------------------------------------

    def to_markdown_table(
        self,
        database_id: str,
        output_path: str | Path | None = None,
        filter: dict[str, Any] | None = None,
        columns: list[str] | None = None,
    ) -> str:
        """Exporte une base de données sous forme de tableau Markdown.

        Returns:
            Le tableau Markdown sous forme de chaîne.
        """
        rows = self.extract_database(database_id, filter=filter)
        if not rows:
            return ""

        if columns:
            headers = columns
        else:
            headers = [k for k in rows[0] if k != "id"]

        lines = []
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")

        for row in rows:
            values = []
            for h in headers:
                val = row.get(h, "")
                if isinstance(val, list):
                    val = ", ".join(str(v) for v in val)
                elif isinstance(val, dict):
                    val = json.dumps(val, ensure_ascii=False)
                values.append(str(val).replace("|", "\\|"))
            lines.append("| " + " | ".join(values) + " |")

        md_content = "\n".join(lines)

        if output_path:
            Path(output_path).write_text(md_content, encoding="utf-8")

        return md_content

    # -- Import CSV -> Notion ---------------------------------------------------

    def import_csv(
        self,
        database_id: str,
        csv_path: str | Path,
        column_mapping: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Importe un fichier CSV dans une base de données Notion.

        Args:
            database_id: ID de la base de données cible.
            csv_path: Chemin du fichier CSV.
            column_mapping: Dict {nom_colonne_csv: fonction_de_conversion}.
                La fonction reçoit la valeur string du CSV et retourne
                un dict propriété Notion. Si None, tout est traité comme
                rich_text sauf la première colonne (title).

        Returns:
            Liste des pages créées.
        """
        from notion_api.models import rich_text, title

        path = Path(csv_path)
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []

            results = []
            for row_data in reader:
                properties: dict[str, Any] = {}
                for i, col in enumerate(fieldnames):
                    value = row_data.get(col, "")
                    if column_mapping and col in column_mapping:
                        properties[col] = column_mapping[col](value)
                    elif i == 0:
                        properties[col] = title(value)
                    else:
                        properties[col] = rich_text(value)

                result = self.databases.insert_row(database_id, properties)
                results.append(result)

            return results
