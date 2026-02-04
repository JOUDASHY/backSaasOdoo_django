#!/usr/bin/env python3
"""
Script pour remplir automatiquement les container_name manquants
pour les instances Odoo existantes.
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_backend.settings')
django.setup()

from saas_core.models import OdooInstance

def fill_container_names():
    """Remplit les container_name manquants pour les instances existantes"""
    instances_without_container = OdooInstance.objects.filter(container_name__isnull=True)
    count = instances_without_container.count()
    
    if count == 0:
        print("✅ Toutes les instances ont déjà un container_name.")
        return
    
    print(f"📦 Trouvé {count} instance(s) sans container_name.")
    print("🔄 Remplissage en cours...\n")
    
    for instance in instances_without_container:
        old_container_name = instance.container_name
        instance.container_name = f"odoo_{instance.name}"
        instance.save()
        print(f"  ✓ {instance.name} -> {instance.container_name}")
    
    print(f"\n✅ {count} container_name(s) rempli(s) avec succès!")

if __name__ == '__main__':
    fill_container_names()
