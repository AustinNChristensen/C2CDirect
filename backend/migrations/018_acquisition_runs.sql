CREATE TABLE IF NOT EXISTS acquisition_runs(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  kind text NOT NULL CHECK(kind IN('public_sources','web_scout','email_sync','import')),
  status text NOT NULL DEFAULT 'queued' CHECK(status IN('queued','running','completed','failed','cancelled')),
  request_json jsonb NOT NULL DEFAULT '{}',
  result_json jsonb,
  error_code text,
  attempts smallint NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_acquisition_runs_tenant_created
  ON acquisition_runs(tenant_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_acquisition_runs_queue
  ON acquisition_runs(status,created_at) WHERE status IN('queued','running');

ALTER TABLE acquisition_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE acquisition_runs FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_acquisition_runs ON acquisition_runs
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

CREATE OR REPLACE FUNCTION claim_acquisition_run()
RETURNS TABLE(run_id uuid,run_tenant_id uuid,run_user_id uuid,run_kind text,run_request jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE selected acquisition_runs%ROWTYPE;
BEGIN
  SELECT * INTO selected FROM public.acquisition_runs
   WHERE status='queued'
      OR (status='running' AND started_at < now()-interval '1 hour' AND attempts < 3)
   ORDER BY created_at
   FOR UPDATE SKIP LOCKED LIMIT 1;
  IF selected.id IS NULL THEN RETURN; END IF;
  UPDATE public.acquisition_runs SET status='running',attempts=attempts+1,
         started_at=now(),updated_at=now(),error_code=NULL WHERE id=selected.id;
  RETURN QUERY SELECT selected.id,selected.tenant_id,selected.user_id,selected.kind,selected.request_json;
END $$;

REVOKE ALL ON FUNCTION claim_acquisition_run() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION claim_acquisition_run() TO c2cdirect_app;
GRANT SELECT,INSERT,UPDATE,DELETE ON acquisition_runs TO c2cdirect_app;
