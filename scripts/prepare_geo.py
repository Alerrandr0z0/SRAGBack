"""Prepare the SINAN-30 candidate GeoJSON from docs/BAIRROS_nomeado.kml.

Reads the 37 polygons of the derived KML (36 cadastral + Alagados) and groups them under the
30 SINAN Online labels (FotoBairros-1-2.pdf), dissolving sub-polygons per
label with shapely so shared borders (e.g. Abolicao I-V) render as one
bairro. Alagados wins over its neighbors: its ring is cut out of Belo
Horizonte and Planalto 13 de Maio so it renders instead of being buried.

Output (candidate only, never overwrites production):
    data/geojson/mossoro_bairros_sinan30.geojson

Sync: when the sibling SRAGFront checkout is present, the same payload is
also written to SRAGFront/public/geo/mossoro_bairros.geojson — the file the
front "Mapa territorial" component loads. The map changes rarely, so a
static copy with explicit sync (instead of an API endpoint) is enough.

Plus a console gap report: SINAN labels without geometry and KML polygons
without a confirmed SINAN parent.
"""

from __future__ import annotations

import json
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

# Path adjustment for local imports (same pattern as ingest_data.py)
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from shapely.geometry import MultiPolygon, Polygon, mapping  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from shapely.validation import make_valid  # noqa: E402

if TYPE_CHECKING:
    from shapely.geometry.base import BaseGeometry

from srag.data.loader import OFFICIAL_BAIRROS  # noqa: E402

KML_PATH = Path(__file__).resolve().parent.parent / "docs" / "BAIRROS_nomeado.kml"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "geojson" / "mossoro_bairros_sinan30.geojson"

# Static-asset sync: the front "Mapa territorial" loads this file, so every
# run also refreshes it. Written only when the sibling checkout layout is
# present; otherwise skipped with a warning so backend-only environments
# (e.g. Docker) keep working.
FRONT_GEO_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "SRAGFront"
    / "public"
    / "geo"
    / "mossoro_bairros.geojson"
)

NS = {"kml": "http://www.opengis.net/kml/2.2"}

# The 30 SINAN Online labels (display form, as in FotoBairros-1-2.pdf).
SINAN_30 = [
    "ABOLIÇÕES",
    "AEROPORTO",
    "ALTO DE SÃO MANOEL",
    "ALTO DO SUMARÉ",
    "ALTO DA CONCEIÇÃO",
    "ALTO DA BELA VISTA",
    "ALAGADOS",
    "BARROCAS",
    "BOM JARDIM",
    "BELO HORIZONTE",
    "BOA VISTA",
    "BOM JESUS",
    "CENTRO",
    "COSTA E SILVA",
    "DOM JAIME CÂMARA",
    "DOZE ANOS",
    "GOV DIX SEPT ROSADO",
    "ITAPETINGA",
    "ILHA DE SANTA LUZIA",
    "LAGOA DO MATO",
    "MONSENHOR ALFREDO SIMONETI",
    "NOVA BETÂNIA",
    "PINTOS",
    "PAREDÕES",
    "PLANALTO 13 DE MAIO",
    "REDENÇÃO",
    "RINCÃO",
    "SANTO ANTÔNIO",
    "SANTA DELMIRA",
    "SANTA JÚLIA",
]

# KML <nome> -> SINAN display label. Identity mappings are explicit so the
# report can tell "confirmed" from "missing".
KML_TO_SINAN: dict[str, str] = {
    "Abolição I": "ABOLIÇÕES",
    "Abolição II": "ABOLIÇÕES",
    "Abolição III": "ABOLIÇÕES",
    "Abolição IV": "ABOLIÇÕES",
    "Abolição V": "ABOLIÇÕES",
    "Aeroporto I": "AEROPORTO",
    "Aeroporto II": "AEROPORTO",
    "Alto de São Manoel": "ALTO DE SÃO MANOEL",
    "Alto da Conceição": "ALTO DA CONCEIÇÃO",
    "Boa Vista": "BOA VISTA",
    "Bom Jardim": "BOM JARDIM",
    "Bom Jesus": "BOM JESUS",
    "Barrocas": "BARROCAS",
    "Belo Horizonte": "BELO HORIZONTE",
    "Centro": "CENTRO",
    "Doze Anos": "DOZE ANOS",
    "Nova Betânia": "NOVA BETÂNIA",
    "Sumaré": "ALTO DO SUMARÉ",
    "Presidente Costa e Silva": "COSTA E SILVA",
    "Dix-Sept Rosado": "GOV DIX SEPT ROSADO",
    "Dom Jaime Câmara": "DOM JAIME CÂMARA",
    "Ilha de Santa Luzia": "ILHA DE SANTA LUZIA",
    "Lagoa do Mato": "LAGOA DO MATO",
    "Paredões": "PAREDÕES",
    "Pintos": "PINTOS",
    "Planalto Treze de Maio": "PLANALTO 13 DE MAIO",
    "Cidade Oeste": "ITAPETINGA",
    "Vingt Rosado": "RINCÃO",
    # Trinta de Setembro is a cadastral polygon aggregated into RINCÃO
    # per vigilância definition (shares 4 vertices with Vingt Rosado).
    "Trinta de Setembro": "RINCÃO",
    "Américo Simonete": "MONSENHOR ALFREDO SIMONETI",
    "Santa Júlia": "SANTA JÚLIA",
    "Nova Mossoró": "SANTA JÚLIA",
    "Santa Delmira": "SANTA DELMIRA",
    "Santo Antônio": "SANTO ANTÔNIO",
    "Redenção": "REDENÇÃO",
    # Bela Vista (KML) is ALTO DA BELA VISTA (SINAN), confirmed per vigilância.
    "Bela Vista": "ALTO DA BELA VISTA",
    # Alagados ring comes from the production geojson (vigilância artifact);
    # KML/PDF carry no Alagados polygon.
    "Alagados": "ALAGADOS",
}

