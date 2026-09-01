-- Make source health and application preparation auditable product state.
-- These records intentionally contain only explicit source facts and candidate-approved evidence.

CREATE TABLE source_sync_runs(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  target_slug text NOT NULL,
  adapter text NOT NULL,
  query text,
  status text NOT NULL CHECK(status IN ('running','succeeded','failed')),
  received_count int NOT NULL DEFAULT 0,
  selected_count int NOT NULL DEFAULT 0,
  created_count int NOT NULL DEFAULT 0,
  enriched_count int NOT NULL DEFAULT 0,
  error_code text,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz
);

CREATE INDEX idx_source_sync_runs_tenant_target ON source_sync_runs(tenant_id,target_slug,started_at DESC);

CREATE TABLE application_packages(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
  status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','approved','submitted','archived')),
  resume_evidence_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  role_evidence_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  gaps_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  verification_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  cover_note text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_application_packages_tenant_job ON application_packages(tenant_id,job_id,updated_at DESC);

ALTER TABLE source_sync_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_sync_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE application_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_packages FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_source_sync_runs ON source_sync_runs
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_application_packages ON application_packages
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT,UPDATE,DELETE ON source_sync_runs,application_packages TO c2cdirect_app;
