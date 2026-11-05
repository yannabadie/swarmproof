====================================================================
AGENTPROOF — EVIDENCE PACK
====================================================================

Audit            : pristine
Date (UTC)       : 2026-11-05T18:12:45Z
Outil            : AgentProof 1.0.0 — analyse statique déterministe, hors ligne, sans LLM
Cible            : /private/var/folders/2c/92cnz9_x3fjcph_b4570j8140000gn/T/swarmproof-run-b_rz_zuo/pristine
Commit           : non déterminé
Commande         : agentproof audit /var/folders/2c/92cnz9_x3fjcph_b4570j8140000gn/T/swarmproof-run-b_rz_zuo/pristine
Score pondéré    : 25.0/100 (E — Insuffisant)
Contrôles        : 68 (évalués : 39, non évalués : 29)
Findings affichés: 35 (filtre : info) — critique 1, élevé 19, moyen 14, faible 1, info 0

CONTENU DU PACK
---------------
report.md        Rapport complet (résumé exécutif, score, findings, preuves, limites, avertissement)
findings.json    Findings filtrés, structurés, avec preuves et mappings
checks.json      Résultat de tous les contrôles (y compris conformes et non évalués)
mapping.json     Correspondances AI Act / ISO 42001 / OWASP Agentic (indicatives)
remediation.md   Plan d'action 30 / 60 / 90 jours
manifest.sha256  SHA-256 de chaque fichier du pack (le manifeste ne s'auto-référence pas)
README.txt       Ce fichier

VÉRIFIER L'INTÉGRITÉ
--------------------
Dans ce répertoire :

    sha256sum -c manifest.sha256

Toutes les lignes doivent afficher « OK ». Le manifeste couvre tous les fichiers du pack sauf
lui-même. Alternative intégrée :

    python -m agentproof verify .

CE QUE CE PACK PROUVE
---------------------
- à une date et sur un commit donnés, un ensemble de safeguards techniques était présent ou absent ;
- chaque constat est rattaché à un fichier et une ligne du dépôt (preuve vérifiable manuellement) ;
- le pack n'a pas été modifié après génération (empreintes SHA-256).

CE QUE CE PACK NE PROUVE PAS
----------------------------
- l'absence de vulnérabilité ni l'absence de risque résiduel ;
- la conformité AI Act, RGPD ou ISO/IEC 42001 (aucune certification) ;
- le comportement réel du système en production (aucune exécution, aucun test dynamique ici) ;
- l'absence de secrets dans l'historique git (l'analyse porte sur l'arborescence courante).

REPRODUCTIBILITÉ
----------------
Le nom du répertoire et les champs generated_at dérivent de l'horodatage du run (UTC, seconde).
Pour rejouer à l'identique : même dépôt, même version d'AgentProof, même horodatage.
L'horodatage peut être figé avec la variable standard SOURCE_DATE_EPOCH ou l'option --timestamp :

    SOURCE_DATE_EPOCH=1793902365 python -m agentproof audit <repo> --out <dir>

Les JSON sont triés (clés), indentés en 2 espaces, en UTF-8 et fins de ligne LF : deux runs
avec le même timestamp produisent des fichiers identiques, manifeste compris.

AVERTISSEMENT
-------------
Preuve technique, pas une certification. Ce pack est un support d'audit produit par une analyse
statique heuristique ; il doit être complété par une revue humaine et, si nécessaire, par un audit
indépendant. Aucune décision de conformité ne doit être prise sur la seule base de ce document.
