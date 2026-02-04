from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import Plan


DEFAULT_PLANS = [
    {
        "name": "Starter",
        "price": "19.00",
        "max_users": 3,
        "storage_limit_gb": 10,
        "max_instances": 1,
        "allowed_modules": [
            "base",
            "web",
            "mail",
            "contacts",
            "calendar",
            "crm",
            "sale",
            "purchase",
            "stock",
            "account",
        ],
        "is_active": True,
    },
    {
        "name": "Business",
        "price": "49.00",
        "max_users": 15,
        "storage_limit_gb": 50,
        "max_instances": 2,
        "allowed_modules": [
            "base",
            "web",
            "mail",
            "contacts",
            "calendar",
            "crm",
            "sale",
            "purchase",
            "stock",
            "account",
            "project",
            "hr",
            "helpdesk",
            "website",
            "mass_mailing",
        ],
        "is_active": True,
    },
    {
        "name": "Enterprise",
        "price": "99.00",
        "max_users": 50,
        "storage_limit_gb": 200,
        "max_instances": 5,
        "allowed_modules": [
            "base",
            "web",
            "mail",
            "contacts",
            "calendar",
            "crm",
            "sale",
            "purchase",
            "stock",
            "account",
            "project",
            "hr",
            "helpdesk",
            "website",
            "mass_mailing",
            "documents",
            "sign",
            "voip",
            "knowledge",
            "studio",
        ],
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Seed default SaaS plans (Starter/Business/Enterprise). Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--deactivate-missing", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        deactivate_missing: bool = options["deactivate_missing"]

        names = [p["name"] for p in DEFAULT_PLANS]
        created = 0
        updated = 0

        for plan_data in DEFAULT_PLANS:
            name = plan_data["name"]
            obj = Plan.objects.filter(name=name).first()

            if obj is None:
                created += 1
                if not dry_run:
                    Plan.objects.create(**plan_data)
                self.stdout.write(f"{'[dry-run] ' if dry_run else ''}create Plan '{name}'")
                continue

            changed_fields = []
            for field, value in plan_data.items():
                if getattr(obj, field) != value:
                    changed_fields.append(field)
                    if not dry_run:
                        setattr(obj, field, value)

            if changed_fields:
                updated += 1
                if not dry_run:
                    obj.save(update_fields=changed_fields)
                self.stdout.write(
                    f"{'[dry-run] ' if dry_run else ''}update Plan '{name}' fields: {', '.join(changed_fields)}"
                )

        if deactivate_missing:
            qs = Plan.objects.exclude(name__in=names).filter(is_active=True)
            count = qs.count()
            if count:
                if not dry_run:
                    qs.update(is_active=False)
                self.stdout.write(f"{'[dry-run] ' if dry_run else ''}deactivate {count} plan(s)")

        self.stdout.write(f"done: created={created}, updated={updated}")

