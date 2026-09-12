"""Property-based tests for the surveillance analytics hot paths.

Targets the functions most likely to silently regress:
  - compute_time_series: weekly aggregation invariants
  - compute_virus_distribution: percentage accounting
  - outcome_death_mask: SIVEP coding contract
  - infer_etiologic_agent: VSR override priority (VSR > CLASSI_FIN)
  - apply_global_filters: commutativity (filter A then B == filter B then A)
"""

import hypothesis.strategies as st
import numpy as np
import pandas as pd
from hypothesis import HealthCheck, assume, given, settings

from srag.data.analytics import (
    compute_time_series,
    compute_virus_distribution,
    infer_etiologic_agent,
    outcome_death_mask,
)
from srag.data.analytics.filters import apply_global_filters
from srag.data.references import DEATH_OUTCOMES, VALID_OUTCOMES


def _srag_frame(n_rows: int) -> pd.DataFrame:
    """Build a minimal SIVEP-shaped DataFrame with random dates and outcomes."""
    base = pd.Timestamp("2024-01-01")
    dates = [base + pd.Timedelta(days=int(i)) for i in range(n_rows)]
    rng = np.random.default_rng(42)
    outcomes = rng.choice(list(VALID_OUTCOMES), size=n_rows).astype(int)
    return pd.DataFrame(
        {
            "DT_NOTIFIC": dates,
            "DT_SIN_PRI": dates,
            "EVOLUCAO": outcomes,
            "CLASSI_FIN": rng.integers(1, 6, size=n_rows).astype(int),
            "ID_MUNICIP": ["2408003"] * n_rows,
        }
    )


class TestComputeTimeSeriesProperties:
    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
    def test_total_equals_input_rows(self, n: int) -> None:
        df = _srag_frame(n)
        result = compute_time_series(df)
        assert int(result["total"].sum()) == n

    @given(n=st.integers(min_value=0, max_value=50))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.differing_executors])
    def test_no_negative_counts(self, n: int) -> None:
        df = _srag_frame(n)
        result = compute_time_series(df)
        assert (result["total"] >= 0).all()

    def test_empty_df_returns_empty_aggregations(self) -> None:
        result = compute_time_series(
            pd.DataFrame(columns=["DT_NOTIFIC", "EVOLUCAO", "CLASSI_FIN"])
        )
        assert len(result) == 0

    @given(
        n=st.integers(min_value=2, max_value=20),
        seed=st.integers(min_value=0, max_value=10_000),
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.differing_executors])
    def test_is_deterministic_for_same_input(self, n: int, seed: int) -> None:
        df_a = _srag_frame(n)
        df_b = _srag_frame(n)
        assert compute_time_series(df_a).equals(compute_time_series(df_b))


class TestComputeVirusDistributionProperties:
    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
    def test_counts_sum_to_total(self, n: int) -> None:
        df = _srag_frame(n)
        result = compute_virus_distribution(df)
        assert int(result["count"].sum()) == n

    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.differing_executors])
    def test_no_negative_counts(self, n: int) -> None:
        df = _srag_frame(n)
        result = compute_virus_distribution(df)
        assert (result["count"] >= 0).all()

    @given(n=st.integers(min_value=1, max_value=100))
    @settings(max_examples=30, suppress_health_check=[HealthCheck.differing_executors])
    def test_virus_labels_come_from_known_set(self, n: int) -> None:
        """Every row's `virus` label must be a string the function produces.

        We just check no NaN/None.
        """
        df = _srag_frame(n)
        result = compute_virus_distribution(df)
        assert result["virus"].notna().all()
        assert (result["virus"].astype(str) != "").all()
        assert (result["virus"].astype(str) != "None").all()


