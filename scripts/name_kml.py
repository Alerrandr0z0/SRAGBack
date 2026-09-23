"""Backfill Placemark <name> labels in a derived copy of docs/BAIRROS.kml.

The cadastral source (Plano Diretor) stores the official label only in
ExtendedData/SimpleData[@name='nome'], so 32 of 36 placemarks open as
"untitled" in GIS viewers. This script writes docs/BAIRROS_nomeado.kml
with <name> set from the SimpleData 'nome' (exact PDF spelling, e.g.
"Santa Júlia" instead of the unaccented "Santa Julia" some placemarks
carry). Geometry and attributes are untouched; the source file is never
modified.

Verification: coordinate multiset identical before/after, 36/36 named.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)

SRC = Path(__file__).resolve().parent.parent / "docs" / "BAIRROS.kml"
DST = Path(__file__).resolve().parent.parent / "docs" / "BAIRROS_nomeado.kml"


def _qname(tag: str) -> str:
    return f"{{{KML_NS}}}{tag}"


def _official_name(pm: ET.Element) -> str | None:
    for data in pm.findall(f".//{_qname('SimpleData')}[@name='nome']"):
        if data.text and data.text.strip():
            return data.text.strip()
    return None


def _coordinates(pm: ET.Element) -> list[str]:
    return [
        tok
        for coords in pm.findall(f".//{_qname('coordinates')}")
        if coords.text
        for tok in coords.text.split()
    ]


def main() -> int:
    tree = ET.parse(SRC)
    root = tree.getroot()
    placemarks = root.findall(f".//{_qname('Placemark')}")
    print(f"Placemarks: {len(placemarks)}")

    before = sorted(tok for pm in placemarks for tok in _coordinates(pm))

    fixed = 0
    for pm in placemarks:
        official = _official_name(pm)
        if not official:
            print(f"  [warn] {pm.get('id')}: no SimpleData nome, skipped")
            continue
        name_el = pm.find(_qname("name"))
        if name_el is None:
            name_el = ET.Element(_qname("name"))
            name_el.text = official
            pm.insert(0, name_el)
            fixed += 1
        elif (name_el.text or "").strip() != official:
            print(f"  [rename] {pm.get('id')}: {name_el.text!r} -> {official!r}")
            name_el.text = official
            fixed += 1

    after = sorted(tok for pm in placemarks for tok in _coordinates(pm))
    assert before == after, "geometry changed during rename!"
    named = sum(1 for pm in placemarks if pm.find(_qname("name")) is not None)
    print(f"Backfilled/renamed: {fixed}; named now: {named}/{len(placemarks)}")

    tree.write(DST, encoding="utf-8", xml_declaration=True)
    print(f"Wrote: {DST}")
    return 0 if named == len(placemarks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
