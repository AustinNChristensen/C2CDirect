-- Founder workflow: source freshness, explicit disposition, and real application follow-up.
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS posted_at timestamptz,
  ADD COLUMN IF NOT EXISTS last_source_seen_at timestamptz,
  ADD COLUMN IF NOT EXISTS hidden_at timestamptz,
  ADD COLUMN IF NOT EXISTS hidden_reason text,
  ADD COLUMN IF NOT EXISTS applied_at timestamptz,
  ADD COLUMN IF NOT EXISTS follow_up_at timestamptz,
  ADD COLUMN IF NOT EXISTS closed_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_jobs_tenant_freshness
  ON jobs(tenant_id,last_source_seen_at DESC NULLS LAST,posted_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant_follow_up
  ON jobs(tenant_id,follow_up_at) WHERE status IN ('submitted','interview');

UPDATE jobs SET
  last_source_seen_at = coalesce(last_source_seen_at,last_verified_at,updated_at,created_at),
  posted_at = coalesce(posted_at,created_at)
WHERE last_source_seen_at IS NULL OR posted_at IS NULL;
