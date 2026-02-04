from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from billing.models import Plan, Subscription, Payment
from billing.serializers import PlanSerializer, SubscriptionSerializer, PaymentSerializer


class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class SubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Subscription.objects.all()
        if hasattr(user, "client_profile"):
            return Subscription.objects.filter(client=user.client_profile)
        return Subscription.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "client_profile"):
            from rest_framework import exceptions
            raise exceptions.PermissionDenied("User has no Client profile")
        
        # Suspend previous active subscriptions if any (to respect the unique constraint or business logic)
        Subscription.objects.filter(client=user.client_profile, status="ACTIVE").update(status="SUSPENDED")
        # Also suspend pending subscriptions
        Subscription.objects.filter(client=user.client_profile, status="PENDING").update(status="SUSPENDED")
        
        # Create subscription with PENDING status (will be activated when payment is confirmed)
        serializer.save(client=user.client_profile, status="PENDING")


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        if hasattr(user, "client_profile"):
            return Payment.objects.filter(subscription__client=user.client_profile)
        return Payment.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not hasattr(user, "client_profile"):
            from rest_framework import exceptions
            raise exceptions.PermissionDenied("User has no Client profile")
        
        # Get the subscription from the request data
        subscription_id = serializer.validated_data.get("subscription")
        if not subscription_id:
            from rest_framework import exceptions
            raise exceptions.ValidationError("Subscription is required")
        
        # Verify the subscription belongs to the client
        subscription = subscription_id
        if subscription.client != user.client_profile:
            from rest_framework import exceptions
            raise exceptions.PermissionDenied("Subscription does not belong to this client")
        
        # Set default method to MANUAL if not provided
        if not serializer.validated_data.get("method"):
            serializer.validated_data["method"] = "MANUAL"
        
        serializer.save()

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def validate_payment(self, request, pk=None):
        """Admin action to validate a payment (mark as PAID)"""
        payment = self.get_object()
        payment.status = "PAID"
        payment.save()  # This will trigger subscription activation via the model's save method
        return Response({"status": "Payment validated", "payment_id": payment.id}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject_payment(self, request, pk=None):
        """Admin action to reject a payment (mark as FAILED)"""
        payment = self.get_object()
        payment.status = "FAILED"
        payment.save()
        return Response({"status": "Payment rejected", "payment_id": payment.id}, status=status.HTTP_200_OK)