# KML polygons with no SINAN parent (reported, excluded from the candidate).
# Currently empty: Trinta de Setembro was assigned to RINCÃO per vigilância.
UNMAPPED: dict[str, str] = {}


def _norm(text: str) -> str:
    """Uppercase unaccented form, matching loader normalization."""
    text = "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )
    return " ".join(text.upper().split())


def _placemark_name(pm: ET.Element) -> str | None:
    for data in pm.findall(".//kml:SimpleData[@name='nome']", NS):
        if data.text and data.text.strip():
            return data.text.strip()
    name_el = pm.find("kml:name", NS)
    if name_el is not None and name_el.text and name_el.text.strip():
        return name_el.text.strip()
    return None


def _parse_ring(ring: ET.Element) -> list[list[float]]:
    coords_el = ring.find("kml:coordinates", NS)
    if coords_el is None or not coords_el.text:
        return []
    pts: list[list[float]] = []
    for tok in coords_el.text.split():
        parts = tok.split(",")
        if len(parts) >= 2:
            pts.append([float(parts[0]), float(parts[1])])
    return pts


def _parse_kml(path: Path) -> list[tuple[str, list[list[list[list[float]]]]]]:
    """Return [(nome, [polygons])], each polygon = [outer, hole, ...]."""
    root = ET.parse(path).getroot()
    out: list[tuple[str, list[list[list[list[float]]]]]] = []
    for pm in root.findall(".//kml:Placemark", NS):
        nome = _placemark_name(pm)
        if not nome:
            continue
        polys: list[list[list[list[float]]]] = []
        for poly in pm.findall(".//kml:Polygon", NS):
            rings: list[list[list[float]]] = []
            outer = poly.find("kml:outerBoundaryIs/kml:LinearRing", NS)
            if outer is not None:
                rings.append(_parse_ring(outer))
            for inner in poly.findall("kml:innerBoundaryIs/kml:LinearRing", NS):
                rings.append(_parse_ring(inner))
            if rings and rings[0]:
                polys.append(rings)
        out.append((nome, polys))
    return out


# Clean partition: sequential precedence differencing so no two labels
# overlap with nonzero area (overlaps render as stray interior strokes).
# ALAGADOS first (it wins everywhere, incl. BH/Planalto), then the rest by
# descending area so big polygons keep their shape.
_CLEAN_ORDER = ["ALAGADOS"]


def _clean_partition(dissolved: dict) -> dict:
    order = [label for label in _CLEAN_ORDER if label in dissolved] + sorted(
        (label for label in dissolved if label not in _CLEAN_ORDER),
        key=lambda label: dissolved[label].area,
        reverse=True,
    )
    placed: dict = {}
    occupied = None
    for label in order:
        geom = dissolved[label]
        if occupied is not None and not occupied.is_empty:
            inter = geom.intersection(occupied)
            if not inter.is_empty and inter.area > 0:
                print(f"  [partition] cut {inter.area:.6f} deg² from {label}")
                geom = _polygonal(geom.difference(occupied))
                if not geom.is_valid:
                    geom = make_valid(geom)
        placed[label] = geom
        occupied = geom if occupied is None else occupied.union(geom)
    return placed


def _to_polygons(polys: list[list[list[list[float]]]]) -> list[Polygon]:
    """KML [outer, hole, ...] rings -> valid shapely Polygons."""
    out: list[Polygon] = []
    for rings in polys:
        if not rings or not rings[0]:
            continue
        geom: Polygon = Polygon(rings[0], holes=rings[1:] or None)
        if not geom.is_valid:
            geom = make_valid(geom)
        out.append(geom)
    return out


