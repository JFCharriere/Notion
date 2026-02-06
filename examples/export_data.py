#!/usr/bin/env python3
"""Exemple : exporter des données depuis une base de données Notion."""

from notion_api import DataExporter, NotionClient

# Remplacez par l'ID de votre base de données
DATABASE_ID = "VOTRE_DATABASE_ID_ICI"

client = NotionClient()
exporter = DataExporter(client)

# 1. Export CSV
print("--- Export CSV ---")
csv_content = exporter.to_csv(DATABASE_ID, output_path="export.csv")
print(f"Fichier export.csv créé ({len(csv_content)} caractères)")

# 2. Export JSON
print("\n--- Export JSON ---")
json_content = exporter.to_json(DATABASE_ID, output_path="export.json")
print(f"Fichier export.json créé ({len(json_content)} caractères)")

# 3. Export Markdown
print("\n--- Export Markdown ---")
md_content = exporter.to_markdown_table(DATABASE_ID, output_path="export.md")
print(md_content)

# 4. Extraction d'une page en texte brut
# PAGE_ID = "VOTRE_PAGE_ID_ICI"
# text = exporter.extract_page_as_text(PAGE_ID)
# print(text)
