"""
Tool d'exécution de code Python pour SARIEL.

Phase 1 : isolation basique via un sous-processus séparé avec timeout.
Phase 2 : ajout d'un filtre statique AST (tools/safety.py) qui bloque les
imports et appels dangereux (os, subprocess, eval, etc.) AVANT tout
lancement de sous-processus.
Ce n'est toujours PAS une sandbox de sécurité complète (pas de conteneur,
pas de restriction réseau/fichiers au niveau OS) — le filtre AST arrête
les maladresses et l'injection grossière, pas un adversaire déterminé.
À durcir si le projet évolue vers un usage multi-utilisateur (voir
Suggestions & Optimisations).
"""

import subprocess
import sys
import tempfile
import os

from tools.base import Tool, ToolSchema, ToolResult, registry
from tools.safety import static_code_check

_TIMEOUT_SECONDS = 10


def python_exec(arguments: dict) -> ToolResult:
    """
    Exécute un extrait de code Python dans un sous-processus isolé et
    renvoie stdout (ou stderr en cas d'erreur du script lui-même).

    Le code passe d'abord par le filtre statique (tools/safety.py) avant
    tout lancement de sous-processus : un code refusé n'est JAMAIS exécuté,
    même partiellement — voir tools/safety.py pour le raisonnement sur
    ce choix (échec définitif plutôt que demande de confirmation).
    """
    code = arguments.get("code")
    if not code or not isinstance(code, str):
        return ToolResult.fail("Paramètre 'code' manquant ou invalide.")

    allowed, reason = static_code_check(code)
    if not allowed:
        return ToolResult.fail(f"Code refusé par le filtre de sécurité : {reason}")

    # Fichier temporaire plutôt que `python -c` : évite les soucis
    # d'échappement avec du code multi-lignes ou contenant des guillemets.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp_file:
        tmp_file.write(code)
        tmp_path = tmp_file.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ToolResult.fail(
            f"Le script a dépassé le délai autorisé ({_TIMEOUT_SECONDS}s) "
            "et a été interrompu."
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult.fail(f"Échec du lancement du sous-processus : {exc}")
    finally:
        os.unlink(tmp_path)

    if result.returncode != 0:
        # Le code a échoué (exception Python) — on renvoie stderr comme
        # résultat normal, PAS comme échec du tool lui-même : le tool a
        # bien fonctionné, c'est le code utilisateur qui a une erreur.
        return ToolResult.ok(
            f"Le script a levé une erreur (code {result.returncode}) :\n{result.stderr}"
        )

    output = result.stdout.strip()
    if not output:
        return ToolResult.ok("Le script s'est exécuté sans erreur, sans sortie sur stdout.")

    return ToolResult.ok(output)


_schema = ToolSchema(
    name="python_exec",
    description=(
        "Exécute un extrait de code Python et renvoie sa sortie standard. "
        "À utiliser pour des calculs, transformations de données, ou toute "
        "tâche qu'il est plus fiable de résoudre par le code que par le "
        "raisonnement seul. Le code doit utiliser print() pour produire "
        "une sortie visible."
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Code Python valide et autonome à exécuter.",
            }
        },
        "required": ["code"],
    },
)

registry.register(Tool(schema=_schema, function=python_exec))
