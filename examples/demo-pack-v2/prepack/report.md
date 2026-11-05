# Audit AgentProof — pristine

> **Preuve technique, pas une certification.** Ce rapport documente des observations statiques et reproductibles sur un dépôt. Il ne certifie ni la conformité AI Act / ISO 42001, ni l'absence de risque.

## 1. Métadonnées

| Champ | Valeur |
|---|---|
| Date de génération | 2026-11-05 18:12:45 UTC |
| Outil | AgentProof (déterministe, hors ligne, sans LLM) |
| Version | 1.0.0 |
| Dépôt audité | `pristine` |
| Commit | `non déterminé (pas de métadonnée git)` |
| Commande | `agentproof audit /var/folders/2c/92cnz9_x3fjcph_b4570j8140000gn/T/swarmproof-run-b_rz_zuo/pristine` |
| Contrôles | 68 contrôles déterministes |
| Filtre de sévérité | `info` |

## 2. Résumé exécutif

Le dépôt obtient un score pondéré de **25.0/100** (niveau **E — Insuffisant**) sur 39 contrôles évalués. **1 contrôle(s) critique(s)** et 17 élevé(s) restent non conformes : ils doivent être traités avant tout déploiement client.

Répartition : 25 non conforme(s), 10 partiel(s), 4 conforme(s), 29 non évalué(s).

**Findings prioritaires :**

1. **LOG-03** · Critique · Preuve d'inviolabilité du journal (chaîne de hachage/signature) — Aucune preuve d'inviolabilité (chaîne de hachage, signature) pour le journal d'audit. _(preuve : — (contrôle par absence))_
2. **DOC-01** · Élevée · Limites et cas non couverts documentés — Aucune documentation des limites ou des cas non couverts : le périmètre réel est indiscernable. _(preuve : — (contrôle par absence))_
3. **DOC-02** · Élevée · Politique de divulgation de vulnérabilités — Aucune politique de divulgation de vulnérabilité (SECURITY.md / contact). _(preuve : — (contrôle par absence))_
4. **EGRESS-01** · Élevée · Allowlist d'égress réseau des outils de l'agent — Aucun contrôle d'égress réseau (allowlist ou blocklist) détecté. _(preuve : — (contrôle par absence))_
5. **EGRESS-02** · Élevée · Protection SSRF du fetcher web — Aucune protection SSRF détectée autour des outils réseau/web_fetch. _(preuve : — (contrôle par absence))_

## 3. Périmètre et méthode

Le dépôt `pristine` (commit `non déterminé (pas de métadonnée git)`) a été parcouru en lecture seule. AgentProof applique 68 contrôles déterministes répartis en 15 catégories : secrets, prompts, permissions d'outils, MCP, journalisation, supervision humaine, sandbox, égress réseau, pinning modèles, fournisseurs, évaluations, données personnelles, supply chain, documentation, intégrité.

**Méthode :**

- lecture du code, des configurations, des prompts et de la documentation présents dans le dépôt ;
- recherche de preuves positives (safeguard présent) ou négatives (absence de safeguard) par motifs déterministes ;
- chaque finding cite un fichier et une ligne vérifiables manuellement (`fichier:ligne`) ;
- aucun appel réseau, aucun appel LLM, aucune modification du dépôt ;
- exécution reproductible : mêmes fichiers + même version d'AgentProof + même horodatage ⇒ même pack (voir `manifest.sha256` et `README.txt`).

## 4. Score global et par catégorie

Le score est une moyenne pondérée par sévérité : `pass = 1,0`, `warn = 0,5`, `fail = 0,0` ; les contrôles `unknown` sont exclus du dénominateur. Poids : critique 10, élevé 6, moyen 3, faible 1, info 0,25.

**Score global : 25.0/100 — niveau E (Insuffisant)**

