# Changelog — SwarmProof

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le versionnage
sémantique. Rappel : SwarmProof produit une **preuve technique, pas une certification** ;
la supériorité du hybrid swarm sur un agent seul n'est pas prouvée par ce projet.

## [0.2.1] — 2026-11-05 — levée des réserves R1/R3 du re-test red team

### Modifié
- **R1 — libellé/exit de `verify`** : sans `--allow-oracle-cmd`, le résultat affiche désormais
  **« PACK COHÉRENT — intégrité OK, verdict NON rejoué (origine non prouvée) »** (exit 0 si intact,
  1 si altéré). **« PACK VALIDE » est réservé au rejeu réussi et cohérent** ; un rejeu mismatch ou
  une commande refusée donne « PACK ALTÉRÉ/INVALIDE » (exit 1). JSON enrichi (`label`,
  `verdict_replayed`, `exit_code`).
- **R3 — tokens Codex** : parsing durci (`tokens used` sur stdout **et** stderr, valeur sur la ligne
  suivante, séparateurs milliers `12,345`/`1 234`/`12.345`, variantes `total tokens`/`tokens consumed`) ;
  tests unitaires + test d'intégration via shim CLI (vrai chemin subprocess, aucun appel modèle) ; tentative de validation live unique = timeout CLI 120 s, non relancée (instabilité codex documentée dans `reports/swarmproof-r1r3.md`).
- README : compteur de tests corrigé (**87**), en-tête explicite « preuve technique de cohérence
  interne, pas d'origine — non opposable en l'état, signature prévue (R2) ».
- Version 0.2.1.

## [0.2.0] — 2026-11-05 — durcissement « utilisable et publiable »

### Ajouté
- **Retry infra borné** : `--max-retries N` (défaut 1) sur erreur CLI/timeout, compté séparément
  (`run.json.retries`, `trace.jsonl` : `call_retry`, `call_budget_exhausted`).
- **Plafond global d'appels** : `--max-calls N` (retries inclus). À épuisement, plus aucun appel
  n'est émis et le verdict devient **INCONCLUSIVE** — jamais de PASS silencieux.
- **Verdicts explicites à 3 états** : `PASS` (oracle), `FAIL` (oracle a jugé et refusé),
  `INCONCLUSIVE` (erreur infra définitive, budget épuisé, aucun candidat exploitable, timeout oracle).
  Le statut auto-déclaré du moteur NEXUS n'entre jamais dans le verdict.
- **Correctifs multi-fichiers** : parsing de blocs étiquetés `--- FILE: chemin.py ---`, un fichier
  complet par bloc ; **application atomique** (tout ou rien) ; rejet explicite des blocs partiels,
  des diffs, des placeholders `...`, des doublons, des chemins hors arborescence et des blocs
  non étiquetés ambigus. Les rejets sont publiés dans `run.json.rejected_candidates` et `report.md`.
- **Tokens Codex** : capture de la ligne `tokens used: N` (`run.json.model_calls[].tokens_total`,
  `trace.jsonl`) ; le coût USD Codex reste `n/a` (non exposé par le CLI). Claude inchangé
  (tokens + coût notionnel via `--output-format json`).
- **Ergonomie CLI** : `--json` (résumé machine-lisible sur stdout, logs humains sur stderr),
  `--oracle-timeout`, codes retour documentés `0=PASS`, `1=FAIL|INCONCLUSIVE`, `2=usage/erreur`.
- **Fixture multi-fichiers** `examples/fixture-multi/` : bug de cache/invalidation réparti sur
  `src/store.py` + `src/cache.py` (2 tests rouges / 4), support des tests et de la démo v2.
- **Tests** : 87 tests `unittest` stdlib (≥50 requis), dont retry, budget, multi-fichiers atomiques,
  verdicts INCONCLUSIVE, tokens Codex, `--json`/codes retour, et intégration du vrai moteur NEXUS
  avec drivers simulés (mono et multi-fichiers, zéro appel API).
- **CI GitHub Actions** (`.github/workflows/ci.yml`) : matrice Python 3.11–3.13, tests, démo
  dry-run + `verify`, build wheel + installation + `swarmproof --version`.

### Modifié
- `swarmproof fix` restructuré : budget d'appels, retries, parsing multi-fichiers, verdict à 3 états.
- `report.md`/`run.json` enrichis : retries, budget, rejets de propositions, justification du verdict,
  et rappel explicite « preuve technique, pas certification ; supériorité du swarm non prouvée ».
- Version 0.2.0.

### Sécurité (corrections red team indépendant — 3 vulnérabilités critiques v0.1)
- **Oracle contournable** : PASS exige désormais une preuve d'exécution de tests
  (`tests_run >= 1` + marqueur unittest/pytest parsable). Un exit 0 nu (ex. `os._exit(0)`) donne
  `INCONCLUSIVE`, jamais PASS.
- **`verify` dangereux (RCE)** : aucune commande du pack n'est exécutée par défaut ; rejeu optionnel
  via `--allow-oracle-cmd` en mode **argv sans shell** (métacaractères refusés). Chemins absolus,
  `..`, symlinks et fichiers non listés refusés ; JSON invalide géré ; manifeste re-signé =
  cohérence interne, **pas** preuve d'origine (`origin_proven=false`).
- **Fuite secrets/chemins** : fichiers `.env`/`*.pem`/`*.key`/`id_rsa*` exclus des copies, motifs de
  clés redactés (`[REDACTED_SECRET]`), chemins locaux absolus neutralisés dans les métadonnées.
- `--target` validé (relatif, dans le dépôt, existant, jamais un fichier de test).
- 14 tests de régression red team (`tests/test_security.py`) ; suite portée à **87 tests** (97 en 0.2.1).

### Corrigé
- v0.1 : un échec d'agent pouvait rester masqué derrière un statut moteur `COMPLETED` — exposé via
  `engine_ok`/`engine_errors` (déjà en v0.1) et désormais répercuté sur le verdict (`INCONCLUSIVE`).

## [0.1.0] — 2026-11-05 — MVP

- `swarmproof fix` / `verify` : moteur NEXUS réel via `invoke_agent`, drivers CLI claude/codex,
  oracle externe (tests restaurés), Evidence Pack hashé et autosuffisant, verrou « le statut moteur
  n'est pas la preuve ».
- 38 tests, démo réelle PASS (`examples/demo-pack/`), rapport `reports/swarmproof-mvp.md`.
