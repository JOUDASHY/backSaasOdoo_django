from rest_framework import permissions, viewsets, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Client
from accounts.serializers import ClientSerializer, RegisterSerializer

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Client.objects.all()
        return Client.objects.filter(user=user)


class UserMeView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        role = "ADMIN" if request.user.is_staff else ("CLIENT" if hasattr(request.user, "client_profile") else None)
        return Response(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "is_staff": request.user.is_staff,
                "role": role,
            }
        )

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class GoogleLogin(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        from rest_framework_simplejwt.tokens import RefreshToken
        import requests
        
        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'error': 'access_token is required'}, status=400)
        
        try:
            # Verify the token with Google
            userinfo_response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if userinfo_response.status_code != 200:
                return Response({'error': 'Invalid Google token'}, status=401)
            
            userinfo = userinfo_response.json()
            email = userinfo.get('email')
            
            if not email:
                return Response({'error': 'Email not found in Google response'}, status=400)
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': userinfo.get('given_name', ''),
                    'last_name': userinfo.get('family_name', ''),
                }
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                }
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email requis'}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Pour des raisons de sécurité, on ne dit pas si l'email existe ou non
            return Response({'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.'}, status=200)
        
        # Générer le token
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        # Créer le lien de réinitialisation
        reset_link = f"http://localhost:3000/reset-password?uid={uid}&token={token}"
        
        # Créer le message HTML
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #7C2D12 0%, #991B1B 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9fafb; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 15px 30px; background: #7C2D12; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Réinitialisation de mot de passe</h1>
                </div>
                <div class="content">
                    <p>Bonjour,</p>
                    <p>Vous avez demandé à réinitialiser votre mot de passe pour votre compte <strong>Jounaid SaaS</strong>.</p>
                    <p>Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe :</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Réinitialiser mon mot de passe</a>
                    </div>
                    <p style="margin-top: 30px; font-size: 14px; color: #6b7280;">
                        Ou copiez ce lien dans votre navigateur :<br>
                        <code style="background: #e5e7eb; padding: 5px 10px; border-radius: 4px; display: inline-block; margin-top: 10px;">{reset_link}</code>
                    </p>
                    <p style="margin-top: 30px; padding: 15px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 4px;">
                        ⚠️ <strong>Important :</strong> Ce lien expire dans 24 heures. Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
                    </p>
                </div>
                <div class="footer">
                    <p>© 2026 Jounaid SaaS - Tous droits réservés</p>
                    <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Envoyer l'email
        try:
            from django.core.mail import EmailMultiAlternatives
            
            subject = '🔐 Réinitialisation de votre mot de passe - Jounaid SaaS'
            from_email = settings.DEFAULT_FROM_EMAIL
            to_email = [email]
            
            text_content = f'''
Bonjour,

Vous avez demandé à réinitialiser votre mot de passe pour votre compte Jounaid SaaS.

Cliquez sur ce lien pour créer un nouveau mot de passe :
{reset_link}

Ce lien expire dans 24 heures.

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

---
© 2026 Jounaid SaaS
            '''
            
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_message, "text/html")
            msg.send()
            
            print(f"\n✅ Email de réinitialisation envoyé à {email}")
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'envoi de l'email: {str(e)}")
            # En cas d'erreur, afficher le lien dans la console
            print(f"\n{'='*80}")
            print(f"LIEN DE RÉINITIALISATION DE MOT DE PASSE")
            print(f"{'='*80}")
            print(f"Email: {email}")
            print(f"Lien: {reset_link}")
            print(f"{'='*80}\n")
        
        return Response({'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.'}, status=200)

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not all([uid, token, new_password]):
            return Response({'error': 'Tous les champs sont requis'}, status=400)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Lien invalide'}, status=400)
        
        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Lien expiré ou invalide'}, status=400)
        
        # Réinitialiser le mot de passe
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Mot de passe réinitialisé avec succès'}, status=200)

@receiver(post_save, sender=User)
def create_client_profile(sender, instance, created, **kwargs):
    if created:
        Client.objects.get_or_create(
            user=instance,
            defaults={
                "company_name": instance.username if instance.username else f"Client {instance.id}"
            }
        )
