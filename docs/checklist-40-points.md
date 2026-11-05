# 40 points de contrôle — agents IA & MCP

**Checklist d'auditabilité pour équipes qui mettent des agents en production**
*Version publique 1.0 — 4 novembre 2026. Licence : CC BY 4.0 (réutilisation libre avec attribution).*

> **Avertissement.** Cette checklist est une **grille de lecture**, pas une certification, pas un audit, pas un avis juridique. Elle ne garantit aucune conformité. Les correspondances réglementaires sont indicatives et doivent être validées par votre juriste. Pour un audit sur pièces, avec constats sourcés et Evidence Pack vérifiable, voir la fin du document.

---

## Comment l'utiliser (10 minutes par catégorie)

1. **Faire l'inventaire** : lister les agents, leurs outils, les serveurs MCP, les modèles et les données qu'ils touchent.
2. **Répondre par OUI / NON / JE NE SAIS PAS** à chaque point — « je ne sais pas » compte comme un risque, pas comme un passe.
3. **Prioriser** : traiter d'abord les critiques, puis les élevés. Un point non documenté est un point non prouvable.
4. **Dater et archiver** vos réponses : une checklist remplie est déjà un premier élément de preuve interne.

**Sévérités** : 🔴 Critique (à traiter avant mise en production) · 🟠 Élevée (à traiter sous 30 jours) · 🟡 Moyenne (à planifier).

**Référentiels utilisés** :
- **AI Act** : règlement (UE) 2024/1689. Articles cités : 9 (gestion des risques), 10 (données), 12 (journalisation), 13 (instructions), 14 (supervision humaine), 15 (exactitude/robustesse/cybersécurité), 26 (obligations du déployeur), 50 (transparence). *Calendrier indicatif à date (nov. 2026) : art. 50 applicable depuis août 2026 ; obligations haut risque reportées au 2 déc. 2027 / 2 août 2028.*
- **ISO 42001** : ISO/IEC 42001:2023, annexe A (A.2 politique, A.3 organisation, A.4 ressources, A.5 impacts, A.6 cycle de vie, A.7 données, A.8 information, A.9 usage, A.10 tiers).
- **OWASP Agentic** : OWASP Top 10 for Agentic Applications (déc. 2025), risques ASI01 à ASI10 : ASI01 Agent Goal Hijack · ASI02 Tool Misuse · ASI03 Identity & Privilege Abuse · ASI04 Agentic Supply Chain · ASI05 Unexpected Code Execution · ASI06 Memory & Context Poisoning · ASI07 Insecure Inter-Agent Comms · ASI08 Cascading Failures · ASI09 Human-Agent Trust Exploitation · ASI10 Rogue Agents.

---

## 1. Secrets & clés (SECRET)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| SECRET-01 | Aucun secret en dur dans le code, les prompts, les fichiers de configuration ou les notebooks | 🔴 | Une clé exposée dans un dépôt ou un prompt est une fuite immédiate, permanente, et souvent invisible dans les logs | AI Act 15 · ISO A.6.2 · ASI03 |
| SECRET-02 | Secrets chargés par variables d'environnement ou coffre ; `.env` exclu de git et des images | 🟠 | Un `.env` committé annule tout le reste : la clé est dans l'historique pour toujours | AI Act 15 · ISO A.6.2 · ASI04 |
| SECRET-03 | Clés à privilèges minimaux, par agent et par outil, avec rotation et révocation possibles | 🔴 | Une clé unique qui donne accès à tout transforme un agent compromis en accès total | AI Act 15 · ISO A.6.2 · ASI03 |
| SECRET-04 | Secrets exclus des logs, traces, messages d'erreur et réponses d'API | 🟠 | Les traces sont souvent partagées, exportées ou envoyées à un fournisseur : un secret dans un log est une fuite différée | AI Act 12/15 · ISO A.6.8 · ASI03 |
| SECRET-05 | Accès humain aux secrets tracé et restreint (qui peut voir quoi, et pourquoi) | 🟡 | Sans traçabilité des accès, une fuite interne est indétectable et non imputable | AI Act 15 · ISO A.10 · ASI03 |

