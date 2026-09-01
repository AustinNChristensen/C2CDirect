ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS auth_issuer text,
  ADD COLUMN IF NOT EXISTS external_tenant_id text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenants_external_identity
  ON tenants(auth_issuer, external_tenant_id)
  WHERE auth_issuer IS NOT NULL AND external_tenant_id IS NOT NULL;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE search_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE budget_reservations FORCE ROW LEVEL SECURITY;
