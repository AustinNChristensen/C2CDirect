CREATE OR REPLACE FUNCTION reserve_ai_budget(
  p_tenant uuid,
  p_date date,
  p_amount numeric,
  p_limit numeric
) RETURNS TABLE(id uuid, reserved_usd numeric)
LANGUAGE plpgsql
AS $$
DECLARE
  total numeric;
  new_id uuid;
BEGIN
  PERFORM pg_advisory_xact_lock(hashtext(p_tenant::text || p_date::text));
  SELECT coalesce(sum(coalesce(br.actual_usd, br.reserved_usd)), 0)
    INTO total
    FROM budget_reservations AS br
   WHERE br.tenant_id = p_tenant
     AND br.usage_date = p_date
     AND br.status IN ('reserved', 'reconciled');
  IF total + p_amount > p_limit THEN
    RETURN;
  END IF;
  INSERT INTO budget_reservations(tenant_id, usage_date, reserved_usd)
  VALUES(p_tenant, p_date, p_amount)
  RETURNING budget_reservations.id INTO new_id;
  RETURN QUERY SELECT new_id, p_amount;
END
$$;

GRANT EXECUTE ON FUNCTION reserve_ai_budget(uuid,date,numeric,numeric) TO c2cdirect_app;
