from datetime import UTC, date, datetime, timedelta
from typing import Never

import numpy as np
import pandas as pd
import pytest

from srag.api.core import _cache, apply_surveillance_filters, get_df, sanitize_data


class TestSanitizeData:
    def test_sanitize_dict(self) -> None:
        data = {"key": "value", "count": np.int64(5), "rate": np.float64(3.14)}
        result = sanitize_data(data)
        assert result == {"key": "value", "count": 5, "rate": 3.14}
        assert isinstance(result["count"], int)
        assert isinstance(result["rate"], float)

    def test_sanitize_list(self) -> None:
        data = [np.int64(1), np.int32(2), np.float64(1.5)]
        result = sanitize_data(data)
        assert result == [1, 2, 1.5]

    def test_sanitize_nested(self) -> None:
        data = {"items": [{"value": np.float64(1.0)}, {"value": np.int64(2)}]}
        result = sanitize_data(data)
        assert result == {"items": [{"value": 1.0}, {"value": 2}]}

    def test_sanitize_numpy_array(self) -> None:
        data = np.array([1, 2, 3])
        result = sanitize_data(data)
        assert result == [1, 2, 3]

    def test_sanitize_none(self) -> None:
        assert sanitize_data(None) is None

    def test_sanitize_pandas_na(self) -> None:
        assert sanitize_data(pd.NA) is None
        assert sanitize_data(np.nan) is None


class TestApplySurveillanceFilters:
    def test_filter_by_years(self) -> None:
        df = pd.DataFrame({"DT_SIN_PRI": [date(2023, 1, 1), date(2024, 1, 1), date(2025, 1, 1)]})
        result = apply_surveillance_filters(df, years=[2024])
        assert len(result) == 1
        assert result.iloc[0]["DT_SIN_PRI"] == date(2024, 1, 1)

    def test_filter_by_years_empty(self) -> None:
        df = pd.DataFrame({"DT_SIN_PRI": [date(2023, 1, 1)]})
        result = apply_surveillance_filters(df, years=[2025])
        assert len(result) == 0

    def test_filter_by_agents(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "srag.api.core.infer_etiologic_agent",
            lambda df: pd.Series(["COVID-19", "Influenza", "COVID-19"]),
        )
        df = pd.DataFrame({"CLASSI_FIN": [1, 5, 1]})
        result = apply_surveillance_filters(df, agents=["COVID-19"])
        assert len(result) == 2

    def test_filter_by_both(self, monkeypatch) -> None:
        df = pd.DataFrame(
            {
                "DT_SIN_PRI": [date(2024, 1, 1), date(2024, 1, 1)],
                "CLASSI_FIN": [1, 5],
            }
        )
        monkeypatch.setattr(
            "srag.api.core.infer_etiologic_agent",
            lambda df: pd.Series(["COVID-19", "Influenza"]),
        )
        result = apply_surveillance_filters(df, years=[2024], agents=["COVID-19"])
        assert len(result) == 1

    def test_no_filters_returns_original(self) -> None:
        df = pd.DataFrame({"DT_SIN_PRI": [date(2024, 1, 1)]})
        result = apply_surveillance_filters(df)
        assert len(result) == 1

    def test_filter_with_invalid_years(self) -> None:
        df = pd.DataFrame({"DT_SIN_PRI": [date(2024, 1, 1)]})
        result = apply_surveillance_filters(df, years=[None])
        assert len(result) == 0

    def test_filter_without_dt_sin_pri(self) -> None:
        df = pd.DataFrame({"OTHER": [1, 2]})
        result = apply_surveillance_filters(df, years=[2024])
        assert len(result) == 2

    def test_filter_with_none_agents(self) -> None:
        df = pd.DataFrame(
            {
                "CLASSI_FIN": [1, 5],
            }
        )

        def monkeypatch_agents(df):
            return pd.Series(["COVID-19", "Influenza"])

        # Even if agents contains None, it should filter the valid ones
        import srag.api.core

        original = srag.api.core.infer_etiologic_agent
        try:
            srag.api.core.infer_etiologic_agent = monkeypatch_agents
            result = apply_surveillance_filters(df, agents=[None, "COVID-19"])
            assert len(result) == 1
        finally:
            srag.api.core.infer_etiologic_agent = original


class TestGetDf:
    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        _cache["df"] = None
        _cache["loaded_at"] = None

    def test_get_df_cache_hit(self, monkeypatch) -> None:
        df_mock = pd.DataFrame({"DT_NOTIFIC": ["2024-01-01"]})
        _cache["df"] = df_mock
        _cache["loaded_at"] = datetime.now(UTC)

        def fake_read_sql(*args, **kwargs) -> Never:
            raise ValueError("Should not be called")

        monkeypatch.setattr("pandas.read_sql", fake_read_sql)

        result = get_df()
        assert result is df_mock

    def test_get_df_cache_expired(self, monkeypatch) -> None:
        df_mock = pd.DataFrame({"DT_NOTIFIC": ["2024-01-01"], "DT_SIN_PRI": ["2024-01-01"]})
        _cache["df"] = pd.DataFrame()
        _cache["loaded_at"] = datetime.now(UTC) - timedelta(minutes=40)

        monkeypatch.setattr("pandas.read_sql", lambda *args, **kwargs: df_mock)
        result = get_df()
        assert len(result) == 1

    def test_get_df_success(self, monkeypatch) -> None:
        df_mock = pd.DataFrame(
            {"DT_NOTIFIC": ["2024-01-01"], "DT_SIN_PRI": ["2024-01-01"], "DT_INTERNA": [None]}
        )
        monkeypatch.setattr("pandas.read_sql", lambda *args, **kwargs: df_mock)
        result = get_df()
        assert len(result) == 1
        assert result["DT_NOTIFIC"].iloc[0] == date(2024, 1, 1)

    def test_get_df_filters_na_dt_sin_pri(self, monkeypatch) -> None:
        df_mock = pd.DataFrame(
            {"DT_NOTIFIC": ["2024-01-01", "2024-01-02"], "DT_SIN_PRI": ["2024-01-01", None]}
        )
        monkeypatch.setattr("pandas.read_sql", lambda *args, **kwargs: df_mock)
        result = get_df()
        assert len(result) == 1

    def test_get_df_error_without_cache(self, monkeypatch) -> None:
        def fake_read_sql(*args, **kwargs) -> Never:
            raise Exception("DB Error")

        monkeypatch.setattr("pandas.read_sql", fake_read_sql)
        result = get_df()
        assert len(result) == 0

    def test_get_df_error_with_cache(self, monkeypatch) -> None:
        df_mock = pd.DataFrame({"DT_NOTIFIC": ["2024-01-01"]})
        _cache["df"] = df_mock
        _cache["loaded_at"] = datetime.now(UTC) - timedelta(minutes=40)

        def fake_read_sql(*args, **kwargs) -> Never:
            raise Exception("DB Error")

        monkeypatch.setattr("pandas.read_sql", fake_read_sql)
        result = get_df()
        assert result is df_mock
