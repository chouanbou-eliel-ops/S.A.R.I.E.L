# S.A.R.I.E.L


Assistant IA personnel type "Jarvis" — un noyau agentique unique (LLM + tool-calling + mémoire) sur lequel viennent se brancher plusieurs interfaces : texte, voix, domotique. À la fois majordome, partenaire de labo et intime.

> Statut : 🚧 en tout début de construction — rien n'est codé, la roadmap ci-dessous sert de plan de route.

## Vision

Plutôt que de reconstruire un système à chaque nouvelle capacité, Sariel repose sur **un seul cœur agentique** :

- Un LLM comme moteur de raisonnement
- Du tool-calling pour agir concrètement (chercher, exécuter du code, manipuler des fichiers...)
- Une mémoire persistante pour se souvenir entre les sessions

Les interfaces (terminal, voix, domotique, dashboard) sont des couches ajoutées par-dessus ce noyau, pas des projets séparés.

## Roadmap

- [ ] **Phase 1 — Noyau agentique en texte**
  LLM + function calling brut (pas de gros framework, pour comprendre le mécanisme) + mémoire simple (JSON/SQLite). Objectif : un agent en ligne de commande capable de chercher sur le web et d'exécuter du code Python.

- [ ] **Phase 2 — Outils étendus**
  Lecture/écriture de fichiers, exécution de scripts, appels à des APIs externes. Sariel devient un assistant codage terminal.

- [ ] **Phase 3 — Mémoire long terme**
  Base vectorielle (Chroma ou FAISS) pour retenir préférences, projets et conversations entre les sessions.

- [ ] **Phase 4 — Couche vocale**
  Whisper (speech-to-text) + un TTS (Coqui, piper ou ElevenLabs) branché sur le même noyau.

- [ ] **Phase 5 — Wake word + écoute continue**
  Détection de mot d'activation (Porcupine ou openWakeWord).

- [ ] **Phase 6 — Domotique**
  Home Assistant + objets connectés (ESP32, prises smart). Dépend du matériel disponible — reste en simulation si besoin.

- [ ] **Phase 7 — Dashboard unifié**
  Interface web/desktop centralisant logs, historique et contrôle manuel.

## Stack

| Composant     | Choix                                  |
|---------------|-----------------------------------------|
| Langage       | Python                                  |
| LLM           | 🔲 non décidé (API Claude / OpenAI / modèle local — arbitrage coût / confidentialité / perf à faire) |
| Mémoire (v1)  | JSON ou SQLite                          |
| Mémoire (v3)  | Chroma / FAISS                          |
| STT           | Whisper                                 |
| TTS           | Coqui / piper / ElevenLabs (à trancher) |
| Wake word     | Porcupine ou openWakeWord               |
| Domotique     | Home Assistant                          |

## Principes de dev

- Comprendre les mécanismes avant d'empiler des frameworks — le noyau (phase 1) se fait en function calling brut, pas via un wrapper qui cache tout
- Avancer phase par phase, sans sauter d'étape
- Projet perso, mais pensé pour être présentable en portfolio (candidatures Master Data & AI)

## Installation

_À compléter une fois la phase 1 démarrée._

```bash
git clone <repo>
cd sariel
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Structure du projet

_À compléter au fur et à mesure — pas encore de code._

## Auteur

Eliel — étudiant en Licence Sciences de l'Ingénieur (Informatique), ENSPY, Yaoundé
