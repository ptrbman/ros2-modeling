#!/usr/bin/env python3
from pathlib import Path

POL = {"drop_newest": "POLICY_DROP_NEWEST", "drop_oldest": "POLICY_DROP_OLDEST", "drop_lowest_prio": "POLICY_DROP_LOWEST_PRIO"}


def _decl(n: int, load: int, policy: str, deterministic_host: bool = True) -> str:
    subs = [f"FUSIONxOBJDET_{i}" for i in range(1, n)]
    c = 3 * n + 1
    names = [f"CAMERA_{i}" for i in range(n)] + [f"OBJDET_{i}" for i in range(n)] + ["FUSION", "ACTUATOR"] + subs
    prio = [str(i + 1) for i in range(n)] + [str(n + i + 1) for i in range(n)] + [str(2 * n + 1), str(2 * n + 2)] + [str(2 * n + 1)] * (n - 1)
    wcet = ["20"] * n + ["50"] * n + ["90", "50"] + ["10"] * (n - 1)
    host_mode = "true" if deterministic_host else "false"
    L = [f"const int deterministic_host = {host_mode};", f"int QUEUE_POLICY = {POL[policy]};", "", f"const int C = {c};", ""]
    for i in range(n): L += [f"const int CAM_{i}_PERIOD = 1000;", f"const int CAM_{i}_DEADLINE = 850;", f"const int CAM_{i}_GEN_PROB = {load};", ""]
    for i, nm in enumerate(names): L += [f"const int {nm} = {i};", f"int {nm}_data = 0;", f"const int {nm}_WCET = {wcet[i]};"]
    L += [f"int DATA[C] = {{{','.join('EMPTY' for _ in range(c))}}};", f"int PRIO[C] = {{{','.join(prio)}}};", "const int NO_PRIO = 0;", f"int SRC_PRIO[C] = {{{','.join(prio)}}};", f"int WCET[C] = {{{','.join(f'{x}_WCET' for x in names)}}};", "", f"const int GENS = {n};"]
    for i in range(n): L.append(f"const int GEN_CAM_{i} = {i};")
    L += [f"const int GEN_WCET[GENS] = {{{','.join(f'GEN_CAM_{i}' for i in range(n))}}};", f"const int GEN_PRIO[GENS] = {{{','.join(str(i + 1) for i in range(n))}}};", f"const int DEADLINES[GENS] = {{{','.join(f'CAM_{i}_DEADLINE' for i in range(n))}}};", f"int SRC[C] = {{{','.join('SOURCE_UNKNOWN' for _ in range(c))}}};", "const int MONITORED_SRC = GEN_CAM_0;", "", "const int FUSION_TIMER_PERIOD = 500;"]
    return "\n".join(L)


def _system(n: int) -> str:
    L = ["host = Host(deterministic_host);", ""]
    L += [f"gen_cam_{i} = DataGenerator(CAMERA_{i}, CAM_{i}_PERIOD, GEN_CAM_{i}, CAM_{i}_GEN_PROB);" for i in range(n)] + [""]
    L += [f"sub_objdet_{i} = Relay(OBJDET_{i}, publish[CAMERA_{i}]);" for i in range(n)] + ["sub_actuator = Relay(ACTUATOR, publish[FUSION]);", "", "fusion = Timer(FUSION, FUSION_TIMER_PERIOD, DATA[OBJDET_0], SRC[OBJDET_0]);"]
    L += [f"fusionxobjdet_{i} = Subscriber(FUSIONxOBJDET_{i}, publish[OBJDET_{i}], pd, GEN_CAM_{i});" for i in range(1, n)]
    sys = [f"gen_cam_{i}" for i in range(n)] + [f"sub_objdet_{i}" for i in range(n)] + ["sub_actuator", "fusion"] + [f"fusionxobjdet_{i}" for i in range(1, n)] + ["host", "monitor"]
    return "\n".join(L + ["", "monitor = Monitor(ACTUATOR, 0);", f"system {','.join(sys)};", ""])


def render_xml(
    template: Path,
    out_xml: Path,
    n: int,
    load: int,
    policy: str,
    deterministic_host: bool = True,
) -> None:
    t = template.read_text()
    out = t.replace(
        "!!!DECLARATIONS!!!",
        _decl(n, load, policy, deterministic_host=deterministic_host),
    ).replace("!!!SYSTEM!!!", _system(n))
    out_xml.write_text(out)
