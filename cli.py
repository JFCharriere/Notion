#!/usr/bin/env python3
"""Interface en ligne de commande pour le client Notion API.

Usage:
    python cli.py search "mon texte"
    python cli.py databases list
    python cli.py databases query <database_id>
    python cli.py databases create <parent_page_id> "Titre"
    python cli.py pages get <page_id>
    python cli.py pages create <parent_page_id> "Titre"
    python cli.py export csv <database_id> [output.csv]
    python cli.py export json <database_id> [output.json]
    python cli.py export markdown <database_id> [output.md]
    python cli.py import csv <database_id> <input.csv>
    python cli.py dashboard create <parent_page_id> "Titre" [db_id1,db_id2,...]
    python cli.py whoami
"""

from __future__ import annotations

import argparse
import json
import sys

from notion_api.client import NotionClient
from notion_api.databases import DatabaseManager
from notion_api.dashboard import DashboardBuilder
from notion_api.export import DataExporter
from notion_api.models import extract_plain_text
from notion_api.pages import PageManager


def _print_json(data, indent=2):
    """Affiche des données en JSON formaté."""
    print(json.dumps(data, indent=indent, ensure_ascii=False, default=str))


def cmd_whoami(args):
    client = NotionClient()
    info = client.get_me()
    _print_json(info)


def cmd_search(args):
    client = NotionClient()
    results = client.search(
        query=args.query,
        filter_type=args.type,
    )
    for item in results:
        obj_type = item.get("object", "")
        item_id = item.get("id", "")
        title_parts = []

        if obj_type == "page":
            for prop in item.get("properties", {}).values():
                if prop.get("type") == "title":
                    title_parts.append(extract_plain_text(prop))
        elif obj_type == "database":
            for t in item.get("title", []):
                title_parts.append(t.get("plain_text", ""))

        title = " ".join(title_parts) or "(sans titre)"
        print(f"[{obj_type}] {item_id}  {title}")


def cmd_db_list(args):
    db = DatabaseManager()
    databases = db.client.list_databases()
    for item in databases:
        item_id = item.get("id", "")
        title_parts = [t.get("plain_text", "") for t in item.get("title", [])]
        title = " ".join(title_parts) or "(sans titre)"
        print(f"{item_id}  {title}")


def cmd_db_get(args):
    db = DatabaseManager()
    data = db.get(args.database_id)
    _print_json(data)


def cmd_db_schema(args):
    db = DatabaseManager()
    schema = db.get_schema(args.database_id)
    for name, prop in schema.items():
        print(f"  {name}: {prop.get('type', '?')}")


def cmd_db_query(args):
    db = DatabaseManager()
    rows = db.query_as_dicts(args.database_id)
    _print_json(rows)


def cmd_db_create(args):
    db = DatabaseManager()
    result = db.create(
        parent_page_id=args.parent_page_id,
        title=args.title,
    )
    print(f"Base de données créée : {result['id']}")
    print(f"URL : {result.get('url', '')}")


def cmd_page_get(args):
    pm = PageManager()
    page = pm.get(args.page_id)
    _print_json(page)


def cmd_page_content(args):
    exporter = DataExporter()
    text = exporter.extract_page_as_text(args.page_id)
    print(text)


def cmd_page_create(args):
    pm = PageManager()
    from notion_api.models import title

    page = pm.create(
        parent_page_id=args.parent_page_id,
        properties={"title": title(args.title)},
    )
    print(f"Page créée : {page['id']}")
    print(f"URL : {page.get('url', '')}")


def cmd_export_csv(args):
    exporter = DataExporter()
    csv_content = exporter.to_csv(
        args.database_id,
        output_path=args.output,
    )
    if not args.output:
        print(csv_content)
    else:
        print(f"Export CSV enregistré : {args.output}")


def cmd_export_json(args):
    exporter = DataExporter()
    json_content = exporter.to_json(
        args.database_id,
        output_path=args.output,
    )
    if not args.output:
        print(json_content)
    else:
        print(f"Export JSON enregistré : {args.output}")


def cmd_export_markdown(args):
    exporter = DataExporter()
    md_content = exporter.to_markdown_table(
        args.database_id,
        output_path=args.output,
    )
    if not args.output:
        print(md_content)
    else:
        print(f"Export Markdown enregistré : {args.output}")


def cmd_import_csv(args):
    exporter = DataExporter()
    results = exporter.import_csv(
        database_id=args.database_id,
        csv_path=args.csv_file,
    )
    print(f"{len(results)} lignes importées.")


