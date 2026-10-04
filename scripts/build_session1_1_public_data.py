#!/usr/bin/env python3
"""Build app-ready Session 1.1 public network CSV files from documented public sources."""

from __future__ import annotations

import io
import subprocess
import urllib.request
import zipfile
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "data" / "public"
LAZEGA_URL = "https://www.stats.ox.ac.uk/~snijders/siena/LazegaLawyers.zip"


def extract_statnet() -> None:
    subprocess.run(
        [
            "Rscript",
            str(PROJECT_DIR / "scripts" / "extract_statnet_session1_1_data.R"),
            str(OUTPUT_DIR),
        ],
        check=True,
    )


def extract_lazega() -> None:
    with urllib.request.urlopen(LAZEGA_URL, timeout=60) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        advice = np.loadtxt(io.BytesIO(archive.read("ELadv.dat")), dtype=int)
        attributes = pd.read_csv(
            io.BytesIO(archive.read("ELattr.dat")), sep=r"\s+", header=None, dtype=str
        )
    if advice.shape != (71, 71) or int(advice.sum()) != 892:
        raise RuntimeError(
            f"Unexpected Lazega advice matrix check: shape={advice.shape}, ties={int(advice.sum())}."
        )
    if attributes.shape != (71, 8):
        raise RuntimeError(
            f"Unexpected Lazega attribute-table shape: {attributes.shape}."
        )
    attributes.columns = [
        "seniority",
        "status",
        "gender",
        "office",
        "years_firm",
        "age",
        "practice",
        "law_school",
    ]
    nodes = attributes.assign(
        id=[f"L{number:02d}" for number in range(1, 72)],
        status=attributes["status"]
        .map({"1": "partner", "2": "associate"})
        .fillna(attributes["status"]),
        gender=attributes["gender"]
        .map({"1": "man", "2": "woman"})
        .fillna(attributes["gender"]),
        office=attributes["office"]
        .map({"1": "Boston", "2": "Hartford", "3": "Providence"})
        .fillna(attributes["office"]),
        practice=attributes["practice"]
        .map({"1": "litigation", "2": "corporate"})
        .fillna(attributes["practice"]),
        law_school=attributes["law_school"]
        .map({"1": "Harvard/Yale", "2": "UConnecticut", "3": "other"})
        .fillna(attributes["law_school"]),
    )[
        [
            "id",
            "seniority",
            "status",
            "gender",
            "office",
            "years_firm",
            "age",
            "practice",
            "law_school",
        ]
    ]
    for column in ["seniority", "years_firm", "age"]:
        nodes[column] = pd.to_numeric(nodes[column], errors="raise")
    source, target = np.where(advice == 1)
    edges = pd.DataFrame(
        {
            "source": [f"L{number + 1:02d}" for number in source],
            "target": [f"L{number + 1:02d}" for number in target],
        }
    )
    nodes.to_csv(OUTPUT_DIR / "lazega_advice_nodes.csv", index=False)
    edges.to_csv(OUTPUT_DIR / "lazega_advice_edges.csv", index=False)


def extract_davis() -> None:
    graph = nx.davis_southern_women_graph()
    women = list(graph.graph["top"])
    events = list(graph.graph["bottom"])
    if len(women) != 18 or len(events) != 14 or graph.number_of_edges() != 89:
        raise RuntimeError(
            "The NetworkX Davis Southern Women graph failed its documented size check."
        )
    nodes = pd.DataFrame(
        {
            "id": [f"W_{name}" for name in women] + [f"E_{name}" for name in events],
            "mode": ["woman"] * len(women) + ["event"] * len(events),
            "label": women + events,
        }
    )
    edges = pd.DataFrame(
        {
            "source": [
                f"W_{source}" if source in women else f"E_{source}"
                for source, _ in graph.edges()
            ],
            "target": [
                f"W_{target}" if target in women else f"E_{target}"
                for _, target in graph.edges()
            ],
        }
    )
    nodes.to_csv(OUTPUT_DIR / "davis_affiliation_nodes.csv", index=False)
    edges.to_csv(OUTPUT_DIR / "davis_affiliation_edges.csv", index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    extract_statnet()
    extract_lazega()
    extract_davis()
    print(f"Wrote Session 1.1 public data to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
