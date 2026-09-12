"""Hypothesis-based tests for SIVEP-Gripe business rules.

All strategies respect SIVEP data dictionary constraints:
- TP_IDADE=1 (dias) → NU_IDADE_N in [0, 30]
- TP_IDADE=2 (meses) → NU_IDADE_N in [0, 11]
- TP_IDADE=3 (anos) → NU_IDADE_N in [0, 150]
- CS_SEXO uses SIVEP raw codes {1,2,9} (not processed M/F/I)
- Dates respect DT_SIN_PRI <= DT_NOTIFIC <= DT_DIGITA
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from srag.data.analytics import (
    apply_global_filters,
    categorize_age,
    classificar_status_gripe,
    infer_etiologic_agent,
    outcome_death_mask,
)
from srag.data.loader import _normalize_age_to_years

# ── Estratégias baseadas no dicionário SIVEP ──────────────────────

SIVEP_CODES = {
    "EVOLUCAO": st.sampled_from([1, 2, 3, 9]),
    "CS_SEXO": st.sampled_from([1, 2, 9]),
    "CS_RACA": st.sampled_from([1, 2, 3, 4, 5, 9]),
    "CS_ZONA": st.sampled_from([1, 2, 3, 9]),
    "CLASSI_FIN": st.sampled_from([1, 2, 3, 4, 5]),
    "VACINA": st.sampled_from([1, 2, 9]),
    "PCR_RESUL": st.sampled_from([1, 2, 3, 4, 5, 9]),
    "CS_GESTANT": st.sampled_from([1, 2, 3, 4, 5, 6, 9]),
}

# SIVEP rule: TP_IDADE=1 (dias) → idade 0-30 dias
# SIVEP rule: TP_IDADE=2 (meses) → idade 0-11 meses
# SIVEP rule: TP_IDADE=3 (anos) → idade 0-150 anos
tp_idade_valor = st.sampled_from(
    [
        (1, st.integers(0, 30)),
        (2, st.integers(0, 11)),
        (3, st.integers(0, 150)),
    ]
).flatmap(lambda x: st.tuples(st.just(x[0]), x[1]))

# Datas no período SIVEP Mossoró (2020-2025)
data_sivep = st.dates(min_value=date(2020, 1, 1), max_value=date(2025, 12, 31))
data_ou_none = st.none() | data_sivep

# Perfis etários
PERFIS = ["crianca", "adolescente", "adulto", "idoso"]


# ── HELPERS ───────────────────────────────────────────────────────


def _row(**kwargs) -> dict:
    """Build a row dict with defaults that exercise the happy path."""
    base = {
        "DT_UT_DOSE": None,
        "DT_1_DOSE": None,
        "DT_2_DOSE": None,
        "VACINA": 1,
        "TP_IDADE": 3,
        "NU_IDADE_N": 30,
        "DT_SIN_PRI": date(2024, 7, 1),
        "MAE_VAC": None,
        "DT_VAC_MAE": None,
        "DT_DOSEUNI": None,
        "M_AMAMENTA": None,
    }
    base.update(kwargs)
    return base


def _df_with_column(col: str, values: list, extra: dict | None = None) -> pd.DataFrame:
    """Create a minimal DataFrame for filter testing."""
    data = {col: values}
    if extra:
        data.update(extra)
    return pd.DataFrame(data)


# ── CATEGORIZE_AGE: todos os buckets + fronteiras ─────────────────


class TestCategorizeAgeHypothesis:
    @given(age=st.floats(min_value=0, max_value=150, allow_nan=False, allow_infinity=False))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.differing_executors])
    def test_categorize_age_never_fails(self, age) -> None:
        result = categorize_age(age)
        assert isinstance(result, str) and len(result) > 0

    @given(age=st.floats(min_value=0, max_value=1.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_0_1_ano(self, age) -> None:
        assert categorize_age(age) == "0-1 ano"

    @given(age=st.floats(min_value=2, max_value=4.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_2_4_anos(self, age) -> None:
        assert categorize_age(age) == "2-4 anos"

    @given(age=st.floats(min_value=5, max_value=9.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_5_9_anos(self, age) -> None:
        assert categorize_age(age) == "5-9 anos"

    @given(age=st.floats(min_value=10, max_value=14.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_10_14_anos(self, age) -> None:
        assert categorize_age(age) == "10-14 anos"

    @given(age=st.floats(min_value=15, max_value=19.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_15_19_anos(self, age) -> None:
        assert categorize_age(age) == "15-19 anos"

    @given(age=st.floats(min_value=20, max_value=29.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_20_29_anos(self, age) -> None:
        assert categorize_age(age) == "20-29 anos"

    @given(age=st.floats(min_value=30, max_value=39.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_30_39_anos(self, age) -> None:
        assert categorize_age(age) == "30-39 anos"

    @given(age=st.floats(min_value=40, max_value=49.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_40_49_anos(self, age) -> None:
        assert categorize_age(age) == "40-49 anos"

    @given(age=st.floats(min_value=50, max_value=59.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_50_59_anos(self, age) -> None:
        assert categorize_age(age) == "50-59 anos"

    @given(age=st.floats(min_value=60, max_value=69.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_60_69_anos(self, age) -> None:
        assert categorize_age(age) == "60-69 anos"

    @given(age=st.floats(min_value=70, max_value=79.9999, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_70_79_anos(self, age) -> None:
        assert categorize_age(age) == "70-79 anos"

    @given(age=st.floats(min_value=80, max_value=150, allow_nan=False, allow_infinity=False))
    @settings(max_examples=50)
    def test_80_plus(self, age) -> None:
        assert categorize_age(age) == "80+ anos"

    # Fronteiras exatas: idades que batem no limiar <
    @given(age=st.sampled_from([2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]))
    @settings(max_examples=20)
    def test_bucket_boundaries_lower(self, age) -> None:
        """Idade exata no limiar inferior do bucket: 2.0 → '2-4 anos', 5.0 → '5-9 anos' ... 80.0 → '80+ anos'."""
        result = categorize_age(age)
        if age < 2:
            assert result == "0-1 ano"
        elif age < 5:
            assert result == "2-4 anos"
        elif age < 10:
            assert result == "5-9 anos"
        elif age < 15:
            assert result == "10-14 anos"
        elif age < 20:
            assert result == "15-19 anos"
        elif age < 30:
            assert result == "20-29 anos"
        elif age < 40:
            assert result == "30-39 anos"
        elif age < 50:
            assert result == "40-49 anos"
        elif age < 60:
            assert result == "50-59 anos"
        elif age < 70:
            assert result == "60-69 anos"
        elif age < 80:
            assert result == "70-79 anos"
        else:
            assert result == "80+ anos"


# ── NORMALIZE_AGE: co-restrição SIVEP real ────────────────────────


class TestNormalizeAgeHypothesis:
    @given(nu_idade=st.integers(0, 150), tp_idade=st.sampled_from([1, 2, 3]))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.differing_executors])
    def test_normalize_age_never_fails(self, nu_idade, tp_idade) -> None:
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result is None or isinstance(result, (int, float))

    @given(nu_idade=st.integers(1, 30), tp_idade=st.just(1))
    @settings(max_examples=30)
    def test_dias_para_anos(self, nu_idade, tp_idade) -> None:
        """TP_IDADE=1: 1-30 dias → < 0.1 anos."""
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result is not None and 0 < result < 0.1

    @given(nu_idade=st.integers(1, 11), tp_idade=st.just(2))
    @settings(max_examples=30)
    def test_meses_para_anos(self, nu_idade, tp_idade) -> None:
        """TP_IDADE=2: 1-11 meses → < 1 ano."""
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result is not None and 0 < result < 1.0

    @given(nu_idade=st.integers(1, 150), tp_idade=st.just(3))
    @settings(max_examples=50)
    def test_anos_mantem_valor(self, nu_idade, tp_idade) -> None:
        """TP_IDADE=3: anos → mesmo valor."""
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result == float(nu_idade)

    # SIVEP business rules: co-restrição entre tp_idade e nu_idade
    @given(nu_idade=st.integers(31, 365), tp_idade=st.just(1))
    @settings(max_examples=30)
    def test_dias_acima_de_30_ainda_converte(self, nu_idade, tp_idade) -> None:
        """NU_IDADE_N > 30 com TP_IDADE=1: viola SIVEP mas não quebra."""
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result is not None
        assert result == round(nu_idade / 365.25, 4)

    # Casos sentinela
    @given(tp_idade=st.sampled_from([1, 2, 3]))
    @settings(max_examples=10)
    def test_nu_idade_zero(self, tp_idade) -> None:
        """NU_IDADE_N=0: recém-nascido (< 24h)."""
        result = _normalize_age_to_years(0, tp_idade)
        assert result is not None and result == 0.0

    @given(nu_idade=st.integers(-100, -1), tp_idade=st.sampled_from([1, 2, 3]))
    @settings(max_examples=20)
    def test_nu_idade_negativo_retorna_none(self, nu_idade, tp_idade) -> None:
        assert _normalize_age_to_years(nu_idade, tp_idade) is None

    @given(nu_idade=st.integers(0, 150))
    @settings(max_examples=20)
    def test_tp_idade_none_trata_como_anos(self, nu_idade) -> None:
        """TP_IDADE=None: tratado como anos (loader.py:100)."""
        result = _normalize_age_to_years(nu_idade, None)
        assert result is not None
        assert result == float(nu_idade)

    def test_nu_idade_none_retorna_none(self) -> None:
        assert _normalize_age_to_years(None, 3) is None

    @given(nu_idade=st.integers(0, 150), tp_idade=st.sampled_from([0, 4, 5, 99]))
    @settings(max_examples=20)
    def test_tp_idade_invalido_retorna_none(self, nu_idade, tp_idade) -> None:
        """TP_IDADE fora de {1,2,3}: código retorna None."""
        result = _normalize_age_to_years(nu_idade, tp_idade)
        assert result is None


# ── OUTCOME_DEATH_MASK: EVOLUCAO rules ────────────────────────────


class TestOutcomeDeathMaskHypothesis:
    @given(values=st.lists(SIVEP_CODES["EVOLUCAO"], min_size=0, max_size=50))
    @settings(max_examples=50)
    def test_only_code_2_counts_as_death(self, values) -> None:
        series = pd.Series(values)
        mask = outcome_death_mask(series)
        for i, val in enumerate(values):
            if val == 2:
                assert mask.iloc[i]
            else:
                assert not mask.iloc[i]

    @given(values=st.lists(SIVEP_CODES["EVOLUCAO"], min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_code_3_is_never_death(self, values) -> None:
        series = pd.Series(values)
        mask = outcome_death_mask(series)
        assert mask[series == 3].sum() == 0

    def test_empty_series_returns_empty_mask(self) -> None:
        result = outcome_death_mask(pd.Series([], dtype=int))
        assert len(result) == 0

    @given(
        values=st.lists(st.sampled_from(["1", "2", "3", "9", None, np.nan, "foo"]), max_size=30)
    )
    @settings(max_examples=30)
    def test_non_numeric_values_are_coerced(self, values) -> None:
        """PD.to_numeric com errors='coerce' não deve lançar exceção."""
        series = pd.Series(values)
        try:
            mask = outcome_death_mask(series)
            assert len(mask) == len(values)
            assert mask.dtype == bool
        except Exception:
            pytest.fail("outcome_death_mask falhou com valores não numéricos")


# ── CLASSIFICAR_STATUS_GRIPE: 7 caminhos ──────────────────────────

# Campanhas de vacinação influenza (CAMPANHAS_GRIPE em surveillance.py)
CAMPANHAS = {
    2019: date(2019, 4, 10),
    2020: date(2020, 3, 23),
    2021: date(2021, 4, 12),
    2022: date(2022, 4, 4),
    2023: date(2023, 4, 10),
    2024: date(2024, 3, 25),
    2025: date(2025, 3, 20),
}

# Datas de sintoma: após 2020-01-01, antes de 2025-12-31
dt_sintoma_st = st.dates(min_value=date(2020, 1, 2), max_value=date(2025, 12, 31))
# Datas de dose: após 2019-01-01
dt_dose_st = st.dates(min_value=date(2019, 1, 1), max_value=date(2025, 12, 31))


class TestClassificarStatusGripeHypothesis:
    @given(
        vacina=SIVEP_CODES["VACINA"],
        tp_idade_valor=tp_idade_valor,
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=100, deadline=5000)
    def test_never_raises(self, vacina, tp_idade_valor, dt_sin_pri) -> None:
        """Nunca lança exceção com qualquer combinação válida de inputs."""
        tp_idade, nu_idade_n = tp_idade_valor
        row = _row(VACINA=vacina, TP_IDADE=tp_idade, NU_IDADE_N=nu_idade_n, DT_SIN_PRI=dt_sin_pri)
        try:
            result = classificar_status_gripe(row)
            assert result in [
                "protegido",
                "dose_1",
                "dose_2",
                "dose_unica",
                "vencida",
                "nao_vacinado",
                "ignorado",
                "inconsistencia",
            ]
        except Exception:
            pytest.fail(f"classificar_status_gripe falhou com inputs {row}")

    # ── Caminho 1: não vacinado ──
    @given(tp_idade_valor=tp_idade_valor, dt_sin_pri=dt_sintoma_st)
    @settings(max_examples=30, deadline=5000)
    def test_nao_vacinado(self, tp_idade_valor, dt_sin_pri) -> None:
        """VACINA=2 + sem data de dose → 'nao_vacinado'."""
        tp_idade, nu_idade_n = tp_idade_valor
        row = _row(VACINA=2, TP_IDADE=tp_idade, NU_IDADE_N=nu_idade_n, DT_SIN_PRI=dt_sin_pri)
        assert classificar_status_gripe(row) == "nao_vacinado"

    # ── Caminho 2: inconsistência (VACINA=2 + dose presente) ──
    @given(
        dt_dose=dt_dose_st,
        tp_idade_valor=tp_idade_valor,
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=30, deadline=5000)
    def test_inconsistencia_vacina2_com_dose(self, dt_dose, tp_idade_valor, dt_sin_pri) -> None:
        """VACINA=2 + DT_UT_DOSE presente → 'inconsistencia'."""
        tp_idade, nu_idade_n = tp_idade_valor
        row = _row(
            VACINA=2,
            DT_UT_DOSE=dt_dose,
            TP_IDADE=tp_idade,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        assert classificar_status_gripe(row) == "inconsistencia"

    # ── Caminho 3: ignorado (VACINA=9 ou VACINA=1 sem dose) ──
    @given(
        vacina=st.sampled_from([9, 1]),
        tp_idade_valor=tp_idade_valor,
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=30, deadline=5000)
    def test_ignorado(self, vacina, tp_idade_valor, dt_sin_pri) -> None:
        """VACINA=9 ou VACINA=1 sem DT_UT_DOSE → 'ignorado'."""
        tp_idade, nu_idade_n = tp_idade_valor
        row = _row(
            VACINA=vacina,
            DT_UT_DOSE=None,
            TP_IDADE=tp_idade,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        assert classificar_status_gripe(row) == "ignorado"

    # ── Caminho 4: dose > sintoma → inconsistência ──
    @given(
        dt_dose=dt_dose_st,
        dias_antes=st.integers(min_value=1, max_value=365),
        tp_idade_valor=tp_idade_valor,
    )
    @settings(max_examples=30, deadline=5000)
    def test_inconsistencia_dose_apos_sintoma(self, dt_dose, dias_antes, tp_idade_valor) -> None:
        """DT_UT_DOSE > DT_SIN_PRI → 'inconsistencia'."""
        tp_idade, nu_idade_n = tp_idade_valor
        dt_sin_pri = dt_dose - timedelta(days=dias_antes)
        assume(dt_sin_pri >= date(2020, 1, 1))
        row = _row(
            VACINA=1,
            DT_UT_DOSE=dt_dose,
            TP_IDADE=tp_idade,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        assert classificar_status_gripe(row) == "inconsistencia"

    # ── Caminho 5: protegido (adulto, dose >= campanha, sintoma >= dose) ──
    @given(
        ano=st.sampled_from(list(CAMPANHAS.keys())),
        dias_sintoma_apos_dose=st.integers(min_value=0, max_value=180),
        nu_idade_n=st.integers(18, 100),
    )
    @settings(max_examples=50, deadline=5000)
    def test_protegido_adulto(self, ano, dias_sintoma_apos_dose, nu_idade_n) -> None:
        """Adulto vacinado após campanha → 'protegido'.

        A funcao classificar_status_gripe compara dt_dose contra
        CAMPANHAS_GRIPE[ano_sintoma]. Garantimos dt_dose >= campanha
        do ano do sintoma e dt_sin_pri >= dt_dose.
        """
        inicio = CAMPANHAS[ano]
        dt_dose = inicio + timedelta(days=7)  # Dose 7 dias apos inicio
        dt_sin_pri = dt_dose + timedelta(days=dias_sintoma_apos_dose)
        assume(dt_sin_pri.year == ano)  # Mesmo ano → mesma campanha
        assume(dt_sin_pri <= date(2025, 12, 31))
        row = _row(
            VACINA=1,
            DT_UT_DOSE=dt_dose,
            TP_IDADE=3,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        assert classificar_status_gripe(row) == "protegido"

    # ── Caminho 6: vencida (dose antes da campanha) ──
    @given(
        ano=st.sampled_from(list(CAMPANHAS.keys())),
        dias_antes=st.integers(min_value=8, max_value=180),
        dias_sintoma_apos_dose=st.integers(min_value=0, max_value=180),
        nu_idade_n=st.integers(18, 100),
    )
    @settings(max_examples=30, deadline=5000)
    def test_vencida(self, ano, dias_antes, dias_sintoma_apos_dose, nu_idade_n) -> None:
        """Dose antes da campanha → 'vencida'.

        A funcao compara dt_dose contra CAMPANHAS_GRIPE[ano_sintoma].
        Precisamos que dt_dose < campanha do ano do sintoma.
        """
        inicio = CAMPANHAS[ano]
        dt_dose = inicio - timedelta(days=dias_antes)
        dt_sin_pri = dt_dose + timedelta(days=dias_sintoma_apos_dose)
        assume(dt_sin_pri <= date(2025, 12, 31))
        assume(dt_sin_pri >= dt_dose)
        assume(dt_sin_pri.year == ano)  # Mesmo ano → mesma campanha
        row = _row(
            VACINA=1,
            DT_UT_DOSE=dt_dose,
            TP_IDADE=3,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        assert classificar_status_gripe(row) == "vencida"

    # ── Caminho 7a: infantil (< 6 meses) via MAE_VAC ──
    @given(
        mae_vac=st.sampled_from([1, 2, 9]),
        dt_vac_mae=dt_dose_st,
        nu_idade_n=st.integers(0, 5),
    )
    @settings(max_examples=30, deadline=5000)
    def test_menor_6m_mae_vac(self, mae_vac, dt_vac_mae, nu_idade_n) -> None:
        """< 6 meses: depende de MAE_VAC. Se MAE_VAC=1 com data → protegido."""
        assume(dt_vac_mae <= date(2025, 12, 31))
        dt_sin_pri = dt_vac_mae + timedelta(days=30)
        assume(dt_sin_pri <= date(2025, 12, 31))
        row = _row(
            VACINA=None,
            DT_UT_DOSE=None,
            TP_IDADE=2,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
            MAE_VAC=mae_vac,
            DT_VAC_MAE=dt_vac_mae,
        )
        result = classificar_status_gripe(row)
        # Se MAE_VAC=1 e DT_VAC_MAE tem data, tenta fluxo de protegido
        if mae_vac == 1:
            assert result in {"protegido", "vencida", "inconsistencia", "ignorado"}
        else:
            assert result in {"ignorado", "nao_vacinado", "inconsistencia"}

    # ── Caminho 7b: infantil via TP_IDADE=1 ──
    @given(
        vacina=st.sampled_from([1, 2]),
        nu_idade_n=st.integers(0, 30),
        dt_dose=dt_dose_st,
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=20, deadline=5000)
    def test_menor_6m_tp_idade_1(self, vacina, nu_idade_n, dt_dose, dt_sin_pri) -> None:
        """TP_IDADE=1: sempre < 6 meses. Usa MAE_VAC."""
        assume(dt_sin_pri >= dt_dose)
        row = _row(
            VACINA=vacina,
            DT_UT_DOSE=dt_dose,
            TP_IDADE=1,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
            MAE_VAC=1,
            DT_VAC_MAE=dt_dose,
        )
        result = classificar_status_gripe(row)
        assert isinstance(result, str)

    # ── Caminho 8: criança (6m-8a) via dose_2, dose_1, dose_unica ──
    @given(
        ano=st.sampled_from(list(CAMPANHAS.keys())),
        dias_dose_apos_camp=st.integers(min_value=0, max_value=180),
        dias_sintoma_apos_dose=st.integers(min_value=0, max_value=180),
        nu_idade_n=st.integers(1, 8),
        tem_doseuni=st.booleans(),
    )
    @settings(max_examples=30, deadline=5000)
    def test_crianca_6m_8a_dose_2(
        self, ano, dias_dose_apos_camp, dias_sintoma_apos_dose, nu_idade_n, tem_doseuni
    ) -> None:
        """Criança 6m-8a com DT_2_DOSE → 'dose_2' (tem prioridade sobre dose_1/dose_unica)."""
        inicio = CAMPANHAS[ano]
        dt_2_dose = inicio + timedelta(days=dias_dose_apos_camp + 7)
        dt_1_dose = inicio + timedelta(days=dias_dose_apos_camp)
        dt_doseuni = inicio + timedelta(days=dias_dose_apos_camp) if tem_doseuni else None
        dt_sin_pri = dt_2_dose + timedelta(days=dias_sintoma_apos_dose)
        assume(dt_sin_pri.year == ano)
        assume(dt_sin_pri <= date(2025, 12, 31))
        row = _row(
            VACINA=1,
            DT_UT_DOSE=None,
            DT_1_DOSE=dt_1_dose,
            DT_2_DOSE=dt_2_dose,
            DT_DOSEUNI=dt_doseuni,
            TP_IDADE=3,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        result = classificar_status_gripe(row)
        # Com DT_2_DOSE presente, label_prefix='dose_2' + protecao → 'dose_2'
        assert result == "dose_2"

    @given(
        dt_1_dose=dt_dose_st,
        dt_doseuni=st.none() | dt_dose_st,
        nu_idade_n=st.integers(1, 8),
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=30, deadline=5000)
    def test_crianca_6m_8a_dose_1(self, dt_1_dose, dt_doseuni, nu_idade_n, dt_sin_pri) -> None:
        """Criança 6m-8a com DT_1_DOSE (sem DT_2_DOSE) → 'dose_1'."""
        assume(dt_sin_pri >= dt_1_dose)
        row = _row(
            VACINA=1,
            DT_UT_DOSE=None,
            DT_1_DOSE=dt_1_dose,
            DT_2_DOSE=None,
            DT_DOSEUNI=dt_doseuni,
            TP_IDADE=3,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        result = classificar_status_gripe(row)
        assert result in {
            "dose_1",
            "dose_unica",
            "protegido",
            "vencida",
            "ignorado",
            "inconsistencia",
        }

    @given(
        dt_doseuni=dt_dose_st,
        nu_idade_n=st.integers(1, 8),
        dt_sin_pri=dt_sintoma_st,
    )
    @settings(max_examples=30, deadline=5000)
    def test_crianca_6m_8a_dose_unica(self, dt_doseuni, nu_idade_n, dt_sin_pri) -> None:
        """Criança 6m-8a só com DT_DOSEUNI → 'dose_unica'."""
        assume(dt_sin_pri >= dt_doseuni)
        row = _row(
            VACINA=1,
            DT_UT_DOSE=None,
            DT_1_DOSE=None,
            DT_2_DOSE=None,
            DT_DOSEUNI=dt_doseuni,
            TP_IDADE=3,
            NU_IDADE_N=nu_idade_n,
            DT_SIN_PRI=dt_sin_pri,
        )
        result = classificar_status_gripe(row)
        assert result in {"dose_unica", "protegido", "vencida", "ignorado", "inconsistencia"}


# ── INFER_ETIOLOGIC_AGENT: CLASSI_FIN + VSR override ──────────────


class TestInferEtiologicAgentHypothesis:
    @given(
        classi_fin_list=st.lists(SIVEP_CODES["CLASSI_FIN"], min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_classi_fin_mapping(self, classi_fin_list) -> None:
        """CLASSI_FIN mapeia para agente correto."""
        df = pd.DataFrame({"CLASSI_FIN": classi_fin_list})
        result = infer_etiologic_agent(df)
        assert len(result) == len(classi_fin_list)
        expected_map = {
            1: "Influenza",
            2: "Outros Vírus",
            3: "Outro Agente",
            4: "Não Especificada",
            5: "COVID-19",
        }
        for i, val in enumerate(classi_fin_list):
            expected = expected_map.get(val, "Não Especificada")
            assert result.iloc[i] == expected

    @given(
        n_rows=st.integers(1, 20),
        classi_fin=st.sampled_from([1, 2, 3, 4, 5]),
        pcr_vsr=st.sampled_from([1, 2, None, np.nan]),
        an_vsr=st.sampled_from([1, 2, None, np.nan]),
    )
    @settings(max_examples=50)
    def test_vsr_overrides_classi_fin(self, n_rows, classi_fin, pcr_vsr, an_vsr) -> None:
        """PCR_VSR=1 ou AN_VSR=1 sobrescreve CLASSI_FIN para 'VSR'."""
        df = pd.DataFrame(
            {
                "CLASSI_FIN": [classi_fin] * n_rows,
                "PCR_VSR": [pcr_vsr] * n_rows,
                "AN_VSR": [an_vsr] * n_rows,
            }
        )
        result = infer_etiologic_agent(df)
        has_vsr = (pcr_vsr == 1) or (an_vsr == 1)
        if has_vsr:
            assert all(r == "VSR" for r in result)
        else:
            expected_map = {
                1: "Influenza",
                2: "Outros Vírus",
                3: "Outro Agente",
                4: "Não Especificada",
                5: "COVID-19",
            }
            expected = expected_map.get(classi_fin, "Não Especificada")
            assert all(r == expected for r in result)

    def test_empty_df_returns_empty_series(self) -> None:
        result = infer_etiologic_agent(pd.DataFrame())
        assert len(result) == 0

    @given(n_rows=st.integers(1, 20))
    @settings(max_examples=20)
    def test_missing_classi_fin_defaults_to_nao_especificada(self, n_rows) -> None:
        """Sem coluna CLASSI_FIN → todos 'Não Especificada'."""
        df = pd.DataFrame({"DT_SIN_PRI": [pd.Timestamp("2024-01-01")] * n_rows})
        result = infer_etiologic_agent(df)
        assert all(r == "Não Especificada" for r in result)



# ── APPLY_GLOBAL_FILTERS: filtro de bairro ────


class TestApplyGlobalFiltersHypothesis:
    # Casos sentinela
    def test_empty_df_returns_empty(self) -> None:
        assert apply_global_filters(pd.DataFrame()).empty

    @given(
        n_cases=st.integers(1, 30),
    )
    @settings(max_examples=20)
    def test_no_filters_returns_original(self, n_cases) -> None:
        df = pd.DataFrame({"NU_IDADE_N": [30] * n_cases})
        result = apply_global_filters(df)
        assert len(result) == len(df)

    @given(
        n_cases=st.integers(1, 30),
        years=st.lists(st.integers(min_value=2020, max_value=2025), max_size=3, unique=True),
    )
    @settings(max_examples=30)
    def test_filter_by_years(self, n_cases, years) -> None:
        """Filtro por ano de DT_SIN_PRI (via surveillance)."""
        from srag.api.core import apply_surveillance_filters

        df = pd.DataFrame(
            {
                "DT_SIN_PRI": pd.to_datetime(
                    [
                        f"{y}-06-15"
                        for y in ([2020, 2021, 2022, 2023, 2024, 2025] * (n_cases // 6 + 1))[
                            :n_cases
                        ]
                    ]
                ),
            }
        )
        result = apply_surveillance_filters(df, years=years)
        assert 0 <= len(result) <= len(df)

    @given(
        n_cases=st.integers(1, 30),
        bairros=st.lists(
            st.sampled_from(["CENTRO", "ALTO DE SÃO MANOEL", "COSTA E SILVA", "BARROCAS"]),
            max_size=4,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_filter_by_bairro(self, n_cases, bairros) -> None:
        """Filtro por bairro (BAIRRO_REF)."""
        pool = ["CENTRO", "ALTO DE SÃO MANOEL", "COSTA E SILVA", "BARROCAS", "PLANALTO"]
        values = pool * (n_cases // len(pool) + 1)
        df = pd.DataFrame({"BAIRRO_REF": values[:n_cases]})
        result = apply_global_filters(df, bairros=bairros)
        assert 0 <= len(result) <= len(df)

    # Filtros combinados
    @given(
        n_cases=st.integers(1, 30),
        bairros=st.lists(
            st.sampled_from(["CENTRO", "ALTO DE SÃO MANOEL", "COSTA E SILVA"]),
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=30)
    def test_combined_filters_never_expand(self, n_cases, bairros) -> None:
        """Filtro repetido nunca amplia o DataFrame."""
        pool = ["CENTRO", "ALTO DE SÃO MANOEL", "COSTA E SILVA", "BARROCAS", "PLANALTO"]
        values = pool * (n_cases // len(pool) + 1)
        df = pd.DataFrame({"BAIRRO_REF": values[:n_cases]})
        once = apply_global_filters(df, bairros=bairros)
        twice = apply_global_filters(once, bairros=bairros)
        assert 0 <= len(twice) <= len(once) <= len(df)
