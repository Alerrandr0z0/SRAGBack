#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8001}"
VITE_PORT="${VITE_PORT:-5174}"

usage() {
  cat <<'EOF'
Uso:
  ./scripts/port_control.sh start  # sobe backend + frontend
  ./scripts/port_control.sh stop                  # encerra backend + frontend
  ./scripts/port_control.sh restart               # stop + start
  ./scripts/port_control.sh status                # mostra estado das portas

Variaveis opcionais:
  API_PORT=8001 VITE_PORT=5174 ./scripts/port_control.sh start
EOF
}

port_busy() {
  local port="$1"
  ss -ltn "( sport = :$port )" | tail -n +2 | grep -q .
}

show_port_hint() {
  local port="$1"
  printf "\nPorta %s ja esta em uso.\n" "$port"
  printf "Verifique com:\n"
  printf "  ss -ltnp '( sport = :%s )'\n" "$port"
  printf "\nOpcional: rode com outra porta:\n"
  printf "  API_PORT=8001 VITE_PORT=5174 ./scripts/port_control.sh start\n\n"
}

front_active_port() {
  printf "%s" "$VITE_PORT"
}

show_status() {
  local active_front
  active_front="$(front_active_port)"
  printf "\nEstado atual:\n"
  if port_busy "$API_PORT" || port_busy "$active_front"; then
    ss -ltnp "( sport = :$API_PORT or sport = :$active_front )"
  else
    printf "Nenhuma porta em uso (%s, %s).\n" "$API_PORT" "$active_front"
  fi
}

stop_by_port() {
  local port="$1"
  local label="$2"
  mapfile -t pids < <(ss -ltnp "( sport = :$port )" | awk -F'pid=' 'NR>1 && NF>1 {print $2}' | awk -F',' '{print $1}' | sort -u)

  if [[ ${#pids[@]} -eq 0 ]]; then
    printf "%s: nada em execucao na porta %s.\n" "$label" "$port"
    return
  fi

  printf "%s: encerrando PID(s) na porta %s -> %s\n" "$label" "$port" "${pids[*]}"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}

force_kill_port() {
  local port="$1"
  local label="$2"
  if port_busy "$port"; then
    printf "%s: porta %s ainda ocupada, forcando encerramento...\n" "$label" "$port"
    mapfile -t pids < <(ss -ltnp "( sport = :$port )" | awk -F'pid=' 'NR>1 && NF>1 {print $2}' | awk -F',' '{print $1}' | sort -u)
    for pid in "${pids[@]:-}"; do
      [[ -n "$pid" ]] && kill -9 "$pid" 2>/dev/null || true
    done
  fi
}

do_stop() {
  local active_front
  active_front="$(front_active_port)"

  stop_by_port "$API_PORT" "API"
  stop_by_port "$active_front" "Frontend"

  # Fallback for uvicorn reload parent process
  pkill -f "uvicorn srag.api.main:app" 2>/dev/null || true
  pkill -f "vite --host 0.0.0.0" 2>/dev/null || true

  sleep 1
  force_kill_port "$API_PORT" "API"
  force_kill_port "$active_front" "Frontend"
  sleep 1
  show_status
}

cleanup_start() {
  local code=$?
  trap - EXIT INT TERM
  if [[ -n "${API_PID:-}" ]] && kill -0 "$API_PID" 2>/dev/null; then
    kill "$API_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONT_PID:-}" ]] && kill -0 "$FRONT_PID" 2>/dev/null; then
    kill "$FRONT_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  exit "$code"
}

do_start() {
  local active_front
  active_front="$(front_active_port)"

  if port_busy "$API_PORT"; then
    show_port_hint "$API_PORT"
    exit 1
  fi
  if port_busy "$active_front"; then
    show_port_hint "$active_front"
    exit 1
  fi

  trap cleanup_start EXIT INT TERM

  printf "Iniciando backend em http://127.0.0.1:%s ...\n" "$API_PORT"
  (
    cd "$ROOT_DIR"
    export PYTHONPATH="$ROOT_DIR/src"
    uv run uvicorn srag.api.main:app --reload --host "$API_HOST" --port "$API_PORT"
  ) &
  API_PID=$!

  printf "Iniciando frontend em http://127.0.0.1:%s ...\n" "$VITE_PORT"
  (
    cd "$ROOT_DIR/../SRAGFront"
    npm run dev -- --host 0.0.0.0 --port "$VITE_PORT" --strictPort
  ) &
  FRONT_PID=$!

  printf "\nServicos em execucao:\n"
  printf -- "- API:      http://127.0.0.1:%s\n" "$API_PORT"
  printf -- "- Frontend: http://127.0.0.1:%s\n" "$active_front"
  printf "\nPressione Ctrl+C para encerrar tudo.\n"

  wait -n "$API_PID" "$FRONT_PID"
}

ACTION="${1:-}"
shift || true

case "$ACTION" in
  start)
    do_start
    ;;
  stop)
    do_stop
    ;;
  restart)
    do_stop
    do_start
    ;;
  status)
    show_status
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    printf "Acao invalida: %s\n" "$ACTION"
    usage
    exit 1
    ;;
esac
