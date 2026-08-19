"""
Boucle agentique de SARIEL — Phase 1.

C'est ici que se joue le mécanisme central du projet : l'agent envoie la
conversation au LLM avec la liste des tools disponibles, le LLM répond
soit par du texte, soit en demandant l'exécution d'un ou plusieurs tools.
Dans ce dernier cas, on exécute localement, on renvoie le résultat au
modèle dans le fil de conversation, et on recommence — jusqu'à ce que le
modèle produise une réponse texte finale (ou qu'on atteigne la limite
d'itérations de sécurité).

Déroulé exact d'un tour de boucle (à connaître par cœur, pas juste à
lire dans le code) :
  1. Envoi : messages + schémas des tools → API Anthropic.
  2. Le modèle répond avec un ou plusieurs blocs de contenu, mélangeant
     éventuellement du texte et des blocs "tool_use" (nom du tool +
     arguments déjà parsés en JSON par l'API elle-même).
  3. Pour chaque bloc tool_use : on appelle registry.execute(nom, args).
  4. On construit un message "user" contenant un bloc "tool_result" par
     tool_use, avec le contenu renvoyé par le tool.
  5. On rappelle l'API avec l'historique augmenté de ces deux nouveaux
     messages (la réponse du modèle + les résultats de tools).
  6. Si la réponse ne contient plus de bloc tool_use → c'est la réponse
     finale, on sort de la boucle.
"""

import anthropic

import config
from memory import Memory
from tools import memory_save as memory_save_tool
from tools import permissions
from tools.base import registry

_SYSTEM_PROMPT_TEMPLATE = """Tu es SARIEL, un assistant IA personnel.
Tu as accès à des tools pour rechercher sur le web et exécuter du code Python.
Utilise-les chaque fois qu'ils peuvent t'aider à répondre plus précisément
ou plus fiablement qu'en raisonnant seul.

{memory_context}"""


class Agent:
    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=config.LLM_API_KEY)
        self.memory = Memory(config.MEMORY_PATH)
        memory_save_tool.bind_memory(self.memory)
        self.messages: list[dict] = []

    def _system_prompt(self) -> str:
        memory_context = self.memory.as_context_string()
        return _SYSTEM_PROMPT_TEMPLATE.format(memory_context=memory_context)

    def _call_llm(self) -> anthropic.types.Message:
        return self.client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=1024,
            system=self._system_prompt(),
            tools=registry.list_schemas(),
            messages=self.messages,
        )

    def _execute_tool_calls(self, response) -> list[dict]:
        """
        Exécute chaque bloc tool_use de la réponse et construit la liste
        de blocs tool_result correspondants, dans le format attendu par
        l'API pour le prochain message "user".
        """
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            if config.VERBOSE:
                print(f"  [tool_call] {block.name}({block.input})")

            tool = registry.get(block.name)
            if tool is not None and tool.schema.requires_confirmation:
                if not permissions.request_confirmation(block.name, block.input):
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": (
                                "Action refusée par l'utilisateur : "
                                "confirmation requise non accordée."
                            ),
                            "is_error": True,
                        }
                    )
                    continue

            result = registry.execute(block.name, block.input)

            if config.VERBOSE:
                status = "OK" if result.success else "ÉCHEC"
                print(f"  [tool_result:{status}] {result.content[:200]}")

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.content,
                    "is_error": not result.success,
                }
            )
        return tool_results

    def run(self, user_input: str) -> str:
        """
        Point d'entrée principal : envoie une requête utilisateur, gère
        la boucle d'appels de tools en interne, retourne la réponse
        texte finale du modèle.
        """
        self.messages.append({"role": "user", "content": user_input})

        for _ in range(config.MAX_AGENT_ITERATIONS):
            response = self._call_llm()
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                # Le modèle a fini : on extrait le texte de sa réponse.
                return self._extract_text(response)

            tool_results = self._execute_tool_calls(response)
            self.messages.append({"role": "user", "content": tool_results})

        return (
            "Nombre maximal d'itérations atteint sans réponse finale. "
            "La requête est peut-être trop complexe ou un tool boucle sans progresser."
        )

    @staticmethod
    def _extract_text(response) -> str:
        parts = [block.text for block in response.content if block.type == "text"]
        return "\n".join(parts) if parts else "(réponse vide)"
