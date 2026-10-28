# Garmin Trainer — spécifications produit et architecture

> **Statut :** brouillon de cadrage à valider
> **Version :** 0.1 — 22 octobre 2026
> **Périmètre :** MVP single-user, hébergé dans le cloud. Aucun code d’application n’est inclus dans ce document.

## 1. Vision

Garmin Trainer est un coach d’endurance personnel consulté le matin. Il aide l’utilisateur à progresser vers un objectif de long terme en proposant une séance adaptée aux données Garmin récentes, à l’historique d’entraînement et aux retours subjectifs de l’utilisateur. Il doit favoriser une progression prudente et signaler les situations où il vaut mieux alléger ou interrompre l’entraînement.

Le produit complète Garmin Connect : il apporte une recommandation et un accompagnement conversationnel, sans chercher à remplacer ses tableaux de bord.

## 2. Utilisateur et contexte

- **Utilisateur cible du MVP :** une seule personne, propriétaire de son compte Garmin.
- **Moment d’usage principal :** le matin, sur téléphone.
- **Interface :** application web progressive (PWA), responsive et installable.
- **Mode de consultation :** à la demande ; pas de génération automatique ni de notification dans le MVP.
- **Hébergement :** Google Cloud. Le coût de calcul récurrent doit rester inférieur à 5 €/mois après la période d’essai ; ce seuil sera vérifié par mesure réelle.

## 3. Objectifs produit

1. Rendre visible une séance du jour cohérente avec l’objectif long terme.
2. Ajuster le plan à la récupération, à la charge récente et aux retours après entraînement.
3. Permettre de demander une alternative ou de modifier une séance sans perdre le fil du plan.
4. Conserver une conversation contextualisée dans le temps.
5. Réduire les risques liés à une charge excessive, sans prétendre diagnostiquer une blessure ou une maladie.

### Hors objectifs du MVP

- Application native iOS/Android.
- Notifications ou génération planifiée de la séance.
- Graphiques et tableaux de bord de métriques déjà disponibles dans Garmin Connect.
- Utilisateurs multiples, partage social ou fonctionnalités coach/athlète.
- Écriture ou synchronisation de séances d’entraînement vers Garmin Connect ou une montre.
- Diagnostic médical, traitement ou promesse de prévention des blessures.

## 4. Parcours principaux

### 4.1 Première utilisation

1. L’utilisateur ouvre l’application et s’authentifie.
2. Il renseigne son objectif principal : discipline, date, cible mesurable si applicable, expérience, jours disponibles, contraintes et préférences utiles à l’entraînement.
3. Il relie ou configure l’accès à ses données Garmin.
4. Il lance une synchronisation et voit clairement les données disponibles, leur fraîcheur et les éventuelles lacunes.
5. L’application présente une première proposition de plan/séance, avec les limites des données utilisées.

### 4.2 Séance du jour

1. L’utilisateur consulte la séance proposée ou demande sa génération/actualisation.
2. La proposition expose son objectif, son intensité, sa durée ou son volume, ses étapes utiles et les métriques/contextes qui la motivent.
3. L’utilisateur peut demander une alternative (par exemple plus légère, moins intense ou adaptée au temps disponible) ou modifier la séance.
4. Une alternative ou modification ne remplace le plan que lorsque l’utilisateur la confirme.

### 4.3 Retour après séance

Le feedback est saisi dans Garmin Trainer, afin de conserver des champs cohérents et exploitables, indépendamment des champs exposés par Garmin.

Champs fixes envisagés pour le MVP :

- effort perçu (RPE, échelle explicitée dans l’interface) ;
- sensations/fatigue générale et état des jambes ;
- douleur : présence, intensité et zone, avec commentaire facultatif ;
- commentaire libre facultatif.

Le feedback est associé à une activité Garmin lorsqu’une correspondance fiable est disponible ; sinon l’utilisateur peut choisir l’activité ou enregistrer le retour sans activité associée. Le feedback doit être conservé même si la source Garmin ne permet pas de l’écrire dans Garmin Connect.

### 4.4 Chat avec mémoire

- L’utilisateur peut poser des questions libres sur son entraînement et discuter d’une séance.
- L’application conserve les messages et le contexte utile : objectif, décisions confirmées, séances et feedback.
- La mémoire ne doit pas conduire le modèle à inventer des métriques absentes ; l’application doit distinguer données mesurées, feedback utilisateur et inférences.
- L’utilisateur peut corriger le contexte ou demander l’effacement de l’historique selon la politique de conservation retenue.

## 5. Données et exigences fonctionnelles

### 5.1 Données nécessaires au coaching

Le MVP doit rechercher, par ordre de priorité :

