-- App/worker database role provisioning (run once per environment by an admin).
-- The runtime role must be NOSUPERUSER and NOBYPASSRLS so forced RLS always
-- applies (CLAUDE.md rules 1-2). Set the password out-of-band from the approved
-- secrets backend (never commit it).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
    CREATE ROLE app_role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  ELSE
    ALTER ROLE app_role NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END
$$;