def cmd_dashboard_create(args):
    builder = DashboardBuilder()
    db_ids = [d.strip() for d in args.database_ids.split(",")] if args.database_ids else []
    dashboard = builder.create_full_dashboard(
        parent_page_id=args.parent_page_id,
        title=args.title,
        database_ids=db_ids,
    )
    print(f"Dashboard créé : {dashboard['id']}")
    print(f"URL : {dashboard.get('url', '')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Client CLI pour l'API Notion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commande")

    # whoami
    subparsers.add_parser("whoami", help="Affiche les infos de l'intégration")

    # search
    p_search = subparsers.add_parser("search", help="Recherche dans Notion")
    p_search.add_argument("query", help="Texte à rechercher")
    p_search.add_argument(
        "--type", choices=["page", "database"], default=None,
        help="Filtrer par type",
    )

    # databases
    p_db = subparsers.add_parser("databases", aliases=["db"], help="Bases de données")
    db_sub = p_db.add_subparsers(dest="db_command")

    db_sub.add_parser("list", help="Lister les bases de données")

    p_db_get = db_sub.add_parser("get", help="Détails d'une base de données")
    p_db_get.add_argument("database_id")

    p_db_schema = db_sub.add_parser("schema", help="Schéma d'une base de données")
    p_db_schema.add_argument("database_id")

    p_db_query = db_sub.add_parser("query", help="Interroger une base de données")
    p_db_query.add_argument("database_id")

    p_db_create = db_sub.add_parser("create", help="Créer une base de données")
    p_db_create.add_argument("parent_page_id")
    p_db_create.add_argument("title")

    # pages
    p_pages = subparsers.add_parser("pages", help="Pages")
    pages_sub = p_pages.add_subparsers(dest="page_command")

    p_page_get = pages_sub.add_parser("get", help="Détails d'une page")
    p_page_get.add_argument("page_id")

    p_page_content = pages_sub.add_parser("content", help="Contenu d'une page")
    p_page_content.add_argument("page_id")

    p_page_create = pages_sub.add_parser("create", help="Créer une page")
    p_page_create.add_argument("parent_page_id")
    p_page_create.add_argument("title")

    # export
    p_export = subparsers.add_parser("export", help="Exporter des données")
    export_sub = p_export.add_subparsers(dest="export_format")

    for fmt in ("csv", "json", "markdown"):
        p_fmt = export_sub.add_parser(fmt, help=f"Export {fmt.upper()}")
        p_fmt.add_argument("database_id")
        p_fmt.add_argument("output", nargs="?", default=None, help="Fichier de sortie")

    # import
    p_import = subparsers.add_parser("import", help="Importer des données")
    import_sub = p_import.add_subparsers(dest="import_format")
    p_import_csv = import_sub.add_parser("csv", help="Importer un CSV")
    p_import_csv.add_argument("database_id")
    p_import_csv.add_argument("csv_file")

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="Dashboards")
    dash_sub = p_dash.add_subparsers(dest="dash_command")
    p_dash_create = dash_sub.add_parser("create", help="Créer un dashboard")
    p_dash_create.add_argument("parent_page_id")
    p_dash_create.add_argument("title")
    p_dash_create.add_argument(
        "database_ids", nargs="?", default="",
        help="IDs de bases de données séparés par des virgules",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "whoami": cmd_whoami,
        "search": cmd_search,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
        return

    if args.command in ("databases", "db"):
        db_dispatch = {
            "list": cmd_db_list,
            "get": cmd_db_get,
            "schema": cmd_db_schema,
            "query": cmd_db_query,
            "create": cmd_db_create,
        }
        if args.db_command in db_dispatch:
            db_dispatch[args.db_command](args)
        else:
            print("Sous-commande manquante. Utilisez: list, get, schema, query, create")

    elif args.command == "pages":
        page_dispatch = {
            "get": cmd_page_get,
            "content": cmd_page_content,
            "create": cmd_page_create,
        }
        if args.page_command in page_dispatch:
            page_dispatch[args.page_command](args)
        else:
            print("Sous-commande manquante. Utilisez: get, content, create")

    elif args.command == "export":
        export_dispatch = {
            "csv": cmd_export_csv,
            "json": cmd_export_json,
            "markdown": cmd_export_markdown,
        }
        if args.export_format in export_dispatch:
            export_dispatch[args.export_format](args)
        else:
            print("Format manquant. Utilisez: csv, json, markdown")

    elif args.command == "import":
        if args.import_format == "csv":
            cmd_import_csv(args)
        else:
            print("Format manquant. Utilisez: csv")

    elif args.command == "dashboard":
        if args.dash_command == "create":
            cmd_dashboard_create(args)
        else:
            print("Sous-commande manquante. Utilisez: create")


if __name__ == "__main__":
    main()
