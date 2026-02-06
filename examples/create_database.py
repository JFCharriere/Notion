#!/usr/bin/env python3
"""Exemple : créer une base de données et y insérer des données."""

from notion_api import DatabaseManager, NotionClient
from notion_api.models import (
    checkbox,
    date_prop,
    number,
    rich_text,
    schema_checkbox,
    schema_date,
    schema_number,
    schema_rich_text,
    schema_select,
    schema_title,
    select,
    title,
)

# Remplacez par l'ID d'une page parente dans votre espace Notion
PARENT_PAGE_ID = "VOTRE_PAGE_ID_ICI"

client = NotionClient()
db = DatabaseManager(client)

# 1. Créer la base de données avec un schéma personnalisé
schema = {
    **schema_title("Nom"),
    **schema_rich_text("Description"),
    **schema_number("Prix", fmt="euro"),
    **schema_select("Catégorie", options=["Électronique", "Livre", "Vêtement"]),
    **schema_checkbox("En stock"),
    **schema_date("Date d'ajout"),
}

result = db.create(
    parent_page_id=PARENT_PAGE_ID,
    title="Catalogue Produits",
    properties=schema,
    icon="🛍️",
)
database_id = result["id"]
print(f"Base de données créée : {database_id}")

# 2. Insérer des données
produits = [
    {
        "Nom": title("MacBook Pro 14"),
        "Description": rich_text("Ordinateur portable Apple M3"),
        "Prix": number(2399),
        "Catégorie": select("Électronique"),
        "En stock": checkbox(True),
        "Date d'ajout": date_prop("2025-01-15"),
    },
    {
        "Nom": title("Clean Code"),
        "Description": rich_text("Robert C. Martin — Guide du code propre"),
        "Prix": number(35),
        "Catégorie": select("Livre"),
        "En stock": checkbox(True),
        "Date d'ajout": date_prop("2025-02-01"),
    },
    {
        "Nom": title("T-shirt Python"),
        "Description": rich_text("T-shirt noir logo Python"),
        "Prix": number(25),
        "Catégorie": select("Vêtement"),
        "En stock": checkbox(False),
        "Date d'ajout": date_prop("2025-03-10"),
    },
]

results = db.insert_rows(database_id, produits)
print(f"{len(results)} produits insérés.")

# 3. Lire les données
print("\n--- Contenu de la base ---")
rows = db.query_as_dicts(database_id)
for row in rows:
    print(f"  {row.get('Nom', '?')} — {row.get('Prix', '?')}€ [{row.get('Catégorie', '')}]")
