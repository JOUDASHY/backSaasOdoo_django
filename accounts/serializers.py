from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import Client


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff", "is_active", "date_joined", "role"]

    def get_role(self, obj):
        if obj.is_staff:
            return "ADMIN"
        if hasattr(obj, "client_profile"):
            return "CLIENT"
        return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "company_name", "phone"]

    def create(self, validated_data):
        company_name = validated_data.pop("company_name")
        phone = validated_data.pop("phone")
        password = validated_data.pop("password")

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()

        Client.objects.update_or_create(
            user=user, 
            defaults={"company_name": company_name, "phone": phone}
        )

        return user


class ClientSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Client
        fields = "__all__"

