from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import (
    ClientViewSet, UserMeView, RegisterView, GoogleLogin,
    PasswordResetRequestView, PasswordResetConfirmView
)
from billing.views import PlanViewSet, SubscriptionViewSet, PaymentViewSet
from billing.stripe_views import CreateStripeCheckoutSessionView, StripeWebhookView
from instances.views import OdooInstanceViewSet, DeploymentLogViewSet

router = DefaultRouter()
router.register(r"clients", ClientViewSet)
router.register(r"plans", PlanViewSet)
router.register(r"subscriptions", SubscriptionViewSet)
router.register(r"instances", OdooInstanceViewSet)
router.register(r"payments", PaymentViewSet)
router.register(r"deployment-logs", DeploymentLogViewSet, basename="deployment-logs")
router.register(r"me", UserMeView, basename="me")

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegisterView.as_view(), name="register"),
    path("auth/google/", GoogleLogin.as_view(), name="google_login"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("payments/create-stripe-checkout/", CreateStripeCheckoutSessionView.as_view(), name="create_stripe_checkout"),
    path("billing/stripe-webhook/", StripeWebhookView.as_view(), name="stripe_webhook"),
    path("", include(router.urls)),
]