1. sommeil récent et indicateurs de récupération disponibles ;
2. HRV/tendance si disponible ;
3. entraînements récents, type, durée, intensité et détails utiles ;
4. charge d’entraînement et readiness/statut d’entraînement si disponibles ;
5. profil et zones/repères sportifs disponibles ;
6. feedback subjectif saisi dans l’application ;
7. objectif et contraintes définis par l’utilisateur.

VO₂ max, records personnels et prédictions de course sont des informations utiles mais non bloquantes pour la première proposition de séance.

Les données doivent être accompagnées de leur source et date de dernière synchronisation. Une absence ou une ancienneté excessive doit être visible et ne doit pas être transformée en valeur supposée.

### 5.2 Couche d’intégration Garmin

L’application doit séparer le domaine coaching du fournisseur de données via une interface de connecteur. Le connecteur doit normaliser au minimum les activités, le sommeil, les indicateurs de récupération et les données de synchronisation.

**Candidat prioritaire à valider : Garmin Connect Personal API.** La documentation Garmin présente un accès personnel aux données d’activité et de santé, avec récupération par l’application. La page publique ne garantit toutefois pas que toutes les métriques du coach actuel (en particulier training readiness, charge/statut d’entraînement, VO₂ max ou prédictions) soient disponibles dans cette offre. Il faut valider les champs et historiques réels avec un compte avant de s’engager.

**Solution de repli à évaluer :** conserver `garmin-health-data` ou un autre connecteur de Garmin Connect si l’accès personnel officiel ne fournit pas les champs essentiels. Son architecture actuelle est centrée sur une base SQLite locale ; sa compatibilité avec un service cloud et la robustesse de son authentification restent à étudier.

La sélection finale doit comparer : couverture des métriques, profondeur historique, fréquence et simplicité de synchronisation, stabilité/maintenance, conditions d’utilisation, stockage des identifiants et effort opérationnel. Le MVP ne doit pas dépendre de l’interface web Garmin ni d’un scraping fragile sans décision explicite.

### 5.3 Synchronisation

- Synchronisation déclenchée à la demande par l’utilisateur ; l’application peut proposer de synchroniser lorsque les données sont trop anciennes.
- Affichage de l’état (en cours, réussi, partiel, échec), date de dernière réussite et lacunes.
- Opération idempotente : une resynchronisation ne crée pas de doublons.
- Les erreurs d’accès, l’expiration d’identifiants et les limites de débit doivent être présentées avec une action de reprise claire.

### 5.4 Stockage, mémoire et conservation — décision retenue

L’application cloud conservera une copie **minimale et normalisée** des données utiles au coaching dans Firestore. Garmin reste la source de référence des mesures Garmin ; l’application est la source de référence des objectifs, séances confirmées, feedbacks et échanges. Les données ne seront pas re-téléchargées intégralement depuis Garmin à chaque question.

| Donnée | Stockage proposé | Conservation proposée |
|---|---|---|
| Objectif, préférences et contraintes | Profil structuré dans Firestore | Tant que l’objectif est actif ; objectifs terminés archivés jusqu’à suppression par l’utilisateur |
| Activités Garmin | Identifiant Garmin + résumé normalisé (date, type, durée, distance/intensité si disponibles, données utiles à l’entraînement) | Historique résumé glissant de 24 mois |
| Santé Garmin | Résumés quotidiens utiles (par ex. sommeil/HRV/récupération si disponibles), source et horodatage | 12 mois de données quotidiennes pour les tendances ; pas de flux seconde par seconde dans le MVP |
| Détails bruts Garmin | FIT, GPS et flux détaillés | Non conservés par défaut ; récupération ponctuelle si nécessaire et permise, puis traitement transitoire |
| Feedback et séances confirmées | Enregistrements structurés liés à la date/activité, avec commentaire fourni par l’utilisateur | Jusqu’à suppression par l’utilisateur ; export et effacement à prévoir |
| Conversations | Messages conservés pour l’historique produit ; contexte mémoire séparé | Historique complet 12 mois, effaçable à tout moment |
| Mémoire de coaching | Résumé structuré des objectifs, préférences confirmées, décisions et feedbacks utiles — pas de diagnostic inféré | Tant que le compte reste actif, effaçable ou réinitialisable indépendamment de l’historique de chat |
| Secrets Garmin et IA | Secret Manager, jamais dans Firestore ni le navigateur | Jusqu’à révocation/remplacement |

Ces durées sont retenues pour le MVP. Le faible volume des résumés n’est pas le facteur principal ; les enjeux sont la confidentialité, l’utilité historique et la capacité à effacer/exporter les données.

