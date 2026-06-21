"""Billing surface: mock by default, Stripe **test mode** only — never real charges."""

import logging

from app.config import Settings, get_settings
from app.schemas.usage import BillingStatusResponse, CheckoutSessionResponse

logger = logging.getLogger(__name__)


def _is_stripe_test(settings: Settings) -> bool:
    """True only when configured for Stripe test mode with a test secret key."""
    return (
        settings.billing_mode == "stripe_test"
        and settings.stripe_secret_key.startswith("sk_test")
    )


def get_billing_status(settings: Settings | None = None) -> BillingStatusResponse:
    settings = settings or get_settings()
    stripe_test = _is_stripe_test(settings)
    mode = "stripe_test" if stripe_test else "mock"
    return BillingStatusResponse(
        mode=mode,
        stripe_configured=stripe_test,
        customer_id=None,
        checkout_url=None,
        status=mode,
    )


def create_checkout_session(settings: Settings | None = None) -> CheckoutSessionResponse:
    """Create a checkout session.

    In mock mode (default, no keys) returns a non-functional placeholder URL — no
    Stripe call and no charge. In stripe_test mode (test key only) attempts a real
    *test-mode* Checkout Session; falls back to mock if the SDK/price is unavailable.
    """
    settings = settings or get_settings()

    if _is_stripe_test(settings) and settings.stripe_price_id:
        try:
            import stripe  # lazy import; optional dependency

            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="subscription",
                line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
                success_url=f"{settings.frontend_url}/usage?checkout=success",
                cancel_url=f"{settings.frontend_url}/usage?checkout=cancel",
            )
            return CheckoutSessionResponse(
                mode="stripe_test", checkout_url=session.url, session_id=session.id
            )
        except Exception:  # noqa: BLE001 - never block on Stripe/SDK issues
            logger.warning("Stripe test checkout unavailable; returning mock", exc_info=True)

    return CheckoutSessionResponse(
        mode="mock",
        checkout_url=f"{settings.frontend_url}/usage?checkout=mock",
        session_id=None,
    )
