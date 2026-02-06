#!/usr/bin/env python3
"""Exemple : importer un fichier CSV dans une base de données Notion."""

from notion_api import DataExporter, NotionClient
from notion_api.models import checkbox, number, select, title

# Remplacez par l'ID de votre base de données
DATABASE_ID = "VOTRE_DATABASE_ID_ICI"
CSV_FILE = "donnees.csv"

client = NotionClient()
exporter = DataExporter(client)

# Import simple (première colonne = titre, reste = texte)
# results = exporter.import_csv(DATABASE_ID, CSV_FILE)

# Import avec mapping de colonnes personnalisé
column_mapping = {
    "Nom": lambda v: title(v),
    "Prix": lambda v: number(float(v)) if v else number(0),
    "Catégorie": lambda v: select(v) if v else select("Autre"),
    "Disponible": lambda v: checkbox(v.lower() in ("oui", "true", "1")),
}

results = exporter.import_csv(
    database_id=DATABASE_ID,
    csv_path=CSV_FILE,
    column_mapping=column_mapping,
)
print(f"{len(results)} lignes importées depuis {CSV_FILE}")
