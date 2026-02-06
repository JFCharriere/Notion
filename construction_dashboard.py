#!/usr/bin/env python3
"""Dashboard Construction Belvédère 2 - Farvagny.

Analyse les dépassements de budget, retards de paiement et échéances
à partir des bases de données Notion du projet de construction.

Usage:
    python construction_dashboard.py                  # Rapport complet dans le terminal
    python construction_dashboard.py --alerte-jours 14  # Alertes pour les 14 prochains jours
    python construction_dashboard.py --export csv       # Export CSV des alertes
    python construction_dashboard.py --notion PAGE_ID   # Créer le dashboard dans Notion
"""

from __future__ import annotations

import argparse
import json
import csv
import io
from datetime import datetime, date, timedelta
from typing import Any

from notion_api.client import NotionClient
from notion_api.blocks import BlockBuilder
from notion_api.databases import DatabaseManager
from notion_api.models import extract_property_value
from notion_api.pages import PageManager

# ============================================================================
# IDs des bases de données
# ============================================================================
DB_FACTURES = "2cca4dcc-3612-8179-bae1-dee3928586cb"
DB_POSTES = "2cca4dcc-3612-810c-b84b-cd36d865c5d0"
DB_ENTREPRISES = "2cca4dcc-3612-818b-b9b2-fb8630090022"

# ============================================================================
# Couleurs terminal
# ============================================================================
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _parse_date(d: Any) -> date | None:
    """Parse une date depuis une propriété Notion."""
    if d is None:
        return None
    if isinstance(d, dict):
        d = d.get("start", "")
    if isinstance(d, str) and d:
        try:
            return datetime.fromisoformat(d.split("T")[0]).date()
        except ValueError:
            return None
    return None


def _fmt_chf(val: Any) -> str:
    """Formate un nombre en CHF."""
    if val is None:
        return "—"
    try:
        return f"{float(val):,.2f} CHF".replace(",", "'")
    except (ValueError, TypeError):
        return str(val)


def _color_pct(pct: float | None) -> str:
    """Colore un pourcentage selon le niveau de risque."""
    if pct is None:
        return "—"
    if pct > 100:
        return f"{RED}{BOLD}{pct:.1f}%{RESET}"
    if pct > 90:
        return f"{YELLOW}{pct:.1f}%{RESET}"
    return f"{GREEN}{pct:.1f}%{RESET}"


