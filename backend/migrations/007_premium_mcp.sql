CREATE TABLE IF NOT EXISTS mcp_audit_events(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  request_id text NOT NULL,
  tool_name text NOT NULL,
  scopes text[] NOT NULL DEFAULT '{}',
  status text NOT NULL DEFAULT 'started',
  error_code text,
  latency_ms int,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  UNIQUE(tenant_id, request_id)
);

CREATE INDEX IF NOT EXISTS idx_mcp_audit_tenant_created
  ON mcp_audit_events(tenant_id, created_at DESC);

ALTER TABLE mcp_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE mcp_audit_events FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_mcp_audit ON mcp_audit_events;
CREATE POLICY tenant_mcp_audit ON mcp_audit_events
  USING(tenant_id::text = current_setting('app.tenant_id', true))
  WITH CHECK(tenant_id::text = current_setting('app.tenant_id', true));

CREATE OR REPLACE FUNCTION reserve_mcp_call(
  p_tenant uuid,
  p_user uuid,
  p_request_id text,
  p_tool_name text,
  p_scopes text[],
  p_daily_limit int
) RETURNS uuid
LANGUAGE plpgsql
AS $$
DECLARE
  used_today int;
  audit_id uuid;
BEGIN
  IF p_daily_limit <= 0 THEN
    RETURN NULL;
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext('mcp|' || p_tenant::text || '|' || current_date::text));
  SELECT count(*) INTO used_today
    FROM mcp_audit_events
   WHERE tenant_id = p_tenant AND created_at >= current_date;
  IF used_today >= p_daily_limit THEN
    RETURN NULL;
  END IF;
  INSERT INTO mcp_audit_events(tenant_id,user_id,request_id,tool_name,scopes)
  VALUES(p_tenant,p_user,p_request_id,p_tool_name,p_scopes)
  RETURNING id INTO audit_id;
  RETURN audit_id;
END
$$;

REVOKE ALL ON FUNCTION reserve_mcp_call(uuid,uuid,text,text,text[],int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION reserve_mcp_call(uuid,uuid,text,text,text[],int) TO c2cdirect_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON mcp_audit_events TO c2cdirect_app;
