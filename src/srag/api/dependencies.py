"""API dependency injections for SRAG Mossoró."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel

from srag.data.references import BASE_ANALISE_VALUES, GRAVIDADE_VALUES, SYMPTOM_FIELDS


class CommonFilters(BaseModel):
    """Filter parameters sent by the frontend (years/agents/bairros/classi/...)."""

    years: list[int] | None = None
    agents: list[str] | None = None
    bairros: list[str] | None = None
    classi: list[int] | None = None
    base: str | None = None
    gravidade: str | None = None
    sintomas: list[str] | None = None


def _validate_years(years: list[int] | None) -> None:
    if years is None:
        return
    for y in years:
        if not (1900 <= y <= 2030):
            raise HTTPException(status_code=422, detail=f"Year {y} out of range [1900, 2030]")


def _validate_string_lists(v: list[str] | None) -> None:
    if v is None:
        return
    for item in v:
        if len(item) > 100:
            raise HTTPException(status_code=422, detail=f"Filter value too long: {item[:50]}...")


def _validate_classi(classi: list[int] | None) -> None:
    if classi is None:
        return
    for c in classi:
        if not (1 <= c <= 9):
            raise HTTPException(status_code=422, detail=f"Classi {c} out of range [1, 9]")


def _validate_base(base: str | None) -> None:
    if base is None:
        return
    if base not in BASE_ANALISE_VALUES:
        raise HTTPException(
            status_code=422,
            detail=f"base '{base}' invalid, expected one of {sorted(BASE_ANALISE_VALUES)}",
        )


def _validate_gravidade(gravidade: str | None) -> None:
    if gravidade is None or gravidade == "todos":
        return
    if gravidade not in GRAVIDADE_VALUES:
        raise HTTPException(
            status_code=422,
            detail=f"gravidade '{gravidade}' invalid, expected one of "
            f"{sorted(GRAVIDADE_VALUES)} or 'todos'",
        )


def _validate_sintomas(sintomas: list[str] | None) -> None:
    if sintomas is None:
        return
    for s in sintomas:
        if s not in SYMPTOM_FIELDS:
            raise HTTPException(
                status_code=422,
                detail=f"sintoma '{s}' invalid, expected one of {sorted(SYMPTOM_FIELDS)}",
            )


def get_common_filters(
    years: Annotated[list[int] | None, Query()] = None,
    agents: Annotated[list[str] | None, Query()] = None,
    bairros: Annotated[list[str] | None, Query()] = None,
    classi: Annotated[list[int] | None, Query()] = None,
    base: Annotated[str | None, Query()] = None,
    gravidade: Annotated[str | None, Query()] = None,
    sintomas: Annotated[list[str] | None, Query()] = None,
) -> CommonFilters:
    """Dependency provider for common filters across endpoints."""
    _validate_years(years)
    _validate_classi(classi)
    _validate_string_lists(agents)
    _validate_string_lists(bairros)
    _validate_base(base)
    _validate_gravidade(gravidade)
    _validate_sintomas(sintomas)
    return CommonFilters(
        years=years,
        agents=agents,
        bairros=bairros,
        classi=classi,
        base=base,
        gravidade=gravidade,
        sintomas=sintomas,
    )


CommonFiltersDep = Annotated[CommonFilters, Depends(get_common_filters)]
