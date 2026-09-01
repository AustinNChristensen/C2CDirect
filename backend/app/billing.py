import hashlib

import stripe
from fastapi import HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

from .database import tenant_connection


class BillingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_solo: str = ""
    stripe_price_pro: str = ""


settings = BillingSettings()
stripe.api_key = settings.stripe_secret_key


async def process_stripe_webhook(payload: bytes, signature: str):
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise HTTPException(400, "Invalid Stripe webhook") from exc
    obj = event["data"]["object"]
    customer = obj.get("customer")
    tenant_id = (obj.get("metadata") or {}).get("tenant_id")
    if not tenant_id or not customer:
        return {"ignored": True}
    fingerprint = hashlib.sha256(payload).hexdigest()
    async with tenant_connection(tenant_id) as conn:
        inserted = await conn.fetchval(
            "INSERT INTO webhook_events(id,tenant_id,provider,event_type,payload_sha256) VALUES($1,$2,'stripe',$3,$4) ON CONFLICT DO NOTHING RETURNING id",
            event["id"],
            tenant_id,
            event["type"],
            fingerprint,
        )
        if not inserted:
            return {"duplicate": True}
        if event["type"] in ("customer.subscription.created", "customer.subscription.updated"):
            price = ((obj.get("items") or {}).get("data") or [{}])[0].get("price", {}).get("id")
            plan = (
                "pro"
                if price == settings.stripe_price_pro
                else "solo"
                if price == settings.stripe_price_solo
                else "community"
            )
            await conn.execute(
                "UPDATE tenants SET plan=$1,stripe_customer_id=$2 WHERE id=$3",
                plan,
                customer,
                tenant_id,
            )
        elif event["type"] == "customer.subscription.deleted":
            await conn.execute("UPDATE tenants SET plan='community' WHERE id=$1", tenant_id)
    return {"processed": True}
