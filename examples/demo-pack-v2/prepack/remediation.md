# Plan de remédiation — pristine

Généré le 2026-11-05 18:12:45 UTC par AgentProof 1.0.0.
Horizons : 30 jours = critique/élevé, 60 jours = moyen, 90 jours = faible/informatif.
Chaque action référence les preuves (`fichier:ligne`) du rapport ; le rapport reste la source de vérité.

## Horizon 30 jours (20 action(s))

### 1. `LOG-03` — Preuve d'inviolabilité du journal (chaîne de hachage/signature)

- **Sévérité** : Critique · **Statut** : Non conforme · **Catégorie** : Journalisation & audit trail
- **Observation** : Aucune preuve d'inviolabilité (chaîne de hachage, signature) pour le journal d'audit.
- **Action attendue** : Enchaîner les événements par hash (prev_hash), sceller périodiquement la chaîne dans un manifeste SHA-256 et vérifier en CI.
- **Référentiels (indicatif)** : AI Act art. 12 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI08, ASI10

### 2. `DOC-01` — Limites et cas non couverts documentés

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Documentation & limites
- **Observation** : Aucune documentation des limites ou des cas non couverts : le périmètre réel est indiscernable.
- **Action attendue** : Publier une section Limitations/cas non couverts, datée, liée depuis le README et mise à jour à chaque release.
- **Référentiels (indicatif)** : AI Act art. 50 ; ISO 42001 A.8.2, A.9.2 ; OWASP ASI09

### 3. `DOC-02` — Politique de divulgation de vulnérabilités

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Documentation & limites
- **Observation** : Aucune politique de divulgation de vulnérabilité (SECURITY.md / contact).
- **Action attendue** : Créer SECURITY.md à la racine avec contact, délais de réponse et périmètre de divulgation responsable.
- **Référentiels (indicatif)** : AI Act art. 15, art. 26 ; ISO 42001 A.3.2, A.9.2 ; OWASP ASI04

### 4. `EGRESS-01` — Allowlist d'égress réseau des outils de l'agent

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Égress réseau & SSRF
- **Observation** : Aucun contrôle d'égress réseau (allowlist ou blocklist) détecté.
- **Action attendue** : Définir une allowlist de domaines par outil, l'appliquer avant chaque requête et journaliser les refus.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.10.1 ; OWASP ASI02, ASI05

### 5. `EGRESS-02` — Protection SSRF du fetcher web

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Égress réseau & SSRF
- **Observation** : Aucune protection SSRF détectée autour des outils réseau/web_fetch.
- **Action attendue** : Bloquer localhost, IP privées, link-local, métadonnées cloud et variantes d'encodage ; résoudre puis vérifier l'IP.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI05

### 6. `EVAL-01` — Suite de tests automatisés

- **Sévérité** : Élevée · **Statut** : Partiel · **Catégorie** : Évaluations & tests
- **Observation** : Suite de tests réduite (1 fichier(s)).
- **Action attendue** : Maintenir une suite de tests exécutable hors ligne et la faire tourner sur chaque changement.
- **Preuves à corriger** :
  - `tests/test_cache.py`
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI08

### 7. `EVAL-04` — Tests exécutés en CI

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Évaluations & tests
- **Observation** : Aucune CI exécutant les tests : les garanties ne sont pas vérifiées à chaque changement.
- **Action attendue** : Configurer une CI qui exécute tests, lint et scans de sécurité sur chaque PR, avec artifacts archivés.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, 9.1 ; OWASP ASI04

### 8. `HITL-01` — Mécanisme d'approbation humaine présent

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Supervision humaine
- **Observation** : Aucun mécanisme d'approbation humaine (HITL) détecté.
- **Action attendue** : Exposer un canal d'approbation (CLI, API, notification) permettant d'approuver, refuser ou interrompre une action.
- **Référentiels (indicatif)** : AI Act art. 14 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI09, ASI10

