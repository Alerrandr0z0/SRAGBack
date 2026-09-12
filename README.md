# SRAG Mossoró/RN — Backend

Sistema de vigilância epidemiológica municipal para Mossoró/RN, automatizando o processamento, higienização e disponibilização dos dados de Síndrome Respiratória Aguda Grave (SIVEP-Gripe).

## Stack

- **Linguagem & Runtime:** Python 3.14 (gerenciado via `uv`)
- **API Framework:** FastAPI, Uvicorn, Pydantic v2
- **ETL & Analytics:** DuckDB, Pandas, NumPy
- **Relatórios:** fpdf2 (PDFs dinâmicos)
- **Qualidade & Segurança:** Pyright (strict), Ruff, Bandit, Complexipy, pytest, pytest-cov (cobertura ~86%), pytest-benchmark, Hypothesis

## Toolchain (`Makefile`)

```bash
make setup              # Primeira instalação (uv + hooks)
make ingest             # ETL DuckDB → SQLite
make lint               # Ruff + Pyright (strict) + Complexipy (max 15)
make test               # Suíte de testes unitários e de integração + coverage (gate 80%)
make property-test      # Testes de propriedade com Hypothesis
make bench              # Benchmarks de performance (pytest-benchmark)
make fix                # Ruff auto-fix + auto-format
make security           # Bandit + Gitleaks + pip-audit
make start              # Sobe a API FastAPI em http://localhost:8001
```

## Estrutura do Projeto

```text
SRAGBack/
├── data/               # raw/ → processed/ (srag_mossoro.db) → geojson/
├── docs/               # Dicionário SIVEP e documentação de apoio
├── nginx/              # Configuração Nginx de produção
├── scripts/            # Scripts operacionais (ingest_data.py, smoke_test.sh, port_control.sh)
├── src/srag/           # Código-fonte principal
│   ├── api/            # Endpoints FastAPI, schemas Pydantic e controle de sessão/JWT
│   ├── data/           # Motor de analytics vetorizado, loader SIVEP, SQLite e DuckDB ETL
│   ├── reporting.py    # Gerador de relatórios PDF (FPDF2)
│   └── utils/          # Utilitários de semanas epidemiológicas
└── tests/              # Suíte de testes (unit, integration, performance, property)
```

## Endpoints Principais

- `GET /api/summary` — Resumo epidemiológico global
- `GET /api/trends` — Tendências históricas por semana epidemiológica
- `GET /api/territory_bootstrap` — Distribuição territorial e por zona urbana/rural
- `GET /api/citizen_bootstrap` — Perfis sociodemográficos (pirâmide etária, raça, escolaridade)
- `GET /api/vaccination_profile` — Resumo de vacinação COVID e Influenza
- `GET /api/laboratory_network` — Casos com diagnósticos laboratoriais
- `GET /api/virus` — Distribuição por agente etiológico
- `GET /api/clinical/*` — Pareto e marcadores clínicos
- `GET /api/manage/*` & `GET /api/ingest/*` — Gestão de usuários, quarentena e upload de planilhas (ADMIN)
- `GET /api/reports/*` — Geração de relatórios PDF em lote
