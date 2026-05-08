#!/usr/bin/env python3
"""Instantiate multisrc_v1.xml from a JSON specification."""

import json
import os
import sys
from pathlib import Path


def _const(name: str) -> str:
    return name.upper()


def _instance(name: str) -> str:
    return name.lower()


def _generator_timing_symbol(gen: dict, kind: str) -> str:
    explicit = gen.get(f"{kind}_const")
    if explicit:
        return str(explicit)

    gname = _const(gen["name"])
    if gname.startswith("GEN_"):
        base = gname[4:] + "_GEN"
    else:
        base = gname + "_GEN"
    return f"{base}_{kind.upper()}"


def _queue_policy_const(policy: str) -> str:
    normalized = policy.strip().lower()
    mapping = {
        "drop_newest": "POLICY_DROP_NEWEST",
        "drop_oldest": "POLICY_DROP_OLDEST",
        "drop_lowest_prio": "POLICY_DROP_LOWEST_PRIO",
    }
    if normalized not in mapping:
        raise ValueError(
            "queue_policy must be one of: drop_newest, drop_oldest, drop_lowest_prio"
        )
    return mapping[normalized]


def _timer_symbol(timer: dict, kind: str) -> str:
    explicit = timer.get(f"{kind}_const")
    if explicit:
        return str(explicit)

    tname = _const(timer["name"])
    return f"{tname}_{kind.upper()}"


def _symbol_or_expr(value: str) -> str:
    text = str(value).strip()
    if text == "":
        raise ValueError("symbol/expression must be non-empty")
    if text.lower() == "pd" or text.lower() == "ps":
        return text.lower()
    if any(ch.islower() for ch in text):
        return text
    if any(ch in text for ch in "[]()+-*/ "):
        return text
    return _const(text)


def _parse_subprocesses(
    owner_task: str,
    subprocesses: list,
    known_nodes: set[str],
    default_prio: int,
) -> list[dict]:
    parsed: list[dict] = []
    owner = _const(owner_task)

    for entry in subprocesses:
        if isinstance(entry, str):
            entry = {"source": entry}

        source = _const(entry["source"])
        if source not in known_nodes:
            raise ValueError(f"subprocess source '{source}' must be one of nodes")

        if "wcet" not in entry:
            raise ValueError(
                f"subprocess for '{owner}' from '{source}' must define 'wcet'"
            )

        name = _const(entry.get("name", f"{owner}x{source}"))
        parsed.append(
            {
                "name": name,
                "source": source,
                "data_source": str(entry.get("data_source", "pd")),
                "src": str(entry.get("src", source)),
                "wcet": int(entry["wcet"]),
                "prio": int(entry.get("prio", default_prio)),
                "instance": str(entry.get("instance", _instance(name))),
            }
        )

    return parsed


def _collect_expanded_nodes(spec: dict) -> tuple[list[dict], dict[str, list[dict]]]:
    base_nodes = spec["nodes"]
    subscribers = spec.get("subscribers", [])
    timers = spec.get("timers", [])

    node_names = {_const(node["name"]) for node in base_nodes}
    node_prios = {_const(node["name"]): int(node["prio"]) for node in base_nodes}

    expanded_nodes: list[dict] = [
        {
            "name": _const(node["name"]),
            "wcet": int(node["wcet"]),
            "prio": int(node["prio"]),
        }
        for node in base_nodes
    ]

    subprocesses_by_owner: dict[str, list[dict]] = {}
    all_subprocesses: list[dict] = []

    for entry in subscribers:
        owner = _const(entry["task"])
        if owner not in node_names:
            raise ValueError(f"subscriber task '{owner}' must be one of nodes")
        parsed = _parse_subprocesses(
            owner_task=owner,
            subprocesses=entry.get("subprocesses", []),
            known_nodes=node_names,
            default_prio=node_prios[owner],
        )
        if parsed:
            subprocesses_by_owner.setdefault(owner, []).extend(parsed)
            all_subprocesses.extend(parsed)

    for entry in timers:
        owner = _const(entry["task"])
        if owner not in node_names:
            raise ValueError(f"timer task '{owner}' must be one of nodes")
        parsed = _parse_subprocesses(
            owner_task=owner,
            subprocesses=entry.get("subprocesses", []),
            known_nodes=node_names,
            default_prio=node_prios[owner],
        )
        if parsed:
            subprocesses_by_owner.setdefault(owner, []).extend(parsed)
            all_subprocesses.extend(parsed)

    seen_names = set(node_names)
    for proc in all_subprocesses:
        pname = proc["name"]
        if pname in seen_names:
            raise ValueError(f"subprocess node name '{pname}' duplicates an existing node")
        seen_names.add(pname)
        expanded_nodes.append(
            {
                "name": pname,
                "wcet": proc["wcet"],
                "prio": proc["prio"],
            }
        )

    return expanded_nodes, subprocesses_by_owner


