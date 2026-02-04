import os
import subprocess
import threading
from datetime import datetime

from django.utils.crypto import get_random_string
from django.conf import settings
from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from instances.models import OdooInstance, DeploymentLog
from instances.serializers import OdooInstanceSerializer, DeploymentLogSerializer


class OdooInstanceViewSet(viewsets.ModelViewSet):
    queryset = OdooInstance.objects.all()
    serializer_class = OdooInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = OdooInstance.objects.none()
        if user.is_staff:
            qs = OdooInstance.objects.all()
        elif hasattr(user, "client_profile"):
            qs = OdooInstance.objects.filter(client=user.client_profile)
        
        # Sync status for the queryset
        self.sync_docker_status(qs)
        return qs

    def sync_docker_status(self, queryset):
        """Check real Docker status and update DB if needed."""
        try:
            # Get list of running container names
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=2
            )
            running_containers = result.stdout.splitlines()

            for instance in queryset:
                # We only sync instances that are supposed to be RUNNING or STOPPED
                # (We don't touch DEPLOYING or CREATED because they are in transition)
                if instance.status in ["RUNNING", "STOPPED", "ERROR"]:
                    is_running = instance.container_name in running_containers
                    new_status = "RUNNING" if is_running else "STOPPED"
                    
                    if instance.status != new_status:
                        instance.status = new_status
                        instance.save()
        except Exception as e:
            print(f"Error syncing docker status: {e}")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        instance = self.get_object()
        try:
            script_path = str(settings.BASE_DIR / "deployer" / "manage-instances.sh")
            subprocess.run(["bash", script_path, "start", instance.name], check=True)
            instance.status = "RUNNING"
            instance.save()
            return Response({"status": "Instance started"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        instance = self.get_object()
        try:
            script_path = str(settings.BASE_DIR / "deployer" / "manage-instances.sh")
            subprocess.run(["bash", script_path, "stop", instance.name], check=True)
            instance.status = "STOPPED"
            instance.save()
            return Response({"status": "Instance stopped"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def restart(self, request, pk=None):
        instance = self.get_object()
        try:
            script_path = str(settings.BASE_DIR / "deployer" / "manage-instances.sh")
            subprocess.run(["bash", script_path, "restart", instance.name], check=True)
            instance.status = "RUNNING"
            instance.save()
            return Response({"status": "Instance restarted"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        instance = self.get_object()
        try:
            script_path = str(settings.BASE_DIR / "deployer" / "manage-instances.sh")
            # In manage-instances.sh it's 'remove'
            subprocess.run(["bash", script_path, "remove", instance.name], check=True)
            instance.delete()
            return Response({"status": "Instance removed"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        user = self.request.user

        if not hasattr(user, "client_profile"):
            raise permissions.exceptions.PermissionDenied("User has no Client profile")

        client = user.client_profile
        admin_password = get_random_string(12)

        # Règles métier: abonnement actif + limites de plan
        subscription = client.subscriptions.filter(status="ACTIVE").first()
        if not subscription:
            raise permissions.exceptions.ParseError("No active subscription found for this client")

        if client.instances.count() >= subscription.plan.max_instances:
            raise permissions.exceptions.ParseError(
                f"Maximum instances limit reached ({subscription.plan.max_instances})"
            )

        last_instance = OdooInstance.objects.order_by("-port").first()
        next_port = 8070 if not last_instance else last_instance.port + 1

        instance_name = serializer.validated_data["name"]
        instance = serializer.save(
            client=client,
            subscription=subscription,
            port=next_port,
            db_name=instance_name,
            container_name=f"odoo_{instance_name}",
            admin_password=admin_password,
            odoo_version=subscription.plan.odoo_version,
            status="CREATED",
        )

        DeploymentLog.objects.create(
            instance=instance,
            user=user,
            action="CREATE",
            status="IN_PROGRESS",
            details={"name": instance_name, "domain": instance.domain, "port": next_port},
        )

        thread = threading.Thread(target=self.deploy_instance, args=(instance,))
        thread.start()

    def deploy_instance(self, instance: OdooInstance):
        start_time = datetime.now()
        log = DeploymentLog.objects.filter(instance=instance, action="CREATE", status="IN_PROGRESS").first()

        try:
            instance.status = "DEPLOYING"
            instance.save()

            script_path = str(settings.BASE_DIR / "deployer" / "deploy-instance.sh")
            modules = ",".join(instance.subscription.plan.allowed_modules) or "base"
            cmd = [
                "bash",
                script_path,
                instance.name, 
                instance.domain, 
                str(instance.port), 
                instance.odoo_version,
                instance.admin_password,
                modules
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)

            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                instance.status = "RUNNING"
                if log:
                    log.status = "SUCCESS"
                    log.duration_seconds = int(duration)
                    log.details.update({"output": result.stdout})
                    log.save()
            else:
                instance.status = "ERROR"
                if log:
                    log.status = "FAILED"
                    log.error_message = result.stderr
                    log.duration_seconds = int(duration)
                    log.save()
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            instance.status = "ERROR"
            if log:
                log.status = "FAILED"
                log.error_message = str(e)
                log.duration_seconds = int(duration)
                log.save()
        finally:
            instance.save()


class DeploymentLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DeploymentLog.objects.all()
    serializer_class = DeploymentLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        instance_id = self.request.query_params.get("instance")

        qs = DeploymentLog.objects.all()
        if instance_id:
            qs = qs.filter(instance_id=instance_id)

        if user.is_staff:
            return qs
        if hasattr(user, "client_profile"):
            return qs.filter(instance__client=user.client_profile)
        return DeploymentLog.objects.none()

