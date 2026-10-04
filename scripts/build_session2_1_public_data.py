#!/usr/bin/env python3
"""Build app-ready public repeated-network panels for Session 2.1.

No fabricated or simulated network is used. Every output row derives from a documented
public source. Risk sets are made explicit where actor presence or dyad observation
changes over time.
"""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "data" / "public"
KNECHT_URL = "https://www.stats.ox.ac.uk/~snijders/siena/klas12b.zip"
COW_ALLIANCES_URL = "https://correlatesofwar.org/wp-content/uploads/version4.1_csv.zip"
COW_SYSTEM_URL = "https://correlatesofwar.org/wp-content/uploads/System2024.zip"
WINDSURFER_URL = "https://raw.githubusercontent.com/statnet/networkDynamic/master/data/windsurferPanels.rda"
COW_YEARS = list(range(1960, 1971))


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=180) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target)


def _write_panel(prefix: str, nodes: pd.DataFrame, edges: pd.DataFrame, risk: pd.DataFrame | None = None) -> None:
    nodes = nodes[["wave", "id"]].astype(str).sort_values(["wave", "id"])
    edges = edges[["wave", "source", "target"]].astype(str).sort_values(["wave", "source", "target"])
    nodes.to_csv(OUTPUT_DIR / f"{prefix}_nodes.csv", index=False)
    edges.to_csv(OUTPUT_DIR / f"{prefix}_edges.csv", index=False)
    if risk is not None:
        risk = risk[["wave", "source", "target"]].astype(str).sort_values(["wave", "source", "target"])
        risk.to_csv(OUTPUT_DIR / f"{prefix}_risk.csv", index=False)
    print(f"{prefix}: waves={nodes['wave'].nunique()}, node rows={len(nodes)}, edges={len(edges)}")


def _load_numeric_matrix(data: bytes) -> np.ndarray:
    matrix = np.loadtxt(io.BytesIO(data), dtype=int)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise RuntimeError(f"Expected a square adjacency matrix, got shape={matrix.shape}.")
    return matrix


def extract_knecht() -> None:
    """Extract four friendship panels and their observed-dyad sets without zero-filling 9/10."""
    with tempfile.TemporaryDirectory(prefix="knecht_") as directory:
        archive_path = Path(directory) / "klas12b.zip"
        download(KNECHT_URL, archive_path)
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            candidate_sets = []
            for wave in range(1, 5):
                found = [name for name in names if name.lower().endswith(f"net-{wave}.dat")]
                if len(found) != 1:
                    raise RuntimeError(f"Unable to locate unique klas12b wave {wave} network file: {found}")
                candidate_sets.append(found[0])
            matrices = [_load_numeric_matrix(archive.read(name)) for name in candidate_sets]
            if any(matrix.shape != (26, 26) for matrix in matrices):
                raise RuntimeError(f"Unexpected klas12b matrix shapes: {[matrix.shape for matrix in matrices]}")

            # Presence data record the documented departure. If unavailable, derive only a
            # conservative active set from rows/columns that are not entirely structural 10.
            present_candidates = [name for name in names if name.lower().endswith("present.dat")]
            present_intervals = None
            if len(present_candidates) == 1:
                present_intervals = np.loadtxt(
                    io.BytesIO(archive.read(present_candidates[0])), dtype=int
                )
                if present_intervals.shape != (26, 2):
                    raise RuntimeError(
                        f"Unexpected klas12b presence-interval shape: {present_intervals.shape}"
                    )

    node_rows: list[dict[str, str]] = []
    edge_rows: list[dict[str, str]] = []
    risk_rows: list[dict[str, str]] = []
    for wave_index, matrix in enumerate(matrices, start=1):
        wave = str(wave_index)
        if present_intervals is not None:
            active_indices = [
                index
                for index, (first_wave, last_wave) in enumerate(present_intervals)
                if int(first_wave) <= wave_index <= int(last_wave)
            ]
        else:
            active_indices = [
                index
                for index in range(26)
                if not (np.all(matrix[index, :] == 10) and np.all(matrix[:, index] == 10))
            ]
        for index in active_indices:
            node_rows.append({"wave": wave, "id": f"K{index + 1:02d}"})
        for source in active_indices:
            for target in active_indices:
                if source == target:
                    continue
                value = int(matrix[source, target])
                # 0 and 1 are observed outcomes; 9 and 10 are explicitly not risk-set zeros.
                if value not in {0, 1}:
                    continue
                source_id, target_id = f"K{source + 1:02d}", f"K{target + 1:02d}"
                risk_rows.append({"wave": wave, "source": source_id, "target": target_id})
                if value == 1:
                    edge_rows.append({"wave": wave, "source": source_id, "target": target_id})
    _write_panel(
        "knecht_friendship_temporal",
        pd.DataFrame(node_rows),
        pd.DataFrame(edge_rows),
        pd.DataFrame(risk_rows),
    )


