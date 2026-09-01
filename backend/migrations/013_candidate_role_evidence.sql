-- Bidirectional evidence index. Tenant RLS remains the trust boundary.
CREATE TABLE candidate_profiles(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL,
  headline text NOT NULL,
  profile_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,user_id,name)
);

CREATE TABLE candidate_evidence(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  candidate_id uuid NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
  source_ref text NOT NULL,
  kind text NOT NULL CHECK(kind IN ('experience','project','skill','summary')),
  heading text NOT NULL,
  body text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', heading || ' ' || body)) STORED,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(candidate_id,source_ref)
);

CREATE TABLE job_evidence(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  citation text NOT NULL,
  section text NOT NULL,
  body text NOT NULL,
  metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', body)) STORED,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(job_id,citation)
);

CREATE INDEX idx_candidate_evidence_tenant_candidate ON candidate_evidence(tenant_id,candidate_id);
CREATE INDEX idx_candidate_evidence_search ON candidate_evidence USING gin(search_vector);
CREATE INDEX idx_job_evidence_tenant_job ON job_evidence(tenant_id,job_id);
CREATE INDEX idx_job_evidence_search ON job_evidence USING gin(search_vector);

ALTER TABLE candidate_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE candidate_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_evidence FORCE ROW LEVEL SECURITY;
ALTER TABLE job_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_evidence FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_candidate_profiles ON candidate_profiles USING(tenant_id::text=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_candidate_evidence ON candidate_evidence USING(tenant_id::text=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_job_evidence ON job_evidence USING(tenant_id::text=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
GRANT SELECT,INSERT,UPDATE,DELETE ON candidate_profiles,candidate_evidence,job_evidence TO c2cdirect_app;
