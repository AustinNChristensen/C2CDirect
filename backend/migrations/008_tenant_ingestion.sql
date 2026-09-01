ALTER TABLE webhook_events
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'completed',
  ADD COLUMN IF NOT EXISTS response_json jsonb;

CREATE INDEX IF NOT EXISTS idx_webhook_tenant_provider_processed
  ON webhook_events(tenant_id,provider,processed_at DESC);
