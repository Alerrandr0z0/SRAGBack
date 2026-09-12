#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"

printf "[1/7] Verificando API em %s ...\n" "$API_BASE"
curl -sSf "$API_BASE/docs" >/dev/null
printf "OK: API acessivel.\n\n"

printf "[2/7] GET /summary (Visão Geral)\n"
curl -sSf "$API_BASE/summary" | head -c 200
printf "...\n\n"

printf "[3/7] GET /trends (Tendências)\n"
curl -sSf "$API_BASE/trends?last_n_weeks=26" | head -c 200
printf "...\n\n"

printf "[4/7] GET /citizen_bootstrap (Painel Cidadão / Perfil Materno)\n"
curl -sSf "$API_BASE/citizen_bootstrap" | head -c 200
printf "...\n\n"

printf "[5/7] GET /vaccination_profile (Perfil de Imunização)\n"
curl -sSf "$API_BASE/vaccination_profile" | head -c 200
printf "...\n\n"

printf "[6/7] GET /laboratory_network (Painel Vigilância)\n"
curl -sSf "$API_BASE/laboratory_network" | head -c 200
printf "...\n\n"

printf "[7/7] GET /territory_bootstrap (Território)\n"
curl -sSf "$API_BASE/territory_bootstrap?min_cases=1" | head -c 200
printf "...\n\n"

printf "Smoke test concluido com sucesso.\n"