def _read_csv_from_zip(archive: zipfile.ZipFile, predicate: callable) -> pd.DataFrame:
    matches = [
        name
        for name in archive.namelist()
        if not name.startswith("__MACOSX/") and not Path(name).name.startswith("._") and predicate(name.lower())
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one matching CSV in archive; found {matches}")
    return pd.read_csv(archive.open(matches[0]), low_memory=False)


def _member_rows(system: pd.DataFrame) -> pd.DataFrame:
    lower = {column.lower(): column for column in system.columns}
    country = next((lower[key] for key in ("ccode", "stateabb", "cowcode") if key in lower), None)
    year = lower.get("year")
    if country is None:
        raise RuntimeError(f"Could not identify a COW country-code column in {list(system.columns)}")
    if year:
        member = system[[year, country]].copy()
        member.columns = ["year", "ccode"]
        return member.loc[member["year"].isin(COW_YEARS)]
    start = next((lower[key] for key in ("styear", "startyear", "start_year") if key in lower), None)
    end = next((lower[key] for key in ("endyear", "end_year") if key in lower), None)
    if start is None or end is None:
        raise RuntimeError(f"Could not derive COW membership years from {list(system.columns)}")
    rows: list[dict[str, int]] = []
    for _, item in system.iterrows():
        first = int(item[start])
        last = int(item[end])
        for year_value in COW_YEARS:
            if first <= year_value <= last:
                rows.append({"year": year_value, "ccode": int(item[country])})
    return pd.DataFrame(rows)


def extract_cow_alliances() -> None:
    """Build an annual 1960–1970 binary COW alliance panel with a changing risk set."""
    with tempfile.TemporaryDirectory(prefix="cow_") as directory:
        directory_path = Path(directory)
        alliance_path = directory_path / "alliances.zip"
        system_path = directory_path / "system.zip"
        download(COW_ALLIANCES_URL, alliance_path)
        download(COW_SYSTEM_URL, system_path)
        with zipfile.ZipFile(alliance_path) as archive:
            alliances = _read_csv_from_zip(archive, lambda name: "by_dyad_yearly" in name and name.endswith(".csv"))
        with zipfile.ZipFile(system_path) as archive:
            system = _read_csv_from_zip(archive, lambda name: "system" in name and name.endswith(".csv"))

    columns = {column.lower(): column for column in alliances.columns}
    year_col = columns.get("year")
    first_col = next((columns[key] for key in ("ccode1", "state1", "cowcode1") if key in columns), None)
    second_col = next((columns[key] for key in ("ccode2", "state2", "cowcode2") if key in columns), None)
    if not all((year_col, first_col, second_col)):
        raise RuntimeError(f"Could not identify annual COW dyad columns in {list(alliances.columns)}")
    members = _member_rows(system)
    members["year"] = pd.to_numeric(members["year"], errors="raise").astype(int)
    members["ccode"] = pd.to_numeric(members["ccode"], errors="raise").astype(int)
    member_by_year = {
        year: set(members.loc[members["year"] == year, "ccode"].tolist())
        for year in COW_YEARS
    }
    if any(len(member_by_year[year]) < 2 for year in COW_YEARS):
        raise RuntimeError("At least one requested COW year has fewer than two system members.")
    annual = alliances.loc[pd.to_numeric(alliances[year_col], errors="coerce").isin(COW_YEARS), [year_col, first_col, second_col]].copy()
    annual.columns = ["year", "ccode1", "ccode2"]
    annual = annual.apply(pd.to_numeric, errors="raise").astype(int)

    node_rows: list[dict[str, str]] = []
    edge_rows: list[dict[str, str]] = []
    for year in COW_YEARS:
        codes = sorted(member_by_year[year])
        node_rows.extend({"wave": str(year), "id": f"COW_{code}", "ccode": str(code)} for code in codes)
        active_pairs = annual.loc[annual["year"] == year, ["ccode1", "ccode2"]].drop_duplicates()
        for first, second in active_pairs.itertuples(index=False, name=None):
            if first in member_by_year[year] and second in member_by_year[year] and first != second:
                source, target = sorted((int(first), int(second)))
                edge_rows.append({"wave": str(year), "source": f"COW_{source}", "target": f"COW_{target}"})
    _write_panel("cow_alliances_1960_1970_temporal", pd.DataFrame(node_rows), pd.DataFrame(edge_rows))


def extract_statnet_panels() -> None:
    """Download the public daily panel archive and call the R extractor for three sources."""
    with tempfile.TemporaryDirectory(prefix="statnet_temporal_") as directory:
        wind_path = Path(directory) / "windsurferPanels.rda"
        download(WINDSURFER_URL, wind_path)
        subprocess.run(
            [
                "Rscript",
                str(PROJECT_DIR / "scripts" / "extract_session2_1_r_data.R"),
                str(OUTPUT_DIR),
                str(wind_path),
            ],
            check=True,
        )
    windsurfer_nodes_path = OUTPUT_DIR / "windsurfers_interaction_temporal_nodes.csv"
    windsurfer_nodes = pd.read_csv(windsurfer_nodes_path, dtype={"wave": str, "id": str})
    # Date 921 is a documented missing panel. Keep both observed runs but do not
    # create a false one-day lag from 920 to 922.
    windsurfer_nodes["transition_block"] = np.where(
        pd.to_numeric(windsurfer_nodes["wave"], errors="raise") <= 920,
        "before_missing_921",
        "after_missing_921",
    )
    windsurfer_nodes.to_csv(windsurfer_nodes_path, index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extract_knecht()
    extract_statnet_panels()
    extract_cow_alliances()
    print(f"Wrote Session 2.1 public temporal data to {OUTPUT_DIR}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Session 2.1 public-data build failed: {error}", file=sys.stderr)
        raise
