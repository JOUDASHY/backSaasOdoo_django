from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string

from accounts.models import Client
from billing.models import Subscription


class OdooInstance(models.Model):
    STATUS_CHOICES = [
        ("CREATED", "Created - Pending Deployment"),
        ("DEPLOYING", "Deploying"),
        ("RUNNING", "Running"),
        ("STOPPED", "Stopped"),
        ("ERROR", "Error"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="instances")
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="instances")
    name = models.CharField(max_length=100, unique=True, help_text="Instance identifier (e.g. client1)")
    container_name = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Docker container name (auto-generated if empty)",
    )

    db_name = models.CharField(max_length=100)
    db_password = models.CharField(max_length=100, blank=True)
    admin_password = models.CharField(max_length=100, blank=True)

    domain = models.CharField(max_length=255, unique=True)
    port = models.IntegerField(unique=True, help_text="Assigned internal port")
    odoo_version = models.CharField(max_length=20, default="18", help_text="Odoo version (e.g., 16, 17, 18)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="CREATED")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.subscription and self.subscription.client_id != self.client_id:
            raise ValidationError("Subscription must belong to the same client")

    def save(self, *args, **kwargs):
        if not self.db_password:
            self.db_password = get_random_string(32)
        if not self.container_name:
            self.container_name = f"odoo_{self.name}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status})"


class DeploymentLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("START", "Start"),
        ("STOP", "Stop"),
        ("RESTART", "Restart"),
        ("DELETE", "Delete"),
        ("UPDATE", "Update"),
        ("BACKUP", "Backup"),
        ("RESTORE", "Restore"),
    ]

    STATUS_CHOICES = [
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("IN_PROGRESS", "In Progress"),
    ]

    instance = models.ForeignKey(OdooInstance, on_delete=models.CASCADE, related_name="deployment_logs")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="IN_PROGRESS")
    details = models.JSONField(default=dict)
    error_message = models.TextField(blank=True, null=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} - {self.instance.name} ({self.status})"