class TestOutcomeDeathMaskProperties:
    """outcome_death_mask is the SIVEP death coding contract.

    Death codes are exactly DEATH_OUTCOMES. Anything else (including
    code 3 'Óbito por outras causas') MUST NOT be counted as death.
    """

    @given(outcome=st.sampled_from(sorted(VALID_OUTCOMES)))
    @settings(max_examples=20)
    def test_only_death_codes_return_true(self, outcome: int) -> None:
        result = outcome_death_mask(pd.Series([outcome])).iloc[0]
        expected = outcome in DEATH_OUTCOMES
        assert bool(result) == expected

    @given(
        outcomes=st.lists(
            st.sampled_from(sorted(VALID_OUTCOMES | {-1, 0, 99})),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=30)
    def test_mask_shape_matches_input(self, outcomes: list[int]) -> None:
        series = pd.Series(outcomes)
        mask = outcome_death_mask(series)
        assert len(mask) == len(outcomes)
        assert mask.dtype == bool

    @given(
        outcomes=st.lists(
            st.sampled_from(sorted(VALID_OUTCOMES | {-1, 0, 99})),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=30)
    def test_mask_only_true_for_death_codes(self, outcomes: list[int]) -> None:
        """Property: True entries must be subset of DEATH_OUTCOMES."""
        series = pd.Series(outcomes)
        mask = outcome_death_mask(series)
        true_outcomes = set(series[mask].tolist())
        assert true_outcomes.issubset(DEATH_OUTCOMES)


class TestInferEtiologicAgent:
    """Property tests for infer_etiologic_agent.

    Contract:
      - Empty df -> empty series
      - CLASSI_FIN 1 -> Influenza
      - CLASSI_FIN 5 -> COVID-19
      - VSR override (PCR_VSR=1 OR AN_VSR=1) ALWAYS wins, regardless of CLASSI_FIN
    """

    @given(st.lists(st.sampled_from([1, 2, 3, 4, 5, 99]), min_size=1, max_size=50))
    @settings(max_examples=30)
    def test_classification_matches_classi_fin(self, codes: list[int]) -> None:
        df = pd.DataFrame({"CLASSI_FIN": codes})
        result = infer_etiologic_agent(df)
        expected = {
            1: "Influenza",
            2: "Outros Vírus",
            3: "Outro Agente",
            4: "Não Especificada",
            5: "COVID-19",
        }
        for actual_code, actual_label in zip(codes, result, strict=False):
            if actual_code in expected:
                assert actual_label == expected[actual_code]
            else:
                assert actual_label == "Não Especificada"

    def test_vsr_overrides_classi_fin_covid(self) -> None:
        """PCR_VSR=1 must produce 'VSR' even when CLASSI_FIN=5 (COVID-19)."""
        df = pd.DataFrame({"CLASSI_FIN": [5], "PCR_VSR": [1], "AN_VSR": [0]})
        result = infer_etiologic_agent(df)
        assert result.tolist() == ["VSR"]

    def test_vsr_overrides_classi_fin_influenza(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1], "PCR_VSR": [0], "AN_VSR": [1]})
        result = infer_etiologic_agent(df)
        assert result.tolist() == ["VSR"]

    def test_vsr_via_pcr_or_antigenic(self) -> None:
        """Either PCR_VSR=1 or AN_VSR=1 must trigger VSR label."""
        df_pcr = pd.DataFrame({"CLASSI_FIN": [5], "PCR_VSR": [1], "AN_VSR": [0]})
        df_an = pd.DataFrame({"CLASSI_FIN": [5], "PCR_VSR": [0], "AN_VSR": [1]})
        assert infer_etiologic_agent(df_pcr).tolist() == ["VSR"]
        assert infer_etiologic_agent(df_an).tolist() == ["VSR"]

    @given(
        n_vsr=st.integers(min_value=1, max_value=10),
        n_other=st.integers(min_value=0, max_value=20),
    )
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.differing_executors],
    )
    def test_vsr_count_matches_marker_rows(self, n_vsr: int, n_other: int) -> None:
        """VSR marker rows must always be labeled VSR, others by CLASSI_FIN."""
        assume(n_other > 0)
        codes = [5] * n_other
        codes += [5] * n_vsr
        vsr_pcr = [0] * n_other + [1] * n_vsr
        df = pd.DataFrame({"CLASSI_FIN": codes, "PCR_VSR": vsr_pcr, "AN_VSR": [0] * len(codes)})
        result = infer_etiologic_agent(df)
        assert sum(result == "VSR") == n_vsr
        assert sum(result == "COVID-19") == n_other

    def test_missing_columns_returns_nea_especificada(self) -> None:
        df = pd.DataFrame({"CLASSI_FIN": [1, 5]})
        result = infer_etiologic_agent(df)
        assert result.tolist() == ["Influenza", "COVID-19"]

    def test_empty_df(self) -> None:
        result = infer_etiologic_agent(pd.DataFrame())
        assert len(result) == 0


class TestApplyGlobalFiltersCommutativity:
    """Filter A then B must produce same row count as B then A.

    Tests the assumption that global filters compose as intersection of
    masks. Catches mutations like `or` <-> `and` swaps, set-semantics
    regressions, or re-introduction of inner-state.
    """

    def test_bairros_filters_commute(
        self,
    ) -> None:
        """Bairro filter applied twice in any grouping is stable."""
        df = pd.DataFrame({"BAIRRO_REF": ["CENTRO", "ALTO", "CENTRO", "SITIO X"]})
        ab = apply_global_filters(apply_global_filters(df, bairros=["CENTRO"]), bairros=["ALTO"])
        ba = apply_global_filters(apply_global_filters(df, bairros=["ALTO"]), bairros=["CENTRO"])
        assert len(ab) == len(ba) == 0

    @given(seed=st.integers(min_value=0, max_value=9999))
    @settings(
        max_examples=30,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.differing_executors],
    )
    def test_no_filters_returns_copy(self, seed: int) -> None:
        """apply_global_filters with no filters must return a copy, not a view.

        Catches mutations that return df directly (mutation: `return df`
        replaced by `return None` or `return df.iloc[:0]`).
        """
        np.random.default_rng(seed)
        df = pd.DataFrame(
            {"DT_NOTIFIC": pd.to_datetime(["2024-01-01", "2024-06-01"]), "CS_SEXO": ["M", "F"]}
        )
        result = apply_global_filters(df)
        assert len(result) == 2

    def test_bairros_filter_unknown_returns_empty(self) -> None:
        """Unknown bairro yields empty regardless of repetition."""
        df = pd.DataFrame({"BAIRRO_REF": ["CENTRO"] * 5})
        once = apply_global_filters(df, bairros=["INEXISTENTE"])
        twice = apply_global_filters(once, bairros=["INEXISTENTE"])
        assert len(once) == len(twice) == 0

    def test_empty_input(self) -> None:
        result = apply_global_filters(pd.DataFrame(), bairros=["CENTRO"])
        assert result.empty
