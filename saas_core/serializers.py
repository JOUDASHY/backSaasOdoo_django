from rest_framework import serializers
from .models import Client, Plan, Subscription, OdooInstance, Payment, DeploymentLog
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_staff', 'is_active', 'date_joined', 'role']
    
    def get_role(self, obj):
        """Retourne le rôle de l'utilisateur (ADMIN ou CLIENT)"""
        if obj.is_staff:
            return 'ADMIN'
        if hasattr(obj, 'client_profile'):
            return 'CLIENT'
        return None

class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    active_subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def get_active_subscription(self, obj):
        """Retourne l'abonnement actif"""
        subscription = obj.get_active_subscription()
        if subscription:
            return SubscriptionSerializer(subscription).data
        return None

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_price = serializers.DecimalField(source='plan.price', max_digits=10, decimal_places=2, read_only=True)
    client_company = serializers.CharField(source='client.company_name', read_only=True)
    is_active_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = '__all__'
    
    def get_is_active_status(self, obj):
        """Retourne le statut actif réel"""
        return obj.is_active()

class PaymentSerializer(serializers.ModelSerializer):
    subscription_plan = serializers.CharField(source='subscription.plan.name', read_only=True)
    client_company = serializers.CharField(source='subscription.client.company_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['created_at']

class OdooInstanceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    client_company = serializers.CharField(source='client.company_name', read_only=True)
    subscription_plan = serializers.CharField(source='subscription.plan.name', read_only=True)
    
    class Meta:
        model = OdooInstance
        fields = '__all__'
        read_only_fields = ['client', 'subscription', 'status', 'db_password', 'port', 'db_name', 'admin_password', 'container_name', 'created_at', 'updated_at']

class DeploymentLogSerializer(serializers.ModelSerializer):
    instance_name = serializers.CharField(source='instance.name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeploymentLog
        fields = '__all__'
        read_only_fields = ['timestamp']
