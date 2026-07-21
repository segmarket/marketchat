-- Emergência: Postgres em 192.168.1.30 sem slots ("too many clients already").
-- Rodar como superuser (postgres) no host do banco.

-- 1) Diagnóstico rápido
SELECT count(*) AS total,
       (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
       (SELECT setting::int FROM pg_settings WHERE name = 'superuser_reserved_connections') AS reserved
FROM pg_stat_activity;

SELECT coalesce(datname, '?') AS db, count(*)
FROM pg_stat_activity
GROUP BY 1
ORDER BY 2 DESC;

-- 2) Aumentar limite (ex.: 100 -> 200). Exige restart do Postgres.
-- ALTER SYSTEM SET max_connections = 200;
-- SELECT pg_reload_conf();  -- NÃO basta para max_connections; precisa restart:
-- sudo systemctl restart postgresql

-- 3) Reduzir pools JDBC dos outros apps (sonar / tracker*) é preferível a subir sem
--    revisar shared_buffers / RAM do host.
