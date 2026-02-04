from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Client


class Command(BaseCommand):
    help = "Create demo admin and client users"

    def handle(self, *args, **options):
        # Admin
        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_password = "Admin123!"
        admin, created = User.objects.get_or_create(
            username=admin_username,
            defaults={"email": admin_email, "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(admin_password)
            admin.save()
            self.stdout.write(self.style.SUCCESS(f"created admin {admin_username} / {admin_password}"))
        else:
            self.stdout.write(self.style.WARNING(f"admin {admin_username} already exists"))

        # Client user + profile
        client_username = "client"
        client_email = "client@example.com"
        client_password = "Client123!"
        user, created = User.objects.get_or_create(
            username=client_username,
            defaults={"email": client_email, "is_staff": False, "is_superuser": False},
        )
        if created:
            user.set_password(client_password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"created client user {client_username} / {client_password}"))
        else:
            self.stdout.write(self.style.WARNING(f"client user {client_username} already exists"))

        client_profile, created = Client.objects.get_or_create(
            user=user,
            defaults={"company_name": "Demo Company", "phone": "0000000000", "address": "Demo address"},
        )
        if created:
            self.stdout.write(self.style.SUCCESS("created client profile"))
        else:
            self.stdout.write(self.style.WARNING("client profile already exists"))

