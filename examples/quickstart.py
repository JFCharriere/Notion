#!/usr/bin/env python3
"""Exemple de démarrage rapide — montre les opérations de base."""

from notion_api import NotionClient

# 1. Connexion (le token est lu depuis .env ou la variable d'environnement)
client = NotionClient()

# 2. Vérifier la connexion
me = client.get_me()
print(f"Connecté en tant que : {me['name']} ({me['type']})")

# 3. Lister les bases de données accessibles
print("\n--- Bases de données ---")
databases = client.list_databases()
for db in databases:
    title = "".join(t.get("plain_text", "") for t in db.get("title", []))
    print(f"  {db['id']}  {title}")

# 4. Lister les pages accessibles
print("\n--- Pages ---")
pages = client.list_pages()
for page in pages[:10]:  # Limiter à 10
    props = page.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            from notion_api.models import extract_plain_text

            title = extract_plain_text(prop)
            print(f"  {page['id']}  {title}")
            break