## 2. Permissions d'outils (TOOL)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| TOOL-01 | Allowlist explicite des outils autorisés par agent, aucun outil implicite ou découvert dynamiquement | 🔴 | Un agent qui peut appeler n'importe quel outil est un agent sans périmètre : le « moindre privilège » est la première barrière | AI Act 14/15 · ISO A.6.2 · ASI02 |
| TOOL-02 | Paramètres d'outils validés (schéma, types, plages, échappement) avant exécution | 🟠 | Une injection dans un paramètre peut transformer un outil de lecture en outil d'écriture | AI Act 15 · ISO A.6.2 · ASI02/ASI05 |
| TOOL-03 | Actions irréversibles (envoi, suppression, paiement, écriture en base) protégées par approbation ou garde-fou | 🔴 | Une action irréversible mal exécutée ne se « rollback » pas : elle se retrouve dans un audit client | AI Act 14 · ISO A.6.2 · ASI02/ASI09 |
| TOOL-04 | Budget d'appels d'outils et de coût par tâche, avec coupure automatique | 🟠 | Sans budget, une boucle d'agent peut consommer, spammer ou saturer un service tiers | AI Act 15 · ISO A.6.6 · ASI08 |
| TOOL-05 | Sorties d'outils traitées comme des données non fiables (jamais exécutées comme instructions) | 🔴 | Un résultat d'outil peut contenir une injection : c'est le vecteur privilégié des agents connectés | AI Act 15 · ISO A.6.2 · ASI01/ASI02 |

## 3. MCP — Model Context Protocol (MCP)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| MCP-01 | Inventaire des serveurs MCP : origine, mainteneur, version, propriétaire, date d'ajout | 🟠 | On ne peut pas sécuriser ce qu'on ne sait pas lister ; un serveur MCP oublié est une porte ouverte | AI Act 15 · ISO A.10 · ASI04 |
| MCP-02 | Serveurs MCP tiers évalués et approuvés avant activation (code, permissions, réputation) | 🔴 | Chaque serveur tiers exécute du code avec les droits que vous lui donnez | AI Act 15 · ISO A.10 · ASI04 |
| MCP-03 | Authentification et permissions minimales sur chaque serveur MCP | 🔴 | Un serveur MCP sans authentification est une API interne exposée | AI Act 15 · ISO A.6.2 · ASI03 |
| MCP-04 | Configuration MCP versionnée et revue comme du code | 🟠 | Une config modifiée sans revue est un changement de périmètre non audité | AI Act 15 · ISO A.6.2 · ASI04 |
| MCP-05 | Égress réseau des serveurs MCP limité (domaines, IP, méthodes) | 🟠 | Sans allowlist d'égression, un serveur compromis peut exfiltrer des données | AI Act 15 · ISO A.6.2 · ASI05/ASI07 |

## 4. Journalisation & audit trail (LOG)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| LOG-01 | Chaque action d'agent journalisée : qui, quoi, quand, avec quel outil, quel résultat | 🔴 | C'est la base de toute preuve : sans log d'action, aucun incident n'est reconstituable | AI Act 12 · ISO A.6.8 · ASI06/ASI10 |
| LOG-02 | Identifiants de corrélation (`trace_id` / `run_id`) propagés de bout en bout | 🟠 | Sans corrélation, les logs sont un tas de lignes non rattachables à une tâche | AI Act 12 · ISO A.6.8 · ASI06 |
| LOG-03 | Logs append-only ou chaînés par hash, avec détection d'altération | 🟠 | Un log modifiable ne vaut rien face à un auditeur ou à un assureur | AI Act 12 · ISO A.6.8 · ASI06 |
| LOG-04 | Politique de rétention, d'accès et de suppression des logs documentée | 🟡 | La rétention est une exigence de preuve et une exigence RGPD : les deux doivent être écrites | AI Act 12/26 · ISO A.6.8/A.8 · ASI06 |
| LOG-05 | Logs exploitables par un tiers : format stable, export, pseudonymisation | 🟠 | Un log illisible par un tiers est une narration, pas une preuve | AI Act 12 · ISO A.8 · ASI06 |

