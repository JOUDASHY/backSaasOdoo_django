from rest_framework import serializers
from django.db.models import Sum

from billing.models import Plan, Subscription, Payment


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = "__all__"


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)
    plan_price = serializers.DecimalField(source="plan.price", max_digits=10, decimal_places=2, read_only=True)
    client_company = serializers.CharField(source="client.company_name", read_only=True)
    plan_allowed_modules = serializers.ListField(source="plan.allowed_modules", child=serializers.CharField(), read_only=True)
    total_paid = serializers.SerializerMethodField()
    amount_due = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = "__all__"
        read_only_fields = ["client"]

    def get_total_paid(self, obj):
        agg = obj.payments.filter(status="PAID").aggregate(total=Sum("amount"))
        return agg["total"] or 0

    def get_amount_due(self, obj):
        price = obj.plan.price or 0
        total_paid = self.get_total_paid(obj)
        remaining = price - total_paid
        return remaining if remaining > 0 else 0


class PaymentSerializer(serializers.ModelSerializer):
    subscription_plan = serializers.CharField(source="subscription.plan.name", read_only=True)
    client_company = serializers.CharField(source="subscription.client.company_name", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["created_at", "payment_date"]

