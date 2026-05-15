#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path


def fmt(x: str, whole: bool = False) -> str:
    try:
        return str(int(float(x))) if whole else f"{float(x):.4f}"
    except Exception:
        return x


def latex_escape(x: str) -> str:
    return x.replace("_", "\\_")


def resolve_input(arg: str | None) -> Path:
    if arg in (None, "smaller", "large"):
        mode = "smaller" if arg is None else arg
        p = Path(f"camera_results_{mode}.csv")
        if p.exists():
            return p
        if mode == "smaller" and Path("camera_results.csv").exists():
            return Path("camera_results.csv")
        return p
    return Path(arg)


def f1(v: str | None) -> str:
    try:
        return f"{float(v):.1f}"
    except Exception:
        return "-"


def f2(v: str | None) -> str:
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "-"


def cell(row: dict[str, str] | None, n: int, load: int) -> tuple[str, str, str, str, str]:
    if row is None:
        return str(n), f"{load}\\%", "-", "-", "-"
    try:
        pr = float(row.get("pr_upper", ""))
        yn = "Y" if pr <= 0.05 else "N"
        yn = rf"\textbf{{{yn}}}"
    except Exception:
        yn = "-"
    return str(n), f"{load}\\%", yn, f1(row.get("e_viol")), f2(row.get("q2_s"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="smaller|large or explicit csv path")
    args = parser.parse_args()
    inp = resolve_input(args.input)
    if not inp.exists():
        raise SystemExit(f"CSV not found: {inp}. Run 'python camera_experiments.py smaller' or 'python camera_experiments.py large' first.")
    rows = list(csv.DictReader(inp.open()))
    data: dict[tuple[int, int], dict[str, str]] = {}
    for r in rows:
        n = int(float(r["n"]))
        load = int(float(r["load"]))
        data[(n, load)] = r

    print(r"\begin{table}")
    print(r"\centering")
    print(r"\begin{tabular}{|c|c|c|c|c|c|c|c|c|c|}")
    print(r"\hline")
    print(r"\#Cams & Load & $\leq 850$ & E(viol) & Time & \#Cams & Load & $\leq 850$ & E(viol) & Time\\")
    print(r"\hline")
    loads = [25, 50, 75, 100]
    for left in (1, 3, 5, 7, 9):
        right = left + 1
        for load in loads:
            l = cell(data.get((left, load)), left, load)
            r = cell(data.get((right, load)), right, load)
            print(" & ".join([l[0], l[1], l[2], l[3], l[4], r[0], r[1], r[2], r[3], r[4]]) + r"\\")
        print(r"\hline")
    print(r"\end{tabular}")
    print(r"\caption{Combined industrial-example results with fixed queue policy drop\_oldest.}")
    print(r"\label{table:usecaseresults}")
    print(r"\end{table}")


if __name__ == "__main__":
    main()
