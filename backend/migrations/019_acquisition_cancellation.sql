ALTER TABLE acquisition_runs
  ADD COLUMN IF NOT EXISTS cancel_requested boolean NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION claim_acquisition_run()
RETURNS TABLE(run_id uuid,run_tenant_id uuid,run_user_id uuid,run_kind text,run_request jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE selected acquisition_runs%ROWTYPE;
BEGIN
  SELECT * INTO selected FROM public.acquisition_runs
   WHERE user_id IS NOT NULL AND cancel_requested=false AND
         (status='queued'
          OR (status='running' AND started_at < now()-interval '1 hour' AND attempts < 3))
   ORDER BY created_at
   FOR UPDATE SKIP LOCKED LIMIT 1;
  IF selected.id IS NULL THEN RETURN; END IF;
  UPDATE public.acquisition_runs SET status='running',attempts=attempts+1,
         started_at=now(),updated_at=now(),error_code=NULL WHERE id=selected.id;
  RETURN QUERY SELECT selected.id,selected.tenant_id,selected.user_id,selected.kind,selected.request_json;
END $$;

REVOKE ALL ON FUNCTION claim_acquisition_run() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION claim_acquisition_run() TO c2cdirect_app;