## 5. Human-in-the-loop & approbations (HITL)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| HITL-01 | Points d'approbation humaine définis pour les actions sensibles | 🔴 | L'humain doit être un point de passage, pas un observateur | AI Act 14 · ISO A.6.2 · ASI09 |
| HITL-02 | Approbation non contournable par l'agent (séparation des rôles) | 🔴 | Si l'agent peut approuver sa propre action, le contrôle n'existe pas | AI Act 14 · ISO A.6.2 · ASI09 |
| HITL-03 | Escalade, délais et conduite à tenir sans humain disponibles | 🟠 | Un agent bloqué en attente d'approbation doit échouer proprement, pas improviser | AI Act 14 · ISO A.6.6 · ASI08 |
| HITL-04 | Décisions humaines tracées (qui a approuvé/refusé, quand, sur quelle base) | 🟠 | Une approbation non tracée ne prouve rien le jour de l'incident | AI Act 12/14 · ISO A.6.8 · ASI09 |
| HITL-05 | Arrêt d'urgence / kill switch testé et documenté | 🔴 | Le seul contrôle qui compte quand tout le reste échoue | AI Act 14/15 · ISO A.6.6 · ASI10 |

## 6. Sandbox & containment (SANDBOX)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| SANDBOX-01 | Exécution de code isolée (conteneur/VM, limites CPU/mémoire, pas d'accès hôte) | 🔴 | L'exécution de code est le risque le plus élevé d'un agent : elle doit être contenue | AI Act 15 · ISO A.6.2 · ASI05 |
| SANDBOX-02 | Égress réseau restreint par défaut (allowlist), pour les agents et leurs outils | 🔴 | Sans contrôle d'égression, une injection devient une exfiltration | AI Act 15 · ISO A.6.2 · ASI05 |
| SANDBOX-03 | Accès fichiers limité au périmètre nécessaire, en lecture seule par défaut | 🟠 | Un agent qui lit tout le disque peut lire ce qu'il ne devrait jamais voir | AI Act 15 · ISO A.6.2 · ASI05 |
| SANDBOX-04 | Sauvegarde et rollback avant action destructive | 🟠 | La capacité à revenir en arrière fait partie du contrôle des actions | AI Act 15 · ISO A.6.6 · ASI08 |
| SANDBOX-05 | Isolation entre agents, tâches et secrets (pas de contamination croisée) | 🟠 | Un contexte partagé entre agents est un canal de propagation d'attaque | AI Act 15 · ISO A.6.2 · ASI07/ASI10 |

## 7. Modèles, prompts & fournisseurs (MODEL)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| MODEL-01 | Versions de modèles épinglées et documentées | 🟠 | Un modèle qui change sans version épinglée rend le comportement et la preuve non reproductibles | AI Act 15 · ISO A.6.2 · ASI04 |
| MODEL-02 | Fournisseur(s) et fallback documentés (pas de dépendance unique non maîtrisée) | 🟡 | L'indisponibilité d'un fournisseur est un incident réel : il doit être anticipé | AI Act 15 · ISO A.10 · ASI08 |
| MODEL-03 | Prompts système versionnés, revus et testés comme du code | 🟠 | Le prompt système est le véritable programme de l'agent : il doit être relu | AI Act 15 · ISO A.6.2 · ASI01 |
| MODEL-04 | Comportement dégradé propre si le fournisseur est indisponible (pas de perte silencieuse) | 🟠 | Un agent qui échoue silencieusement est plus dangereux qu'un agent qui s'arrête | AI Act 15 · ISO A.6.6 · ASI08 |
| MODEL-05 | Limites documentées de l'agent : ce qu'il ne fait pas, quand il doit refuser | 🟠 | Un agent sans limites écrites promet implicitement plus qu'il ne peut tenir | AI Act 13/50 · ISO A.8 · ASI01/ASI09 |

## 8. Données & évaluations (DATA)

