"""Territory API routers (tópico Bairro + zona sociodemográfica)."""

# ruff: noqa

from typing import Any

from fastapi import APIRouter, Query

from srag.api.dependencies import CommonFiltersDep
from srag.api.core import get_df, apply_surveillance_filters, sanitize_data
from srag.data.analytics import (
    apply_global_filters,
    compute_territory_distribution,
    compute_zone_distribution,
    normalize_territory_labels,
)

router = APIRouter(tags=["territory"])


@router.get("/territory_bootstrap")
def territory_bootstrap(
    filters: CommonFiltersDep,
    min_cases: int = Query(5, ge=1),
) -> Any:
    df = get_df()
    df = apply_global_filters(
        df, filters.bairros, filters.base, filters.gravidade, filters.sintomas
    )
    df = apply_surveillance_filters(df, filters.years, filters.agents, filters.classi)

    if df.empty:
        return sanitize_data({"territory": {"bairros": [], "zonas": []}})

    # Regra do bairro oficial: só OFFICIAL_BAIRROS (+ pais do mapa) é bairro;
    # o resto vira "AREA RURAL DE MOSSORO"; oficial com zona rural vira urbano.
    df = normalize_territory_labels(df)

    bairros_df = compute_territory_distribution(df, min_cases=0)

    return sanitize_data(
        {
            "territory": {
                "bairros": bairros_df[bairros_df["count"] >= min_cases].to_dict(orient="records"),
                "zonas": compute_zone_distribution(df).to_dict(orient="records"),
            },
        }
    )
