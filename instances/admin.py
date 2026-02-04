from django.contrib import admin

from instances.models import OdooInstance, DeploymentLog


@admin.register(OdooInstance)
class OdooInstanceAdmin(admin.ModelAdmin):
    list_display = ["name", "client", "subscription", "domain", "port", "status", "odoo_version", "created_at"]
    list_filter = ["status", "odoo_version", "created_at"]
    search_fields = ["name", "domain", "client__company_name"]
    raw_id_fields = ["client", "subscription"]
    readonly_fields = ["created_at", "updated_at", "db_password", "admin_password"]


@admin.register(DeploymentLog)
class DeploymentLogAdmin(admin.ModelAdmin):
    list_display = ["instance", "action", "status", "timestamp", "duration_seconds", "user"]
    list_filter = ["action", "status", "timestamp"]
    search_fields = ["instance__name", "error_message"]
    raw_id_fields = ["instance", "user"]
    readonly_fields = ["timestamp"]

