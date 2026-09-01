CREATE TABLE job_decisions(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  outcome text NOT NULL CHECK(outcome IN('not_interested','denied')),
  reason_code text NOT NULL CHECK(reason_code IN(
    'c2c_not_accepted','rate_below_floor','skill_mismatch','location_mismatch',
    'seniority_mismatch','vendor_chain_concern','role_not_compelling','expired_or_filled',
    'denied_by_client','no_response','timing','other'
  )),
  notes text CHECK(notes IS NULL OR char_length(notes) <= 2000),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_job_decisions_tenant_job_created
  ON job_decisions(tenant_id,job_id,created_at DESC);
CREATE INDEX idx_job_decisions_tenant_training
  ON job_decisions(tenant_id,outcome,reason_code,created_at DESC);

ALTER TABLE job_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_decisions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_job_decisions ON job_decisions
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT ON job_decisions TO c2cdirect_app;
