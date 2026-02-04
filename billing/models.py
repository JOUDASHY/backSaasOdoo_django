from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import Client


class Plan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_users = models.IntegerField(default=1, help_text="Maximum allowed users in Odoo")
    storage_limit_gb = models.IntegerField(default=10, help_text="Maximum storage in GB")
    max_instances = models.IntegerField(default=1, help_text="Maximum number of Odoo instances allowed")
    allowed_modules = models.JSONField(default=list, help_text="List of Technical Names of allowed modules")
    odoo_version = models.CharField(max_length=10, default="18", help_text="Version d'Odoo pour ce plan (ex: 16, 17, 18)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("EXPIRED", "Expired"),
    ]

    BILLING_CYCLE_CHOICES = [
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    auto_renew = models.BooleanField(default=True, help_text="Auto-renew subscription when it expires")
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default="MONTHLY")
    next_billing_date = models.DateField(null=True, blank=True, help_text="Next billing date for auto-renewal")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.client.company_name} - {self.plan.name} ({self.status})"

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("end_date must be after start_date")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client", "status"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_subscription_per_client",
            ),
            models.UniqueConstraint(
                fields=["client", "status"],
                condition=models.Q(status="PENDING"),
                name="unique_pending_subscription_per_client",
            )
        ]


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("MANUAL", "Manual Payment"),
        ("CREDIT_CARD", "Credit Card"),
        ("BANK_TRANSFER", "Bank Transfer"),
        ("PAYPAL", "PayPal"),
        ("STRIPE", "Stripe"),
    ]

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="MANUAL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    transaction_id = models.CharField(max_length=255, blank=True, null=True, help_text="External transaction ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Activate subscription when payment is marked as PAID"""
        is_new = self.pk is None
        old_status = None
        
        if not is_new:
            try:
                old_payment = Payment.objects.get(pk=self.pk)
                old_status = old_payment.status
            except Payment.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

        # Activate subscription when payment status changes to PAID
        if not is_new and old_status != "PAID" and self.status == "PAID":
            # Recalculate total paid for this subscription
            from django.db.models import Sum  # local import to avoid circulars at module load

            agg = self.subscription.payments.filter(status="PAID").aggregate(total=Sum("amount"))
            total_paid = agg["total"] or 0
            required_amount = self.subscription.plan.price or 0

            # Only activate if the total paid covers at least the plan price
            if total_paid < required_amount:
                # Still underpaid: keep subscription in its current status (typically PENDING)
                return

            # Suspend other active subscriptions for this client
            Subscription.objects.filter(
                client=self.subscription.client,
                status="ACTIVE"
            ).exclude(pk=self.subscription.pk).update(status="SUSPENDED")

            # Activate the subscription
            self.subscription.status = "ACTIVE"
            self.subscription.save()

    def __str__(self):
        return f"Payment {self.amount} - {self.subscription.client.company_name} ({self.status})"

