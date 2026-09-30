#!/bin/sh
# Agendador: roda check_subscriptions na subida e a cada CHECK_SUBSCRIPTIONS_INTERVAL_SECONDS.
# Não aplica migrações (isso é do backend); espera o banco estar migrado antes da 1ª execução.
set -u

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"
INTERVAL="${CHECK_SUBSCRIPTIONS_INTERVAL_SECONDS:-3600}"

trap 'echo "[scheduler] Encerrando."; exit 0' TERM INT

until python manage.py migrate --check >/dev/null 2>&1; do
  echo "[scheduler] Banco indisponível ou migrações pendentes; nova verificação em 15s..."
  sleep 15 &
  wait $!
done

echo "[scheduler] check_subscriptions a cada ${INTERVAL}s (DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE)"
while true; do
  echo "[scheduler] $(date -Iseconds) check_subscriptions"
  python manage.py check_subscriptions || echo "[scheduler] check_subscriptions terminou com código $?"
  sleep "$INTERVAL" &
  wait $!
done
