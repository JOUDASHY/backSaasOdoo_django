# Changelog - Améliorations du modèle de données SaaS Kit

## Date: 2026-01-27

### Résumé des modifications

Ce document décrit toutes les modifications apportées au modèle de données pour aligner le code avec le diagramme de classes et améliorer le système SaaS Kit Odoo.

---

## ✅ Modifications effectuées

### 1. Diagramme de classes PlantUML
- ✅ Créé le fichier `diagram_class.puml` avec le diagramme complet et corrigé
- ✅ Toutes les relations sont correctement définies
- ✅ Tous les champs nécessaires sont inclus

### 2. Modèle Client
- ✅ Ajout de la méthode `get_active_subscription()`
- ✅ Ajout de la méthode `can_create_instance()` pour vérifier les limites du plan
- ✅ Le champ `created_at` était déjà présent

### 3. Modèle Plan
- ✅ Ajout du champ `max_instances` (limite d'instances par client)
- ✅ Ajout du champ `created_at`
- ✅ Ajout de la méthode `is_module_allowed(module_name)`

### 4. Modèle Subscription
- ✅ Ajout du champ `auto_renew` (renouvellement automatique)
- ✅ Ajout du champ `billing_cycle` (MONTHLY/YEARLY)
- ✅ Ajout du champ `next_billing_date`
- ✅ Ajout du champ `created_at`
- ✅ Ajout de la méthode `is_active()` pour vérifier le statut réel
- ✅ Ajout de la méthode `check_expiration()` pour auto-expirer
- ✅ Ajout de la méthode `clean()` pour validation des dates
- ✅ Ajout d'une contrainte unique pour éviter plusieurs abonnements actifs par client

### 5. Modèle OdooInstance
- ✅ Ajout du champ `container_name` (utilisé dans docker-compose.yml)
- ✅ Ajout du champ `odoo_version` (version Odoo déployée)
- ✅ Ajout du champ `updated_at`
- ✅ Ajout du statut `DEPLOYING` dans STATUS_CHOICES
- ✅ Correction du `related_name` de `subscription` : `'instance'` → `'instances'`
- ✅ Ajout de la méthode `clean()` pour valider la cohérence client/subscription
- ✅ Génération automatique de `container_name` si non fourni
- ✅ Ajout des méthodes `start()`, `stop()`, `restart()` (à implémenter dans les services)

### 6. Nouveau modèle Payment
- ✅ Création complète du modèle `Payment`
- ✅ Champs : `amount`, `payment_date`, `method`, `status`, `transaction_id`
- ✅ Relation ForeignKey vers `Subscription`
- ✅ Choix pour `method` : CREDIT_CARD, BANK_TRANSFER, PAYPAL, STRIPE
- ✅ Choix pour `status` : PENDING, PAID, FAILED, REFUNDED

### 7. Nouveau modèle DeploymentLog
- ✅ Création complète du modèle `DeploymentLog`
- ✅ Champs : `timestamp`, `action`, `status`, `details`, `error_message`, `duration_seconds`
- ✅ Relation ForeignKey vers `OdooInstance` et `User`
- ✅ Choix pour `action` : CREATE, START, STOP, RESTART, DELETE, UPDATE, BACKUP, RESTORE
- ✅ Choix pour `status` : SUCCESS, FAILED, IN_PROGRESS
- ✅ Index pour optimiser les requêtes

### 8. Serializers
- ✅ Mise à jour de `UserSerializer` avec le champ `role` (méthode)
- ✅ Mise à jour de `ClientSerializer` avec `active_subscription`
- ✅ Mise à jour de `SubscriptionSerializer` avec `is_active_status`
- ✅ Mise à jour de `OdooInstanceSerializer` avec les nouveaux champs
- ✅ Création de `PaymentSerializer`
- ✅ Création de `DeploymentLogSerializer`

### 9. Views (ViewSets)
- ✅ Mise à jour de `OdooInstanceViewSet.perform_create()` pour utiliser `can_create_instance()`
- ✅ Mise à jour de `deploy_instance()` pour créer des logs de déploiement
- ✅ Ajout du statut `DEPLOYING` pendant le déploiement
- ✅ Création de `PaymentViewSet` avec filtrage par client
- ✅ Création de `DeploymentLogViewSet` (read-only) avec filtrage par instance et client
- ✅ Mise à jour de `UserMeView` pour inclure le champ `role`

### 10. URLs
- ✅ Ajout de la route `/api/payments/`
- ✅ Ajout de la route `/api/deployment-logs/`

### 11. Admin Django
- ✅ Enregistrement de tous les modèles dans l'admin
- ✅ Configuration des list_display, list_filter, search_fields pour chaque modèle
- ✅ Configuration des raw_id_fields pour les ForeignKeys

---

## 📋 Prochaines étapes

### 1. Installer les dépendances
```bash
pip install -r requirements.txt
# ou
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt
```

### 2. Créer les migrations
```bash
cd saas_backend
python manage.py makemigrations saas_core
```

### 3. Appliquer les migrations
```bash
python manage.py migrate
```

### 4. Vérifier les données existantes
⚠️ **Attention** : Les migrations peuvent nécessiter des valeurs par défaut pour les nouveaux champs obligatoires :
- `Plan.max_instances` : valeur par défaut = 1
- `Subscription.auto_renew` : valeur par défaut = True
- `Subscription.billing_cycle` : valeur par défaut = 'MONTHLY'
- `OdooInstance.container_name` : généré automatiquement si vide
- `OdooInstance.odoo_version` : valeur par défaut = '18'

### 5. Tests recommandés
- ✅ Tester la création d'une instance avec les nouvelles validations
- ✅ Tester la création d'un Payment
- ✅ Tester les logs de déploiement
- ✅ Vérifier les contraintes (ex: un seul abonnement actif par client)
- ✅ Tester les limites du plan (max_instances)

---

## 🔍 Points d'attention

### Contrainte unique sur Subscription
Une contrainte unique a été ajoutée pour empêcher plusieurs abonnements ACTIVE par client. Si vous avez des données existantes avec plusieurs abonnements actifs, vous devrez les corriger avant d'appliquer la migration.

### Related_name corrigé
Le `related_name` de `OdooInstance.subscription` a été changé de `'instance'` à `'instances'` pour être cohérent (relation many-to-one).

### Génération automatique container_name
Si `container_name` n'est pas fourni lors de la création, il sera automatiquement généré comme `odoo_{instance_name}`.

---

## 📊 Résumé des nouveaux endpoints API

```
GET    /api/payments/              # Liste des paiements
POST   /api/payments/              # Créer un paiement
GET    /api/payments/{id}/         # Détails d'un paiement
PUT    /api/payments/{id}/         # Modifier un paiement
DELETE /api/payments/{id}/         # Supprimer un paiement

GET    /api/deployment-logs/       # Liste des logs de déploiement
GET    /api/deployment-logs/{id}/ # Détails d'un log
GET    /api/deployment-logs/?instance={id}  # Filtrer par instance
```

---

## 🎯 Fonctionnalités ajoutées

1. **Gestion des paiements** : Suivi complet des paiements des abonnements
2. **Logs de déploiement** : Traçabilité complète de toutes les actions sur les instances
3. **Validation des limites** : Vérification automatique des limites du plan avant création d'instance
4. **Renouvellement automatique** : Support pour le renouvellement automatique des abonnements
5. **Cycle de facturation** : Support pour facturation mensuelle/annuelle
6. **Statut DEPLOYING** : Meilleur suivi du processus de déploiement

---

## 📝 Notes techniques

- Tous les modèles utilisent `created_at` avec `auto_now_add=True`
- Les modèles `OdooInstance` et `DeploymentLog` utilisent aussi `updated_at` / `timestamp`
- Les mots de passe (`db_password`, `admin_password`) sont stockés en clair (à chiffrer en production)
- Les `DeploymentLog` sont en lecture seule via l'API (création uniquement côté serveur)
