CREATE TABLE recruiter_contacts(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  provider_id uuid REFERENCES providers(id) ON DELETE SET NULL,
  name text NOT NULL,
  email text,
  company text,
  relationship_stage text NOT NULL DEFAULT 'target' CHECK(relationship_stage IN(
    'target','connected','active','paused','avoid'
  )),
  source text NOT NULL DEFAULT 'manual',
  notes text,
  last_contacted_at timestamptz,
  next_follow_up_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_recruiter_contacts_tenant_email
  ON recruiter_contacts(tenant_id,lower(email)) WHERE email IS NOT NULL;
CREATE INDEX idx_recruiter_contacts_follow_up
  ON recruiter_contacts(tenant_id,next_follow_up_at) WHERE relationship_stage NOT IN ('paused','avoid');

CREATE TABLE job_contacts(
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  job_id uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  contact_id uuid NOT NULL REFERENCES recruiter_contacts(id) ON DELETE CASCADE,
  contact_role text NOT NULL DEFAULT 'recruiter',
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(tenant_id,job_id,contact_id)
);

ALTER TABLE recruiter_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE recruiter_contacts FORCE ROW LEVEL SECURITY;
ALTER TABLE job_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_contacts FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_recruiter_contacts ON recruiter_contacts
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_job_contacts ON job_contacts
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
GRANT SELECT,INSERT,UPDATE,DELETE ON recruiter_contacts,job_contacts TO c2cdirect_app;
