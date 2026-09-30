#!/usr/bin/env bash
# Roda testes num container descartável no host de QA (padrão: tests/test_qa_billing_delinquency.py).
#
# Uso (no servidor): bash run-qa-billing-tests.sh /tmp/marketchat-qa-tests-<stamp>.tar.gz [testes...]
#   Ex.: ... tests/test_billing_delinquency_cycle.py tests/test_subscription_enforcement.py
#   TEST_TIMEOUT=300 amplia o limite de 150 s.
#
# - Imagem própria (marketchat-qa-tests:<stamp>) a partir de docker/Dockerfile.backend
#   + requirements-dev.txt; não reutiliza nem sobrescreve as imagens do Compose de staging.
# - config.settings.test (SQLite em memória, cache locmem), sem --env-file e com
#   --network none: sem .env.staging/.env.production, banco, Redis ou integrações.
# - 4 GB de RAM sem swap, 2 CPUs, 150 s de limite; faulthandler a cada 25 s e SIGABRT no
#   limite global (o faulthandler imprime a pilha de todas as threads antes de encerrar).
# - O container é removido ao final; saída, amostras de memória e código de retorno ficam
#   em /tmp/marketchat-qa-tests-<stamp>.{pytest,stats}.log.

set -uo pipefail

TARBALL="${1:?uso: $0 /tmp/marketchat-qa-tests-<stamp>.tar.gz}"
STAMP="$(basename "$TARBALL" .tar.gz)"
STAMP="${STAMP#marketchat-qa-tests-}"
WORKDIR="/tmp/marketchat-qa-tests-$STAMP"
IMAGE="marketchat-qa-tests:$STAMP"
NAME="marketchat-qa-tests-$STAMP"
LOG="$WORKDIR.pytest.log"
STATS="$WORKDIR.stats.log"
TESTS=("${@:2}")
[[ ${#TESTS[@]} -eq 0 ]] && TESTS=("tests/test_qa_billing_delinquency.py")
TEST_FILES="$(printf '%s\n' "${TESTS[@]}" | sed 's/::.*//' | sort -u | tr '\n' ' ')"
TEST_TIMEOUT="${TEST_TIMEOUT:-150}"
SAMPLER=""

cleanup() {
  [[ -n "$SAMPLER" ]] && kill "$SAMPLER" 2>/dev/null
  docker rm -f "$NAME" >/dev/null 2>&1
  return 0
}
trap cleanup EXIT

echo "== Pacote: $TARBALL"
rm -rf "$WORKDIR" && mkdir -p "$WORKDIR" || exit 2
tar -xzf "$TARBALL" -C "$WORKDIR" || exit 2
REAL_ENV_FILES=".env .env.test .env.development .env.staging .env.production"
for env_file in $REAL_ENV_FILES; do
  [[ -e "$WORKDIR/$env_file" ]] && FOUND_ENV=1
done
if [[ -n "${FOUND_ENV:-}" ]]; then
  echo "ERRO: arquivo .env real dentro do pacote; abortado." >&2
  exit 2
fi

echo "== Build da imagem de testes: $IMAGE"
docker build -f "$WORKDIR/docker/Dockerfile.backend" -t "$IMAGE-base" "$WORKDIR" || exit 3
docker build -t "$IMAGE" - <<EOF || exit 3
FROM $IMAGE-base
RUN pip install -r requirements-dev.txt
ENTRYPOINT []
EOF

echo "== Conferência da imagem (antes de executar)"
docker run --rm --network none --entrypoint sh "$IMAGE" -c "
  set -e
  for f in $TEST_FILES; do
    if [ ! -f \"\$f\" ]; then echo \"ERRO: \$f ausente\"; exit 1; fi
    echo \"ok: \$f\"
  done
  test -f tests/conftest.py && test -f tests/factories.py && echo 'ok: tests/conftest.py e tests/factories.py'
  python -m pytest --version
  python -c 'import pytest_django, factory; from importlib.metadata import version as v; print(\"ok: pytest-django\", v(\"pytest-django\"), \"factory-boy\", v(\"factory-boy\"))'
  for f in $REAL_ENV_FILES; do
    if [ -e \"\$f\" ]; then echo \"ERRO: \$f dentro da imagem\"; exit 1; fi
  done
  echo 'ok: nenhum .env real na imagem ($REAL_ENV_FILES)'
" || { echo "ERRO: imagem sem os testes ou sem pytest; nada foi executado." >&2; exit 4; }

echo "== Execução (limites: 4g RAM sem swap, 2 CPUs, ${TEST_TIMEOUT} s): ${TESTS[*]}" | tee "$LOG"
(
  for _ in $(seq 1 $((TEST_TIMEOUT / 5 + 10))); do
    docker stats --no-stream --format '{{.Name}} mem={{.MemUsage}} cpu={{.CPUPerc}} pids={{.PIDs}}' "$NAME" 2>/dev/null \
      | sed "s/^/$(date +%T) /"
    sleep 5
  done
) >"$STATS" &
SAMPLER=$!

timeout --kill-after=20 $((TEST_TIMEOUT + 50)) docker run --name "$NAME" \
  --network none \
  --memory 4g --memory-swap 4g --cpus 2 --pids-limit 512 \
  -e DJANGO_SETTINGS_MODULE=config.settings.test \
  -e PYTHONFAULTHANDLER=1 \
  --entrypoint timeout \
  "$IMAGE" \
  --signal=ABRT --kill-after=15 "$TEST_TIMEOUT" \
  python -X faulthandler -m pytest "${TESTS[@]}" \
    -p no:cacheprovider -o addopts="" -o faulthandler_timeout=25 -x -vv \
  2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}

docker inspect -f 'container: exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} erro={{.State.Error}}' \
  "$NAME" 2>&1 | tee -a "$LOG"
echo "código de retorno: $RC (0 = ok; 1 = falha de teste; 124 = limite de ${TEST_TIMEOUT} s; 137 = SIGKILL/OOM)" | tee -a "$LOG"
echo "log: $LOG"
echo "memória/CPU a cada 5 s: $STATS"
echo "limpeza opcional: docker image rm $IMAGE $IMAGE-base && rm -rf $WORKDIR"
exit "$RC"
