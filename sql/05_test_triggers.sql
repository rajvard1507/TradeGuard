-- Run in a development database only. These are inspection queries, not destructive tests.
-- Check installed triggers:
SELECT event_object_table, trigger_name, action_timing, event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND event_object_table = 'TRADE'
ORDER BY trigger_name;

-- Check current configured risk rules:
SELECT rule_id, pattern_type, threshold_value, is_active
FROM "RISK_RULE"
ORDER BY rule_id;

-- After placing a test trade through the app, inspect its alerts:
-- SELECT * FROM "BEHAVIORAL_ALERT" ORDER BY detected_at DESC;
