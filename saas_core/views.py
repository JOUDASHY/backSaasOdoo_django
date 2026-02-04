from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Client, Plan, Subscription, OdooInstance, Payment, DeploymentLog
from .serializers import (
    ClientSerializer, PlanSerializer, SubscriptionSerializer, 
    OdooInstanceSerializer, PaymentSerializer, DeploymentLogSerializer
)
import subprocess
import threading
import os
from django.utils import timezone
from datetime import datetime
from django.conf import settings

class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Admin sees all, Client sees only self
        user = self.request.user
        if user.is_staff:
            return Client.objects.all()
        return Client.objects.filter(user=user)

class PlanViewSet(viewsets.ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
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
        if hasattr(user, 'client_profile'):
            return Subscription.objects.filter(client=user.client_profile)
        return Subscription.objects.none()

class OdooInstanceViewSet(viewsets.ModelViewSet):
    queryset = OdooInstance.objects.all()
    serializer_class = OdooInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return OdooInstance.objects.all()
        if hasattr(user, 'client_profile'):
            return OdooInstance.objects.filter(client=user.client_profile)
        return OdooInstance.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        
        # Security: Ensure user has a Client profile
        if not hasattr(user, 'client_profile'):
            raise permissions.exceptions.PermissionDenied("User has no Client profile")
        
        client = user.client_profile
        
        # Vérifier si le client peut créer une instance
        can_create, error_message = client.can_create_instance()
        if not can_create:
            raise permissions.exceptions.ParseError(error_message)
        
        # Auto-detect active subscription
        subscription = client.get_active_subscription()
        if not subscription:
            raise permissions.exceptions.ParseError("No active subscription found for this client")

        # Auto-assign next available port
        last_instance = OdooInstance.objects.order_by('-port').first()
        next_port = 8070 if not last_instance else last_instance.port + 1
        
        instance_name = serializer.validated_data['name']
        container_name = f"odoo_{instance_name}"
        
        instance = serializer.save(
            client=client,
            subscription=subscription,
            port=next_port,
            db_name=instance_name,
            container_name=container_name,
            status='CREATED'
        )
        
        # Créer un log de déploiement
        DeploymentLog.objects.create(
            instance=instance,
            user=user,
            action='CREATE',
            status='IN_PROGRESS',
            details={'name': instance_name, 'domain': instance.domain, 'port': next_port}
        )
        
        # Trigger background deployment
        thread = threading.Thread(target=self.deploy_instance, args=(instance, user))
        thread.start()

    def deploy_instance(self, instance, user=None):
        start_time = datetime.now()
        log = DeploymentLog.objects.filter(instance=instance, action='CREATE', status='IN_PROGRESS').first()
        
        try:
            # Marquer comme en cours de déploiement
            instance.status = 'DEPLOYING'
            instance.save()
            
            if log:
                log.status = 'IN_PROGRESS'
                log.save()
            
            # Script path
            script_path = str(settings.BASE_DIR / "deployer" / "deploy-instance.sh")
            
            # Run: ./deploy-instance.sh <name> <domain> <port>
            cmd = [
                "bash",
                script_path,
                instance.name,
                instance.domain,
                str(instance.port)
            ]
            
            print(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if result.returncode == 0:
                print("Deployment Success")
                instance.status = 'RUNNING'
                if log:
                    log.status = 'SUCCESS'
                    log.duration_seconds = int(duration)
                    log.details.update({'output': result.stdout})
                    log.save()
            else:
                print(f"Deployment Failed: {result.stderr}")
                instance.status = 'ERROR'
                if log:
                    log.status = 'FAILED'
                    log.error_message = result.stderr
                    log.duration_seconds = int(duration)
                    log.save()
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            print(f"Exception during deployment: {error_msg}")
            instance.status = 'ERROR'
            if log:
                log.status = 'FAILED'
                log.error_message = error_msg
                log.duration_seconds = int(duration)
                log.save()
        finally:
            instance.save()

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        if hasattr(user, 'client_profile'):
            # Retourner les paiements des abonnements du client
            return Payment.objects.filter(subscription__client=user.client_profile)
        return Payment.objects.none()

class DeploymentLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeploymentLog.objects.all()
    serializer_class = DeploymentLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        instance_id = self.request.query_params.get('instance', None)
        
        queryset = DeploymentLog.objects.all()
        
        if instance_id:
            queryset = queryset.filter(instance_id=instance_id)
        
        if user.is_staff:
            return queryset
        
        if hasattr(user, 'client_profile'):
            # Retourner les logs des instances du client
            return queryset.filter(instance__client=user.client_profile)
        
        return DeploymentLog.objects.none()

class UserMeView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        role = 'ADMIN' if request.user.is_staff else ('CLIENT' if hasattr(request.user, 'client_profile') else None)
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "is_staff": request.user.is_staff,
            "role": role
        })