Pour chaque génération, le backend compose un contexte limité à partir de l’objectif actif, des métriques Garmin récentes, des dernières activités, du feedback pertinent, de la mémoire structurée et d’une fenêtre récente du chat. Il ne renvoie pas automatiquement tout l’historique au modèle. Les anciens échanges peuvent être résumés, mais le résumé doit rester identifiable comme une synthèse et pouvoir être supprimé. Les corps des requêtes IA ne sont pas dupliqués dans les logs ; les politiques de conservation du fournisseur restent à vérifier séparément.

## 6. Sécurité et garde-fous de coaching

- L’IA produit une aide à l’entraînement, pas un avis médical.
- Une douleur signalée ou des signes de fatigue importante doivent déclencher un comportement prudent : questionner si nécessaire, proposer repos/allègement et recommander une évaluation professionnelle en cas de symptôme préoccupant. Ne jamais encourager à s’entraîner malgré une douleur importante ou une maladie.
- Les règles de sécurité critiques ne doivent pas dépendre uniquement du prompt ou d’une décision probabiliste du modèle.
- La séance est une proposition : l’utilisateur peut la refuser ou la modifier.
- Les appels au modèle doivent recevoir le minimum de données nécessaire. Aucune clé API ne doit être exposée dans la PWA.
- Cloud Run est joignable par Firebase Hosting pour le proxy `/api/**` ; chaque endpoint applicatif (hors `/healthz`) vérifie côté API le jeton Firebase et l’adresse e-mail vérifiée autorisée. L’invocation Cloud Run publique ne constitue pas l’autorisation applicative.
- Les données Garmin, les retours et les conversations sont des données personnelles sensibles : chiffrement en transit, accès limité au compte utilisateur, secrets hors du code, suppression/export à prévoir.
- Les modalités d’export/suppression et la revue des règles d’accès restent à tester avant mise en production.

## 7. Architecture cible proposée — à valider

### 7.1 Choix retenus pour le MVP

- **Frontend :** PWA web responsive en TypeScript (framework à confirmer, recommandation initiale : React).
- **Backend :** API Python/FastAPI, cohérente avec les outils d’extraction existants.
- **Hébergement API :** Google Cloud Run avec instances minimales à zéro, sans service toujours actif.
- **Frontend :** Firebase Hosting.
- **Authentification :** Firebase Authentication par e-mail/mot de passe, adresse vérifiée et allowlist serveur sur l’unique e-mail autorisé.
- **Persistance :** Cloud Firestore dans la région `europe-west1`, privilégiant l’absence de coût de base de données toujours active et l’intégration GCP. Les données seront stockées en documents par domaine (objectif, journée santé, activité, séance, feedback, conversation). Si les requêtes historiques/relations deviennent complexes, réévaluer PostgreSQL avant d’étendre le modèle.
- **Secrets :** Secret Manager pour l’accès Garmin et les clés de fournisseur IA.
- **Observabilité :** logs et métriques Cloud, avec exclusion des secrets et minimisation des données de santé dans les logs.
- **Infrastructure as Code :** Terraform versionné dans le dépôt ; état distant dans un bucket GCS privé et versionné.
- **CI/CD :** GitHub Actions pour les tests, la validation Terraform et les déploiements. Authentification GitHub vers GCP par OIDC/Workload Identity Federation, sans clé de compte de service persistante.

Cette proposition vise un coût de calcul faible pour un usage personnel et irrégulier ; **elle ne garantit pas à elle seule** un coût total inférieur à 5 €/mois. Le backend, le stockage, le trafic, les éventuelles tâches planifiées et l’inférence sont à budgéter séparément. Le MVP ne requiert pas de tâche planifiée.

L’emplacement Firestore est choisi à la création et ne se déplace pas simplement ensuite ; `europe-west1` est donc un choix explicite. Une alerte de budget GCP sera configurée, sachant qu’une alerte n’est pas un plafond automatique de dépenses.

### 7.2 Infrastructure et CI/CD

- Terraform gère les ressources GCP nécessaires : APIs, Firebase Project/Auth/Hosting, Firestore, Cloud Run, Artifact Registry, Secret Manager et IAM. Le bootstrap WIF est créé une fois par le script gcloud puis importé dans Terraform.
- L’état Terraform est conservé dans un bucket GCS privé avec versioning et accès minimal. Le bootstrap initial du bucket et de l’identité fédérée doit être documenté ; aucun secret ne doit être commité.
- Les valeurs des secrets Garmin/IA sont ajoutées à Secret Manager hors du code et ne sont pas passées comme valeurs Terraform persistées dans le state.
- Sur pull request : formatage Terraform, validation, tests API et build PWA ; aucun accès GCP ni `apply`.
- Sur `main`, le workflow GitHub Actions `workflow_dispatch` applique Terraform puis déploie l’application via WIF. Aucun `terraform apply` local n’est autorisé.
- Le compte WIF doit recevoir les permissions de provisionnement nécessaires avant le premier dispatch ; `roles/resourcemanager.projectIamAdmin` est particulièrement puissant et doit être approuvé/protégé.
- L’identité WIF a aussi des rôles de déploiement Cloud Run/Hosting et l’accès au dépôt d’images/state. Les sorties et artefacts GitHub ne doivent pas exposer de secrets.

