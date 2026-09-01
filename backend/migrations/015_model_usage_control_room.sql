ALTER TABLE budget_reservations
  ADD COLUMN IF NOT EXISTS operation text NOT NULL DEFAULT 'screen_job',
  ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'deterministic',
  ADD COLUMN IF NOT EXISTS model text NOT NULL DEFAULT 'local-rules';

-- Older Core builds reserved estimated model spend without executing a provider.
-- Correct that simulated history so Control Room never presents it as real spend.
UPDATE budget_reservations
   SET actual_usd=0,input_tokens=0,output_tokens=0,
       provider='deterministic',model='local-rules'
 WHERE provider='deterministic' AND model='local-rules';

CREATE INDEX IF NOT EXISTS idx_budget_tenant_recent
  ON budget_reservations(tenant_id,created_at DESC);

GRANT SELECT, INSERT, UPDATE ON budget_reservations TO c2cdirect_app;
