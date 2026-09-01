DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'c2cdirect_app') THEN
    CREATE ROLE c2cdirect_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
$$;

DO $$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO c2cdirect_app', current_database());
END
$$;
GRANT USAGE ON SCHEMA public TO c2cdirect_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO c2cdirect_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO c2cdirect_app;
GRANT EXECUTE ON FUNCTION reserve_ai_budget(uuid,date,numeric,numeric) TO c2cdirect_app;
GRANT EXECUTE ON FUNCTION reconcile_ai_budget(uuid,uuid,numeric,int,int) TO c2cdirect_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO c2cdirect_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO c2cdirect_app;