| Catégorie | Score | Niveau | Conformes | Partiels | Non conformes | Non évalués |
|---|---:|---|---:|---:|---:|---:|
| Secrets & identifiants | 79.3 | B — Correct | 2 | 1 | 1 | 0 |
| Prompts système & injection | 7.1 | E — Insuffisant | 0 | 1 | 4 | 0 |
| Permissions d'outils | 41.1 | D — Critique | 1 | 1 | 3 | 0 |
| MCP & intégrations | n/a | — — Non évalué | 0 | 0 | 0 | 5 |
| Journalisation & audit trail | 0.0 | E — Insuffisant | 0 | 0 | 5 | 1 |
| Supervision humaine | 0.0 | E — Insuffisant | 0 | 0 | 2 | 2 |
| Sandbox & containment | n/a | — — Non évalué | 0 | 0 | 0 | 5 |
| Égress réseau & SSRF | 0.0 | E — Insuffisant | 0 | 0 | 2 | 3 |
| Pinning modèles & versions | 16.7 | E — Insuffisant | 0 | 1 | 1 | 2 |
| Fournisseurs & failover | 50.0 | D — Critique | 0 | 1 | 0 | 2 |
| Évaluations & tests | 28.6 | E — Insuffisant | 0 | 3 | 2 | 0 |
| Données personnelles | 8.3 | E — Insuffisant | 0 | 1 | 3 | 0 |
| Supply chain | n/a | — — Non évalué | 0 | 0 | 0 | 6 |
| Documentation & limites | 25.0 | E — Insuffisant | 1 | 1 | 2 | 0 |
| Intégrité & artefacts | n/a | — — Non évalué | 0 | 0 | 0 | 3 |

## 5. Findings

35 finding(s) affiché(s) (filtre `info`). Les contrôles conformes sont listés en fin de section ; les non évalués figurent dans `checks.json`.

