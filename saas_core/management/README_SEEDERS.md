## Seeders (Django)

Dans Django, l’équivalent d’un **seeder Laravel** est généralement :
- une **management command** (recommandé pour du seed “intelligent” et idempotent),
- ou des **fixtures** (`loaddata`).

### Seeder des Plans

Commande :

```bash
python3 manage.py seed_plans
```

Options utiles :

```bash
# Voir ce qui changerait sans écrire en base
python3 manage.py seed_plans --dry-run

# Désactiver (is_active=False) les plans existants qui ne sont pas dans la liste DEFAULT_PLANS
python3 manage.py seed_plans --deactivate-missing
```

Les plans sont créés/mis à jour via `update_or_create` “manuel” (idempotent), donc tu peux relancer la commande sans dupliquer les données.

