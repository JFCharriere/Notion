"""Client HTTP de base pour l'API Notion."""

from __future__ import annotations

import re
import time
from typing import Any

import requests


def normalize_id(raw_id: str) -> str:
    """Convertit un ID Notion (avec ou sans tirets) au format UUID standard."""
    clean = raw_id.strip().replace("-", "")
    if len(clean) == 32 and re.fullmatch(r"[0-9a-fA-F]+", clean):
        return f"{clean[:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:]}"
    return raw_id

from notion_api.config import NOTION_API_VERSION, NOTION_BASE_URL, get_token


class NotionClient:
    """Client bas niveau pour interagir avec l'API REST de Notion.

    Gère l'authentification, les requêtes paginées et le rate-limiting.
    """

    def __init__(self, token: str | None = None):
        self.token = token or get_token()
        self.base_url = NOTION_BASE_URL
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            }
        )

    # -- Méthodes HTTP de base --------------------------------------------------

    def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Effectue une requête HTTP avec gestion du rate-limiting."""
        # Normalise les IDs dans l'endpoint (ex: databases/abc123... → databases/abc-123-...)
        parts = endpoint.lstrip("/").split("/")
        parts = [normalize_id(p) if len(p.replace("-", "")) == 32 else p for p in parts]
        endpoint = "/".join(parts)
        url = f"{self.base_url}/{endpoint}"
        retries = 0
        max_retries = 3

        while True:
            response = self.session.request(method, url, **kwargs)

            if response.status_code == 429:
                retries += 1
                if retries > max_retries:
                    response.raise_for_status()
                wait = float(
                    response.headers.get("Retry-After", 2**retries)
                )
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

    def get(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("POST", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> dict[str, Any]:
        return self._request("DELETE", endpoint, **kwargs)

    # -- Pagination -------------------------------------------------------------

    def paginated_post(
        self, endpoint: str, body: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Effectue une requête POST paginée et retourne tous les résultats."""
        body = body or {}
        results: list[dict[str, Any]] = []
        has_more = True
        next_cursor: str | None = None

        while has_more:
            if next_cursor:
                body["start_cursor"] = next_cursor
            data = self.post(endpoint, json=body)
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return results

    def paginated_get(
        self, endpoint: str
    ) -> list[dict[str, Any]]:
        """Effectue une requête GET paginée et retourne tous les résultats."""
        results: list[dict[str, Any]] = []
        has_more = True
        next_cursor: str | None = None

        while has_more:
            params: dict[str, str] = {}
            if next_cursor:
                params["start_cursor"] = next_cursor
            data = self.get(endpoint, params=params)
            results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            next_cursor = data.get("next_cursor")

        return results

    # -- Raccourcis pratiques ---------------------------------------------------

    def search(
        self,
        query: str = "",
        filter_type: str | None = None,
        sort_direction: str = "descending",
        sort_timestamp: str = "last_edited_time",
    ) -> list[dict[str, Any]]:
        """Recherche dans l'espace de travail Notion."""
        body: dict[str, Any] = {}
        if query:
            body["query"] = query
        if filter_type in ("database", "page"):
            body["filter"] = {"value": filter_type, "property": "object"}
        body["sort"] = {
            "direction": sort_direction,
            "timestamp": sort_timestamp,
        }
        return self.paginated_post("search", body)

    def list_databases(self) -> list[dict[str, Any]]:
        """Liste toutes les bases de données accessibles."""
        return self.search(filter_type="database")

    def list_pages(self) -> list[dict[str, Any]]:
        """Liste toutes les pages accessibles."""
        return self.search(filter_type="page")

    def get_me(self) -> dict[str, Any]:
        """Retourne les informations sur le bot/l'intégration."""
        return self.get("users/me")
