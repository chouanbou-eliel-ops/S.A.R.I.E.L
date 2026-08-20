# SARIEL — Critères de "Done" par Phase

> Chaque critère doit être vérifiable en moins de 5 minutes, sans jugement subjectif de type "je pense que c'est prêt". Ce document sert aussi de preuve documentée de rigueur d'ingénierie pour le portfolio.

---

## Phase 1 — Noyau agentique en texte

- [ ] L'agent répond à une requête en CLI en utilisant au moins 2 tools différents (web search + exécution Python) dans une même conversation, **sans intervention manuelle** entre les deux appels.
- [ ] La mémoire simple (JSON/SQLite) persiste entre deux lancements du script : fermeture du terminal, relance, l'agent retrouve un fait donné en session précédente.
- [ ] Capacité à expliquer, sans regarder le code, le déroulé du function calling brut : parsing de la requête du modèle → exécution du tool → renvoi du résultat → décision du modèle (continuer ou conclure).
- [ ] Gestion d'erreur basique : si un tool échoue (ex. pas de connexion internet), l'agent ne crash pas — il informe l'utilisateur et reste utilisable.

**Test de validation rapide (< 5 min) :**
1. Lancer l'agent, poser une question nécessitant une recherche web puis un calcul Python dans le même échange → vérifier l'enchaînement sans intervention.
2. Donner un fait à retenir, quitter, relancer, redemander ce fait.
3. Couper le réseau, poser une question nécessitant le web → vérifier que l'agent répond proprement au lieu de crasher.

---

## Phase 2 — Outils étendus

- [ ] L'agent peut lire ET écrire un fichier sur demande, sans corrompre son contenu (test : écrire, relire, comparer).
- [ ] Au moins un appel à une API externe réelle (pas juste web search générique) fonctionne de bout en bout.
- [ ] Système de permissions minimal : l'agent ne peut pas supprimer un fichier sans confirmation explicite de l'utilisateur.

---

## Phase 3 — Mémoire long terme

- [ ] Un fait donné il y a au moins 10-15 sessions est retrouvé correctement via recherche vectorielle, sans halluciner un fait proche mais faux.
- [ ] Moyen d'inspecter le contenu de la mémoire (pas une boîte noire totale) — au minimum un script qui dump les embeddings + texte associé.

---

## Phase 4 — Couche vocale

- [ ] Cycle complet voix → texte → LLM → texte → voix fonctionne avec une latence jugée acceptable à l'usage réel.
- [ ] **Seuil de latence fixé à l'avance :** < 3 secondes (à ajuster ici si besoin, mais avant les tests, pas après).

---

## Phase 5 — Wake word

- [ ] Le wake word déclenche l'écoute dans un environnement avec bruit de fond réaliste (pas un silence de labo).
- [ ] Taux de faux positifs jugé tolérable sur une session d'1h (seuil à définir avant test).

---

## Phase 6 — Domotique

- [ ] Même en simulation, un ordre vocal ou texte déclenche une action simulée traçable dans un log.
- [ ] Format de log conçu pour basculer vers du matériel réel sans réécrire la logique métier.

---

## Phase 7 — Dashboard

- [ ] Depuis l'interface web, possibilité de voir l'historique d'une session passée.
- [ ] Possibilité de déclencher manuellement un tool depuis le dashboard, sans repasser par la CLI.

---

## Historique des décisions techniques

| Date | Décision | Justification |
|------|----------|----------------|
| 2026-08-16 | Recherche web : Tavily API | API pensée pour agents LLM, résultats JSON déjà nettoyés, 1000 requêtes/mois gratuites. Le scraping direct ajoute une complexité incidentielle (parsing HTML, blocage anti-bot) hors du critère de succès de la Phase 1 (tool-chaining, pas robustesse de parsing). Sert aussi de premier exemple d'intégration d'API externe réelle. |
| _(à compléter)_ | LLM Phase 1 | _(à compléter)_ |
| 2026-08-19 | Permissions : module dédié `tools/permissions.py` plutôt que logique inline dans `agent.py` | Séparation des responsabilités cohérente avec `tools/base.py` : la boucle agentique orchestre le LLM, elle ne doit pas porter la politique de sécurité. Anticipe la Phase 6 où la politique de confirmation deviendra plus riche (niveaux de risque, listes blanches) sans jamais toucher au cœur du function calling. |
| 2026-08-19 | Filtre `python_exec` : blocage définitif (`ToolResult.fail`) plutôt que passage par `requires_confirmation` | Distinction de nature assumée entre deux mécanismes : `requires_confirmation` sert des actions légitimes nécessitant un feu vert (ex. `write_file`), le filtre AST pose des lignes rouges structurelles non négociables en conversation (ex. `import os`). Les mélanger banaliserait le signal de confirmation et ajouterait une friction inutile pour des cas déjà tranchés par design. |
| 2026-08-19 | Liste noire AST étendue au-delà de `docs/secu.md` (ajout `pathlib`, `ctypes`, `importlib`, `urllib`, `http`, `getattr`/`setattr`/`globals`/`locals`, accès `__builtins__`) | La liste initiale couvrait les vecteurs évidents (import direct) mais pas les contournements immédiats par introspection (`getattr(__builtins__, 'eval')`) ni les modules équivalents non listés (`pathlib` pour le filesystem, `urllib`/`http` pour le réseau). Limite assumée : reste un filtre statique, pas une sandbox — voir `tools/safety.py`. |
| 2026-08-19 | API externe #1 : Wikipedia (REST API officielle Wikimedia) | Complémentaire à Tavily plutôt que redondant : données structurées et sourcées d'une seule encyclopédie de référence (champ `extract`), vs résumé agrégé du web générique. Aucune clé API, aucune authentification — friction d'intégration nulle, cohérent avec le choix Tavily. Repli automatique sur l'endpoint de recherche (`/w/rest.php/v1/search/page`) si le titre exact échoue (404), pour éviter de renvoyer un échec sec au modèle sur une simple imprécision de formulation. Lecture seule → pas de `requires_confirmation`. |
