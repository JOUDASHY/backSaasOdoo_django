"""
Stripe Checkout and Webhook views.
Uses STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET from environment.
"""
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Plan, Subscription, Payment

logger = logging.getLogger(__name__)


def get_stripe():
    """Lazy import stripe to avoid import error if not installed."""
    import stripe
    return stripe


class CreateStripeCheckoutSessionView(APIView):
    """Create a Stripe Checkout Session for a subscription payment."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe_secret = getattr(settings, "STRIPE_SECRET_KEY", None)
        if not stripe_secret:
            return Response(
                {"detail": "Stripe is not configured (STRIPE_SECRET_KEY missing)."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        subscription_id = request.data.get("subscription_id")
        amount = request.data.get("amount")

        if not subscription_id or amount is None:
            return Response(
                {"detail": "subscription_id and amount are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount_decimal = Decimal(str(amount))
        except Exception:
            return Response(
                {"detail": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if amount_decimal <= 0:
            return Response(
                {"detail": "Amount must be positive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not hasattr(user, "client_profile"):
            return Response(
                {"detail": "User has no client profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            subscription = Subscription.objects.get(
                pk=subscription_id,
                client=user.client_profile,
                status="PENDING",
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "Subscription not found or not pending."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Create Payment record (PENDING, STRIPE) before redirecting to Stripe
        payment = Payment.objects.create(
            subscription=subscription,
            amount=amount_decimal,
            method="STRIPE",
            status="PENDING",
        )

        frontend_base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        success_url = f"{frontend_base}/dashboard/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_base}/dashboard/payment?subscription={subscription_id}"

        stripe = get_stripe()
        stripe.api_key = stripe_secret

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "eur",
                            "product_data": {
                                "name": f"Abonnement {subscription.plan.name}",
                                "description": f"Paiement pour le plan {subscription.plan.name}",
                            },
                            "unit_amount": int(amount_decimal * 100),  # cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    "payment_id": str(payment.id),
                    "subscription_id": str(subscription.id),
                },
            )
        except Exception as e:
            logger.exception("Stripe Checkout Session create failed: %s", e)
            payment.delete()
            return Response(
                {"detail": "Stripe error: " + str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"url": session.url, "session_id": session.id})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_POST, name="dispatch")
class StripeWebhookView(View):
    """Handle Stripe webhooks (checkout.session.completed) to mark payment as PAID."""

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

        if not webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not set; skipping signature verification")
            # In dev you may not have a webhook secret; still try to process
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                return HttpResponse(status=400)
        else:
            stripe = get_stripe()
            stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY")
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError:
                return HttpResponse(status=400)
            except Exception as e:
                logger.warning("Stripe webhook signature verification failed: %s", e)
                return HttpResponse(status=400)

        if event.get("type") == "checkout.session.completed":
            session = event.get("data", {}).get("object", {})
            payment_id = session.get("metadata", {}).get("payment_id")
            if not payment_id:
                logger.warning("checkout.session.completed missing metadata.payment_id")
                return HttpResponse(status=200)

            try:
                payment = Payment.objects.get(pk=int(payment_id))
            except (Payment.DoesNotExist, ValueError):
                logger.warning("Payment id %s not found", payment_id)
                return HttpResponse(status=200)

            payment.status = "PAID"
            payment.transaction_id = session.get("id") or session.get("payment_intent")
            payment.save()  # Payment.save() will activate subscription

        return HttpResponse(status=200)
