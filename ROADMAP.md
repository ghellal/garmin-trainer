# Garmin Trainer — feuille de route technique

> **Statut :** proposition de séquencement, sans engagement de dates avant validation des risques Garmin et IA.

## Principes de livraison

- Traiter d’abord les incertitudes qui peuvent invalider l’architecture : couverture Garmin, authenticité de l’accès, usage de l’IA et coût.
- Livrer une tranche verticale utilisable à chaque phase plutôt qu’un backend complet avant l’interface.
- Conserver une architecture single-user, mais isoler les adaptateurs de données et d’IA pour limiter le coût d’un changement futur.
- Ne pas lancer de synchronisation automatique ni de notifications dans le MVP.

## Phase 0 — Décisions et spikes de faisabilité

### Travaux

1. Créer un compte/jeton Garmin Personal API et tester le parcours personnel de bout en bout.
2. Inventorier les données réellement retournées et leur historique : activités/FIT, sommeil, HRV, readiness, charge/statut, profil et métriques complémentaires.
3. Comparer cet inventaire aux besoins minimums d’une séance pertinente ; définir les métriques bloquantes et les solutions de repli.
4. Tester un connecteur de repli (dont `garmin-health-data`) sur les critères de couverture, maintenance, auth, cloud et idempotence.
5. Vérifier la possibilité d’utiliser OpenCode Go depuis un backend applicatif de coaching, les règles d’usage et la rétention des modèles candidats. Aucun vrai historique de santé dans le test initial.
6. Valider une projection de coûts GCP : Cloud Run sans instance minimale, Firebase Hosting/Auth et Firestore ; activer des alertes de budget (elles ne bloquent pas automatiquement les dépenses).

### Critères de sortie

- Décision documentée sur le connecteur primaire et son repli.
- Aucun champ essentiel à la séance n’est supposé disponible sans observation réelle.
- Fournisseur IA de test identifié, solution de repli définie et critères de confidentialité acceptés.
- Estimation et mesure du coût distinguant calcul, stockage, trafic et inférence.

## Phase 1 — Fondations et sécurité

> **État :** code de fondation prêt et validations locales passées. Le bootstrap
> du state est fait et un apply principal a créé une partie des ressources, mais
> Firebase/Hosting et l’invocation Cloud Run restent bloqués. Les prochains
> applies doivent passer uniquement par le workflow GitHub manuel.

### Travaux

- [x] Initialiser la PWA React/TypeScript et l’API FastAPI ; définir `/healthz` et `/api/v1/me`.
- [x] Créer le bucket GCS privé/versionné pour le state et écrire la configuration principale avec import des ressources WIF existantes.
- [x] Décrire Firebase Hosting/Auth, Cloud Run, Firestore en `europe-west1`, Artifact Registry, Secret Manager, IAM et l’alerte de budget facultative dans Terraform.
- [x] Mettre en place les workflows GitHub Actions de tests/validation et un pipeline `workflow_dispatch` WIF pour appliquer Terraform puis déployer l’application.
- [x] Restreindre l’API à un jeton Firebase valide et à l’unique e-mail vérifié autorisé ; ne pas utiliser de clé JSON.
- [x] Ajouter les règles Firestore deny-all côté navigateur, les origines CORS et les logs sans tokens/secrets.
- [x] Décrire les collections Firestore et règles de conservation dans `infra/FIRESTORE_SCHEMA.md`.
- [~] Apply principal partiel : Cloud Run (image hello), Firestore, Artifact Registry, secrets vides et IAM sont créés ; le run a échoué sur la création Firebase et la politique d’invoker public.
- [ ] Configurer `allowed_user_email`, les variables GitHub et, si souhaité, `billing_account_id` ; tester l’inscription, la vérification e-mail et l’appel API sur GCP.
- [ ] Configurer les permissions de provisionnement du compte WIF, déclencher le workflow manuel, puis confirmer les coûts réels.

### Critères de sortie

- Validations locales réussies : build PWA, tests API et `terraform validate` pour les deux configurations ; CI API est corrigée.
- Restent à vérifier en GCP : Firebase/Auth/Hosting, règles Firestore, invoker Cloud Run, budget, compte utilisateur authentifié et déploiement de l’image API.
- Les prochains applies doivent passer par le workflow manuel GitHub Actions. Le dispatch attend les permissions de provisionnement du compte WIF et la résolution de la politique d’organisation.

