CREATE TABLE providers(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  slug text NOT NULL,
  name text NOT NULL,
  provider_type text NOT NULL CHECK(provider_type IN(
    'end_client','employer_ats','prime_vendor','msp_vms','staffing_vendor',
    'aggregator','marketplace','email_channel','public_agency','manual'
  )),
  intake_method text NOT NULL,
  canonical_domain text,
  terms_status text NOT NULL DEFAULT 'needs_review' CHECK(terms_status IN(
    'approved','needs_review','restricted','disabled'
  )),
  baseline_authority smallint NOT NULL DEFAULT 50 CHECK(baseline_authority BETWEEN 0 AND 100),
  typical_layer_min smallint NOT NULL DEFAULT 0 CHECK(typical_layer_min >= 0),
  typical_layer_max smallint NOT NULL DEFAULT 0 CHECK(typical_layer_max >= typical_layer_min),
  direct_source_capable boolean NOT NULL DEFAULT false,
  c2c_reliability numeric(5,4),
  rate_transparency numeric(5,4),
  evidence_json jsonb NOT NULL DEFAULT '[]',
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,slug)
);

CREATE TABLE provider_domains(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  domain text NOT NULL,
  verification_status text NOT NULL DEFAULT 'unverified' CHECK(verification_status IN(
    'unverified','verified','rejected'
  )),
  evidence_json jsonb NOT NULL DEFAULT '[]',
  verified_at timestamptz,
  UNIQUE(tenant_id,domain)
);

ALTER TABLE jobs
  ADD COLUMN canonical_key text,
  ADD COLUMN canonical_provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  ADD COLUMN source_authority smallint NOT NULL DEFAULT 0 CHECK(source_authority BETWEEN 0 AND 100),
  ADD COLUMN provenance_confidence numeric(5,4) NOT NULL DEFAULT 0 CHECK(provenance_confidence BETWEEN 0 AND 1),
  ADD COLUMN provenance_completeness numeric(5,4) NOT NULL DEFAULT 0 CHECK(provenance_completeness BETWEEN 0 AND 1),
  ADD COLUMN quality_lane text NOT NULL DEFAULT 'needs_verification' CHECK(quality_lane IN(
    'direct_prime','needs_verification','low_quality'
  )),
  ADD COLUMN vendor_layer_min smallint NOT NULL DEFAULT 0 CHECK(vendor_layer_min >= 0),
  ADD COLUMN vendor_layer_max smallint NOT NULL DEFAULT 0 CHECK(vendor_layer_max >= vendor_layer_min),
  ADD COLUMN end_client_name text,
  ADD COLUMN canonical_url text,
  ADD COLUMN last_verified_at timestamptz;

CREATE UNIQUE INDEX idx_jobs_tenant_canonical_key
  ON jobs(tenant_id,canonical_key) WHERE canonical_key IS NOT NULL;
CREATE INDEX idx_jobs_tenant_quality
  ON jobs(tenant_id,quality_lane,source_authority DESC,fit_score DESC,created_at DESC);

CREATE TABLE job_observations(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE RESTRICT,
  canonical_job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  provider_job_id text,
  requisition_id text,
  observed_url text,
  canonical_url_candidate text,
  title text NOT NULL,
  company text NOT NULL,
  end_client_name text,
  location text,
  description_sha256 text NOT NULL,
  source_payload_sha256 text NOT NULL,
  engagement_type text,
  rate_min int,
  rate_max int,
  rate_unit text NOT NULL DEFAULT 'hour',
  currency text NOT NULL DEFAULT 'USD',
  recruiter_email_domain text,
  parser_version text NOT NULL,
  confidence numeric(5,4) NOT NULL DEFAULT 0 CHECK(confidence BETWEEN 0 AND 1),
  evidence_json jsonb NOT NULL DEFAULT '[]',
  warnings text[] NOT NULL DEFAULT '{}',
  first_observed_at timestamptz NOT NULL DEFAULT now(),
  last_observed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,provider_id,source_payload_sha256)
);

CREATE INDEX idx_observations_tenant_canonical
  ON job_observations(tenant_id,canonical_job_id,last_observed_at DESC);
CREATE INDEX idx_observations_tenant_requisition
  ON job_observations(tenant_id,requisition_id) WHERE requisition_id IS NOT NULL;

CREATE TABLE provenance_edges(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  canonical_job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  from_provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  to_provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  from_label text,
  to_label text,
  relationship text NOT NULL CHECK(relationship IN(
    'owns_requisition','manages_program','prime_vendor','subvendor','recruits_for',
    'published_by','observed_via'
  )),
  confidence numeric(5,4) NOT NULL CHECK(confidence BETWEEN 0 AND 1),
  evidence_json jsonb NOT NULL DEFAULT '[]',
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  CHECK(from_provider_id IS NOT NULL OR from_label IS NOT NULL),
  CHECK(to_provider_id IS NOT NULL OR to_label IS NOT NULL)
);

CREATE INDEX idx_provenance_edges_tenant_job
  ON provenance_edges(tenant_id,canonical_job_id);

CREATE TABLE provider_quality_metrics(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_id uuid NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  metric_date date NOT NULL,
  observations int NOT NULL DEFAULT 0,
  canonical_source_rate numeric(5,4),
  c2c_confirmed_rate numeric(5,4),
  rate_transparency_rate numeric(5,4),
  duplicate_rate numeric(5,4),
  stale_rate numeric(5,4),
  recruiter_response_rate numeric(5,4),
  submission_to_interview_rate numeric(5,4),
  misrepresentation_count int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,provider_id,metric_date)
);

ALTER TABLE providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE providers FORCE ROW LEVEL SECURITY;
ALTER TABLE provider_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_domains FORCE ROW LEVEL SECURITY;
ALTER TABLE job_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE provenance_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE provenance_edges FORCE ROW LEVEL SECURITY;
ALTER TABLE provider_quality_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_quality_metrics FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_providers ON providers
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_provider_domains ON provider_domains
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_job_observations ON job_observations
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_provenance_edges ON provenance_edges
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_provider_metrics ON provider_quality_metrics
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT,UPDATE,DELETE ON providers,provider_domains,job_observations,
  provenance_edges,provider_quality_metrics TO c2cdirect_app;
