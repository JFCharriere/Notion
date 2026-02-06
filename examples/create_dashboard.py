#!/usr/bin/env python3
"""Exemple : créer un dashboard avec des métriques et des résumés."""

from notion_api import DashboardBuilder, NotionClient

# Remplacez par vos IDs
PARENT_PAGE_ID = "VOTRE_PAGE_ID_ICI"
DATABASE_IDS = [
    # "id_de_votre_base_1",
    # "id_de_votre_base_2",
]

client = NotionClient()
builder = DashboardBuilder(client)

# Option 1 : Dashboard complet automatique
if DATABASE_IDS:
    dashboard = builder.create_full_dashboard(
        parent_page_id=PARENT_PAGE_ID,
        title="Mon Dashboard",
        database_ids=DATABASE_IDS,
        metrics={
            "Chiffre d'affaires": "125 000 €",
            "Clients actifs": 342,
            "Taux de conversion": "3.2%",
        },
    )
    print(f"Dashboard créé : {dashboard.get('url', dashboard['id'])}")

# Option 2 : Construction manuelle pas à pas
else:
    # Créer la page
    dashboard = builder.create_dashboard_page(
        parent_page_id=PARENT_PAGE_ID,
        title="Dashboard Manuel",
        icon="📊",
    )
    dash_id = dashboard["id"]

    # Ajouter des métriques
    builder.add_metric_section(
        dash_id,
        "KPIs du mois",
        {
            "Revenus": "45 000 €",
            "Nouveaux utilisateurs": 128,
            "Tickets résolus": 47,
        },
    )

    # Ajouter un tableau de synthèse
    builder.add_summary_table(
        dash_id,
        "Résumé par équipe",
        headers=["Équipe", "Objectif", "Réalisé", "Taux"],
        rows=[
            ["Ventes", "50 000 €", "45 000 €", "90%"],
            ["Marketing", "1000 leads", "1200 leads", "120%"],
            ["Support", "< 2h réponse", "1.5h", "100%"],
        ],
    )

    print(f"Dashboard créé : {dashboard.get('url', dashboard['id'])}")
