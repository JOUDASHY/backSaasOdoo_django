from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from django.utils import timezone

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} ({self.user.username})"
    
    def get_active_subscription(self):
        """Retourne l'abonnement actif du client"""
        return self.subscriptions.filter(status='ACTIVE').first()
    
    def can_create_instance(self):
        """Vérifie si le client peut créer une nouvelle instance"""
        subscription = self.get_active_subscription()
        if not subscription:
            return False, "No active subscription found"
        
        plan = subscription.plan
        current_instances_count = self.instances.count()
        
        if current_instances_count >= plan.max_instances:
            return False, f"Maximum instances limit reached ({plan.max_instances})"
        
        return True, None

class Plan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_users = models.IntegerField(default=1, help_text="Maximum allowed users in Odoo")
    storage_limit_gb = models.IntegerField(default=10, help_text="Maximum storage in GB")
    max_instances = models.IntegerField(default=1, help_text="Maximum number of Odoo instances allowed")
    allowed_modules = models.JSONField(default=list, help_text="List of Technical Names of allowed modules")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.name
    
    def is_module_allowed(self, module_name):
        """Vérifie si un module est autorisé dans ce plan"""
        return module_name in self.allowed_modules

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
        ('EXPIRED', 'Expired'),
    ]
    
    BILLING_CYCLE_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    auto_renew = models.BooleanField(default=True, help_text="Auto-renew subscription when it expires")
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='MONTHLY')
    next_billing_date = models.DateField(null=True, blank=True, help_text="Next billing date for auto-renewal")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.client.company_name} - {self.plan.name} ({self.status})"
    
    def clean(self):
        """Validation des dates"""
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError("end_date must be after start_date")
    
    def is_active(self):
        """Vérifie si l'abonnement est actif"""
        if self.status != 'ACTIVE':
            return False
        if self.end_date and self.end_date < timezone.now().date():
            return False
        return True
    
    def check_expiration(self):
        """Vérifie et met à jour le statut si l'abonnement a expiré"""
        if self.status == 'ACTIVE' and self.end_date and self.end_date < timezone.now().date():
            self.status = 'EXPIRED'
            self.save()
            return True
        return False
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'status'],
                condition=models.Q(status='ACTIVE'),
                name='unique_active_subscription_per_client'
            )
        ]

class OdooInstance(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Created - Pending Deployment'),
        ('DEPLOYING', 'Deploying'),
        ('RUNNING', 'Running'),
        ('STOPPED', 'Stopped'),
        ('ERROR', 'Error'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='instances')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='instances')
    name = models.CharField(max_length=100, unique=True, help_text="Instance identifier (e.g. client1)")
    container_name = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="Docker container name (auto-generated if empty)")
    
    # Technical details
    db_name = models.CharField(max_length=100)
    db_password = models.CharField(max_length=100, blank=True)
    admin_password = models.CharField(max_length=100, blank=True)
    
    domain = models.CharField(max_length=255, unique=True)
    port = models.IntegerField(unique=True, help_text="Assigned internal port")
    odoo_version = models.CharField(max_length=20, default='18', help_text="Odoo version (e.g., 16, 17, 18)")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        """Validation de cohérence entre client et subscription"""
        if self.subscription and self.subscription.client != self.client:
            raise ValidationError("Subscription must belong to the same client")
    
    def save(self, *args, **kwargs):
        if not self.db_password:
            self.db_password = get_random_string(32)
        if not self.container_name:
            # Générer automatiquement le nom du conteneur si non fourni
            self.container_name = f"odoo_{self.name}"
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.status})"
    
    def start(self):
        """Démarre l'instance Odoo"""
        # Cette méthode sera implémentée dans les views/services
        pass
    
    def stop(self):
        """Arrête l'instance Odoo"""
        # Cette méthode sera implémentée dans les views/services
        pass
    
    def restart(self):
        """Redémarre l'instance Odoo"""
        # Cette méthode sera implémentée dans les views/services
        pass


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CREDIT_CARD', 'Credit Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('PAYPAL', 'PayPal'),
        ('STRIPE', 'Stripe'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=255, blank=True, null=True, help_text="External transaction ID")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} - {self.subscription.client.company_name} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']


class DeploymentLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('START', 'Start'),
        ('STOP', 'Stop'),
        ('RESTART', 'Restart'),
        ('DELETE', 'Delete'),
        ('UPDATE', 'Update'),
        ('BACKUP', 'Backup'),
        ('RESTORE', 'Restore'),
    ]
    
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('IN_PROGRESS', 'In Progress'),
    ]

    instance = models.ForeignKey(OdooInstance, on_delete=models.CASCADE, related_name='deployment_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, help_text="User who performed the action")
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_PROGRESS')
    details = models.JSONField(default=dict, help_text="Additional details about the deployment")
    error_message = models.TextField(blank=True, null=True, help_text="Error message if status is FAILED")
    duration_seconds = models.IntegerField(null=True, blank=True, help_text="Duration of the operation in seconds")

    def __str__(self):
        return f"{self.action} - {self.instance.name} ({self.status}) at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['instance', '-timestamp']),
            models.Index(fields=['status', '-timestamp']),
        ]