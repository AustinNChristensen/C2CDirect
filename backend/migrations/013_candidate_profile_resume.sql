ALTER TABLE search_profiles
  ADD COLUMN IF NOT EXISTS resume_file_name text,
  ADD COLUMN IF NOT EXISTS resume_content_type text,
  ADD COLUMN IF NOT EXISTS resume_size_bytes integer,
  ADD COLUMN IF NOT EXISTS resume_bytes bytea,
  ADD COLUMN IF NOT EXISTS resume_uploaded_at timestamptz;

CREATE UNIQUE INDEX IF NOT EXISTS idx_search_profiles_tenant_user
  ON search_profiles(tenant_id,user_id) WHERE user_id IS NOT NULL;