### 9. `LOG-01` — Journal d'audit structuré et append-only

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Journalisation & audit trail
- **Observation** : Aucun journal d'audit structuré (AuditLogger / append-only) détecté.
- **Action attendue** : Écrire un événement structuré (acteur, action, ressource, statut, horodatage) dans un journal append-only.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, 9.1 ; OWASP ASI08

### 10. `LOG-02` — Identifiant de corrélation propagé entre actions

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Journalisation & audit trail
- **Observation** : Aucun identifiant de corrélation (trace_id/request_id) propagé dans les logs.
- **Action attendue** : Générer un trace_id par requête/run et le propager dans tous les logs, spans et reçus d'outils.
- **Référentiels (indicatif)** : AI Act art. 12 ; ISO 42001 8.3, 9.1 ; OWASP ASI08

### 11. `LOG-04` — Politique de rétention et de rotation des journaux

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Journalisation & audit trail
- **Observation** : Aucune politique de rétention/rotation des journaux d'audit détectée.
- **Action attendue** : Définir une durée de conservation par type de journal, activer la rotation et documenter la procédure.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, A.7.4 ; OWASP ASI08

### 12. `LOG-05` — Rédaction des secrets et données personnelles dans les logs

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Journalisation & audit trail
- **Observation** : Aucune rédaction/masquage des secrets et données personnelles dans les journaux.
- **Action attendue** : Masquer les secrets/PII à l'émission du log, tester la sortie des journaux sur un corpus de canaris.
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 A.7.4, A.8.2 ; OWASP ASI03, ASI06

### 13. `MODEL-03` — Modèle réellement utilisé tracé par appel

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Pinning modèles & versions
- **Observation** : Le modèle réellement utilisé par les appels n'est pas journalisé : décision non attribuable.
- **Action attendue** : Émettre le modèle et sa version dans chaque trace/log d'appel LLM (OpenTelemetry GenAI semconv).
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 8.3, 9.1 ; OWASP ASI04, ASI08

### 14. `PRIVACY-01` — Détection et rédaction des données personnelles

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Données personnelles
- **Observation** : Aucune détection ni rédaction PII identifiée : prompts et logs peuvent contenir des données clients.
- **Action attendue** : Détecter (regex/classifieur) et masquer les PII avant persistance, prompt distant et journalisation.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.7.4, A.5.2 ; OWASP ASI03, ASI06

### 15. `PRIVACY-02` — Rétention et effacement des données

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Données personnelles
- **Observation** : Aucune procédure de rétention/effacement des données personnelles détectée.
- **Action attendue** : Définir une politique de rétention par donnée, implémenter suppression/export et documenter les durées.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 A.7.4, A.9.2 ; OWASP ASI06

### 16. `PROMPT-01` — Prompts système isolés et versionnés

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Prompts système & injection
- **Observation** : Aucun fichier de prompt système versionné identifié.
- **Action attendue** : Extraire les prompts dans un répertoire dédié versionné, avec un identifiant de version par prompt.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01

### 17. `PROMPT-02` — Défense contre l'injection de prompt dans le code

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Prompts système & injection
- **Observation** : Aucune défense anti-injection (InputGuard, patterns, sanitisation) détectée dans le code.
- **Action attendue** : Implémenter un garde d'entrée (patterns, normalisation Unicode, scoring) et l'appliquer à tout contenu non fiable.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI01, ASI06

### 18. `SECRET-03` — Fichiers d'environnement absents ou exclus du versionnement

- **Sévérité** : Élevée · **Statut** : Partiel · **Catégorie** : Secrets & identifiants
- **Observation** : Aucun fichier d'environnement présent, mais .gitignore ne couvre pas .env/credentials.
- **Action attendue** : Ajouter .env, *.pem, *.key et credentials.json au .gitignore, fournir un .env.example sans valeurs.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.2, A.7.4 ; OWASP ASI04

