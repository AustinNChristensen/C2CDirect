ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS contract_duration text,
  ADD COLUMN IF NOT EXISTS engagement_type text;
