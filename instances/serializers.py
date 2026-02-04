from rest_framework import serializers

from instances.models import OdooInstance, DeploymentLog


class OdooInstanceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    client_company = serializers.CharField(source="client.company_name", read_only=True)
    subscription_plan = serializers.CharField(source="subscription.plan.name", read_only=True)

    class Meta:
        model = OdooInstance
        fields = "__all__"
        read_only_fields = [
            "client",
            "subscription",
            "status",
            "db_password",
            "port",
            "db_name",
            "container_name",
            "odoo_version",
            "created_at",
            "updated_at",
        ]


class DeploymentLogSerializer(serializers.ModelSerializer):
    instance_name = serializers.CharField(source="instance.name", read_only=True)
    user_username = serializers.CharField(source="user.username", read_only=True, allow_null=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DeploymentLog
        fields = "__all__"
        read_only_fields = ["timestamp"]

