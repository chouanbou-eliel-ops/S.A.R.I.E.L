"""
Configuration centrale de SARIEL.

Charge les variables d'environnement depuis .env et les expose comme
constantes typées. Aucun autre module ne doit lire os.environ directement
pour la config applicative — tout passe par ici, pour avoir un seul
endroit à vérifier si une variable manque.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# --- LLM ---
LLM_API_KEY: str | None = os.environ.get("LLM_API_KEY")
LLM_MODEL: str = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

# --- Recherche web (Tavily) ---
TAVILY_API_KEY: str | None = os.environ.get("TAVILY_API_KEY")

# --- Mémoire ---
MEMORY_PATH: str = os.environ.get("MEMORY_PATH", "data/memory.json")

# --- Divers ---
VERBOSE: bool = os.environ.get("VERBOSE", "false").lower() == "true"

# Nombre maximal d'itérations de la boucle agentique avant d'abandonner
# et de forcer une réponse — garde-fou contre une boucle infinie de tool
# calls (ex. le modèle rappelle le même tool sans progresser).
MAX_AGENT_ITERATIONS: int = 10


def check_required_config() -> list[str]:
    """
    Vérifie que les variables indispensables au fonctionnement minimal
    sont présentes. Retourne la liste des variables manquantes (vide si
    tout est en ordre). N'arrête pas le programme elle-même — c'est à
    l'appelant (main.py) de décider quoi faire du résultat.
    """
    missing = []
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not TAVILY_API_KEY:
        missing.append("TAVILY_API_KEY")
    return missing


def print_missing_config_and_exit(missing: list[str]) -> None:
    """Affiche un message clair et arrête le programme proprement."""
    print("Configuration incomplète. Variables manquantes dans .env :")
    for var in missing:
        print(f"  - {var}")
    print("\nCopiez .env.example vers .env et renseignez les valeurs manquantes.")
    sys.exit(1)
