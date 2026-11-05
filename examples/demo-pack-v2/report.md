# SwarmProof — Evidence Pack

- **Généré** : 2026-11-05T18:12:45+00:00
- **Outil** : swarmproof 0.2.0
- **Dépôt** : `fixture-multi` (<repo>)
- **Mode** : lead_support — rôles : lead=`codex`, support=`claude`
- **Dry-run** : non

## Verdict

**VERDICT (oracle externe) : PASS**

- Oracle : `python -m unittest discover -s tests -v` (timeout 180.0s)
- Tests exécutés : 4 · échecs : 0
- Tests restaurés avant jugement : tests
- Preuve d'exécution : preuve d'exécution: unittest, 4 test(s), marqueur de synthèse présent
- Tentatives de correctif jugées : 1
- Justification du verdict : oracle PASS sur la tentative 0

## Moteur NEXUS (statut auto-déclaré — NON utilisé comme preuve)

- Statut déclaré : `SwarmPhase.COMPLETED` · mode sélectionné : `lead_support` · version : 12.4.0 (COGNITIVE BOOST)
- `engine_ok` : **True** · erreurs d'agent : 0
- appels CLI : 2/3 · retries : 0

> Rappel : un moteur peut rapporter `COMPLETED` alors qu'un agent a échoué. Seul l'oracle tranche.

## Étapes (rôle / fournisseur / modèle / durée / tokens / coût)

| # | rôle | fournisseur | modèle | tentative | durée (s) | tokens in/out (total) | coût USD | statut |
|---|---|---|---|---|---|---|---|---|
| 1 | lead | codex | n/a | 1 | 21.61 | n/a | n/a | ok |
| 2 | support | claude | claude-opus-5-5 | 1 | 48.86 | 2/5204 | 0.164584 | ok |

## Correctifs proposés et jugements de l'oracle

| # | rôle | agent | fichier cible | sha256 (court) |
|---|---|---|---|---|
| None | lead | lead_agent | None | None |

| tentative | provenance | cible | exit | PASS/FAIL | tests | échecs |
|---|---|---|---|---|---|---|
| 0 | lead/lead_agent | src/cache.py | 0 | PASS | 4 | 0 |

## Propositions rejetées (blocs partiels/ambigus/hors cible)

| rôle | agent | raison | détail |
|---|---|---|---|
| support | support_agent | aucun bloc de code complet détecté |  |

## Changements

Fichiers modifiés vs dépôt source : `src/cache.py`, `src/store.py`.

## Pré-pack statique AgentProof (optionnel)

- AgentProof 1.0.0 : score 25.0/100 (E — Insuffisant), 8 fichiers.
- Sous-pack : `prepack/` · manifeste : `2c3353f093e6239582ac2c2ce73ef2fe7b9f9165c7e0782837d60977dbd64483`

## Ce que ce pack prouve / ne prouve pas

**Prouve** : sur ce dépôt, à cet instant, le correctif de `tree/` fait passer l'oracle `python -m unittest discover -s tests -v` ; les tests ont été restaurés avant jugement ; chaque fichier du pack a l'empreinte SHA-256 listée.

**Ne prouve pas** : la qualité générale du code hors tests, la supériorité d'un swarm sur un agent seul, la reproductibilité des réponses des modèles (non déterministes), ni la sécurité du correctif pour un usage en production.

**Preuve technique, pas certification.** La supériorité du hybrid swarm sur un agent seul n'est pas démontrée par ce pack (n=1, un run).

**Authenticité** : manifeste = cohérence interne auto-attestée (pas de signature, pas de preuve d'origine). Aucune commande du pack n'est exécutée par `verify` sans `--allow-oracle-cmd`.
- Limite : n=1 run, tâche unique : signal de faisabilité, pas de significativité.
- Limite : Le verdict dépend entièrement de l'oracle choisi (qualité des tests).
- Limite : Preuve technique, pas certification ; supériorité du swarm non prouvée.
- Limite : Les réponses des modèles ne sont pas reproductibles à l'identique.
- Limite : Le moteur NEXUS est une extraction (copie /tmp) ; swarm-os n'est pas modifié.