### 19. `TOOL-01` — Politique centrale de permissions d'outils

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Permissions d'outils
- **Observation** : Aucune politique centrale de permissions/validation des commandes d'outils détectée.
- **Action attendue** : Centraliser validation de commandes, chemins et accès réseau dans une ExecutionPolicy testée.
- **Référentiels (indicatif)** : AI Act art. 14, art. 15 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI05

### 20. `TOOL-03` — Containment des écritures fichiers

- **Sévérité** : Élevée · **Statut** : Non conforme · **Catégorie** : Permissions d'outils
- **Observation** : Aucun garde de chemins (containment des écritures) détecté dans le code.
- **Action attendue** : Résoudre les chemins, vérifier le confinement (workspace/parent), refuser les chemins absolus et protéger les fichiers sensibles.
- **Référentiels (indicatif)** : AI Act art. 14, art. 15 ; ISO 42001 8.2, A.7.4 ; OWASP ASI02, ASI05

## Horizon 60 jours (14 action(s))

### 1. `DOC-03` — Architecture et modèle de sécurité documentés

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Documentation & limites
- **Observation** : Aucun document d'architecture/modèle de menace structuré identifié.
- **Action attendue** : Documenter composants, flux de données, frontières de confiance et contre-mesures, avec schéma versionné.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.8.2, A.6.2.4 ; OWASP ASI04

### 2. `EVAL-02` — Évaluations spécifiques à l'agent

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Évaluations & tests
- **Observation** : Aucune évaluation agentique dédiée (benchmark/eval harness) identifiée.
- **Action attendue** : Construire un eval harness avec scénarios, oracles déterministes et seuils de réussite publiés.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI08

### 3. `EVAL-03` — Scénarios de sécurité et red-team

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Évaluations & tests
- **Observation** : Aucun scénario de sécurité adversarial identifié dans les évaluations.
- **Action attendue** : Ajouter des cas d'injection, d'exfiltration et d'abus d'outils à la suite d'évaluation.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01, ASI02

### 4. `EVAL-05` — Artefacts de preuve CI versionnés ou vérifiables

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Évaluations & tests
- **Observation** : Aucun artefact de preuve (couverture, ledger CI, résultats) versionné pour les évaluations.
- **Action attendue** : Publier un ledger d'exécution (commit, environnement, résultat, manifeste SHA-256) attaché à chaque run.
- **Référentiels (indicatif)** : AI Act art. 12, art. 15 ; ISO 42001 9.1, A.6.2.4 ; OWASP ASI04

### 5. `HITL-03` — Décisions d'approbation persistées

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Supervision humaine
- **Observation** : Aucune persistance des décisions d'approbation (impossible de prouver qui a approuvé quoi).
- **Action attendue** : Persister chaque demande et réponse d'approbation (identité, horodatage, action, décision) dans le journal d'audit.
- **Référentiels (indicatif)** : AI Act art. 12, art. 14 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI09

### 6. `MODEL-02` — Registre central des modèles et fournisseurs

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Pinning modèles & versions
- **Observation** : Aucun registre central des modèles : les identifiants sont dispersés dans la configuration.
- **Action attendue** : Centraliser fournisseurs, modèles, fallbacks et statuts dans un registre versionné et généré.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.6.2.4, A.10.1 ; OWASP ASI04

### 7. `PRIVACY-03` — Chiffrement / local-first des données de l'agent

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Données personnelles
- **Observation** : Aucun élément de chiffrement au repos ou de local-first identifié.
- **Action attendue** : Chiffrer les stores sensibles au repos, documenter les flux de données et privilégier le local-first.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.7.4, A.8.2 ; OWASP ASI03

### 8. `PRIVACY-04` — Documentation RGPD/AI Act utilisable par le client

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Données personnelles
- **Observation** : Aucune documentation RGPD/AI Act : la base de conformité de l'agent n'est pas démontrée.
- **Action attendue** : Produire une cartographie des traitements, les rôles, la base légale, la DPIA et les mesures techniques.
- **Référentiels (indicatif)** : AI Act art. 26, art. 50 ; ISO 42001 4.1, A.5.2, A.8.2 ; OWASP ASI09

