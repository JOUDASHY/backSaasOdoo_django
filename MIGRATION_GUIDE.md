# Guide de Migration - Correction container_name

## Problème
Django demande une valeur par défaut pour le champ `container_name` car il y a des données existantes dans `OdooInstance`.

## Solution appliquée
Le champ `container_name` a été rendu **nullable** (`null=True, blank=True`) pour permettre la migration. Les valeurs seront générées automatiquement lors de la sauvegarde grâce à la méthode `save()`.

## Étapes pour créer les migrations

### 1. Créer les migrations
```bash
cd saas_backend
source ../venv/bin/activate  # Activer l'environnement virtuel
python3 manage.py makemigrations saas_core
```

Vous devriez maintenant pouvoir créer les migrations sans erreur.

### 2. Appliquer les migrations
```bash
python3 manage.py migrate
```

### 3. Remplir les container_name existants (optionnel mais recommandé)

Après avoir appliqué les migrations, vous pouvez créer une migration de données pour remplir automatiquement les `container_name` des instances existantes :

```bash
python3 manage.py makemigrations --empty saas_core
```

Cela créera un fichier de migration vide. Modifiez-le pour ajouter cette fonction :

```python
# Dans le fichier de migration créé (ex: 0002_fill_container_names.py)

from django.db import migrations

def fill_container_names(apps, schema_editor):
    """Remplit les container_name manquants pour les instances existantes"""
    OdooInstance = apps.get_model('saas_core', 'OdooInstance')
    for instance in OdooInstance.objects.filter(container_name__isnull=True):
        instance.container_name = f"odoo_{instance.name}"
        instance.save()

def reverse_fill_container_names(apps, schema_editor):
    """Ne fait rien en reverse"""
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('saas_core', '0001_initial'),  # Remplacez par le numéro de votre dernière migration
    ]

    operations = [
        migrations.RunPython(fill_container_names, reverse_fill_container_names),
    ]
```

Puis appliquez cette migration :
```bash
python3 manage.py migrate
```

### 4. (Optionnel) Rendre container_name non-nullable

Si vous voulez rendre le champ obligatoire après avoir rempli toutes les valeurs :

1. Modifiez `models.py` pour retirer `null=True` :
```python
container_name = models.CharField(max_length=100, unique=True, blank=True, help_text="...")
```

2. Créez une nouvelle migration :
```bash
python3 manage.py makemigrations saas_core
```

3. Appliquez-la :
```bash
python3 manage.py migrate
```

## Alternative : Script Python direct

Si vous préférez remplir les données directement sans migration :

```python
# script_fill_container_names.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_backend.settings')
django.setup()

from saas_core.models import OdooInstance

# Remplir les container_name manquants
for instance in OdooInstance.objects.filter(container_name__isnull=True):
    instance.container_name = f"odoo_{instance.name}"
    instance.save()
    print(f"Rempli container_name pour {instance.name}: {instance.container_name}")
```

Exécutez-le :
```bash
python3 script_fill_container_names.py
```

## Vérification

Pour vérifier que tout fonctionne :

```python
python3 manage.py shell
```

```python
from saas_core.models import OdooInstance

# Vérifier qu'il n'y a plus de container_name null
instances_without_container = OdooInstance.objects.filter(container_name__isnull=True)
print(f"Instances sans container_name: {instances_without_container.count()}")

# Vérifier quelques instances
for instance in OdooInstance.objects.all()[:5]:
    print(f"{instance.name} -> {instance.container_name}")
```
