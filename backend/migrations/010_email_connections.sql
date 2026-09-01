CREATE TABLE email_connections(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider text NOT NULL CHECK(provider IN('gmail','microsoft')),
  mailbox_address text,
  encrypted_access_token text NOT NULL,
  encrypted_refresh_token text,
  token_expires_at timestamptz,
  scopes text[] NOT NULL DEFAULT '{}',
  sync_cursor text,
  status text NOT NULL DEFAULT 'active' CHECK(status IN('active','reauthorize','disabled')),
  last_synced_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,user_id,provider)
);

CREATE TABLE email_message_receipts(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  connection_id uuid NOT NULL REFERENCES email_connections(id) ON DELETE CASCADE,
  provider_message_id text NOT NULL,
  internet_message_id text,
  sender_address text,
  subject text,
  received_at timestamptz,
  content_sha256 text NOT NULL,
  canonical_job_id uuid REFERENCES jobs(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'received' CHECK(status IN('received','ingested','ignored','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,connection_id,provider_message_id)
);

ALTER TABLE email_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_connections FORCE ROW LEVEL SECURITY;
ALTER TABLE email_message_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_message_receipts FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_email_connections ON email_connections
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));
CREATE POLICY tenant_email_receipts ON email_message_receipts
  USING(tenant_id::text=current_setting('app.tenant_id',true))
  WITH CHECK(tenant_id::text=current_setting('app.tenant_id',true));

GRANT SELECT,INSERT,UPDATE,DELETE ON email_connections,email_message_receipts TO c2cdirect_app;