## Phase 2 — Connecteur Garmin et qualité des données

### Travaux

- Implémenter l’interface connecteur définie lors de la phase 0.
- Normaliser les données minimales pour le coaching et conserver source, date/heure et disponibilité.
- Ajouter synchronisation manuelle, idempotence, gestion des erreurs, expiration des accès et reprise.
- Construire une vue d’état minimale : dernière synchronisation, fraîcheur et métriques indisponibles (pas un tableau de bord santé).
- Associer une activité à un feedback lorsque la correspondance est fiable, avec possibilité de correction.

### Critères de sortie

- Une nouvelle synchronisation ne produit pas de doublons.
- Les périodes manquantes et erreurs d’accès sont identifiables.
- Un échantillon représentatif confirme la qualité et la fraîcheur des métriques retenues.
- Les retours saisis ne sont jamais perdus lors d’une resynchronisation.

## Phase 3 — Objectif, plan et séance du jour

### Travaux

- Construire les écrans d’onboarding et de configuration de l’objectif et des contraintes.
- Définir une représentation validée d’une séance (objectif, type, durée/volume, intensité, étapes, rationale et provenance des données).
- Implémenter la génération à la demande à partir du profil, de l’objectif, des données récentes et du plan confirmé.
- Ajouter édition par l’utilisateur et demande d’alternative, avec confirmation explicite avant remplacement.
- Ajouter des garde-fous côté backend pour douleur, fatigue importante, données insuffisantes et conseils médicaux.

### Critères de sortie

- Une séance est produite uniquement avec des données effectivement disponibles ou des informations fournies par l’utilisateur.
- L’utilisateur peut refuser/modifier une séance sans perdre l’objectif ni les séances passées.
- Les cas de sécurité ont des tests de comportement explicites.

## Phase 4 — Feedback post-séance et mémoire du chat

### Travaux

- Implémenter le formulaire fixe de feedback : RPE, sensations/fatigue, douleur et commentaire facultatif.
- Enregistrer les conversations et les événements de coaching de manière indépendante du fournisseur IA.
- Construire le contexte envoyé au modèle avec une fenêtre d’historique utile et une synthèse persistée si nécessaire.
- Implémenter l’adaptateur IA, validation des réponses structurées, timeouts, erreurs et fournisseur de remplacement.
- Mesurer coût et latence par génération sans journaliser le contenu sensible inutilement.

### Critères de sortie

- Le feedback affecte les recommandations suivantes et demeure distinguable des mesures Garmin.
- Le chat peut retrouver l’objectif et les retours antérieurs pertinents.
- Changer de fournisseur ne requiert pas de migration de l’historique produit.
- Les erreurs IA ne détruisent ni le chat ni les séances précédentes.

## Phase 5 — Bêta personnelle, fiabilité et décisions de mise en production

### Travaux

- Tester le parcours quotidien sur téléphone et les états sans réseau/données Garmin périmées.
- Vérifier export/suppression des données, renouvellement/révocation des accès et restauration des données.
- Faire une revue de sécurité et de confidentialité des journaux, règles d’accès et appels aux fournisseurs.
- Observer le coût réel sur plusieurs semaines ; ajuster alertes et configuration Cloud Run.
- Relire les recommandations avec prudence particulière sur les douleurs et données incomplètes.

### Critères de sortie

- Utilisation quotidienne stable sans intervention manuelle sur l’infrastructure.
- Budget compute vérifié sous le seuil cible de 5 €/mois, hors stockage/IA, ou décision explicite sur les compromis.
- Données exportables et effaçables, secrets révocables et mécanisme de reprise documenté.
- Limites et statut des données visibles à l’utilisateur.

## Éléments explicitement post-MVP

- Notifications/push et préparation automatique de la séance.
- Écriture de séances ou d’entraînements dans Garmin Connect.
- Application native, multi-utilisateur ou partage d’entraîneur.
- Paramétrage personnalisé des champs de feedback.
- Graphiques d’évolution déjà disponibles dans Garmin Connect.
- Plusieurs sources de données de santé ou fournisseurs IA actifs simultanément.