def _build_monitor_invariant(monitors: int) -> str:
    clauses = [
        "(monitor_payload[{i}] == 0 || monitor_deadline[{i}]== 0 || x[{i}] <= monitor_deadline[{i}])".format(
            i=i
        )
        for i in range(monitors)
    ]
    return "global <= SMC_HORIZON + 1 && " + " &&\n".join(clauses)


def _escape_uppaal_label(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_declarations(spec: dict) -> str:
    nodes, _ = _collect_expanded_nodes(spec)
    generators = spec["generators"]
    timers = spec.get("timers", [])

    if not nodes:
        raise ValueError("nodes must contain at least one non-generator node")
    if not generators:
        raise ValueError("generators must contain at least one data generator")

    node_names = {_const(node["name"]) for node in nodes}

    lines: list[str] = []
    lines.append(
        "const int deterministic_host = {value};".format(
            value="true" if bool(spec.get("deterministic_host", False)) else "false"
        )
    )
    lines.append(
        "int QUEUE_POLICY = {policy};".format(
            policy=_queue_policy_const(spec.get("queue_policy", "drop_oldest"))
        )
    )
    lines.append("")
    lines.append("")

    lines.append(f"const int C = {len(nodes)};")
    lines.append("")

    # Keep generator period/deadline constants in the same section order as legacy models.
    gen_symbols: list[str] = []
    gen_prios: list[str] = []
    gen_deadlines: list[str] = []
    for gen in generators:
        period_symbol = _generator_timing_symbol(gen, "period")
        deadline_symbol = _generator_timing_symbol(gen, "deadline")
        lines.append(f"const int {period_symbol} = {int(gen['period'])};")
        lines.append(f"const int {deadline_symbol} = {int(gen['deadline'])};")
        lines.append("")
        lines.append("")

    node_wcet_symbols: list[str] = []
    node_prios: list[str] = []
    node_src_prios: list[str] = []

    for idx, node in enumerate(nodes):
        name = _const(node["name"])
        wcet = int(node["wcet"])
        prio = int(node["prio"])

        lines.append(f"const int {name} = {idx};")
        lines.append(f"int {name}_data = 0;")
        lines.append(f"const int {name}_WCET = {wcet};")

        node_wcet_symbols.append(f"{name}_WCET")
        node_prios.append(str(prio))
        node_src_prios.append(str(prio))

    lines.append("int DATA[C] = {" + ",".join("EMPTY" for _ in nodes) + "};")
    lines.append("int PRIO[C] = {" + ",".join(node_prios) + "};")
    lines.append("")
    lines.append("")
    lines.append("const int NO_PRIO = 0;")
    lines.append("int SRC_PRIO[C] = {" + ",".join(node_src_prios) + "};")
    lines.append("int WCET[C] = {" + ",".join(node_wcet_symbols) + "};")
    lines.append("")

    lines.append(f"const int GENS = {len(generators)};")

    for gidx, gen in enumerate(generators):
        gname = _const(gen["name"])
        deadline_symbol = _generator_timing_symbol(gen, "deadline")
        gen_symbols.append(gname)
        gen_prios.append(str(int(gen["prio"])))
        gen_deadlines.append(deadline_symbol)
        lines.append(f"const int {gname} = {gidx};")

    lines.append("const int GEN_WCET[GENS] = {" + ", ".join(gen_symbols) + "};")
    lines.append("const int GEN_PRIO[GENS] = {" + ", ".join(gen_prios) + "};")
    lines.append("const int DEADLINES[GENS] = {" + ",".join(gen_deadlines) + "};")
    lines.append("int SRC[C] = {" + ",".join("SOURCE_UNKNOWN" for _ in nodes) + "};")
    monitored_gen = next((gen for gen in generators if gen.get("monitored", False)), None)
    if monitored_gen is None:
        raise ValueError("Exactly one generator must have \"monitored\": true")
    lines.append(f"const int MONITORED_SRC = {_const(monitored_gen['name'])};")
    if timers:
        lines.append("")
        lines.append("")
    for timer in timers:
        period_symbol = _timer_symbol(timer, "period")
        delay_symbol = _timer_symbol(timer, "delay")
        lines.append(f"const int {period_symbol} = {int(timer['period'])};")
        lines.append(f"const int {delay_symbol} = {int(timer.get('delay', 0))};")

    monitor_cfg = spec.get("monitor", {})
    actuator = _const(monitor_cfg.get("actuator", ""))
    if actuator and actuator not in node_names:
        raise ValueError(f"monitor.actuator '{actuator}' must be one of nodes")

    return "\n".join(lines)


def _build_system(spec: dict) -> str:
    nodes, subprocesses_by_owner = _collect_expanded_nodes(spec)
    generators = spec["generators"]
    subscribers = spec.get("subscribers", [])
    timers = spec.get("timers", [])
    node_names = {_const(node["name"]) for node in nodes}

    lines: list[str] = ["// These are always used", "", "host = Host(deterministic_host);", "", ""]

    generator_instances: list[str] = []
    for gen in generators:
        gname = _const(gen["name"])
        period_symbol = _generator_timing_symbol(gen, "period")
        topic = _const(gen["topic"])
        if topic not in node_names:
            raise ValueError(f"generator topic '{topic}' must be one of nodes")

        instance = str(gen.get("instance", _instance(gen["name"])))

        lines.append(
            f"{instance} = DataGenerator({gname}, {period_symbol}, {topic});"
        )
        generator_instances.append(instance)

    lines.append("")

    subscriber_instances: list[str] = []
    for sub in subscribers:
        owner = _const(sub["task"])
        for proc in subprocesses_by_owner.get(owner, []):
            proc_data_source = _symbol_or_expr(proc["data_source"])
            proc_src = _symbol_or_expr(proc["src"])
            lines.append(
                f"{proc['instance']} = AggregateSubscriber({proc['name']}, publish[{proc['source']}], {proc_data_source}, {proc_src});"
            )
            subscriber_instances.append(proc["instance"])

        instance = str(sub.get("instance", _instance(sub["name"])))
        task = _const(sub["task"])
        signal_from = _const(sub["signal_from"])
        if task not in node_names:
            raise ValueError(f"subscriber task '{task}' must be one of nodes")
        if signal_from not in node_names:
            raise ValueError(f"subscriber signal_from '{signal_from}' must be one of nodes")

        if "src" in sub:
            data_source = _symbol_or_expr(str(sub.get("data_source", "pd")))
            src_value = _symbol_or_expr(str(sub["src"]))
            lines.append(
                f"{instance} = AggregateSubscriber({task}, publish[{signal_from}], {data_source}, {src_value});"
            )
        else:
            lines.append(f"{instance} = Subscriber({task}, publish[{signal_from}]);")
        subscriber_instances.append(instance)

    if subscribers:
        lines.append("")

    timer_instances: list[str] = []
    for timer in timers:
        instance = str(timer.get("instance", _instance(timer["name"])))
        task = _const(timer["task"])
        period_symbol = _timer_symbol(timer, "period")

        if "src" in timer:
            data_source_expr = _symbol_or_expr(str(timer.get("data_source", "pd")))
            src_value = _symbol_or_expr(str(timer["src"]))
            lines.append(
                f"{instance} = AggregateTimer({task}, {period_symbol}, {data_source_expr}, {src_value});"
            )
        else:
            data_source = _const(timer["data_source"])
            src_source = _const(timer["src_source"])
            delay_symbol = _timer_symbol(timer, "delay")

            for field_name, field_value in (
                ("task", task),
                ("data_source", data_source),
                ("src_source", src_source),
            ):
                if field_value not in node_names:
                    raise ValueError(f"timer {field_name} '{field_value}' must be one of nodes")

            lines.append(
                f"{instance} = Timer({task}, {period_symbol}, {delay_symbol}, DATA[{data_source}], SRC[{src_source}]);"
            )
        timer_instances.append(instance)

        for proc in subprocesses_by_owner.get(task, []):
            proc_data_source = _symbol_or_expr(proc["data_source"])
            proc_src = _symbol_or_expr(proc["src"])
            lines.append(
                f"{proc['instance']} = AggregateSubscriber({proc['name']}, publish[{proc['source']}], {proc_data_source}, {proc_src});"
            )
            timer_instances.append(proc["instance"])

    if timers:
        lines.append("")

    monitor_cfg = spec["monitor"]
    actuator = _const(monitor_cfg["actuator"])
    period = int(monitor_cfg["period"])
    lines.append(f"monitor = Monitor({actuator}, {period});")

    process_instances = generator_instances + subscriber_instances + timer_instances + ["host", "monitor"]
    lines.append("system " + ",".join(process_instances) + ";")
    lines.append("")
    lines.append("")
    return "\n".join(lines)


def generate_from_json(
    json_path: Path,
    output_path: Path,
    template_path: Path,
) -> None:
    spec = json.loads(json_path.read_text())

    monitors = int(spec.get("monitors", 10))
    if monitors <= 0:
        raise ValueError("monitors must be > 0")

    smc_horizon = int(spec.get("smc_horizon", 100000))
    if smc_horizon <= 0:
        raise ValueError("smc_horizon must be > 0")

    template = template_path.read_text()
    output = template.replace("!!!MONITORS!!!", str(monitors))
    output = output.replace("!!!SMC_HORIZON!!!", str(smc_horizon))
    output = output.replace("!!!DECLARATIONS!!!", _build_declarations(spec))
    output = output.replace("!!!SYSTEM!!!", _build_system(spec))
    output = output.replace(
        "!!!MONITOR_INVARIANT!!!",
        _escape_uppaal_label(_build_monitor_invariant(monitors)),
    )

    # Allow exact reproduction of legacy files that were committed with CRLF.
    line_endings = str(spec.get("line_endings", "lf")).lower()
    normalized = output.replace("\r\n", "\n")
    if line_endings == "crlf":
        normalized = normalized.replace("\n", "\r\n")
    elif line_endings != "lf":
        raise ValueError("line_endings must be either 'lf' or 'crlf'")

    output_path.write_text(normalized, newline="")


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: generate_xml_multisrc_v1.py <spec.json> [output.xml]")
        sys.exit(1)

    json_path = Path(sys.argv[1]).resolve()
    output_path = (
        Path(sys.argv[2]).resolve()
        if len(sys.argv) == 3
        else json_path.with_suffix(".xml")
    )

    script_dir = Path(__file__).resolve().parent
    root_dir = script_dir.parent.parent
    template_override = os.environ.get("UPPAAL_TEMPLATE_PATH")
    template_path = (
        Path(template_override).resolve() if template_override else (root_dir / "multisrc_v1.xml")
    )

    generate_from_json(json_path, output_path, template_path)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
