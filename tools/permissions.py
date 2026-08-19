"""
Système de permissions minimal de SARIEL — Phase 2.

Ce module est le seul endroit qui décide si une action nécessitant une
confirmation doit réellement être exécutée. agent.py ne fait qu'interroger
`request_confirmation` avant d'appeler `registry.execute()` — il ne connaît
aucun détail de la politique elle-même (voir la discussion d'architecture :
séparer "comment on orchestre le LLM" de "quelle politique de sécurité
s'applique", au même titre que tools/base.py sépare le contrat des tools
de leur implémentation).

Phase 2 : la politique est simple (demander sur stdin, oui/non). Elle est
conçue pour évoluer sans toucher agent.py : liste blanche d'actions
auto-approuvées, journalisation systématique, niveaux de risque différenciés
(voir Suggestions & Optimisations en fin de conversation).
"""

import datetime
import os

_LOG_PATH = os.path.join("data", "permissions.log")


def _log_decision(tool_name: str, arguments: dict, approved: bool) -> None:
    """
    Journalise chaque décision de confirmation (accordée ou refusée).
    Recommandation directe de docs/secu.md : logging systématique des
    actions à risque, utile pour l'audit et pour le portfolio.
    """
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    status = "APPROUVÉ" if approved else "REFUSÉ"
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {status} — {tool_name}({arguments})\n")


def request_confirmation(tool_name: str, arguments: dict) -> bool:
    """
    Interrompt la boucle agentique pour demander une confirmation
    explicite à l'utilisateur en CLI avant d'exécuter une action
    sensible (ex. écraser un fichier, créer une issue GitHub).

    Retourne True si l'utilisateur approuve, False sinon. Ne lève jamais
    d'exception — une entrée invalide ou une interruption (Ctrl+C, EOF)
    est traitée comme un refus, jamais comme une approbation par défaut.
    """
    print(f"\n⚠️  SARIEL souhaite exécuter une action sensible : {tool_name}")
    print(f"    Arguments : {arguments}")

    try:
        answer = input("    Confirmer ? [o/N] : ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n    Confirmation annulée.")
        _log_decision(tool_name, arguments, approved=False)
        return False

    approved = answer in ("o", "oui", "y", "yes")
    _log_decision(tool_name, arguments, approved=approved)

    if not approved:
        print("    Action refusée.")

    return approved
