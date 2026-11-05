# SwarmProof

[![CI](https://github.com/yannabadie/swarmproof/actions/workflows/ci.yml/badge.svg)](https://github.com/yannabadie/swarmproof/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Ce n'est pas un framework ni un swarm de plus : le swarm propose, l'oracle externe décide, le pack le prouve.**

`swarmproof` est un CLI de **remédiation vérifiée** pour dépôts de code : il fait travailler un
**hybrid swarm** (moteur NEXUS réel, agents Claude + Codex), **ignore le statut auto-déclaré** du
moteur, restaure les tests avant jugement, et laisse un **oracle externe** (votre suite de tests)
rendre le verdict. Le résultat est un **Evidence Pack** autosuffisant, hashé et vérifiable hors ligne.

> Le produit existe parce qu'un agent qui dit « c'est corrigé » ne prouve rien.
> Ici, la seule chose qui compte est : **l'oracle passe ou il ne passe pas**.

> **Le pack est une preuve technique de cohérence interne, pas d'origine (pas de signature)** :
> il est **non opposable en l'état**. Une signature cryptographique (Ed25519/minisign ou attestation
> CI) est prévue (réserve R2 du red team). Ce que le pack prouve :
> les fichiers n'ont pas changé depuis son écriture et l'oracle rejoué donne le même verdict ;
> ce qu'il ne prouve pas : qui l'a produit ni qu'il n'a pas été forgé par un tiers.

**v0.2.1 (2026-11-05)** : retry infra borné (`--max-retries`), plafond d'appels (`--max-calls`),
verdict explicite **INCONCLUSIVE** (jamais de PASS silencieux en cas d'échec infra), correctifs
**multi-fichiers atomiques**, capture des **tokens Codex**, sortie **`--json`**, CI GitHub Actions,
**97 tests**. Voir [CHANGELOG.md](CHANGELOG.md).

> **Preuve technique, pas certification. La supériorité du hybrid swarm sur un agent seul n'est
> pas prouvée par ce projet** (n=1, un run) — elle fait l'objet d'un pilote séparé.

---

## Pourquoi

Un audit E2E du moteur NEXUS a montré trois faits :

1. le moteur **s'exécute réellement** avec des drivers CLI hétérogènes ;
2. il peut rapporter `COMPLETED` alors qu'un de ses agents a échoué (erreur avalée) ;
3. sa vérification intégrée (`ArtifactVerifier`) ne prouve pas que le code fonctionne.

SwarmProof renverse donc le rapport de confiance : **le swarm est une source de propositions, jamais
une source de vérité**. La vérité est l'exécution d'un oracle indépendant, et la preuve est un pack.

## Ce que fait l'outil

```
swarmproof fix <repo> --oracle "<commande de tests>" --out <pack> [options]
```

1. **Copie jetable** du dépôt (le dépôt source n'est jamais modifié).
2. **Pré-pack statique optionnel** via [AgentProof](../agentproof/) si importable (audit déterministe,
   sans LLM) — sinon marqué « non exécuté », jamais bloquant.
3. **Exécution du moteur NEXUS original** (`HybridSwarmEngine`, extrait de `swarm-os` en copie `/tmp`,
   jamais modifié) via son point d'injection `invoke_agent` : agents CLI hétérogènes (`claude -p`,
   `codex exec`), mode `lead_support` (2 appels) ou `specialist` (1 appel), timeout par appel,
   **retry borné** (`--max-retries`) et **plafond global d'appels** (`--max-calls`).
4. **Aucune confiance dans le statut moteur** : `engine_ok` / `engine_errors` sont calculés à partir
   des statuts d'agents et exposés dans le pack même si le moteur dit `COMPLETED`.
5. **Oracle externe** : chaque correctif candidat — **mono ou multi-fichiers**, appliqué
   **atomiquement** — est évalué dans une copie propre ; les fichiers de **tests sont restaurés depuis
   la copie vierge** (impossible de gagner en modifiant les tests), puis la commande oracle s'exécute.
   C'est la seule source du verdict : `PASS`, `FAIL`, ou `INCONCLUSIVE` si l'infra empêche de juger.
   Les propositions partielles/ambiguës/hors cible sont **refusées** et publiées dans le pack.
6. **Evidence Pack** : `report.md`, `run.json`, `trace.jsonl`, `oracle.jsonl`, `diff.patch`,
   `mapping.json`, `source/`, `tree/`, `manifest.sha256`, `README.txt`.
7. **`swarmproof verify <pack>`** : vérifie le manifeste SHA-256 et **rejoue l'oracle hors ligne**
   (aucun appel modèle) ; compare le verdict rejoué au verdict enregistré.
8. **`--json`** : résumé machine-lisible (verdict, appels/retries, candidats/rejets, oracle, pack,
   code retour) pour l'automatisation ; logs humains redirigés sur stderr.

```
   repo + oracle
        |
        v
 [copie jetable] --> [pré-pack AgentProof (optionnel)]
        |
        v
 [moteur NEXUS: swarm propose] --(CLI claude/codex)--> candidats
        |
        v
 [oracle externe: tests restaurés] --> PASS / FAIL
        |
        v
 [Evidence Pack] --> swarmproof verify / shasum -a 256 -c manifest.sha256
```

## Installation

Python ≥ 3.11, **bibliothèque standard uniquement, zéro dépendance runtime**.

```bash
cd product/swarmproof
pip install -e .            # fournit la commande `swarmproof`
# ou sans installation :
python -m swarmproof --version
./bin/swarmproof --version
```

Prérequis pour un run réel : les CLI `claude` et `codex` authentifiés en non-interactif, et le dépôt
`swarm-os` accessible (par défaut `../../swarm-os` depuis ce répertoire, sinon `--nexus-src` ou
`NEXUS_SRC=/chemin/vers/swarm-os`). Aucune clé API n'est nécessaire.

## Quickstart

```bash
# 1. Dry-run (aucun appel modèle) : valide la mécanique et produit un pack
python -m swarmproof fix examples/fixture \
  --oracle "python -m unittest discover -s tests -v" \
  --out /tmp/swarmproof-dry --dry-run

python -m swarmproof verify /tmp/swarmproof-dry

# 2. Run réel : hybride Codex (lead) + Claude (support), 2 appels
python -m swarmproof fix examples/fixture \
  --oracle "python -m unittest discover -s tests -v" \
  --out /tmp/swarmproof-real --roles codex,claude --timeout 240

# 3. Vérification du pack (hors ligne, sans appel modèle)
python -m swarmproof verify /tmp/swarmproof-real
cd /tmp/swarmproof-real && shasum -a 256 -c manifest.sha256
```

## Démo vérifiée v2 (2026-11-05)

Le pack `examples/demo-pack-v2/` est un **run réel multi-fichiers** (2 bugs de cache/invalidation à
corriger dans `src/store.py` + `src/cache.py`) :

```bash
python -m swarmproof fix examples/fixture-multi \
  --oracle "python -m unittest discover -s tests -v" \
  --out examples/demo-pack-v2 --roles codex,claude --timeout 180 \
  --max-retries 1 --max-calls 3
```

- **Verdict oracle : PASS** — preuve d'exécution vérifiée (`unittest`, 4 tests, marqueur `OK`),
  correctif appliqué **atomiquement sur 2 fichiers** (`src/cache.py` + `src/store.py`), 1ʳᵉ tentative.
- 2 appels CLI (budget 3, retries 0) : codex lead 21,6 s → correctif ; claude support 48,9 s
  (5 204 tokens, 0,1646 $) → revue. Moteur NEXUS `COMPLETED`, `engine_ok=true`.
- 1 proposition **rejetée** explicitement (support : « aucun bloc de code complet détecté » —
  les blocs partiels/ambigus ne sont jamais appliqués), publiée dans le pack.
- Vérification : `swarmproof verify examples/demo-pack-v2` (intégrité, **aucune commande exécutée**)
  → **PACK COHÉRENT — intégrité OK, verdict NON rejoué (origine non prouvée)** ;
  `swarmproof verify examples/demo-pack-v2 --allow-oracle-cmd` (rejeu contrôlé) → PASS rejoué =
  PASS enregistré → **PACK VALIDE** ; `shasum -a 256 -c manifest.sha256` → OK (30 fichiers).
- Pack nettoyé : secrets exclus, `REDACTED`, chemins absolus neutralisés, aucun prompt intégral ;
  manifeste `e3382b1d…`.
- L'ancien pack `examples/demo-pack/` (v0.1) a été retiré : il contenait des chemins locaux absolus
  et sa vérification exécutait la commande du pack (vulnérabilités corrigées en v0.2).

## Options principales

```
swarmproof fix <repo> --oracle CMD --out DIR
  --roles claude,codex     fournisseurs dans l'ordre lead,support (défaut claude,codex)
  --mode lead_support|specialist   défaut lead_support (2 agents ; specialist = 1 agent)
  --timeout S              timeout par appel modèle (défaut 240 s)
  --oracle-timeout S       timeout de la commande oracle (défaut 180 s)
  --max-retries N          retries sur erreur infra/timeout par appel logique (défaut 1)
  --max-calls N            plafond global d'appels CLI réels, retries inclus (défaut 6)
  --target FICHIER         fichier cible (répétable ; sinon auto-détection src/ ou racine)
  --dry-run                aucun appel modèle ni oracle ; pack de simulation
  --json                   résumé machine-lisible sur stdout
  --no-prepack             désactive le pré-pack AgentProof
  --force                  écrase un pack existant
  --nexus-src CHEMIN       dépôt swarm-os (sinon NEXUS_SRC / ../../swarm-os)
  --keep-temp              conserve le répertoire de travail temporaire

swarmproof verify <pack> [--skip-oracle] [--oracle-timeout S] [--json]
swarmproof --version
```

Codes de sortie : `0` = **PASS** ; `1` = **FAIL** ou **INCONCLUSIVE** (jamais un succès) ;
`2` = erreur d'usage/configuration. `verify` : `0` = pack **COHÉRENT** (intégrité OK, verdict non
rejoué) ou **VALIDE** (rejeu `--allow-oracle-cmd` réussi et cohérent) ; `1` = pack **ALTÉRÉ/INVALIDE**.
Le libellé distingue explicitement « cohérent » (sans rejeu) de « valide » (rejeu réussi).

## Evidence Pack

| Fichier | Rôle |
|---|---|
| `report.md` | Résumé lisible : verdict, statut moteur vs vérité oracle, rôles/modèles, coûts/tokens, échecs, limites |
| `run.json` | Données structurées (statuts, durées, tokens, coûts, `engine_ok`, `engine_errors`, verdict) |
| `trace.jsonl` | Une ligne par événement/appel : rôle, fournisseur, `prompt_sha256`, durée, exit, erreurs |
| `oracle.jsonl` | Une ligne par correctif candidat jugé : cible, exit, PASS/FAIL, tests, tests restaurés |
| `diff.patch` | Diff unifié multi-fichiers entre dépôt source et arbre évalué |
| `mapping.json` | Fichiers cibles, chemins de tests restaurés, mapping agents → fournisseurs |
| `source/` | Copie vierge du dépôt (les tests non modifiés) |
| `tree/` | État évalué (correctif + tests restaurés) |
| `prepack/` | Sous-pack AgentProof optionnel (audit statique, si disponible) |
| `manifest.sha256` | SHA-256 de chaque fichier — vérifiable avec `shasum -a 256 -c` |
| `README.txt` | Mode d'emploi du pack pour un relecteur |

Le pack ne contient **aucun secret** : pas de variables d'environnement, pas de prompt intégral
(seulement leurs empreintes SHA-256), seulement des sorties d'agents tronquées et hashées.

## Sécurité (v0.2) — leçons du red team

La v0.1 a été testée par un red team indépendant : 3 vulnérabilités critiques ont été corrigées
dans cette version, et les tests de régression correspondants sont dans `tests/test_security.py`.

| Risque v0.1 | Correctif v0.2 |
|---|---|
| **Oracle contournable** : un candidat qui fait `os._exit(0)` rendait l'oracle « PASS » sans exécuter de test | Le PASS exige désormais une **preuve d'exécution** : `tests_run >= 1` + marqueur de synthèse parsable (unittest `OK/FAILED`, pytest `N passed/failed`). Un exit 0 nu donne **INCONCLUSIVE**, jamais PASS. |
| **`verify` exécutait la commande shell d'un pack non fiable** (RCE) et acceptait `../`, fichiers cachés, re-signature | Par défaut, `verify` **n'exécute aucune commande** : uniquement manifeste + cohérence interne. Le rejeu exige `--allow-oracle-cmd` et n'accepte que des commandes **simples sans métacaractères shell** (pas de shell). Chemins absolus/`..`/symlinks refusés, fichiers non listés refusés, JSON invalide géré proprement. Manifeste re-signé = cohérence interne, **pas** preuve d'origine. |
| **Fuite de secrets/chemins** : `source/`+`tree/` recopiaient `.env`/clés et les chemins absolus apparaissaient dans le pack | Fichiers de secrets exclus (`.env`, `*.pem`, `*.key`, `id_rsa*`, etc.), motifs de clés **redactés** (`[REDACTED_SECRET]`), chemins locaux absolus remplacés par `<repo>`/`<home>` dans les métadonnées. |

**Authenticité** : `manifest.sha256` prouve une **cohérence interne auto-attestée** (les fichiers n'ont
pas changé depuis l'écriture du pack), pas l'origine du pack. Aucune signature cryptographique n'est
incluse ; le pack n'est **pas opposable en l'état**. Pour l'origine, exiger un canal de livraison
authentifié ou ajouter une signature hors pack (prévue). `verify` affiche « PACK COHÉRENT » sans
rejeu et réserve « PACK VALIDE » au rejeu réussi.

**Rôles et safeguards CLI** : le défaut est `--roles claude,codex`. Sur certains prompts générés par le
moteur, le CLI Claude peut refuser (`safeguard`, exit 1) ; un retry ne corrige pas un refus déterministe
— le pack l'expose (`engine_ok=false`) et le verdict devient `INCONCLUSIVE` s'il n'y a pas de candidat
vérifiable. Démo v2 : lead Codex + support Claude (`--roles codex,claude`) pour cette raison.

## Ce que ça prouve / ce que ça ne prouve pas

**Prouve** : sur ce dépôt, à cette date, avec cet oracle, le correctif de `tree/` passe les tests ;
les tests ont été restaurés avant jugement ; chaque fichier du pack a l'empreinte SHA-256 listée ;
le pack est autosuffisant et rejouable hors ligne.

**Ne prouve pas** : la qualité générale du code hors tests, la supériorité d'un swarm sur un agent
seul, la reproductibilité exacte des réponses des modèles, la sécurité du correctif en production,
ni la couverture d'oracle (si vos tests sont mauvais, le verdict l'est aussi).

## Limites connues

- **n=1 run, un dépôt** : c'est une preuve de faisabilité, pas une étude statistique.
- **Tâches à oracle** uniquement : sans tests exécutables, le produit ne peut rien garantir.
- **Coût/latence** : 1 à 2 appels LLM par run (240 s/appel max) ; les CLI peuvent refuser ou timeouter
  — ces échecs sont exposés dans le pack (`engine_ok=false`), pas maquillés.
- **Moteur extrait** : `HybridSwarmEngine` est importé d'une copie jetable du dépôt public
  [`nexus-swarm-os`](https://github.com/yannabadie/nexus-swarm-os) avec un shim de 3 `__init__` ;
  ce n'est pas un package NEXUS publié.
- **Correctifs multi-fichiers** : les fichiers doivent être fournis **complets et étiquetés** par
  l'agent, appliqués atomiquement ; les patchs unifiés partiels, diffs, placeholders et créations de
  fichiers arbitraires sont refusés. Pas encore de résolution de conflits ni de patchs unifiés génériques.

## Tests

```bash
cd product/swarmproof
python -m unittest discover -s tests -v
```

Suite stdlib de **97 tests** (~1,4 s) : candidats mono/multi-fichiers et application atomique, oracle
(red/green + restauration des tests), pack/manifeste/falsification, verdicts PASS/FAIL/INCONCLUSIVE,
retry/budget d'appels, tokens Codex, `--json`/codes retour, dry-run CLI, pré-pack AgentProof, et
intégration du **vrai** moteur NEXUS avec drivers simulés mono et multi-fichiers (zéro appel API ;
ignorée si `swarm-os` est absent).

## Checklist d'audit (ressource)

La checklist 40 points utilisée par la couche de pré-pack (agents/MCP, mapping AI Act / ISO 42001 /
OWASP) est incluse dans [docs/checklist-40-points.md](docs/checklist-40-points.md), sous licence
CC BY 4.0. Elle ne certifie rien : elle montre ce qui manque.

## Licence

MIT — voir [LICENSE](LICENSE).
