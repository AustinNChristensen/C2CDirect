CREATE TABLE IF NOT EXISTS ai_connections(
  tenant_id uuid PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
  provider text NOT NULL CHECK(provider IN ('deterministic','openai_compatible')),
  base_url text NOT NULL DEFAULT '',
  model_name text NOT NULL DEFAULT 'local-rules',
  api_key_encrypted text,
  input_cost_per_million numeric(12,6) NOT NULL DEFAULT 0,
  output_cost_per_million numeric(12,6) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE ai_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_connections FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_ai_connections ON ai_connections;
CREATE POLICY tenant_ai_connections ON ai_connections
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT,UPDATE,DELETE ON ai_connections TO c2cdirect_app;
