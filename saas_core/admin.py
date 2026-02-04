from django.contrib import admin
from .models import Client, Plan, Subscription, OdooInstance, Payment, DeploymentLog

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'phone', 'created_at']
    list_filter = ['created_at']
    search_fields = ['company_name', 'user__username', 'user__email']
    raw_id_fields = ['user']

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'max_users', 'max_instances', 'storage_limit_gb', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['client', 'plan', 'status', 'start_date', 'end_date', 'auto_renew', 'billing_cycle']
    list_filter = ['status', 'billing_cycle', 'auto_renew', 'start_date']
    search_fields = ['client__company_name', 'plan__name']
    raw_id_fields = ['client', 'plan']
    date_hierarchy = 'start_date'

@admin.register(OdooInstance)
class OdooInstanceAdmin(admin.ModelAdmin):
    list_display = ['name', 'client', 'subscription', 'domain', 'port', 'status', 'odoo_version', 'created_at']
    list_filter = ['status', 'odoo_version', 'created_at']
    search_fields = ['name', 'domain', 'client__company_name']
    raw_id_fields = ['client', 'subscription']
    readonly_fields = ['created_at', 'updated_at', 'db_password', 'admin_password']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'method', 'status', 'payment_date', 'transaction_id']
    list_filter = ['status', 'method', 'payment_date']
    search_fields = ['subscription__client__company_name', 'transaction_id']
    raw_id_fields = ['subscription']
    date_hierarchy = 'payment_date'

@admin.register(DeploymentLog)
class DeploymentLogAdmin(admin.ModelAdmin):
    list_display = ['instance', 'action', 'status', 'timestamp', 'duration_seconds', 'user']
    list_filter = ['action', 'status', 'timestamp']
    search_fields = ['instance__name', 'error_message']
    raw_id_fields = ['instance', 'user']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
