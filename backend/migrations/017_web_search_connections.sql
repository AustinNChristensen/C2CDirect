CREATE TABLE IF NOT EXISTS web_search_connections(
  tenant_id uuid PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
  provider text NOT NULL CHECK(provider IN ('disabled','searxng','tavily','brave')),
  base_url text NOT NULL DEFAULT '',
  api_key_encrypted text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE web_search_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE web_search_connections FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_web_search_connections ON web_search_connections;
CREATE POLICY tenant_web_search_connections ON web_search_connections
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT,UPDATE,DELETE ON web_search_connections TO c2cdirect_app;