### 7.3 Couche IA

Le backend doit s’appuyer sur une interface de fournisseur IA, indépendante du fournisseur et du format d’API. OpenCode Go est un candidat de test puisque l’utilisateur dispose déjà d’un abonnement, mais sa documentation décrit un service principalement destiné aux agents de codage. Son adéquation à un coach sportif, ses conditions d’usage, le modèle choisi et sa politique de rétention doivent être vérifiés avant d’envoyer des données réelles. Prévoir un fournisseur de remplacement sans modifier le domaine produit.

Les conversations, plans confirmés et feedbacks sont stockés dans l’application, pas seulement dans l’historique fournisseur. La réponse du modèle doit être structurée et validée côté backend avant d’être affichée ou enregistrée comme séance.

### 7.4 Flux logique

`PWA/Firebase Auth → Firebase Hosting → Cloud Run (public pour le proxy, protégé par Firebase ID token dans FastAPI) → Firestore / connecteurs / fournisseur IA`

Le navigateur ne contacte directement ni Garmin ni le fournisseur IA. Les composants sont séparés derrière des interfaces afin de permettre de changer de connecteur Garmin, de fournisseur IA ou de persistance sans réécrire l’interface et la logique de coaching.

## 8. Critères d’acceptation du MVP

- L’utilisateur peut se connecter depuis un téléphone et configurer un objectif de long terme.
- Il peut lancer une synchronisation Garmin et voir la fraîcheur, les données manquantes et les erreurs.
- Il peut obtenir une séance contextualisée à la demande, demander une alternative et confirmer/modifier sa séance.
- Il peut saisir un feedback structuré après l’activité et le retrouver dans le contexte du coaching suivant.
- Le chat conserve son historique et utilise l’objectif, les séances et feedbacks pertinents.
- La séance distingue les faits Garmin, les déclarations utilisateur et les recommandations.
- Les situations de douleur/fatigue à risque déclenchent les garde-fous documentés.
- L’application continue à expliquer ses limites lorsque la synchronisation ou les métriques nécessaires sont absentes.
- Aucune donnée ou clé sensible n’est envoyée depuis le frontend sans protection.
- Une alerte de budget et une mesure du coût réel sont en place avant l’usage régulier.

## 9. Risques et décisions ouvertes

| Sujet | Risque / question | Traitement prévu |
|---|---|---|
| Garmin Personal API | Couverture réelle des métriques de readiness/charge et profondeur historique inconnues | Spike avec inventaire des champs et comparaison aux besoins du coach ; connecteur interchangeable |
| Accès Garmin | Clé personnelle, génération/expiration de jeton et conditions d’utilisation | Tester le parcours complet et documenter la rotation/révocation |
| Connecteur de repli | Outils communautaires potentiellement sensibles aux changements de Garmin Connect | Comparer maintenance, sécurité et mode d’authentification avant adoption |
| OpenCode Go | Service orienté codage ; conditions, modèles et rétention variables | Test sans données réelles, validation des conditions et sélection explicite du modèle ; fallback abstrait |
| Coûts | Cloud SQL ou instances toujours actives peuvent dépasser le budget compute | Éviter Cloud SQL et instances minimales actives au MVP ; mesurer Cloud Run et mettre une alerte budget |
| Données sensibles | Données Garmin et conversations copiées dans le cloud | Région `europe-west1` et durées de conservation retenues ; export, effacement et minimisation à tester avant bêta |
| Sécurité sportive | L’IA ne remplace ni un médecin ni un coach certifié | Garde-fous déterministes, formulation prudente, validation humaine des séances |

## 10. Références

- [Garmin Connect Developer Program — Overview](https://developer.garmin.com/gc-developer-program/overview/)
- [Garmin Connect Personal API — obtention d’une clé et d’un jeton](https://developer.garmin.com/gc-developer-program/personal/personal-api/)
- [garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data)
- [OpenCode Go — fonctionnement, clients et confidentialité](https://opencode.ai/v2/docs/console/go/)
- [OpenCode Console — API d’inférence](https://opencode.ai/v2/docs/console/api/inference/)
