SwarmProof — Evidence Pack
==========================

Ce pack est la preuve d'un run de remédiation vérifiée :
  * le swarm (moteur NEXUS) a PROPOSÉ des correctifs ;
  * un oracle externe (tests) a DÉCIDÉ ;
  * ce pack documente ce qui s'est passé, avec quels modèles, quels appels,
    quels hashes, quel diff et quel verdict.

Contenu
-------
  report.md        Résumé lisible : verdict, appels, oracle, limites.
  run.json         Données structurées du run (statuts, durées, tokens, coûts).
  trace.jsonl      Une ligne par événement/appel (prompt sha256, durée, statut).
  oracle.jsonl     Une ligne par tentative de correctif jugée par l'oracle.
  diff.patch       Diff unifié entre le dépôt source et l'arbre évalué.
  mapping.json     Fichiers cibles, chemins de tests restaurés, mapping agents.
  source/          Copie vierge du dépôt au moment du run (tests non modifiés).
  tree/            État évalué (correctif appliqué + tests restaurés).
  manifest.sha256  SHA-256 de chaque fichier du pack (vérifiable hors ligne).
  README.txt       Ce fichier.

Vérification
------------
  cd <ce_pack> && shasum -a 256 -c manifest.sha256
  python -m swarmproof verify <ce_pack>

Le second rejoue l'oracle sur tree/ (tests restaurés depuis source/) et compare
le verdict rejoué au verdict enregistré. Aucun appel modèle n'est effectué.

Sécurité / authenticité
-----------------------
  * Ce pack est une COHÉRENCE INTERNE AUTO-ATTESTÉE : le manifeste prouve que les
    fichiers n'ont pas changé depuis l'écriture du pack, PAS qu'il vient de nous.
    Aucune signature cryptographique n'est incluse. Pour l'origine, exigez un canal
    de livraison authentifié (ou ajoutez une signature hors pack).
  * `swarmproof verify` n'exécute AUCUNE commande par défaut : le rejeu de l'oracle
    exige `--allow-oracle-cmd`, et les commandes avec métacaractères shell sont refusées.
  * Les fichiers de secrets connus (.env, *.pem, *.key, id_rsa*, etc.) sont EXCLUS et
    les motifs ressemblant à des clés sont redactés ; les chemins locaux absolus sont
    remplacés par des jetons neutres dans les métadonnées.

Rappels
-------
  * Le verdict vient de l'oracle, jamais du statut auto-déclaré du moteur.
  * `engine_error`/`engine_ok=false` dans run.json signale qu'un agent a échoué
    même si le moteur prétendait avoir terminé.
  * Ce pack ne prouve pas la qualité générale du code : il prouve que, sur ce
    dépôt, à cette date, avec cet oracle, le correctif évalué passe les tests.
  * PREUVE TECHNIQUE, PAS CERTIFICATION. La supériorité du hybrid swarm sur un
    agent seul n'est pas prouvée par ce pack (n=1, un run).