| ID | Point de contrôle | Sévérité | Pourquoi ça compte | Mapping |
|---|---|---|---|---|
| DATA-01 | Classification des données traitées (personnelles, sensibles, secrets, publiques) | 🔴 | On ne peut pas protéger ni déclarer ce qu'on n'a pas classé | AI Act 10 · ISO A.7 · ASI06 |
| DATA-02 | Minimisation : seules les données nécessaires sont transmises au modèle | 🟠 | Chaque donnée envoyée au modèle est une donnée qui peut ressortir ou fuiter | AI Act 10 · ISO A.7 · ASI06 |
| DATA-03 | Rétention et suppression des données et des traces définies et appliquées | 🟠 | La conservation éternelle est à la fois un risque RGPD et une charge de preuve | AI Act 10/26 · ISO A.7/A.8 · ASI06 |
| DATA-04 | Transferts hors UE identifiés et encadrés (DPA, garanties appropriées) | 🟠 | Un agent qui appelle un modèle hors UE est un transfert de données, même sans le dire | AI Act 10/26 · ISO A.7/A.10 · ASI04 |
| DATA-05 | Jeux d'évaluation et tests de non-régression des agents | 🟠 | Sans évals, tout changement de prompt, d'outil ou de modèle est une régression potentielle non détectée | AI Act 15 · ISO A.6.2 · ASI01/ASI08 |

---

## Score et lecture

- Un point critique (🔴) non couvert est un **blocker** : il devrait être corrigé avant toute mise en production.
- Un point élevé (🟠) non couvert est un **risque à planifier** (30 jours).
- Un point moyen (🟡) est une **dette de documentation** : il casse la reproductibilité, pas forcément la sécurité immédiate.
- « Je ne sais pas » vaut « non couvert » : une preuve doit être disponible, pas supposée.

**Pondération indicatrice** : 🔴 = 4 · 🟠 = 3 · 🟡 = 2. Le score peut être calculé par catégorie pour prioriser, mais un score élevé ne vaut pas certification : seuls les constats et leurs preuves comptent.

---

## Ce que cette checklist ne remplace pas

- **Un audit sur pièces** : la checklist dit *quoi* vérifier ; un audit montre *ce qui est vrai* dans votre système, avec preuves `fichier:ligne`, écarts et plan de remédiation.
- **Un avis juridique** : la qualification AI Act (notamment haut risque ou non) relève d'un juriste, pas d'une grille technique.
- **Un pentest** : les tests d'intrusion actifs sont un autre métier.
- **Une certification** : aucune checklist ne certifie quoi que ce soit.

**Le lien avec AgentProof** : l'outil AgentProof CLI exécute 40+ contrôles déterministes (sans réseau, sans clé API) et produit un Evidence Pack vérifiable : constats sourcés, mapping AI Act / ISO 42001 / OWASP, plan de remédiation, manifeste SHA-256. C'est la version « audit sur pièces » de cette checklist. Si vous voulez voir un pack réel : [EMAIL] — 20 minutes suffisent.

---

## Publier cette checklist (GitHub + LinkedIn)

**Structure conseillée du dépôt :**

```
agentproof-checklist/
├── README.md            ← ce document (ou lien vers)
├── CHECKLIST.md         ← les 40 points seuls, sans le marketing
├── LICENSE              ← CC BY 4.0
└── examples/            ← un pack d'audit anonymisé (rapport + manifest)
```

**Bonnes pratiques de publication :**

- [ ] Licence CC BY 4.0 explicite (réutilisation libre avec attribution) : c'est ce qui fait circuler une checklist.
- [ ] README avec une phrase de contexte : à qui ça sert, ce que ça ne remplace pas.
- [ ] Publier aussi les 40 points en carrousel ou fichier PDF sur LinkedIn.
- [ ] Annoncer une version 1.0 et une date de révision (une checklist datée est plus crédible).
- [ ] Demander un retour : « quel point manque à votre avis ? » — les retours font le post suivant.
- [ ] Ne pas mettre de formulaire de capture d'email : le lead magnet gratuit doit être réellement gratuit.

---

*Checklist version 1.0 du 4 novembre 2026 — CC BY 4.0. Les correspondances AI Act / ISO 42001 / OWASP sont indicatives et ne constituent pas un avis juridique. Aucune certification ni conformité n'est délivrée.*