### 9. `PROMPT-03` — Contenu non fiable balisé avant le prompt (spotlighting)

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Prompts système & injection
- **Observation** : Aucun marquage du contenu non fiable (documents, résultats d'outils) avant le prompt.
- **Action attendue** : Baliser chaque contenu externe (source, contexte RAG, sortie d'outil) et indiquer qu'il n'est pas une instruction.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 A.6.2.4, A.7.4 ; OWASP ASI01, ASI06

### 10. `PROMPT-04` — Protection contre la fuite du prompt système

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Prompts système & injection
- **Observation** : Aucun filtre de sortie/protection contre la fuite du prompt système détecté.
- **Action attendue** : Détecter les fuites dans les réponses du modèle et masquer les sections sensibles avant affichage.
- **Référentiels (indicatif)** : AI Act art. 50 ; ISO 42001 8.2, A.8.2 ; OWASP ASI01, ASI09

### 11. `PROMPT-05` — Tests de régression sur l'injection de prompt

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Prompts système & injection
- **Observation** : Aucun test de régression dédié à l'injection de prompt identifié.
- **Action attendue** : Ajouter des cas de test d'injection connus (jailbreak, instruction override) exécutés en CI.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 8.3, A.6.2.4 ; OWASP ASI01

### 12. `SECRET-04` — Gestion des secrets documentée (variables d'environnement, rotation)

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Secrets & identifiants
- **Observation** : Aucune documentation de gestion des secrets (variables d'environnement, rotation, coffre).
- **Action attendue** : Documenter le chargement des secrets, la rotation, les contacts d'urgence et l'interdiction de commit.
- **Référentiels (indicatif)** : AI Act art. 15, art. 26 ; ISO 42001 A.2.2, A.7.4 ; OWASP ASI04

### 13. `TOOL-04` — Permissions d'outils différenciées par état/agent

- **Sévérité** : Moyenne · **Statut** : Partiel · **Catégorie** : Permissions d'outils
- **Observation** : Aucune matrice de permissions par état/agent identifiable ; permissions supposées globales.
- **Action attendue** : Définir une allowlist par phase/état et par rôle d'agent, vérifiée à chaque appel.
- **Référentiels (indicatif)** : AI Act art. 14 ; ISO 42001 8.2, A.6.2.4 ; OWASP ASI02, ASI03

### 14. `TOOL-05` — Reçus structurés des appels d'outils

- **Sévérité** : Moyenne · **Statut** : Non conforme · **Catégorie** : Permissions d'outils
- **Observation** : Aucun reçu d'exécution d'outil (commande, sortie, code retour) détecté.
- **Action attendue** : Émettre un événement d'audit par appel d'outil avec identifiant de trace, arguments masqués et digest de résultat.
- **Référentiels (indicatif)** : AI Act art. 12, art. 26 ; ISO 42001 8.3, 9.1 ; OWASP ASI02, ASI08

## Horizon 90 jours (1 action(s))

### 1. `PROVIDER-03` — Canaris de santé des fournisseurs

- **Sévérité** : Faible · **Statut** : Partiel · **Catégorie** : Fournisseurs & failover
- **Observation** : Aucun canari de santé fournisseur : une panne ou une dérive de modèle ne serait détectée qu'en production.
- **Action attendue** : Exécuter périodiquement des requêtes canaris par fournisseur, comparer aux seuils et archiver les résultats.
- **Référentiels (indicatif)** : AI Act art. 15 ; ISO 42001 9.1, A.10.1 ; OWASP ASI04, ASI08

## Vérification de sortie

Après correction, relancer l'audit et comparer les packs :

```bash
python -m agentproof audit <repo> --out <dir> --name "<même nom>"
sha256sum -c <dir>/evidence-pack-<timestamp>/manifest.sha256
```

Un finding ne doit être considéré comme clos que lorsque le contrôle correspondant repasse en `pass` dans un pack versionné (ou qu'un `unknown` documenté remplace le finding avec justification écrite).

