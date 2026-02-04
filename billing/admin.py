from django.contrib import admin

from billing.models import Plan, Subscription, Payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "max_users", "max_instances", "storage_limit_gb", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["client", "plan", "status", "start_date", "end_date", "auto_renew", "billing_cycle"]
    list_filter = ["status", "billing_cycle", "auto_renew", "start_date"]
    search_fields = ["client__company_name", "plan__name"]
    raw_id_fields = ["client", "plan"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["subscription", "amount", "method", "status", "payment_date", "transaction_id"]
    list_filter = ["status", "method", "payment_date"]
    search_fields = ["subscription__client__company_name", "transaction_id"]
    raw_id_fields = ["subscription"]

