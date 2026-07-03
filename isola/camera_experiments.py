#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
import time
from pathlib import Path

from generate_xml import render_xml

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.xml"
# (monitors, smc_horizon) per size
SIZE_PARAMS = {"small": (10, 10000), "large": (20, 20000)}

# Adjust path for your system
VERIFYTA = Path("/home/ptr/ISoLA/ros2-modeling/verifyta")
FIXED_POLICY = "drop_oldest"
Q_PR_MISS = "Pr[<=SMC_HORIZON] (<> deadline_missed)"
Q_E_VIOL = "E[<=SMC_HORIZON;3000] (max: deadlines_missed)"
Q_E_DROP = "E[<=850;3000](max: dropped_packets)"
MODELS_DIR = HERE / "models"

PR_RE = re.compile(r"Pr\(<>.*?\) in \[([0-9.eE+\-]+),\s*([0-9.eE+\-]+)\]")
MEAN_RE = re.compile(r"mean=([0-9.eE+\-]+)")


def instantiate(n: int, load: int, out_xml: Path, deterministic_host: bool, monitors: int, smc_horizon: int) -> None:
    render_xml(
        TEMPLATE, out_xml, n, load, FIXED_POLICY,
        deterministic_host=deterministic_host, monitors=monitors, smc_horizon=smc_horizon,
    )


def _model_path(n: int, load: int, size: str, deterministic_host: bool) -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    host_mode = "det" if deterministic_host else "nondet"
    return MODELS_DIR / f"{size}_{n}_cameras_{load}_load_{host_mode}.xml"


def _run(cmd: list[str], timeout: int) -> str | None:
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
        return p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return None


def _pr(text: str | None) -> float | None:
    if not text:
        return None
    m = PR_RE.search(text)
    return float(m.group(2)) if m else None


def _mean(text: str | None) -> float | None:
    if not text:
        return None
    m = MEAN_RE.search(text)
    return float(m.group(1)) if m else None


def _run_formula(xml: Path, formula: str, timeout: int) -> str | None:
    with tempfile.NamedTemporaryFile("w", suffix=".q", delete=False) as f:
        f.write(formula + "\n")
        q = Path(f.name)
    try:
        return _run([str(VERIFYTA), str(xml), str(q)], timeout)
    finally:
        q.unlink(missing_ok=True)


def run_case(n: int, load: int, size: str, deterministic_host: bool, timeout: int = 120) -> dict:
    monitors, smc_horizon = SIZE_PARAMS[size]
    xml = _model_path(n, load, size, deterministic_host)
    t0 = time.time(); instantiate(n, load, xml, deterministic_host, monitors, smc_horizon); gen_s = time.time() - t0
    t0 = time.time(); q2 = _run_formula(xml, Q_PR_MISS, timeout); q2_s = time.time() - t0
    t0 = time.time(); q4 = _run_formula(xml, Q_E_VIOL, timeout); q4_s = time.time() - t0
    t0 = time.time(); qd = _run_formula(xml, Q_E_DROP, timeout); drop_s = time.time() - t0
    return {"n": n, "load": load, "pr_upper": _pr(q2), "e_viol": _mean(q4),
            "e_dropped": _mean(qd), "gen_s": gen_s, "q2_s": q2_s, "q4_s": q4_s, "drop_s": drop_s,
            "deterministic_host": deterministic_host, "model_xml": str(xml)}


def sweep(size: str = "smaller") -> None:
    model_size = "small" if size == "smaller" else "large"
    for deterministic_host in (True, False):
        out_suffix = "det_true" if deterministic_host else "det_false"
        out_csv = f"camera_results_{size}_{out_suffix}.csv"
        rows = []
        for n in range(1, 11):
            for load in (25, 50, 75, 100):
                print(
                    f"size={size} n={n} load={load} policy={FIXED_POLICY} "
                    f"deterministic_host={deterministic_host}"
                )
                rows.append(run_case(n, load, model_size, deterministic_host=deterministic_host))
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        print(f"wrote {out_csv}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("size", nargs="?", default="smaller", choices=("smaller", "large"))
    sweep(parser.parse_args().size)
