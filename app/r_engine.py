"""Thin, auditable subprocess bridge from Streamlit to standard R ERGM routines."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
R_FIT_SCRIPT = PROJECT_DIR / "r" / "fit_static_ergm.R"
R_SESSION12_FIT_SCRIPT = PROJECT_DIR / "r" / "fit_session1_2_ergm.R"
R_SAOM_FIT_SCRIPT = PROJECT_DIR / "r" / "fit_saom.R"
R_BOOTSTRAP_SCRIPT = PROJECT_DIR / "r" / "bootstrap_packages.R"


class ErgMRuntimeError(RuntimeError):
    """Raised when the R/statnet execution environment is unavailable or returns invalid output."""


class SAOMRuntimeError(RuntimeError):
    """Raised when the pre-provisioned RSiena engine is unavailable or returns an error."""


def rscript_path() -> str | None:
    return shutil.which("Rscript")


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    # Writable in local and Streamlit-hosted environments; the bootstrap helper uses it.
    environment.setdefault("R_LIBS_USER", str(Path.home() / ".local" / "R" / "library"))
    return environment


def engine_status(timeout_seconds: int = 15) -> dict[str, Any]:
    """Report only verifiable runtime facts; no package install is performed implicitly."""
    executable = rscript_path()
    if executable is None:
        return {"available": False, "reason": "Rscript is not installed."}
    command = [
        executable,
        "-e",
        "cat(if (requireNamespace('ergm', quietly=TRUE)) 'READY' else 'MISSING')",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=_environment(),
        check=False,
    )
    ready = completed.returncode == 0 and completed.stdout.strip() == "READY"
    return {
        "available": ready,
        "reason": "ready"
        if ready
        else "The R package `ergm` is not installed in the active R library.",
        "rscript": executable,
        "stderr": completed.stderr.strip(),
    }


def install_engine(timeout_seconds: int = 1200) -> dict[str, Any]:
    """Install network/ergm/jsonlite into the user-writable R library when explicitly requested."""
    executable = rscript_path()
    if executable is None:
        raise ErgMRuntimeError(
            "Rscript is not installed. Install R before installing the ERGM engine."
        )
    completed = subprocess.run(
        [executable, str(R_BOOTSTRAP_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=_environment(),
        check=False,
    )
    if completed.returncode != 0:
        raise ErgMRuntimeError(
            (
                completed.stderr or completed.stdout or "R package installation failed."
            ).strip()
        )
    return engine_status()


def fit_static_ergm(
    payload: dict[str, Any], timeout_seconds: int = 480
) -> dict[str, Any]:
    """Run the repository's R engine and return its structured result without shell interpolation."""
    status = engine_status()
    if not status["available"]:
        raise ErgMRuntimeError(status["reason"])
    with tempfile.TemporaryDirectory(prefix="static_ergm_") as temporary_directory:
        directory = Path(temporary_directory)
        input_path = directory / "input.json"
        output_path = directory / "output.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False))
        completed = subprocess.run(
            [status["rscript"], str(R_FIT_SCRIPT), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=_environment(),
            check=False,
        )
        if not output_path.exists():
            message = (
                completed.stderr
                or completed.stdout
                or "The ERGM engine did not create a result file."
            ).strip()
            raise ErgMRuntimeError(message)
        result = json.loads(output_path.read_text())
        if result.get("status") != "ok":
            raise ErgMRuntimeError(
                result.get(
                    "message", "The R ERGM engine returned an unspecified error."
                )
            )
        if isinstance(result.get("warnings"), str):
            result["warnings"] = [result["warnings"]]
        elif result.get("warnings") is None:
            result["warnings"] = []
        result["r_stdout"] = completed.stdout.strip()
        result["r_stderr"] = completed.stderr.strip()
        return result


def fit_session12_ergm(
    payload: dict[str, Any], timeout_seconds: int = 900
) -> dict[str, Any]:
    """Run the Session 1.2 curved/stable ERGM engine with full diagnostics."""
    status = engine_status()
    if not status["available"]:
        raise ErgMRuntimeError(status["reason"])
    with tempfile.TemporaryDirectory(prefix="session12_ergm_") as temporary_directory:
        directory = Path(temporary_directory)
        input_path = directory / "input.json"
        output_path = directory / "output.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False))
        completed = subprocess.run(
            [
                status["rscript"],
                str(R_SESSION12_FIT_SCRIPT),
                str(input_path),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=_environment(),
            check=False,
        )
        if not output_path.exists():
            message = (
                completed.stderr
                or completed.stdout
                or "The Session 1.2 ERGM engine did not create a result file."
            ).strip()
            raise ErgMRuntimeError(message)
        result = json.loads(output_path.read_text())
        if result.get("status") != "ok":
            raise ErgMRuntimeError(
                result.get(
                    "message",
                    "The Session 1.2 ERGM engine returned an unspecified error.",
                )
            )
        for field in ("warnings", "diagnostic_flags"):
            if isinstance(result.get(field), str):
                result[field] = [result[field]]
            elif result.get(field) is None:
                result[field] = []
        result["r_stdout"] = completed.stdout.strip()
        result["r_stderr"] = completed.stderr.strip()
        return result


def saom_engine_status(timeout_seconds: int = 15) -> dict[str, Any]:
    """Report the deployed RSiena runtime without installing packages at request time."""
    executable = rscript_path()
    if executable is None:
        return {"available": False, "reason": "Rscript is not installed."}
    completed = subprocess.run(
        [
            executable,
            "-e",
            "cat(if (requireNamespace('RSiena', quietly=TRUE) && requireNamespace('jsonlite', quietly=TRUE)) 'READY' else 'MISSING')",
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=_environment(),
        check=False,
    )
    ready = completed.returncode == 0 and completed.stdout.strip() == "READY"
    return {
        "available": ready,
        "reason": "ready"
        if ready
        else "The R package `RSiena` is not installed in the active R library.",
        "rscript": executable,
        "stderr": completed.stderr.strip(),
    }


def fit_saom(payload: dict[str, Any], timeout_seconds: int = 1200) -> dict[str, Any]:
    """Run the stated RSiena SAOM without shell interpolation or hidden package installation."""
    status = saom_engine_status()
    if not status["available"]:
        raise SAOMRuntimeError(status["reason"])
    with tempfile.TemporaryDirectory(prefix="day3_saom_") as temporary_directory:
        directory = Path(temporary_directory)
        input_path = directory / "input.json"
        output_path = directory / "output.json"
        input_path.write_text(json.dumps(payload, ensure_ascii=False))
        completed = subprocess.run(
            [
                status["rscript"],
                str(R_SAOM_FIT_SCRIPT),
                str(input_path),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=_environment(),
            check=False,
        )
        if not output_path.exists():
            message = (
                completed.stderr
                or completed.stdout
                or "The RSiena engine did not create a result file."
            ).strip()
            raise SAOMRuntimeError(message)
        result = json.loads(output_path.read_text())
        if result.get("status") != "ok":
            raise SAOMRuntimeError(
                result.get(
                    "message", "The RSiena engine returned an unspecified error."
                )
            )
        for field in ("notes",):
            if isinstance(result.get(field), str):
                result[field] = [result[field]]
            elif result.get(field) is None:
                result[field] = []
        result["r_stdout"] = completed.stdout.strip()
        result["r_stderr"] = completed.stderr.strip()
        return result
