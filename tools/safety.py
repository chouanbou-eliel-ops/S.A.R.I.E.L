"""
Filtre statique de sécurité pour le code exécuté par python_exec.

Origine et limites : voir docs/secu.md. Ce filtre analyse l'arbre syntaxique
(AST) du code AVANT toute exécution, et bloque les imports et appels
jugés dangereux. Ce n'est PAS une sandbox — un attaquant déterminé peut
probablement contourner une analyse AST par introspection ou
métaprogrammation. L'objectif assumé (et suffisant à ce stade du projet)
est d'arrêter les maladresses du modèle et l'injection grossière, pas de
résister à un adversaire sophistiqué. Le sandboxing réel du filesystem
(répertoire de travail restreint) est traité séparément par file_tools.py.

Comportement de blocage : un code refusé par ce filtre renvoie un échec
DÉFINITIF du tool (ToolResult.fail), jamais une demande de confirmation.
Contrairement à write_file (action légitime nécessitant un feu vert),
une ligne rouge structurelle comme "import os" n'est pas négociable en
conversation — voir la discussion d'architecture correspondante. Si un
besoin légitime apparaît, la liste noire elle-même doit être révisée.
"""

import ast

# Modules totalement interdits, y compris en import indirect
# (import x.y.z ou from x.y import z sont bloqués dès que le module
# racine "x" est dans cette liste).
FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "pathlib",       # accès filesystem hors du sandbox contrôlé par file_tools.py
    "ctypes",        # accès mémoire bas niveau, contournement d'introspection
    "importlib",     # permet d'importer dynamiquement un module par ailleurs interdit
    "urllib",        # accès réseau, alternative à requests
    "http",          # accès réseau bas niveau
}

# Fonctions/appels interdits, quel que soit le module d'où elles viennent
# (détectées par leur nom d'appel direct : eval(...), exec(...), etc.)
FORBIDDEN_FUNCTIONS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "getattr",   # permet d'atteindre un attribut interdit par un nom construit dynamiquement
    "setattr",
    "delattr",
    "vars",
    "globals",
    "locals",
}

# Noms interdits en accès direct (attribut ou variable), au-delà des
# appels de fonction — ex. "__builtins__" utilisé comme espace de noms
# pour contourner l'absence d'un import explicite.
FORBIDDEN_NAMES = {
    "__builtins__",
    "__loader__",
    "__import__",
}


def static_code_check(code: str) -> tuple[bool, str | None]:
    """
    Analyse statiquement `code` et retourne (autorisé, raison_refus).
    raison_refus est None si autorisé, sinon un message lisible expliquant
    précisément ce qui a été bloqué (utile pour informer le modèle).

    Ne lève jamais d'exception pour du code syntaxiquement invalide :
    un SyntaxError est traité comme "autorisé" ici (l'erreur de syntaxe
    sera de toute façon rapportée par l'exécution réelle dans
    python_exec.py, qui gère déjà ce cas proprement).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return True, None

    for node in ast.walk(tree):
        # import os / import os.path
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"import interdit détecté : '{alias.name}'"

        # from os import remove / from os.path import join
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_module = node.module.split(".")[0]
                if root_module in FORBIDDEN_MODULES:
                    return False, f"import interdit détecté : 'from {node.module} import ...'"

        # eval(...), exec(...), getattr(...), etc.
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FUNCTIONS:
                return False, f"appel interdit détecté : '{node.func.id}(...)'"

            if isinstance(node.func, ast.Name) and node.func.id == "open":
                if _open_call_requests_write(node):
                    return False, "appel à open() en mode écriture détecté (utilisez write_file)"

        # Référence directe à un nom interdit (ex. __builtins__['eval'])
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                return False, f"référence interdite détectée : '{node.id}'"

        # Référence à un attribut interdit (ex. obj.__builtins__)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_NAMES:
                return False, f"référence interdite détectée : '.{node.attr}'"

    return True, None


def _open_call_requests_write(call_node: ast.Call) -> bool:
    """
    Inspecte les arguments d'un appel open(...) pour détecter un mode
    d'écriture. Ne peut détecter que des modes littéraux (chaînes en dur
    dans le code) — un mode construit dynamiquement échapperait à cette
    vérification, limite assumée d'une analyse purement statique.
    """
    mode_arg = None

    if len(call_node.args) >= 2:
        mode_arg = call_node.args[1]
    else:
        for kw in call_node.keywords:
            if kw.arg == "mode":
                mode_arg = kw.value

    if mode_arg is None:
        return False  # mode par défaut de open() est "r" (lecture seule)

    if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
        mode = mode_arg.value
        return any(flag in mode for flag in ("w", "a", "x", "+"))

    # Mode non littéral (variable, f-string...) : on ne peut pas l'évaluer
    # statiquement. On refuse par prudence plutôt que de laisser passer.
    return True