| ID | Sévérité | Catégorie | Constat | Statut | Preuve |
|---|---|---|---|---|---|
| `LOG-03` | Critique | Journalisation & audit trail | Preuve d'inviolabilité du journal (chaîne de hachage/signature) — Aucune preuve d'inviolabilité (chaîne de hachage, signature) pour le journal d'audi… | Non conforme | — (contrôle par absence) |
| `DOC-01` | Élevée | Documentation & limites | Limites et cas non couverts documentés — Aucune documentation des limites ou des cas non couverts : le périmètre réel est indiscernable. | Non conforme | — (contrôle par absence) |
| `DOC-02` | Élevée | Documentation & limites | Politique de divulgation de vulnérabilités — Aucune politique de divulgation de vulnérabilité (SECURITY.md / contact). | Non conforme | — (contrôle par absence) |
| `EGRESS-01` | Élevée | Égress réseau & SSRF | Allowlist d'égress réseau des outils de l'agent — Aucun contrôle d'égress réseau (allowlist ou blocklist) détecté. | Non conforme | — (contrôle par absence) |
| `EGRESS-02` | Élevée | Égress réseau & SSRF | Protection SSRF du fetcher web — Aucune protection SSRF détectée autour des outils réseau/web_fetch. | Non conforme | — (contrôle par absence) |
| `EVAL-01` | Élevée | Évaluations & tests | Suite de tests automatisés — Suite de tests réduite (1 fichier(s)). | Partiel | tests/test_cache.py |
| `EVAL-04` | Élevée | Évaluations & tests | Tests exécutés en CI — Aucune CI exécutant les tests : les garanties ne sont pas vérifiées à chaque changement. | Non conforme | — (contrôle par absence) |
| `HITL-01` | Élevée | Supervision humaine | Mécanisme d'approbation humaine présent — Aucun mécanisme d'approbation humaine (HITL) détecté. | Non conforme | — (contrôle par absence) |
| `LOG-01` | Élevée | Journalisation & audit trail | Journal d'audit structuré et append-only — Aucun journal d'audit structuré (AuditLogger / append-only) détecté. | Non conforme | — (contrôle par absence) |
| `LOG-02` | Élevée | Journalisation & audit trail | Identifiant de corrélation propagé entre actions — Aucun identifiant de corrélation (trace_id/request_id) propagé dans les logs. | Non conforme | — (contrôle par absence) |
| `LOG-04` | Élevée | Journalisation & audit trail | Politique de rétention et de rotation des journaux — Aucune politique de rétention/rotation des journaux d'audit détectée. | Non conforme | — (contrôle par absence) |
| `LOG-05` | Élevée | Journalisation & audit trail | Rédaction des secrets et données personnelles dans les logs — Aucune rédaction/masquage des secrets et données personnelles dans les journaux. | Non conforme | — (contrôle par absence) |
| `MODEL-03` | Élevée | Pinning modèles & versions | Modèle réellement utilisé tracé par appel — Le modèle réellement utilisé par les appels n'est pas journalisé : décision non attribuable. | Non conforme | — (contrôle par absence) |
| `PRIVACY-01` | Élevée | Données personnelles | Détection et rédaction des données personnelles — Aucune détection ni rédaction PII identifiée : prompts et logs peuvent contenir des données clients. | Non conforme | — (contrôle par absence) |
| `PRIVACY-02` | Élevée | Données personnelles | Rétention et effacement des données — Aucune procédure de rétention/effacement des données personnelles détectée. | Non conforme | — (contrôle par absence) |
| `PROMPT-01` | Élevée | Prompts système & injection | Prompts système isolés et versionnés — Aucun fichier de prompt système versionné identifié. | Non conforme | — (contrôle par absence) |
| `PROMPT-02` | Élevée | Prompts système & injection | Défense contre l'injection de prompt dans le code — Aucune défense anti-injection (InputGuard, patterns, sanitisation) détectée dans le code. | Non conforme | — (contrôle par absence) |
| `SECRET-03` | Élevée | Secrets & identifiants | Fichiers d'environnement absents ou exclus du versionnement — Aucun fichier d'environnement présent, mais .gitignore ne couvre pas .env/credentials. | Partiel | — (contrôle par absence) |
| `TOOL-01` | Élevée | Permissions d'outils | Politique centrale de permissions d'outils — Aucune politique centrale de permissions/validation des commandes d'outils détectée. | Non conforme | — (contrôle par absence) |
| `TOOL-03` | Élevée | Permissions d'outils | Containment des écritures fichiers — Aucun garde de chemins (containment des écritures) détecté dans le code. | Non conforme | — (contrôle par absence) |
| `DOC-03` | Moyenne | Documentation & limites | Architecture et modèle de sécurité documentés — Aucun document d'architecture/modèle de menace structuré identifié. | Partiel | — (contrôle par absence) |
| `EVAL-02` | Moyenne | Évaluations & tests | Évaluations spécifiques à l'agent — Aucune évaluation agentique dédiée (benchmark/eval harness) identifiée. | Partiel | — (contrôle par absence) |
| `EVAL-03` | Moyenne | Évaluations & tests | Scénarios de sécurité et red-team — Aucun scénario de sécurité adversarial identifié dans les évaluations. | Partiel | — (contrôle par absence) |
| `EVAL-05` | Moyenne | Évaluations & tests | Artefacts de preuve CI versionnés ou vérifiables — Aucun artefact de preuve (couverture, ledger CI, résultats) versionné pour les évaluations. | Non conforme | — (contrôle par absence) |
| `HITL-03` | Moyenne | Supervision humaine | Décisions d'approbation persistées — Aucune persistance des décisions d'approbation (impossible de prouver qui a approuvé quoi). | Non conforme | — (contrôle par absence) |
| `MODEL-02` | Moyenne | Pinning modèles & versions | Registre central des modèles et fournisseurs — Aucun registre central des modèles : les identifiants sont dispersés dans la configuration. | Partiel | — (contrôle par absence) |
| `PRIVACY-03` | Moyenne | Données personnelles | Chiffrement / local-first des données de l'agent — Aucun élément de chiffrement au repos ou de local-first identifié. | Partiel | — (contrôle par absence) |
| `PRIVACY-04` | Moyenne | Données personnelles | Documentation RGPD/AI Act utilisable par le client — Aucune documentation RGPD/AI Act : la base de conformité de l'agent n'est pas démontrée. | Non conforme | — (contrôle par absence) |
| `PROMPT-03` | Moyenne | Prompts système & injection | Contenu non fiable balisé avant le prompt (spotlighting) — Aucun marquage du contenu non fiable (documents, résultats d'outils) avant le prompt. | Non conforme | — (contrôle par absence) |
| `PROMPT-04` | Moyenne | Prompts système & injection | Protection contre la fuite du prompt système — Aucun filtre de sortie/protection contre la fuite du prompt système détecté. | Non conforme | — (contrôle par absence) |
| `PROMPT-05` | Moyenne | Prompts système & injection | Tests de régression sur l'injection de prompt — Aucun test de régression dédié à l'injection de prompt identifié. | Partiel | — (contrôle par absence) |
| `SECRET-04` | Moyenne | Secrets & identifiants | Gestion des secrets documentée (variables d'environnement, rotation) — Aucune documentation de gestion des secrets (variables d'environnement, rotati… | Non conforme | — (contrôle par absence) |
| `TOOL-04` | Moyenne | Permissions d'outils | Permissions d'outils différenciées par état/agent — Aucune matrice de permissions par état/agent identifiable ; permissions supposées globales. | Partiel | — (contrôle par absence) |
| `TOOL-05` | Moyenne | Permissions d'outils | Reçus structurés des appels d'outils — Aucun reçu d'exécution d'outil (commande, sortie, code retour) détecté. | Non conforme | — (contrôle par absence) |
| `PROVIDER-03` | Faible | Fournisseurs & failover | Canaris de santé des fournisseurs — Aucun canari de santé fournisseur : une panne ou une dérive de modèle ne serait détectée qu'en production. | Partiel | — (contrôle par absence) |

### Contrôles conformes

| ID | Contrôle conforme | Preuve |
|---|---|---|
| `SECRET-01` | Aucune clé API ou token en clair dans le dépôt | — (contrôle par absence) |
| `SECRET-02` | Aucune clé privée ou certificat sensible commité | — (contrôle par absence) |
| `TOOL-02` | Outils shell/exec gated par validation | — (contrôle par absence) |
| `DOC-04` | Hygiène des promesses : claims adossées à des preuves | — (contrôle par absence) |

## 6. Preuves détaillées

### LOG-03 — Preuve d'inviolabilité du journal (chaîne de hachage/signature)

- **Statut** : Non conforme · **Sévérité** : Critique
- **Constat** : Aucune preuve d'inviolabilité (chaîne de hachage, signature) pour le journal d'audit.
- **Pourquoi c'est un risque** : Un audit trail modifiable sans trace ne vaut pas preuve : l'altération des logs est le premier réflexe après un incident.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Enchaîner les événements par hash (prev_hash), sceller périodiquement la chaîne dans un manifeste SHA-256 et vérifier en CI.
- **Référentiels (indicatif)** : AI Act art. 12 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI08, ASI10

### DOC-01 — Limites et cas non couverts documentés

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune documentation des limites ou des cas non couverts : le périmètre réel est indiscernable.
- **Pourquoi c'est un risque** : Un client ne peut pas évaluer le périmètre réel d'un agent si le fournisseur ne déclare pas ses limites.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Publier une section Limitations/cas non couverts, datée, liée depuis le README et mise à jour à chaque release.
- **Référentiels (indicatif)** : AI Act art. 50 ; ISO 42001 A.8.2, A.9.2 ; OWASP ASI09

### DOC-02 — Politique de divulgation de vulnérabilités

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune politique de divulgation de vulnérabilité (SECURITY.md / contact).
- **Pourquoi c'est un risque** : Sans canal de signalement, un chercheur ou un client découvrant une faille n'a pas de chemin de remontée maîtrisé.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Créer SECURITY.md à la racine avec contact, délais de réponse et périmètre de divulgation responsable.
- **Référentiels (indicatif)** : AI Act art. 15, art. 26 ; ISO 42001 A.3.2, A.9.2 ; OWASP ASI04

### EGRESS-01 — Allowlist d'égress réseau des outils de l'agent

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun contrôle d'égress réseau (allowlist ou blocklist) détecté.
- **Pourquoi c'est un risque** : Un agent avec un accès réseau sortant non borné peut exfiltrer des données ou joindre un service interne.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Définir une allowlist de domaines par outil, l'appliquer avant chaque requête et journaliser les refus.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.10.1 ; OWASP ASI02, ASI05

### EGRESS-02 — Protection SSRF du fetcher web

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune protection SSRF détectée autour des outils réseau/web_fetch.
- **Pourquoi c'est un risque** : Sans blocage des hôtes internes/métadonnées, un web_fetch devient un proxy vers le réseau interne (SSRF).
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Bloquer localhost, IP privées, link-local, métadonnées cloud et variantes d'encodage ; résoudre puis vérifier l'IP.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI05

### EVAL-01 — Suite de tests automatisés

- **Statut** : Partiel · **Sévérité** : Élevée
- **Constat** : Suite de tests réduite (1 fichier(s)).
- **Pourquoi c'est un risque** : Sans tests reproductibles, aucune affirmation de qualité de l'agent ne peut être vérifiée par un tiers.
- **Preuves (fichier:ligne)** :
  - `tests/test_cache.py`
- **Remédiation attendue** : Maintenir une suite de tests exécutable hors ligne et la faire tourner sur chaque changement.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI08

### EVAL-04 — Tests exécutés en CI

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune CI exécutant les tests : les garanties ne sont pas vérifiées à chaque changement.
- **Pourquoi c'est un risque** : Une suite de tests non exécutée automatiquement ne protège pas contre les régressions.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Configurer une CI qui exécute tests, lint et scans de sécurité sur chaque PR, avec artifacts archivés.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, 9.1 ; OWASP ASI04

### HITL-01 — Mécanisme d'approbation humaine présent

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun mécanisme d'approbation humaine (HITL) détecté.
- **Pourquoi c'est un risque** : AI Act art. 14 exige une supervision humaine effective : un agent sans canal d'approbation ne peut pas être supervisé.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Exposer un canal d'approbation (CLI, API, notification) permettant d'approuver, refuser ou interrompre une action.
- **Référentiels (indicatif)** : AI Act art. 14 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI09, ASI10

### LOG-01 — Journal d'audit structuré et append-only

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun journal d'audit structuré (AuditLogger / append-only) détecté.
- **Pourquoi c'est un risque** : AI Act art. 12 et ISO 42001 exigent de pouvoir reconstituer les événements du système ; un log applicatif ne suffit pas.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Écrire un événement structuré (acteur, action, ressource, statut, horodatage) dans un journal append-only.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, 9.1 ; OWASP ASI08

### LOG-02 — Identifiant de corrélation propagé entre actions

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun identifiant de corrélation (trace_id/request_id) propagé dans les logs.
- **Pourquoi c'est un risque** : Sans trace_id commun, une chaîne multi-étapes (prompt → outil → réponse) n'est pas reconstructible après incident.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Générer un trace_id par requête/run et le propager dans tous les logs, spans et reçus d'outils.
- **Référentiels (indicatif)** : AI Act art. 12 ; ISO 42001 8.3, 9.1 ; OWASP ASI08

### LOG-04 — Politique de rétention et de rotation des journaux

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune politique de rétention/rotation des journaux d'audit détectée.
- **Pourquoi c'est un risque** : Une rétention non définie viole les obligations de conservation (AI Act art. 26) ou expose des données trop longtemps.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Définir une durée de conservation par type de journal, activer la rotation et documenter la procédure.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, A.7.4 ; OWASP ASI08

### LOG-05 — Rédaction des secrets et données personnelles dans les logs

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune rédaction/masquage des secrets et données personnelles dans les journaux.
- **Pourquoi c'est un risque** : Un journal qui capture prompts, tokens ou données clients devient à son tour une fuite de données.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Masquer les secrets/PII à l'émission du log, tester la sortie des journaux sur un corpus de canaris.
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 A.7.4, A.8.2 ; OWASP ASI03, ASI06

### MODEL-03 — Modèle réellement utilisé tracé par appel

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Le modèle réellement utilisé par les appels n'est pas journalisé : décision non attribuable.
- **Pourquoi c'est un risque** : Sans modèle journalisé, il est impossible de relier une sortie à la version du modèle qui l'a produite.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Émettre le modèle et sa version dans chaque trace/log d'appel LLM (OpenTelemetry GenAI semconv).
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 8.3, 9.1 ; OWASP ASI04, ASI08

### PRIVACY-01 — Détection et rédaction des données personnelles

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune détection ni rédaction PII identifiée : prompts et logs peuvent contenir des données clients.
- **Pourquoi c'est un risque** : Un agent support client manipule noms, emails et historiques : sans redaction, ils finissent dans les logs et les prompts.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Détecter (regex/classifieur) et masquer les PII avant persistance, prompt distant et journalisation.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.7.4, A.5.2 ; OWASP ASI03, ASI06

### PRIVACY-02 — Rétention et effacement des données

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune procédure de rétention/effacement des données personnelles détectée.
- **Pourquoi c'est un risque** : Le RGPD impose une durée de conservation et un droit à l'effacement ; AI Act art. 26 implique de borner les logs.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Définir une politique de rétention par donnée, implémenter suppression/export et documenter les durées.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 A.7.4, A.9.2 ; OWASP ASI06

### PROMPT-01 — Prompts système isolés et versionnés

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun fichier de prompt système versionné identifié.
- **Pourquoi c'est un risque** : Des prompts noyés dans le code ou modifiables sans trace rendent les changements de comportement inauditables.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Extraire les prompts dans un répertoire dédié versionné, avec un identifiant de version par prompt.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01

### PROMPT-02 — Défense contre l'injection de prompt dans le code

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune défense anti-injection (InputGuard, patterns, sanitisation) détectée dans le code.
- **Pourquoi c'est un risque** : Le contenu utilisateur ou externe peut détourner l'agent (ASI01) si aucune barrière d'entrée n'existe.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Implémenter un garde d'entrée (patterns, normalisation Unicode, scoring) et l'appliquer à tout contenu non fiable.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI01, ASI06

### SECRET-03 — Fichiers d'environnement absents ou exclus du versionnement

- **Statut** : Partiel · **Sévérité** : Élevée
- **Constat** : Aucun fichier d'environnement présent, mais .gitignore ne couvre pas .env/credentials.
- **Pourquoi c'est un risque** : Un .env suivi par git contourne les coffres à secrets et fuite à chaque clone ou fork.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Ajouter .env, *.pem, *.key et credentials.json au .gitignore, fournir un .env.example sans valeurs.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.7.4 ; OWASP ASI04

### TOOL-01 — Politique centrale de permissions d'outils

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucune politique centrale de permissions/validation des commandes d'outils détectée.
- **Pourquoi c'est un risque** : Sans politique centralisée, chaque outil décide seul de ses limites et les contournements prolifèrent.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Centraliser validation de commandes, chemins et accès réseau dans une ExecutionPolicy testée.
- **Référentiels (indicatif)** : AI Act art. 14, art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI05

### TOOL-03 — Containment des écritures fichiers

- **Statut** : Non conforme · **Sévérité** : Élevée
- **Constat** : Aucun garde de chemins (containment des écritures) détecté dans le code.
- **Pourquoi c'est un risque** : Un agent doit rester confiné à son workspace ; sinon il peut altérer le code, les prompts ou les secrets.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Résoudre les chemins, vérifier le confinement (workspace/parent), refuser les chemins absolus et protéger les fichiers sensibles.
- **Référentiels (indicatif)** : AI Act art. 14, art. 15 ; ISO 42001 8.2, A.7.4 ; OWASP ASI02, ASI05

### DOC-03 — Architecture et modèle de sécurité documentés

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucun document d'architecture/modèle de menace structuré identifié.
- **Pourquoi c'est un risque** : Une architecture non documentée rend l'audit des flux, des données et des privilèges dépendant de la lecture du code seul.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Documenter composants, flux de données, frontières de confiance et contre-mesures, avec schéma versionné.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.8.2, A.6.2.4 ; OWASP ASI04

### EVAL-02 — Évaluations spécifiques à l'agent

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucune évaluation agentique dédiée (benchmark/eval harness) identifiée.
- **Pourquoi c'est un risque** : Les tests unitaires ne mesurent pas la qualité décisionnelle d'un agent ; il faut des scénarios de bout en bout.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Construire un eval harness avec scénarios, oracles déterministes et seuils de réussite publiés.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI08

### EVAL-03 — Scénarios de sécurité et red-team

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucun scénario de sécurité adversarial identifié dans les évaluations.
- **Pourquoi c'est un risque** : Les défenses non éprouvées par des scénarios adversariaux sont des intentions, pas des garanties.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Ajouter des cas d'injection, d'exfiltration et d'abus d'outils à la suite d'évaluation.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01, ASI02

### EVAL-05 — Artefacts de preuve CI versionnés ou vérifiables

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucun artefact de preuve (couverture, ledger CI, résultats) versionné pour les évaluations.
- **Pourquoi c'est un risque** : Un résultat CI non archivé/vérifiable est une affirmation, pas une preuve : l'audit doit pouvoir le rejouer.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Publier un ledger d'exécution (commit, environnement, résultat, manifeste SHA-256) attaché à chaque run.
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI04

### HITL-03 — Décisions d'approbation persistées

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucune persistance des décisions d'approbation (impossible de prouver qui a approuvé quoi).
- **Pourquoi c'est un risque** : Prouver qui a approuvé quelle action à quel moment est indispensable en audit et en gestion d'incident.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Persister chaque demande et réponse d'approbation (identité, horodatage, action, décision) dans le journal d'audit.
- **Référentiels (indicatif)** : AI Act art. 12, art. 14 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI09

### MODEL-02 — Registre central des modèles et fournisseurs

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucun registre central des modèles : les identifiants sont dispersés dans la configuration.
- **Pourquoi c'est un risque** : Sans source unique, les versions réellement utilisées varient entre environnements et échappent à la revue.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Centraliser fournisseurs, modèles, fallbacks et statuts dans un registre versionné et généré.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.6.2.4, A.10.1 ; OWASP ASI04

### PRIVACY-03 — Chiffrement / local-first des données de l'agent

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucun élément de chiffrement au repos ou de local-first identifié.
- **Pourquoi c'est un risque** : Les mémoires et journaux de l'agent contiennent du contexte client : non chiffrés, ils amplifient toute fuite.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Chiffrer les stores sensibles au repos, documenter les flux de données et privilégier le local-first.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.7.4, A.8.2 ; OWASP ASI03

### PRIVACY-04 — Documentation RGPD/AI Act utilisable par le client

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucune documentation RGPD/AI Act : la base de conformité de l'agent n'est pas démontrée.
- **Pourquoi c'est un risque** : Le déployeur (art. 26) doit informer et documenter ; un document de conformité vérifiable est attendu dans une PME régulée.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Produire une cartographie des traitements, les rôles, la base légale, la DPIA et les mesures techniques.
- **Référentiels (indicatif)** : AI Act art. 26, art. 50 ; ISO 42001 4.1, A.5.2, A.8.2 ; OWASP ASI09

### PROMPT-03 — Contenu non fiable balisé avant le prompt (spotlighting)

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucun marquage du contenu non fiable (documents, résultats d'outils) avant le prompt.
- **Pourquoi c'est un risque** : Sans délimitation explicite, un document ou un résultat d'outil peut être interprété comme instruction.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Baliser chaque contenu externe (source, contexte RAG, sortie d'outil) et indiquer qu'il n'est pas une instruction.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.6.2.4, A.7.4 ; OWASP ASI01, ASI06

### PROMPT-04 — Protection contre la fuite du prompt système

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucun filtre de sortie/protection contre la fuite du prompt système détecté.
- **Pourquoi c'est un risque** : La divulgation du prompt système expose les règles internes et facilite le contournement des garde-fous.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Détecter les fuites dans les réponses du modèle et masquer les sections sensibles avant affichage.
- **Référentiels (indicatif)** : AI Act art. 50 ; ISO 42001 8.2, A.8.2 ; OWASP ASI01, ASI09

### PROMPT-05 — Tests de régression sur l'injection de prompt

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucun test de régression dédié à l'injection de prompt identifié.
- **Pourquoi c'est un risque** : Une défense non testée régresse silencieusement à chaque changement de modèle ou de prompt.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Ajouter des cas de test d'injection connus (jailbreak, instruction override) exécutés en CI.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01

### SECRET-04 — Gestion des secrets documentée (variables d'environnement, rotation)

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucune documentation de gestion des secrets (variables d'environnement, rotation, coffre).
- **Pourquoi c'est un risque** : Sans procédure documentée, la rotation et la révocation d'un secret ne sont pas reproductibles en incident.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Documenter le chargement des secrets, la rotation, les contacts d'urgence et l'interdiction de commit.
- **Référentiels (indicatif)** : AI Act art. 15, art. 26 ; ISO 42001 A.2.2, A.7.4 ; OWASP ASI04

### TOOL-04 — Permissions d'outils différenciées par état/agent

- **Statut** : Partiel · **Sévérité** : Moyenne
- **Constat** : Aucune matrice de permissions par état/agent identifiable ; permissions supposées globales.
- **Pourquoi c'est un risque** : Un agent en phase de réflexion ne doit pas avoir les mêmes droits qu'en phase d'exécution supervisée.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Définir une allowlist par phase/état et par rôle d'agent, vérifiée à chaque appel.
- **Référentiels (indicatif)** : AI Act art. 14 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI03

### TOOL-05 — Reçus structurés des appels d'outils

- **Statut** : Non conforme · **Sévérité** : Moyenne
- **Constat** : Aucun reçu d'exécution d'outil (commande, sortie, code retour) détecté.
- **Pourquoi c'est un risque** : Sans reçu (outil, arguments, résultat, code retour), il est impossible de reconstituer une action après incident.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Émettre un événement d'audit par appel d'outil avec identifiant de trace, arguments masqués et digest de résultat.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, 9.1 ; OWASP ASI02, ASI08

### PROVIDER-03 — Canaris de santé des fournisseurs

- **Statut** : Partiel · **Sévérité** : Faible
- **Constat** : Aucun canari de santé fournisseur : une panne ou une dérive de modèle ne serait détectée qu'en production.
- **Pourquoi c'est un risque** : Les modèles évoluent côté fournisseur : un canari détecte la dérive avant qu'un client ne la subisse.
- **Preuves** : aucune ligne localisée ; constat par absence dans le périmètre analysé.
- **Remédiation attendue** : Exécuter périodiquement des requêtes canaris par fournisseur, comparer aux seuils et archiver les résultats.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 9.1, A.10.1 ; OWASP ASI04, ASI08

## 7. Remédiation 30 / 60 / 90 jours

Priorisation proposée : **30 jours** pour les écarts critiques et élevés, **60 jours** pour les moyens, **90 jours** pour les faibles/informatifs. Le détail actionnable figure dans `remediation.md`.

| Horizon | IDs | Nombre |
|---|---|---:|
| 30 jours | `LOG-03`, `DOC-01`, `DOC-02`, `EGRESS-01`, `EGRESS-02`, `EVAL-01`, `EVAL-04`, `HITL-01`, `LOG-01`, `LOG-02`, `LOG-04`, `LOG-05`, `MODEL-03`, `PRIVACY-01`, `PRIVACY-02`, `PROMPT-01`, `PROMPT-02`, `SECRET-03`, `TOOL-01`, `TOOL-03` | 20 |
| 60 jours | `DOC-03`, `EVAL-02`, `EVAL-03`, `EVAL-05`, `HITL-03`, `MODEL-02`, `PRIVACY-03`, `PRIVACY-04`, `PROMPT-03`, `PROMPT-04`, `PROMPT-05`, `SECRET-04`, `TOOL-04`, `TOOL-05` | 14 |
| 90 jours | `PROVIDER-03` | 1 |

## 8. Correspondances réglementaires (indicatif)

Ce tableau sert de **repère de discussion**, pas d'avis juridique. Il n'existe pas de «certification AgentProof» : les références ci-dessous aident à préparer un dossier AI Act / ISO 42001, elles ne le valident pas.

| Référentiel | Références touchées par des findings |
|---|---|
| EU AI Act (art. 12, 14, 15, 26, 50) | art. 12 (10), art. 14 (5), art. 15 (23), art. 26 (7), art. 50 (3) |
| ISO/IEC 42001:2023 (clauses et Annexe A) | 4.1 (1), 8.2 (9), 8.3 (11), 9.1 (9), A.10.1 (3), A.2.2 (1), A.3.2 (1), A.5.2 (2), A.6.2.4 (16), A.7.4 (9), A.8.2 (6), A.9.2 (3) |
| OWASP Top 10 Agentic (ASI01–ASI10) | ASI01 (6), ASI02 (7), ASI03 (4), ASI04 (9), ASI05 (4), ASI06 (5), ASI08 (9), ASI09 (5), ASI10 (2) |

Détail machine-readable : `mapping.json`.

## 9. Limites de l'audit

- **Analyse statique uniquement** : AgentProof lit le dépôt, n'exécute pas le système, n'appelle aucun modèle et n'accède pas au réseau. Les comportements dynamiques (exfiltration réelle, injection à l'exécution) ne sont pas testés.
- **Pas d'analyse de l'historique git** : un secret supprimé du HEAD peut subsister dans l'historique ; la revue de l'historique et des secrets de CI reste à faire.
- **Heuristiques déterministes** : un contrôle `pass` signifie « preuve de safeguard trouvée », pas « risque nul » ; les faux négatifs restent possibles. Un contrôle `unknown` signifie que le sujet est absent du dépôt analysé.
- **Périmètre** : 8 fichiers texte analysés sur 8 fichiers détectés (0 binaires, 0 fichiers > 2 Mio ignorés) ; répertoires exclus : .git, node_modules, .venv, dist, build, caches.
- **Filtre de sévérité** : `info` ; les contrôles et le score restent calculés sur l'ensemble.
- **Pas de revue humaine des preuves** : ce pack est un support d'audit, il ne remplace ni un pentest, ni un audit ISO 42001, ni une revue juridique AI Act.

## 10. Avertissement

**Preuve technique, pas une certification.** Les constats de ce pack sont des observations automatisées, limitées au périmètre déclaré et à la date de génération. Ils ne constituent ni un avis juridique, ni une attestation de conformité, ni une garantie de sécurité. Toute décision de déploiement ou de mise sur le marché doit être prise après revue humaine et, le cas échéant, audit par un organisme compétent.

Pour vérifier l'intégrité de ce pack : `sha256sum -c manifest.sha256` (voir `README.txt`).