def _polygonal(geom: BaseGeometry) -> BaseGeometry:
    """Keep only the polygonal parts (make_valid can add points/lines)."""
    if geom.is_empty:
        return geom
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    parts = [
        g
        for g in getattr(geom, "geoms", [])
        if g.geom_type == "Polygon" or g.geom_type == "MultiPolygon"
    ]
    flat = [p for part in parts for p in (part.geoms if part.geom_type == "MultiPolygon" else [part])]
    return MultiPolygon(flat) if flat else geom


def _fill_orphan_holes(dissolved: dict) -> dict:
    """Fill interior rings no other label claims (union artifacts).

    Kept holes would render as stray interior strokes; a hole is only kept
    when another label actually occupies it (genuine enclave).
    """
    labels = list(dissolved)
    out: dict = {}
    for label in labels:
        geom = dissolved[label]
        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        fixed = []
        for part in parts:
            if part.geom_type != "Polygon" or not part.interiors:
                fixed.append(part)
                continue
            keep = [
                ring
                for ring in part.interiors
                if any(
                    dissolved[other].intersection(Polygon(ring)).area > 1e-12
                    for other in labels
                    if other != label
                )
            ]
            if len(keep) != len(part.interiors):
                print(f"  [holes] {label}: filled {len(part.interiors) - len(keep)} orphan hole(s)")
            fixed.append(Polygon(part.exterior.coords, holes=keep or None))
        out[label] = (
            MultiPolygon(fixed)
            if len(fixed) > 1 or geom.geom_type == "MultiPolygon"
            else fixed[0]
        )
    return out


def main() -> int:
    placemarks = _parse_kml(KML_PATH)
    print(f"KML placemarks: {len(placemarks)}")

    grouped: dict[str, list[list[list[list[float]]]]] = {}
    unknown: list[str] = []
    for nome, polys in placemarks:
        if nome in UNMAPPED:
            print(f"  [unmapped] {nome}: {UNMAPPED[nome]}")
            continue
        target = KML_TO_SINAN.get(nome)
        if target is None:
            unknown.append(nome)
            continue
        grouped.setdefault(target, []).extend(polys)

    # Dissolve sub-polygons per SINAN label so shared borders disappear.
    dissolved = {}
    for label, polys in grouped.items():
        union = unary_union(_to_polygons(polys))
        union = _polygonal(union if union.is_valid else make_valid(union))
        dissolved[label] = union
    for label in sorted(dissolved):
        n_in = len(grouped[label])
        geom = dissolved[label]
        n_out = len(geom.geoms) if geom.geom_type == "MultiPolygon" else 1
        if n_in > 1 or n_in != n_out:
            print(f"  [dissolve] {label}: {n_in} polys -> {n_out}")

    # Clean partition: no two labels overlap (Alagados wins everywhere).
    dissolved = _clean_partition(dissolved)
    # Fill orphan holes (union artifacts that render as interior strokes).
    dissolved = _fill_orphan_holes(dissolved)

    if unknown:
        print(f"  [unknown] {len(unknown)} KML nomes sem mapeamento: {sorted(set(unknown))}")

    confirmed = set(KML_TO_SINAN.values())
    missing = [label for label in SINAN_30 if label not in confirmed]
    print(f"\nSINAN coverage: {len(confirmed)}/30 with geometry")
    if missing:
        print(f"  [missing geometry] {missing}")

    partial = sorted(
        label
        for label, polys in grouped.items()
        if len(polys) == 1
        and label in {"ITAPETINGA", "RINCÃO", "ALTO DA BELA VISTA", "MONSENHOR ALFREDO SIMONETI"}
    )
    if partial:
        print(f"  [partial: single sub-polygon only] {partial}")

    # Cross-check display labels against the loader canonical set.
    loader_missing = [label for label in SINAN_30 if _norm(label) not in OFFICIAL_BAIRROS]
    if loader_missing:
        print(f"  [loader mismatch] SINAN labels not in OFFICIAL_BAIRROS: {loader_missing}")
    else:
        print("  loader OFFICIAL_BAIRROS: 30/30 SINAN labels matched")

    features = []
    for label in sorted(grouped):
        geom = dissolved[label]
        if geom.is_empty:
            print(f"  [empty geometry] {label}")
            continue
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        features.append(
            {
                "type": "Feature",
                "properties": {"bairro": label},
                "geometry": {"type": "MultiPolygon", "coordinates": mapping(geom)["coordinates"]},
            }
        )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"type": "FeatureCollection", "features": features}, ensure_ascii=False
    )
    OUT_PATH.write_text(payload, encoding="utf-8")
    print(f"\nCandidate written: {OUT_PATH} ({len(features)} features)")
    if FRONT_GEO_PATH.parent.is_dir():
        FRONT_GEO_PATH.write_text(payload, encoding="utf-8")
        print(f"Front copy synced: {FRONT_GEO_PATH}")
    else:
        print(f"NOTE: front copy skipped, dir not found: {FRONT_GEO_PATH.parent}")
    print("NOTE: per-label dissolve + Alagados cut applied (shapely).")
    return 0 if not unknown and not loader_missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
