#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
mkdir -p "${RUN_DIR}"

LIGHTNING_SSH_HOST="${LIGHTNING_SSH_HOST:-s_01kj8andtgxz010b21w69n9ncs@ssh.lightning.ai}"
LIGHTNING_WORKDIR="${LIGHTNING_WORKDIR:-/teamspace/studios/this_studio/indic-tts/backend}"
REMOTE_WORKER_PORT="${REMOTE_WORKER_PORT:-8000}"
TUNNEL_PORT="${TUNNEL_PORT:-9001}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_REMOTE_URL="http://127.0.0.1:${TUNNEL_PORT}"

is_listening() {
  lsof -iTCP:"$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

wait_for_http() {
  local url="$1"
  local retries="${2:-40}"
  local delay="${3:-1}"

  for _ in $(seq 1 "${retries}"); do
    if curl -fsS --max-time 5 "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay}"
  done
  return 1
}

ensure_lightning_worker() {
  echo "[1/4] Ensuring Lightning self-hosted worker is running..."
  local cmd
  cmd="set -e; export PATH=/system/conda/miniconda3/bin:\$PATH; cd '${LIGHTNING_WORKDIR}'; \
if curl -fsS --max-time 5 http://127.0.0.1:${REMOTE_WORKER_PORT}/health >/dev/null 2>&1; then \
  echo 'remote_worker=already_running'; \
else \
  nohup /system/conda/miniconda3/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${REMOTE_WORKER_PORT} >/tmp/tts_worker.log 2>&1 < /dev/null & \
  sleep 2; \
  echo 'remote_worker=started'; \
fi; \
curl -fsS --max-time 15 http://127.0.0.1:${REMOTE_WORKER_PORT}/health >/dev/null; \
echo 'remote_worker=healthy'"

  ssh -o StrictHostKeyChecking=accept-new "${LIGHTNING_SSH_HOST}" "${cmd}"
}

ensure_tunnel() {
  echo "[2/4] Ensuring SSH tunnel localhost:${TUNNEL_PORT} -> Lightning:${REMOTE_WORKER_PORT}..."
  if is_listening "${TUNNEL_PORT}" && curl -fsS --max-time 5 "http://127.0.0.1:${TUNNEL_PORT}/health" >/dev/null 2>&1; then
    echo "tunnel=already_healthy"
    return
  fi

  pkill -f "ssh -f -N -L ${TUNNEL_PORT}:127.0.0.1:${REMOTE_WORKER_PORT} ${LIGHTNING_SSH_HOST}" >/dev/null 2>&1 || true
  ssh -f -N -L "${TUNNEL_PORT}:127.0.0.1:${REMOTE_WORKER_PORT}" "${LIGHTNING_SSH_HOST}"

  if ! wait_for_http "http://127.0.0.1:${TUNNEL_PORT}/health" 30 1; then
    echo "Failed to establish healthy SSH tunnel on port ${TUNNEL_PORT}" >&2
    exit 1
  fi
  echo "tunnel=healthy"
}

ensure_local_backend() {
  echo "[3/4] Ensuring local orchestrator backend on :${BACKEND_PORT}..."
  if is_listening "${BACKEND_PORT}" && curl -fsS --max-time 5 "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    echo "backend=already_healthy"
    return
  fi

  local py_bin
  if [[ -x "${ROOT_DIR}/backend/.venv/bin/python" ]]; then
    py_bin="${ROOT_DIR}/backend/.venv/bin/python"
  else
    py_bin="python3"
  fi

  (
    cd "${ROOT_DIR}/backend"
    nohup env \
      BACKEND_ROLE=orchestrator \
      REMOTE_SELF_HOSTED_URL="${BACKEND_REMOTE_URL}" \
      REMOTE_SELF_HOSTED_TIMEOUT_SECONDS=120 \
      "${py_bin}" -m uvicorn app.main:app --host 0.0.0.0 --port "${BACKEND_PORT}" \
      >"${RUN_DIR}/backend.log" 2>&1 < /dev/null &
    echo $! > "${RUN_DIR}/backend.pid"
  )

  if ! wait_for_http "http://127.0.0.1:${BACKEND_PORT}/health" 40 1; then
    echo "Local backend failed to become healthy. Check ${RUN_DIR}/backend.log" >&2
    exit 1
  fi
  echo "backend=healthy"
}

ensure_frontend() {
  echo "[4/4] Ensuring frontend on :${FRONTEND_PORT}..."
  if is_listening "${FRONTEND_PORT}" && curl -fsS --max-time 5 "http://127.0.0.1:${FRONTEND_PORT}" >/dev/null 2>&1; then
    echo "frontend=already_healthy"
    return
  fi

  (
    cd "${ROOT_DIR}/frontend"
    nohup npm run dev -- --host 0.0.0.0 --port "${FRONTEND_PORT}" \
      >"${RUN_DIR}/frontend.log" 2>&1 < /dev/null &
    echo $! > "${RUN_DIR}/frontend.pid"
  )

  if ! wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" 60 1; then
    echo "Frontend failed to become healthy. Check ${RUN_DIR}/frontend.log" >&2
    exit 1
  fi
  echo "frontend=healthy"
}

ensure_lightning_worker
ensure_tunnel
ensure_local_backend
ensure_frontend

cat <<EOF

Stack is ready.
- Frontend: http://127.0.0.1:${FRONTEND_PORT}
- Local orchestrator backend: http://127.0.0.1:${BACKEND_PORT}
- Remote self-hosted via tunnel: ${BACKEND_REMOTE_URL}

Logs:
- ${RUN_DIR}/backend.log
- ${RUN_DIR}/frontend.log
EOF
