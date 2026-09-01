ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_metadata ON tenants;
CREATE POLICY tenant_metadata ON tenants
  USING(id::text = current_setting('app.tenant_id', true))
  WITH CHECK(id::text = current_setting('app.tenant_id', true));

DROP POLICY IF EXISTS tenant_webhook_events ON webhook_events;
CREATE POLICY tenant_webhook_events ON webhook_events
  USING(tenant_id::text = current_setting('app.tenant_id', true))
  WITH CHECK(tenant_id::text = current_setting('app.tenant_id', true));

CREATE OR REPLACE FUNCTION provision_identity(
  p_issuer text,
  p_external_tenant_id text,
  p_external_subject text,
  p_email text,
  p_role text
) RETURNS TABLE(internal_tenant_id uuid, internal_user_id uuid)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
  resolved_tenant_id uuid;
  resolved_user_id uuid;
  resolved_role text;
BEGIN
  IF p_issuer = '' OR p_external_tenant_id = '' OR p_external_subject = '' THEN
    RAISE EXCEPTION 'identity claims must not be empty';
  END IF;
  resolved_role := CASE WHEN p_role = 'owner' THEN 'owner' ELSE 'member' END;
  INSERT INTO public.tenants(name, auth_issuer, external_tenant_id)
  VALUES('Tenant ' || p_external_tenant_id, p_issuer, p_external_tenant_id)
  ON CONFLICT(auth_issuer, external_tenant_id)
    WHERE auth_issuer IS NOT NULL AND external_tenant_id IS NOT NULL
  DO UPDATE SET name = public.tenants.name
  RETURNING id INTO resolved_tenant_id;

  PERFORM set_config('app.tenant_id', resolved_tenant_id::text, true);
  INSERT INTO public.users(tenant_id, external_subject, email, role)
  VALUES(resolved_tenant_id, p_external_subject, p_email, resolved_role)
  ON CONFLICT(tenant_id, external_subject) DO UPDATE
    SET email = excluded.email, role = excluded.role, updated_at = now()
  RETURNING id INTO resolved_user_id;

  RETURN QUERY SELECT resolved_tenant_id, resolved_user_id;
END
$$;

REVOKE ALL ON FUNCTION provision_identity(text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provision_identity(text,text,text,text,text) TO c2cdirect_app;
REVOKE INSERT ON tenants FROM c2cdirect_app;