class ConstructionDashboard:
    """Analyse et affiche le dashboard du projet de construction."""

    def __init__(self):
        self.client = NotionClient()
        self.db = DatabaseManager(self.client)
        self._factures: list[dict] = []
        self._postes: list[dict] = []
        self._entreprises: list[dict] = []

    def charger_donnees(self):
        """Charge toutes les données depuis Notion."""
        print(f"{CYAN}Chargement des données depuis Notion...{RESET}")
        self._postes = self.db.query_as_dicts(DB_POSTES)
        print(f"  📋 {len(self._postes)} postes de construction")
        self._factures = self.db.query_as_dicts(DB_FACTURES)
        print(f"  🧾 {len(self._factures)} factures")
        self._entreprises = self.db.query_as_dicts(DB_ENTREPRISES)
        print(f"  🏢 {len(self._entreprises)} entreprises")
        print()

    # ========================================================================
    # 1. Dépassements de budget par Poste de Construction
    # ========================================================================
    def rapport_postes(self) -> list[dict]:
        """Analyse les dépassements par poste de construction."""
        resultats = []
        for poste in self._postes:
            budget = poste.get("Budget alloué")
            ecart = poste.get("Ecart")
            pct_consomme = poste.get("% Consommé")
            alerte = poste.get("Alerte budget")
            nom = poste.get("N° Poste", "?")
            desc = poste.get("Description", "")

            # Extraire le libellé CFC (rollup)
            cfc = poste.get("Libellé Code CFC", "")
            if isinstance(cfc, list):
                cfc = ", ".join(str(c) for c in cfc)

            resultats.append({
                "poste": nom,
                "description": desc,
                "code_cfc": cfc,
                "budget": budget,
                "ecart": ecart,
                "pct_consomme": pct_consomme,
                "alerte": alerte,
                "depassement": (ecart is not None and isinstance(ecart, (int, float)) and ecart < 0),
            })

        # Trier : dépassements d'abord, puis par % consommé décroissant
        resultats.sort(
            key=lambda r: (
                not r["depassement"],
                -(r["pct_consomme"] or 0),
            )
        )
        return resultats

    def afficher_postes(self):
        """Affiche le rapport des dépassements par poste."""
        resultats = self.rapport_postes()
        depassements = [r for r in resultats if r["depassement"]]

        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}📋 DÉPASSEMENTS DE BUDGET PAR POSTE DE CONSTRUCTION{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")

        if depassements:
            print(f"\n{RED}{BOLD}⚠ {len(depassements)} poste(s) en dépassement de budget :{RESET}\n")
        else:
            print(f"\n{GREEN}✓ Aucun dépassement de budget détecté.{RESET}\n")

        print(f"  {'Poste':<25} {'Code CFC':<20} {'Budget':<18} {'Écart':<18} {'% Cons.':<10}")
        print(f"  {'─'*25} {'─'*20} {'─'*18} {'─'*18} {'─'*10}")

        for r in resultats:
            ecart_str = _fmt_chf(r["ecart"])
            if r["depassement"]:
                ecart_str = f"{RED}{ecart_str}{RESET}"

            nom = str(r["poste"])[:24]
            cfc = str(r["code_cfc"])[:19]
            print(
                f"  {nom:<25} {cfc:<20} {_fmt_chf(r['budget']):<18} "
                f"{ecart_str:<28} {_color_pct(r['pct_consomme'])}"
            )

        print()

    # ========================================================================
    # 2. Dépassements par Code CFC (agrégé)
    # ========================================================================
    def rapport_par_cfc(self) -> list[dict]:
        """Agrège les budgets et écarts par code CFC."""
        cfc_map: dict[str, dict] = {}

        for poste in self._postes:
            cfc = poste.get("Libellé Code CFC", "")
            if isinstance(cfc, list):
                cfc = ", ".join(str(c) for c in cfc)
            cfc = cfc or "Non classé"

            if cfc not in cfc_map:
                cfc_map[cfc] = {"budget_total": 0, "ecart_total": 0, "nb_postes": 0}

            budget = poste.get("Budget alloué")
            ecart = poste.get("Ecart")

            if isinstance(budget, (int, float)):
                cfc_map[cfc]["budget_total"] += budget
            if isinstance(ecart, (int, float)):
                cfc_map[cfc]["ecart_total"] += ecart
            cfc_map[cfc]["nb_postes"] += 1

        resultats = []
        for cfc, data in cfc_map.items():
            budget_total = data["budget_total"]
            ecart_total = data["ecart_total"]
            pct = ((budget_total - ecart_total) / budget_total * 100) if budget_total > 0 else None
            resultats.append({
                "code_cfc": cfc,
                "budget_total": budget_total,
                "ecart_total": ecart_total,
                "pct_consomme": pct,
                "nb_postes": data["nb_postes"],
                "depassement": ecart_total < 0,
            })

        resultats.sort(key=lambda r: (not r["depassement"], r["ecart_total"]))
        return resultats

    def afficher_par_cfc(self):
        """Affiche le rapport agrégé par code CFC."""
        resultats = self.rapport_par_cfc()
        depassements = [r for r in resultats if r["depassement"]]

        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}🏗️  DÉPASSEMENTS DE BUDGET PAR CODE CFC{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")

        if depassements:
            print(f"\n{RED}{BOLD}⚠ {len(depassements)} code(s) CFC en dépassement :{RESET}\n")
        else:
            print(f"\n{GREEN}✓ Aucun dépassement par code CFC.{RESET}\n")

        print(f"  {'Code CFC':<30} {'Postes':<8} {'Budget total':<18} {'Écart total':<18} {'% Cons.':<10}")
        print(f"  {'─'*30} {'─'*8} {'─'*18} {'─'*18} {'─'*10}")

        for r in resultats:
            ecart_str = _fmt_chf(r["ecart_total"])
            if r["depassement"]:
                ecart_str = f"{RED}{ecart_str}{RESET}"

            cfc = str(r["code_cfc"])[:29]
            print(
                f"  {cfc:<30} {r['nb_postes']:<8} {_fmt_chf(r['budget_total']):<18} "
                f"{ecart_str:<28} {_color_pct(r['pct_consomme'])}"
            )

        print()

    # ========================================================================
    # 3. Dépassements par Entreprise
    # ========================================================================
    def rapport_entreprises(self) -> list[dict]:
        """Analyse le solde par entreprise."""
        resultats = []
        for ent in self._entreprises:
            nom = ent.get("Nom entreprise", "?")
            contrats = ent.get("Valeur totale contrats (CHF) TTC")
            paye = ent.get("Total factures payées")
            solde = ent.get("Solde + - (CHF)")

            resultats.append({
                "nom": nom,
                "contrats_ttc": contrats,
                "total_paye": paye,
                "solde": solde,
                "depassement": (isinstance(solde, (int, float)) and solde < 0),
            })

        resultats.sort(key=lambda r: (not r["depassement"], r.get("solde") or 0))
        return resultats

    def afficher_entreprises(self):
        """Affiche le rapport par entreprise."""
        resultats = self.rapport_entreprises()
        depassements = [r for r in resultats if r["depassement"]]

        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}🏢 SOLDE PAR ENTREPRISE & PRESTATAIRE{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")

        if depassements:
            print(f"\n{RED}{BOLD}⚠ {len(depassements)} entreprise(s) avec solde négatif :{RESET}\n")
        else:
            print(f"\n{GREEN}✓ Tous les soldes sont positifs ou nuls.{RESET}\n")

        print(f"  {'Entreprise':<35} {'Contrats TTC':<18} {'Total payé':<18} {'Solde':<18}")
        print(f"  {'─'*35} {'─'*18} {'─'*18} {'─'*18}")

        for r in resultats:
            solde_str = _fmt_chf(r["solde"])
            if r["depassement"]:
                solde_str = f"{RED}{solde_str}{RESET}"

            nom = str(r["nom"])[:34]
            print(
                f"  {nom:<35} {_fmt_chf(r['contrats_ttc']):<18} "
                f"{_fmt_chf(r['total_paye']):<18} {solde_str}"
            )

        print()

    # ========================================================================
    # 4. Retards de paiement
    # ========================================================================
    def rapport_retards(self) -> list[dict]:
        """Identifie les factures en retard de paiement."""
        aujourd_hui = date.today()
        retards = []

        for fact in self._factures:
            statut = fact.get("Statut paiement", "")
            if statut and isinstance(statut, str) and statut.lower() in ("payé", "payée", "paid"):
                continue

            echeance = _parse_date(fact.get("Date échéance"))
            if echeance is None:
                continue

            if echeance < aujourd_hui:
                jours_retard = (aujourd_hui - echeance).days
                retards.append({
                    "numero": fact.get("N° Facture", "?"),
                    "montant_ttc": fact.get("Montant TTC (CHF)"),
                    "montant_ht": fact.get("Montant HT (CHF)"),
                    "date_echeance": echeance,
                    "jours_retard": jours_retard,
                    "statut": statut,
                    "entreprise": fact.get("🏢 Entreprises & Prestataires", ""),
                })

        retards.sort(key=lambda r: -r["jours_retard"])
        return retards

    def afficher_retards(self):
        """Affiche les factures en retard de paiement."""
        retards = self.rapport_retards()

        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}⏰ RETARDS DE PAIEMENT{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")

        if not retards:
            print(f"\n{GREEN}✓ Aucune facture en retard de paiement.{RESET}\n")
            return

        print(f"\n{RED}{BOLD}⚠ {len(retards)} facture(s) en retard :{RESET}\n")
        print(f"  {'N° Facture':<20} {'Montant HT':<18} {'Échéance':<14} {'Retard':<12} {'Statut':<15}")
        print(f"  {'─'*20} {'─'*18} {'─'*14} {'─'*12} {'─'*15}")

        for r in retards:
            jours = r["jours_retard"]
            if jours > 30:
                retard_str = f"{RED}{BOLD}{jours} jours{RESET}"
            elif jours > 14:
                retard_str = f"{RED}{jours} jours{RESET}"
            else:
                retard_str = f"{YELLOW}{jours} jours{RESET}"

            num = str(r["numero"])[:19]
            montant = _fmt_chf(r["montant_ht"] or r["montant_ttc"])
            echeance = str(r["date_echeance"])
            statut = str(r.get("statut", ""))[:14]

            print(f"  {num:<20} {montant:<18} {echeance:<14} {retard_str:<22} {statut:<15}")

        print()

    # ========================================================================
    # 5. Alertes : factures à payer prochainement
    # ========================================================================
    def rapport_alertes(self, jours_alerte: int = 30) -> list[dict]:
        """Identifie les factures à payer dans les N prochains jours."""
        aujourd_hui = date.today()
        limite = aujourd_hui + timedelta(days=jours_alerte)
        alertes = []

        for fact in self._factures:
            statut = fact.get("Statut paiement", "")
            if statut and isinstance(statut, str) and statut.lower() in ("payé", "payée", "paid"):
                continue

            echeance = _parse_date(fact.get("Date échéance"))
            if echeance is None:
                continue

            # Futures échéances (pas encore en retard)
            if aujourd_hui <= echeance <= limite:
                jours_restants = (echeance - aujourd_hui).days
                alertes.append({
                    "numero": fact.get("N° Facture", "?"),
                    "montant_ttc": fact.get("Montant TTC (CHF)"),
                    "montant_ht": fact.get("Montant HT (CHF)"),
                    "date_echeance": echeance,
                    "jours_restants": jours_restants,
                    "statut": statut,
                    "entreprise": fact.get("🏢 Entreprises & Prestataires", ""),
                })

        alertes.sort(key=lambda r: r["jours_restants"])
        return alertes

    def afficher_alertes(self, jours_alerte: int = 30):
        """Affiche les factures à payer prochainement."""
        alertes = self.rapport_alertes(jours_alerte)

        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}🔔 FACTURES À PAYER DANS LES {jours_alerte} PROCHAINS JOURS{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")

        if not alertes:
            print(f"\n{GREEN}✓ Aucune facture à payer dans les {jours_alerte} prochains jours.{RESET}\n")
            return

        print(f"\n{YELLOW}{BOLD}📌 {len(alertes)} facture(s) à régler :{RESET}\n")
        print(f"  {'N° Facture':<20} {'Montant HT':<18} {'Échéance':<14} {'Dans':<12} {'Statut':<15}")
        print(f"  {'─'*20} {'─'*18} {'─'*14} {'─'*12} {'─'*15}")

        for r in alertes:
            jours = r["jours_restants"]
            if jours <= 7:
                jours_str = f"{RED}{BOLD}{jours} jours{RESET}"
            elif jours <= 14:
                jours_str = f"{YELLOW}{jours} jours{RESET}"
            else:
                jours_str = f"{GREEN}{jours} jours{RESET}"

            num = str(r["numero"])[:19]
            montant = _fmt_chf(r["montant_ht"] or r["montant_ttc"])
            echeance = str(r["date_echeance"])
            statut = str(r.get("statut", ""))[:14]

            print(f"  {num:<20} {montant:<18} {echeance:<14} {jours_str:<22} {statut:<15}")

        print()

    # ========================================================================
    # 6. Résumé global
    # ========================================================================
    def afficher_resume(self):
        """Affiche un résumé global du projet."""
        print(f"{BOLD}{'='*80}{RESET}")
        print(f"{BOLD}📊 RÉSUMÉ GLOBAL — Construction Belvédère 2 - Farvagny{RESET}")
        print(f"{BOLD}{'='*80}{RESET}")
        print(f"  Date du rapport : {date.today()}\n")

        # Budget total
        budget_total = sum(
            p.get("Budget alloué", 0) or 0
            for p in self._postes
            if isinstance(p.get("Budget alloué"), (int, float))
        )
        ecart_total = sum(
            p.get("Ecart", 0) or 0
            for p in self._postes
            if isinstance(p.get("Ecart"), (int, float))
        )
        consomme_total = budget_total - ecart_total if budget_total > 0 else 0
        pct_global = (consomme_total / budget_total * 100) if budget_total > 0 else 0

        print(f"  💰 Budget total alloué :  {_fmt_chf(budget_total)}")
        print(f"  💸 Total consommé :       {_fmt_chf(consomme_total)}")
        ecart_color = RED if ecart_total < 0 else GREEN
        print(f"  📐 Écart global :         {ecart_color}{_fmt_chf(ecart_total)}{RESET}")
        print(f"  📊 % Consommé global :    {_color_pct(pct_global)}")

        # Compteurs
        nb_retards = len(self.rapport_retards())
        nb_alertes = len(self.rapport_alertes(30))
        postes_depassement = sum(1 for r in self.rapport_postes() if r["depassement"])

        print()
        if postes_depassement > 0:
            print(f"  {RED}⚠ {postes_depassement} poste(s) en dépassement de budget{RESET}")
        else:
            print(f"  {GREEN}✓ Aucun poste en dépassement{RESET}")

        if nb_retards > 0:
            print(f"  {RED}⚠ {nb_retards} facture(s) en retard de paiement{RESET}")
        else:
            print(f"  {GREEN}✓ Aucun retard de paiement{RESET}")

        if nb_alertes > 0:
            print(f"  {YELLOW}🔔 {nb_alertes} facture(s) à payer dans les 30 prochains jours{RESET}")
        else:
            print(f"  {GREEN}✓ Pas de facture à payer dans les 30 prochains jours{RESET}")

        print()

    # ========================================================================
    # 7. Création du dashboard dans Notion
    # ========================================================================
    def creer_dans_notion(self, parent_page_id: str, jours_alerte: int = 30) -> str:
        """Crée le dashboard complet comme page Notion.

        Args:
            parent_page_id: ID de la page parente dans Notion.
            jours_alerte: Fenêtre d'alerte en jours.

        Returns:
            URL de la page créée.
        """
        pages = PageManager(self.client)
        B = BlockBuilder

        aujourd_hui = date.today()
        titre = f"Dashboard Construction — {aujourd_hui}"

        print(f"{CYAN}Création de la page dashboard dans Notion...{RESET}")

        # -- Créer la page --
        page = pages.create(
            parent_page_id=parent_page_id,
            properties={
                "title": {
                    "title": [{"type": "text", "text": {"content": titre}}]
                }
            },
            icon="📊",
        )
        page_id = page["id"]
        page_url = page.get("url", "")
        print(f"  Page créée : {page_url}")

        # -- Section 1 : Résumé global --
        budget_total = sum(
            p.get("Budget alloué", 0) or 0
            for p in self._postes
            if isinstance(p.get("Budget alloué"), (int, float))
        )
        ecart_total = sum(
            p.get("Ecart", 0) or 0
            for p in self._postes
            if isinstance(p.get("Ecart"), (int, float))
        )
        consomme_total = budget_total - ecart_total if budget_total > 0 else 0
        pct_global = (consomme_total / budget_total * 100) if budget_total > 0 else 0

        nb_retards = len(self.rapport_retards())
        nb_alertes = len(self.rapport_alertes(jours_alerte))
        postes_depassement = sum(1 for r in self.rapport_postes() if r["depassement"])

        blocs_resume = [
            B.heading_1("📊 Résumé global"),
            B.callout(
                f"Date du rapport : {aujourd_hui}\n"
                f"Budget total : {_fmt_chf(budget_total)}\n"
                f"Consommé : {_fmt_chf(consomme_total)} ({pct_global:.1f}%)\n"
                f"Écart global : {_fmt_chf(ecart_total)}",
                icon="💰",
            ),
            B.callout(
                f"{'⚠️' if postes_depassement > 0 else '✅'} {postes_depassement} poste(s) en dépassement\n"
                f"{'⚠️' if nb_retards > 0 else '✅'} {nb_retards} facture(s) en retard\n"
                f"{'🔔' if nb_alertes > 0 else '✅'} {nb_alertes} facture(s) à payer sous {jours_alerte} jours",
                icon="📋",
            ),
            B.divider(),
        ]
        pages.append_blocks(page_id, blocs_resume)
        print("  ✓ Résumé global")

        # -- Section 2 : Dépassements par poste --
        postes = self.rapport_postes()
        postes_rows = []
        for r in postes:
            ecart_val = r["ecart"]
            pct_val = r["pct_consomme"]
            postes_rows.append([
                str(r["poste"]),
                str(r["code_cfc"] or "—"),
                _fmt_chf(r["budget"]),
                _fmt_chf(ecart_val),
                f"{pct_val:.1f}%" if pct_val is not None else "—",
                "⚠️ OUI" if r["depassement"] else "✅ Non",
            ])

        blocs_postes = [B.heading_1("📋 Dépassements par poste de construction")]
        if postes_rows:
            blocs_postes.append(B.table(
                [["Poste", "Code CFC", "Budget", "Écart", "% Consommé", "Dépassement"]]
                + postes_rows,
                has_column_header=True,
            ))
        else:
            blocs_postes.append(B.callout("Aucun poste trouvé.", icon="ℹ️"))
        blocs_postes.append(B.divider())
        pages.append_blocks(page_id, blocs_postes)
        print("  ✓ Dépassements par poste")

        # -- Section 3 : Dépassements par code CFC --
        cfc_data = self.rapport_par_cfc()
        cfc_rows = []
        for r in cfc_data:
            cfc_rows.append([
                str(r["code_cfc"]),
                str(r["nb_postes"]),
                _fmt_chf(r["budget_total"]),
                _fmt_chf(r["ecart_total"]),
                f"{r['pct_consomme']:.1f}%" if r["pct_consomme"] is not None else "—",
            ])

        blocs_cfc = [B.heading_1("🏗️ Dépassements par code CFC")]
        if cfc_rows:
            blocs_cfc.append(B.table(
                [["Code CFC", "Nb postes", "Budget total", "Écart total", "% Consommé"]]
                + cfc_rows,
                has_column_header=True,
            ))
        else:
            blocs_cfc.append(B.callout("Aucun code CFC trouvé.", icon="ℹ️"))
        blocs_cfc.append(B.divider())
        pages.append_blocks(page_id, blocs_cfc)
        print("  ✓ Dépassements par CFC")

        # -- Section 4 : Solde par entreprise --
        entreprises = self.rapport_entreprises()
        ent_rows = []
        for r in entreprises:
            ent_rows.append([
                str(r["nom"]),
                _fmt_chf(r["contrats_ttc"]),
                _fmt_chf(r["total_paye"]),
                _fmt_chf(r["solde"]),
                "⚠️" if r["depassement"] else "✅",
            ])

        blocs_ent = [B.heading_1("🏢 Solde par entreprise & prestataire")]
        if ent_rows:
            blocs_ent.append(B.table(
                [["Entreprise", "Contrats TTC", "Total payé", "Solde", ""]]
                + ent_rows,
                has_column_header=True,
            ))
        else:
            blocs_ent.append(B.callout("Aucune entreprise trouvée.", icon="ℹ️"))
        blocs_ent.append(B.divider())
        pages.append_blocks(page_id, blocs_ent)
        print("  ✓ Solde par entreprise")

        # -- Section 5 : Retards de paiement --
        retards = self.rapport_retards()
        blocs_retards = [B.heading_1("⏰ Retards de paiement")]
        if retards:
            retard_rows = []
            for r in retards:
                jours = r["jours_retard"]
                urgence = "🔴" if jours > 30 else ("🟠" if jours > 14 else "🟡")
                retard_rows.append([
                    str(r["numero"]),
                    _fmt_chf(r["montant_ht"] or r["montant_ttc"]),
                    str(r["date_echeance"]),
                    f"{urgence} {jours} jours",
                    str(r.get("statut", "")),
                ])
            blocs_retards.append(B.table(
                [["N° Facture", "Montant", "Échéance", "Retard", "Statut"]]
                + retard_rows,
                has_column_header=True,
            ))
        else:
            blocs_retards.append(
                B.callout("✅ Aucune facture en retard de paiement.", icon="👍")
            )
        blocs_retards.append(B.divider())
        pages.append_blocks(page_id, blocs_retards)
        print("  ✓ Retards de paiement")

        # -- Section 6 : Factures à payer --
        alertes = self.rapport_alertes(jours_alerte)
        blocs_alertes = [B.heading_1(f"🔔 Factures à payer ({jours_alerte} prochains jours)")]
        if alertes:
            alerte_rows = []
            for r in alertes:
                jours = r["jours_restants"]
                urgence = "🔴" if jours <= 7 else ("🟠" if jours <= 14 else "🟢")
                alerte_rows.append([
                    str(r["numero"]),
                    _fmt_chf(r["montant_ht"] or r["montant_ttc"]),
                    str(r["date_echeance"]),
                    f"{urgence} {jours} jours",
                    str(r.get("statut", "")),
                ])
            blocs_alertes.append(B.table(
                [["N° Facture", "Montant", "Échéance", "Dans", "Statut"]]
                + alerte_rows,
                has_column_header=True,
            ))
        else:
            blocs_alertes.append(
                B.callout(f"✅ Aucune facture à payer dans les {jours_alerte} prochains jours.", icon="👍")
            )
        pages.append_blocks(page_id, blocs_alertes)
        print(f"\n{GREEN}{BOLD}Dashboard créé avec succès !{RESET}")
        print(f"  URL : {page_url}")

        return page_url

    # ========================================================================
    # Export
    # ========================================================================
    def export_csv(self, output_path: str = "dashboard_construction.csv"):
        """Exporte le rapport complet en CSV."""
        rows = []

        # Postes
        for r in self.rapport_postes():
            rows.append({
                "Section": "Poste",
                "Nom": r["poste"],
                "Code CFC": r["code_cfc"],
                "Budget": r["budget"],
                "Écart": r["ecart"],
                "% Consommé": r["pct_consomme"],
                "Dépassement": "Oui" if r["depassement"] else "Non",
            })

        # Retards
        for r in self.rapport_retards():
            rows.append({
                "Section": "Retard paiement",
                "Nom": r["numero"],
                "Montant": r["montant_ht"] or r["montant_ttc"],
                "Date échéance": str(r["date_echeance"]),
                "Jours retard": r["jours_retard"],
            })

        # Alertes
        for r in self.rapport_alertes(30):
            rows.append({
                "Section": "À payer",
                "Nom": r["numero"],
                "Montant": r["montant_ht"] or r["montant_ttc"],
                "Date échéance": str(r["date_echeance"]),
                "Jours restants": r["jours_restants"],
            })

        if not rows:
            print("Aucune donnée à exporter.")
            return

        all_keys = []
        for row in rows:
            for k in row:
                if k not in all_keys:
                    all_keys.append(k)

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        print(f"Export CSV enregistré : {output_path}")

    # ========================================================================
    # Rapport complet
    # ========================================================================
    def rapport_complet(self, jours_alerte: int = 30):
        """Affiche le rapport complet."""
        self.charger_donnees()
        self.afficher_resume()
        self.afficher_postes()
        self.afficher_par_cfc()
        self.afficher_entreprises()
        self.afficher_retards()
        self.afficher_alertes(jours_alerte)


def main():
    parser = argparse.ArgumentParser(
        description="Dashboard Construction Belvédère 2 - Farvagny"
    )
    parser.add_argument(
        "--alerte-jours", type=int, default=30,
        help="Nombre de jours pour l'alerte des paiements à venir (défaut: 30)",
    )
    parser.add_argument(
        "--export", choices=["csv", "json"],
        help="Exporter le rapport (csv ou json)",
    )
    parser.add_argument(
        "--section",
        choices=["resume", "postes", "cfc", "entreprises", "retards", "alertes"],
        help="Afficher uniquement une section spécifique",
    )
    parser.add_argument(
        "--notion", type=str, metavar="PAGE_ID",
        help="Créer le dashboard dans Notion (spécifier l'ID de la page parente)",
    )

    args = parser.parse_args()
    dashboard = ConstructionDashboard()
    dashboard.charger_donnees()

    if args.notion:
        dashboard.creer_dans_notion(args.notion, jours_alerte=args.alerte_jours)
        return

    if args.export == "csv":
        dashboard.export_csv()
        return
    elif args.export == "json":
        data = {
            "date_rapport": str(date.today()),
            "postes": dashboard.rapport_postes(),
            "par_cfc": dashboard.rapport_par_cfc(),
            "entreprises": dashboard.rapport_entreprises(),
            "retards": dashboard.rapport_retards(),
            "alertes": dashboard.rapport_alertes(args.alerte_jours),
        }
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return

    if args.section:
        sections = {
            "resume": dashboard.afficher_resume,
            "postes": dashboard.afficher_postes,
            "cfc": dashboard.afficher_par_cfc,
            "entreprises": dashboard.afficher_entreprises,
            "retards": dashboard.afficher_retards,
            "alertes": lambda: dashboard.afficher_alertes(args.alerte_jours),
        }
        sections[args.section]()
    else:
        dashboard.afficher_resume()
        dashboard.afficher_postes()
        dashboard.afficher_par_cfc()
        dashboard.afficher_entreprises()
        dashboard.afficher_retards()
        dashboard.afficher_alertes(args.alerte_jours)


if __name__ == "__main__":
    main()
