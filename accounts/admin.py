from django.contrib import admin

from accounts.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["company_name", "user", "phone", "created_at"]
    search_fields = ["company_name", "user__username", "user__email"]
    raw_id_fields = ["user"]

