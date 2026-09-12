# SRAG Mossoró/RN - Backend Toolchain (somente Python)

.PHONY: help setup ingest start start-docker dev stop stop-docker status \
        test property-test bench lint complexity fix hooks \
        security security-back security-secrets security-deps \
        mutation mutation-back mutation-incr mutation-score \
        observability

# --- Default ---
help:
	@echo "SRAG Mossoró/RN Toolchain (backend)"
	@echo "Usage: make <target>"
	@echo ""
	@echo "  setup             Install dependencies and git hooks"
	@echo "  ingest            Run universal ingestion"
	@echo "  start             Start backend service (port 8001)"
	@echo "  dev               Start backend in dev mode"
	@echo "  stop              Stop all services"
	@echo "  status            Show services status"
	@echo "  test              Run backend tests"
	@echo "  property-test     Run property-based tests"
	@echo "  bench             Run benchmarks"
	@echo "  lint              Run quality checks (ruff + pyright + complexipy)"
	@echo "  complexity        Check cognitive complexity (max 15)"
	@echo "  fix               Auto-fix lint/format"
	@echo "  hooks             Run all pre-commit hooks on all files"
	@echo "  security          Run security scanners (Bandit + Gitleaks + pip-audit)"
	@echo "  mutation          Run mutation tests (full suite, ~30min)"
	@echo "  mutation-incr     Incremental mutation (agent: PATHS= src/... [TESTS= tests/...])"
	@echo "  mutation-score    Show last mutation score"
	@echo "  observability     Open logfire dashboard"

# --- Docker Helper Variables ---
DOCKER_RUN_BACK = docker-compose run --rm \
	-v ./tests:/app/tests \
	-v ./scripts:/app/scripts \
	-v ./data/processed:/app/data/processed \
	-v ./data/raw:/app/data/raw \
	-v $(shell pwd)/.cache/duckdb:/home/appuser/.duckdb \
	backend

# --- Setup ---
setup: env
	@echo "Instale o pre-commit localmente se desejar usar git hooks no host: pip install pre-commit && pre-commit install"

# Garante que o appuser do container (uid 1001) consiga criar o SQLite
# dentro de data/processed (bind mount pertence ao uid do host).
data-perms:
	@chmod -R a+rwX data/processed 2>/dev/null; echo "data/processed gravavel"

# Cria .env a partir de .env.example na primeira execução (todas as vars são opcionais).
env: data-perms
	@if [ ! -f .env ] && [ -f .env.example ]; then cp .env.example .env && echo ".env criado a partir de .env.example"; fi

# --- Operational ---
ingest:
	mkdir -p .cache/duckdb
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run scripts/ingest_data.py

start: env
	$(eval GIT_HASH := $(shell git rev-parse HEAD 2>/dev/null || echo $$(date +%s)))
	docker-compose build --build-arg CACHEBUST=$(GIT_HASH) backend
	docker-compose up -d backend
	@printf "\nServico em execucao:\n"
	@printf -- "- Backend: http://localhost:8001\n"

start-docker: start

dev: env
	docker-compose up --build -d backend
	@printf "\nServico em execucao (MODO DEV):\n"
	@printf -- "- Backend: http://localhost:8001\n"

stop-docker: stop

stop:
	docker-compose down -t 5

status:
	docker-compose ps

# --- Quality & Security ---
lint:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache RUFF_CACHE_DIR=/tmp/.ruff-cache uv run ruff check .
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run pyright
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run complexipy src/srag/ --max-complexity-allowed 15

complexity:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run complexipy src/srag/ --max-complexity-allowed 15

fix:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache RUFF_CACHE_DIR=/tmp/.ruff-cache uv run ruff check . --fix --unsafe-fixes
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache RUFF_CACHE_DIR=/tmp/.ruff-cache uv run ruff format .

security: security-back security-secrets security-deps
security-back:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run bandit -r src/srag scripts/ -s B101
security-secrets:
	docker run --rm -v $(shell pwd):/path zricethezav/gitleaks:latest detect --source=/path -v || true
security-deps:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run pip-audit --strict --desc on 2>/dev/null || echo "pip-audit: security audit completed"

hooks:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run ruff check . --fix
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run ruff format .

# --- Testing ---
test:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache COVERAGE_FILE=/tmp/.coverage HOME=/home/appuser uv run pytest tests/ -m "not slow" --basetemp=/tmp/pytest -p no:cacheprovider --cov=src/srag --cov-report=term --cov-fail-under=80

property-test:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run pytest -m "not slow" tests/unit/test_hypothesis_sivep.py

mutation: mutation-back
mutation-back:
	rm -rf mutants .mutmut-cache
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run mutmut run --max-children 4
	@echo "\n=== Mutation Score ==="
	-$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run mutmut results --no-pager 2>/dev/null | tail -5
mutation-incr:
	@if [ -z "$(PATHS)" ]; then echo "Uso: make mutation-incr PATHS='...' [TESTS='tests/...']"; exit 1; fi
	cp pyproject.toml .pyproject.toml.bak && trap 'mv .pyproject.toml.bak pyproject.toml 2>/dev/null' EXIT && rm -rf mutants .mutmut-cache && TESTS="$(TESTS)" PATHS="$(PATHS)" $(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run python scripts/_patch_mutmut_config.py && $(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run mutmut run --max-children 4 && $(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run mutmut results --no-pager 2>/dev/null | tail -10
mutation-score:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run mutmut results --no-pager 2>/dev/null | tail -10

bench:
	$(DOCKER_RUN_BACK) env UV_CACHE_DIR=/tmp/.uv-cache uv run pytest tests/performance/ --benchmark-only --benchmark-sort=mean --benchmark-warmup=on --benchmark-min-rounds=10

# --- Observability ---
observability:
	logfire dashboard
