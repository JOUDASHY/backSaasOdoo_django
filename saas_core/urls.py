from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, PlanViewSet, SubscriptionViewSet, 
    OdooInstanceViewSet, PaymentViewSet, DeploymentLogViewSet, UserMeView
)

router = DefaultRouter()
router.register(r'clients', ClientViewSet)
router.register(r'plans', PlanViewSet)
router.register(r'subscriptions', SubscriptionViewSet)
router.register(r'instances', OdooInstanceViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'deployment-logs', DeploymentLogViewSet, basename='deployment-logs')
router.register(r'me', UserMeView, basename='me')

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
