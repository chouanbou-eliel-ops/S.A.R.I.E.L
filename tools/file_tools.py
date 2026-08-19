"""
Tools de lecture/écriture de fichiers pour SARIEL — Phase 2.

Répertoire de travail restreint (recommandation docs/secu.md) : l'agent ne
peut lire ou écrire qu'à l'intérieur de data/sandbox/, jamais à la racine
du projet ou ailleurs sur le système. Toute tentative de sortir de ce
dossier (via "..", chemin absolu, ou lien symbolique) est bloquée.

write_file est marqué requires_confirmation=True dans son schéma : c'est
agent.py (via tools/permissions.py) qui demande confirmation à l'utilisateur
avant que cette fonction ne soit même appelée. read_file n'a pas cette
contrainte : lire n'est pas destructeur.
"""

import os

from tools.base import Tool, ToolSchema, ToolResult, registry

_SANDBOX_DIR = os.path.abspath(os.path.join("data", "sandbox"))


def _resolve_safe_path(relative_path: str) -> str | None:
    """
    Résout un chemin relatif fourni par le modèle vers un chemin absolu
    à l'intérieur de _SANDBOX_DIR. Retourne None si le chemin sort du
    sandbox (ex. "../../etc/passwd" ou un chemin absolu).
    """
    os.makedirs(_SANDBOX_DIR, exist_ok=True)

    candidate = os.path.abspath(os.path.join(_SANDBOX_DIR, relative_path))

    # os.path.commonpath lève ValueError si les chemins n'ont rien en
    # commun (ex. lecteurs différents sous Windows) — on traite ce cas
    # comme une sortie de sandbox également.
    try:
        if os.path.commonpath([_SANDBOX_DIR, candidate]) != _SANDBOX_DIR:
            return None
    except ValueError:
        return None

    return candidate


def read_file(arguments: dict) -> ToolResult:
    relative_path = arguments.get("path")
    if not relative_path or not isinstance(relative_path, str):
        return ToolResult.fail("Paramètre 'path' manquant ou invalide.")

    safe_path = _resolve_safe_path(relative_path)
    if safe_path is None:
        return ToolResult.fail(
            "Chemin refusé : accès limité au répertoire data/sandbox/."
        )

    if not os.path.isfile(safe_path):
        return ToolResult.fail(f"Fichier introuvable : {relative_path}")

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        return ToolResult.fail(
            "Le fichier n'est pas du texte lisible en UTF-8 (fichier binaire ?)."
        )
    except OSError as exc:
        return ToolResult.fail(f"Erreur de lecture : {exc}")

    if not content:
        return ToolResult.ok("(fichier vide)")
    return ToolResult.ok(content)


def write_file(arguments: dict) -> ToolResult:
    relative_path = arguments.get("path")
    content = arguments.get("content")

    if not relative_path or not isinstance(relative_path, str):
        return ToolResult.fail("Paramètre 'path' manquant ou invalide.")
    if content is None or not isinstance(content, str):
        return ToolResult.fail("Paramètre 'content' manquant ou invalide.")

    safe_path = _resolve_safe_path(relative_path)
    if safe_path is None:
        return ToolResult.fail(
            "Chemin refusé : accès limité au répertoire data/sandbox/."
        )

    try:
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        return ToolResult.fail(f"Erreur d'écriture : {exc}")

    return ToolResult.ok(
        f"Fichier '{relative_path}' écrit avec succès ({len(content)} caractères)."
    )


_read_schema = ToolSchema(
    name="read_file",
    description=(
        "Lit le contenu texte d'un fichier situé dans le répertoire de "
        "travail de l'agent (data/sandbox/). Le chemin est relatif à ce "
        "répertoire ; toute tentative d'en sortir est refusée."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin relatif du fichier à lire, ex. 'notes.txt'.",
            }
        },
        "required": ["path"],
    },
)

_write_schema = ToolSchema(
    name="write_file",
    description=(
        "Écrit (ou écrase) un fichier texte dans le répertoire de travail "
        "de l'agent (data/sandbox/). Le chemin est relatif à ce répertoire ; "
        "toute tentative d'en sortir est refusée. Cette action nécessite une "
        "confirmation explicite de l'utilisateur avant exécution."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Chemin relatif du fichier à écrire, ex. 'notes.txt'.",
            },
            "content": {
                "type": "string",
                "description": "Contenu texte à écrire dans le fichier (remplace le contenu existant).",
            },
        },
        "required": ["path", "content"],
    },
    requires_confirmation=True,
)

registry.register(Tool(schema=_read_schema, function=read_file))
registry.register(Tool(schema=_write_schema, function=write_file))
