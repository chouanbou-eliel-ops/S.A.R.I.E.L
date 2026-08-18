"""
Point d'entrée CLI de SARIEL — Phase 1.

Boucle de lecture au clavier → agent → affichage, avec deux commandes
spéciales interceptées AVANT d'atteindre le LLM :
  /remember <texte>   mémorise un fait manuellement, sans passer par le
                       jugement du modèle (utile si vous voulez être sûr
                       qu'un fait précis est retenu).
  /quit ou /exit       quitte le programme.
"""

import sys

import config
from agent import Agent


def _handle_remember_command(agent: Agent, text: str) -> None:
    fact = agent.memory.add_fact(text)
    print(f"SARIEL > Fait mémorisé manuellement : « {fact.content} »")


def main() -> None:
    missing = config.check_required_config()
    if missing:
        config.print_missing_config_and_exit(missing)

    agent = Agent()

    print("SARIEL — Phase 1 (noyau agentique en texte)")
    print("Tapez /remember <texte> pour mémoriser un fait manuellement.")
    print("Tapez /quit pour quitter.\n")

    while True:
        try:
            user_input = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSARIEL > À bientôt, Monsieur.")
            sys.exit(0)

        if not user_input:
            continue

        if user_input in ("/quit", "/exit"):
            print("SARIEL > À bientôt, Monsieur.")
            break

        if user_input.startswith("/remember "):
            fact_text = user_input[len("/remember "):].strip()
            if fact_text:
                _handle_remember_command(agent, fact_text)
            else:
                print("SARIEL > Précisez le fait à mémoriser après /remember.")
            continue

        try:
            reply = agent.run(user_input)
        except Exception as exc:  # noqa: BLE001 — filet de sécurité au niveau CLI
            reply = f"Une erreur inattendue est survenue : {exc}"

        print(f"SARIEL > {reply}\n")


if __name__ == "__main__":
    main()
