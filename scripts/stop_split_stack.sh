#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"

LIGHTNING_SSH_HOST="${LIGHTNING_SSH_HOST:-s_01kj8andtgxz010b21w69n9ncs@ssh.lightning.ai}"
REMOTE_WORKER_PORT="${REMOTE_WORKER_PORT:-8000}"
TUNNEL_PORT="${TUNNEL_PORT:-9001}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
STOP_REMOTE_WORKER="${STOP_REMOTE_WORKER:-false}"

kill_by_pidfile() {
  local label="$1"
  local file="$2"
  if [[ -f "${file}" ]]; then
    local pid
    pid="$(cat "${file}")"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
      kill "${pid}" >/dev/null 2>&1 || true
      echo "${label}=stopped(pid:${pid})"
    fi
    rm -f "${file}"
  fi
}

kill_on_port() {
  local label="$1"
  local port="$2"
  local pids
  pids="$(lsof -ti tcp:${port} 2>/dev/null || true)"
  if [[ -n "${pids}" ]]; then
    kill ${pids} >/dev/null 2>&1 || true
    sleep 1
    pids="$(lsof -ti tcp:${port} 2>/dev/null || true)"
    if [[ -n "${pids}" ]]; then
      kill -9 ${pids} >/dev/null 2>&1 || true
    fi
    echo "${label}=stopped(port:${port})"
  else
    echo "${label}=not_running"
  fi
}

kill_by_pidfile "backend" "${RUN_DIR}/backend.pid"
kill_by_pidfile "frontend" "${RUN_DIR}/frontend.pid"

# Also ensure ports are clear even if processes were not started via pidfiles.
kill_on_port "frontend" "${FRONTEND_PORT}"
kill_on_port "backend" "${BACKEND_PORT}"

pkill -f "ssh -f -N -L ${TUNNEL_PORT}:127.0.0.1:${REMOTE_WORKER_PORT} ${LIGHTNING_SSH_HOST}" >/dev/null 2>&1 || true
kill_on_port "tunnel" "${TUNNEL_PORT}"

if [[ "${STOP_REMOTE_WORKER}" == "true" ]]; then
  echo "remote_worker=stopping"
  ssh -o StrictHostKeyChecking=accept-new "${LIGHTNING_SSH_HOST}" \
    "pkill -f 'uvicorn app.main:app --host 0.0.0.0 --port ${REMOTE_WORKER_PORT}' >/dev/null 2>&1 || true"
  echo "remote_worker=stopped"
else
  echo "remote_worker=left_running (set STOP_REMOTE_WORKER=true to stop it)"
fi

