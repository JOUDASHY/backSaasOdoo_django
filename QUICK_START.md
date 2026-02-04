# Guide Rapide - Création des Migrations

## ✅ Étape 1 : Créer les migrations

Vous êtes déjà dans le bon répertoire avec le venv activé. Exécutez :

```bash
python3 manage.py makemigrations saas_core
```

Cette commande devrait maintenant fonctionner sans erreur car `container_name` est nullable.

## ✅ Étape 2 : Appliquer les migrations

```bash
python3 manage.py migrate
```

## ✅ Étape 3 : Remplir les container_name existants (si vous avez des données)

Si vous avez des instances Odoo existantes dans votre base de données, exécutez le script :

```bash
python3 fill_container_names.py
```

Ce script remplira automatiquement les `container_name` manquants avec le format `odoo_{instance_name}`.

## ✅ Étape 4 : Vérification

Pour vérifier que tout fonctionne :

```bash
python3 manage.py shell
```

Puis dans le shell Python :
```python
from saas_core.models import OdooInstance, Payment, DeploymentLog, Plan, Subscription

# Vérifier les nouveaux modèles
print(f"Plans: {Plan.objects.count()}")
print(f"Subscriptions: {Subscription.objects.count()}")
print(f"Instances: {OdooInstance.objects.count()}")
print(f"Payments: {Payment.objects.count()}")
print(f"DeploymentLogs: {DeploymentLog.objects.count()}")

# Vérifier les container_name
for instance in OdooInstance.objects.all():
    print(f"{instance.name} -> container: {instance.container_name}")
```

## 📝 Notes importantes

- Le champ `container_name` est maintenant **nullable** pour permettre la migration
- Les nouvelles instances auront leur `container_name` généré automatiquement lors de la création
- Les instances existantes peuvent être mises à jour avec le script `fill_container_names.py`
- Si vous voulez rendre `container_name` non-nullable après avoir rempli toutes les valeurs, consultez `MIGRATION_GUIDE.md`

## 🎯 Résumé des nouveaux champs ajoutés

### Plan
- `max_instances` (défaut: 1)
- `created_at`

### Subscription
- `auto_renew` (défaut: True)
- `billing_cycle` (MONTHLY/YEARLY, défaut: MONTHLY)
- `next_billing_date`
- `created_at`

### OdooInstance
- `container_name` (nullable, auto-généré)
- `odoo_version` (défaut: '18')
- `updated_at`
- Nouveau statut: `DEPLOYING`

### Nouveaux modèles
- `Payment` (avec relation vers Subscription)
- `DeploymentLog` (avec relation vers OdooInstance et User)
