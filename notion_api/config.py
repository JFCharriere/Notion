"""Gestion de la configuration pour le client Notion."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Cherche un fichier .env dans le répertoire courant ou le répertoire parent
_env_path = Path(".env")
if not _env_path.exists():
    _env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "")
NOTION_API_VERSION = os.getenv("NOTION_API_VERSION", "2022-06-28")
NOTION_BASE_URL = "https://api.notion.com/v1"


def get_token() -> str:
    """Retourne le token API Notion, ou lève une erreur s'il n'est pas configuré."""
    token = NOTION_API_TOKEN
    if not token:
        raise ValueError(
            "NOTION_API_TOKEN non configuré. "
            "Créez un fichier .env avec NOTION_API_TOKEN=secret_xxx "
            "ou définissez la variable d'environnement."
        )
    return token
