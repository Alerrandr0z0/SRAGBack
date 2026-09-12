"""API dependency injections for SRAG Mossoró."""

from typing import Annotated

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel


class CommonFilters(BaseModel):
    """Filter parameters sent by the frontend (years/agents/bairros/classi)."""

    years: list[int] | None = None
    agents: list[str] | None = None
    bairros: list[str] | None = None
    classi: list[int] | None = None


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


def get_common_filters(
    years: Annotated[list[int] | None, Query()] = None,
    agents: Annotated[list[str] | None, Query()] = None,
    bairros: Annotated[list[str] | None, Query()] = None,
    classi: Annotated[list[int] | None, Query()] = None,
) -> CommonFilters:
    """Dependency provider for common filters across endpoints."""
    _validate_years(years)
    _validate_classi(classi)
    _validate_string_lists(agents)
    _validate_string_lists(bairros)
    return CommonFilters(
        years=years,
        agents=agents,
        bairros=bairros,
        classi=classi,
    )


CommonFiltersDep = Annotated[CommonFilters, Depends(get_common_filters)]
