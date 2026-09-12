from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from srag.data.database import (
    CASE_HASH_FIELDS,
    SragRecord,
    build_case_hash_sql,
    generate_case_hash,
    init_db,
    save_cases,
)

# Use a temporary file for testing instead of :memory: to avoid
# new engines creating new empty databases.
TEST_DB_FILE = Path("/tmp/test_srag_temp.db")
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture
def test_db_setup(monkeypatch):
    # Patch DB_URL and reset engine in database.py
    import srag.data.database

    monkeypatch.setattr(srag.data.database, "DB_URL", TEST_DB_URL)
    monkeypatch.setattr(srag.data.database, "_ingest_engine", None)

    # Initialize DB
    init_db()

    yield

    # Cleanup
    if srag.data.database._ingest_engine is not None:
        srag.data.database._ingest_engine.dispose()
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()


def test_generate_case_hash() -> None:
    record = {
        "DT_NOTIFIC": date(2024, 5, 1),
        "ID_MUNICIP": "2408003",
        "DT_SIN_PRI": date(2024, 4, 25),
        "NU_IDADE_N": 30,
        "CS_SEXO": "M",
        "ID_UNIDADE": "UPA",
    }
    h1 = generate_case_hash(record)
    h2 = generate_case_hash(record)
    assert h1 == h2
    assert len(h1) == 32


def test_case_hash_contract_fields() -> None:
    assert CASE_HASH_FIELDS == (
        "DT_NOTIFIC",
        "ID_MUNICIP",
        "DT_SIN_PRI",
        "NU_IDADE_N",
        "CS_SEXO",
    )


def test_build_case_hash_sql_uses_contract_fields() -> None:
    sql = build_case_hash_sql(lambda field: field)
    for field in CASE_HASH_FIELDS:
        assert f"CAST({field} AS VARCHAR)" in sql
    assert sql.startswith("md5(")
    assert sql.endswith(")")


def test_save_cases_deduplication(test_db_setup) -> None:
    cases = [
        {
            "DT_NOTIFIC": date(2024, 5, 1),
            "ID_MUNICIP": "2408003",
            "ID_MN_RESI": "2408003",
            "DT_SIN_PRI": date(2024, 4, 25),
            "NU_IDADE_N": 30,
            "CS_SEXO": "M",
            "ID_UNIDADE": "UPA",
            "CLASSI_FIN": 5,
        }
    ]

    # Save once
    added = save_cases(cases)
    assert added == 1

    # Save same case again
    added_again = save_cases(cases)
    assert added_again == 0


def test_save_cases_enrichment(test_db_setup) -> None:
    base_case = {
        "DT_NOTIFIC": date(2024, 5, 1),
        "ID_MUNICIP": "2408003",
        "ID_MN_RESI": "2408003",
        "DT_SIN_PRI": date(2024, 4, 25),
        "NU_IDADE_N": 30,
        "CS_SEXO": "M",
        "ID_UNIDADE": "UPA 1",
        "CLASSI_FIN": 5,
        "TP_IDADE": None,
    }

    save_cases([base_case])

    enriched_case = base_case.copy()
    enriched_case["ID_UNIDADE"] = "UPA 2"
    enriched_case["CLASSI_FIN"] = 4
    enriched_case["TP_IDADE"] = 3

    added = save_cases([enriched_case])
    assert added == 0

    # Verify in DB
    engine = create_engine(TEST_DB_URL)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        record = session.query(SragRecord).first()
        assert record.ID_UNIDADE == "UPA 1"
        assert record.CLASSI_FIN == 5
        assert record.TP_IDADE == 3


def test_save_cases_logs_summary(test_db_setup, caplog) -> None:
    import logging

    case = {
        "DT_NOTIFIC": date(2024, 5, 1),
        "ID_MUNICIP": "2408003",
        "ID_MN_RESI": "2408003",
        "DT_SIN_PRI": date(2024, 4, 25),
        "NU_IDADE_N": 30,
        "CS_SEXO": "M",
    }

    with caplog.at_level(logging.INFO):
        save_cases([case])

    log_messages = [record.message for record in caplog.records]
    assert any("save_cases summary:" in msg for msg in log_messages)
    assert any("new=1" in msg for msg in log_messages)
    assert any("duplicates=0" in msg for msg in log_messages)
    assert any("enriched=0" in msg for msg in log_messages)
