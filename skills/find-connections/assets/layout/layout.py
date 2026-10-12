#!/usr/bin/env python3
"""Layout of the Kiro Allspark cube (phase 2.F of find-connections).

Reads the Level 1 data (repos, systems without a repo, connections, databases) and writes, deterministically:
  - the position of every point (semantic coordinates and already swapped for the export),
  - systems without a repo grouped by provider (one point per provider),
  - connections merged per (source, target group, protocol), with their endpoint weight,
  - database nuclei in a box next to the origin (filled in 3D like every zone), with 1..5 electrons (relative use)
    and an orbit limit so the atoms never cross,
  - the repo -> database links,
  - the entry points (documented frontends and monoliths) and the repos that are not documented yet.

Pure Python standard library (3.8+). Same input -> same output.

Usage:
  layout.py --input level1.json --output layout.json
  layout.py --selftest

Input:
  { "repos":     [ { "id": "org/api-payments", "role": "frontend|mvc-monolith|backend|worker", "documented": true } ],
                   # documented=false: a repo of the workspace that is not documented yet; it gets a position (so the
                   # cube shows the coverage) and is drawn as a hollow, dotted point
    "systems":   [ { "id": "api.stripe.com", "axis": "X|Y|Z" } ],          # X client, Y internal (Acme), Z external
    "vectors":   [ { "source": "org/api-payments", "target": "api.stripe.com", "protocol": "http", "endpoints": 3 } ],
    "databases": [ { "id": "postgres://payments-db/payments", "engine": "postgresql", "name": "payments",
                     "repos": ["org/api-payments"] } ] }

Exit codes: 0 ok, 1 invalid input.
"""
import argparse
import json
import math
import sys

LAYOUT_VERSION = "1.2.0"

# --------------------------------------------------------------------------
# Anchors, migration and secondary axes (semantic coordinates: x=Client, y=Internal, z=External, 0..100)
# --------------------------------------------------------------------------
K, K_FINE, DELTA_MAX, FLOOR = 20, 8, 25, 0.4
CLIENT_PLANE, EXTERNAL_PLANE = 4, 6

# category: (anchor, pure extreme, dominant axis)
CAT = {
    "frontend":     ((58, 48, 5),  (100, 0, 100), 2),
    "mvc-monolith": ((72, 76, 62), (40, 100, 20), 1),
    "backend":      ((70, 70, 70), (0, 100, 0),   1),
    "worker":       ((2, 66, 30),  (0, 100, 100), 2),
    "virtual-X":    ((60, 30, 5),  (100, 0, 0),   0),
    "virtual-Y":    ((70, 72, 70), (0, 100, 0),   1),
    "virtual-Z":    ((40, 30, 95), (0, 0, 100),   2),
}
REPO_COLOR = {"frontend": "blue", "mvc-monolith": "teal", "backend": "green", "worker": "green"}
AXIS_COLOR = {"X": "blue", "Y": "green", "Z": "orange"}


def fnv1a(s):
    h = 0x811c9dc5
    for b in s.encode():
        h ^= b
        h = (h * 0x01000193) & 0xffffffff
    return h


def clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def jitter(pid):
    return (fnv1a(pid) % 100) / 100


def base_position(pid, cat, counts, dom_count):
    """Anchor + migration of the dominant axis + secondary axes."""
    anchor, ext, dom = CAT[cat]
    f = dom_count / (dom_count + K)
    p = [0.0, 0.0, 0.0]
    p[dom] = anchor[dom] + f * (ext[dom] - anchor[dom])
    j = jitter(pid)
    for i in range(3):
        if i == dom:
            continue
        ff = counts[i] / (counts[i] + K_FINE)
        off = max(ff, FLOOR) * DELTA_MAX
        sg = 1 if ext[i] - anchor[i] >= 0 else -1
        p[i] = anchor[i] + (off + j * 0.15 * DELTA_MAX) * sg
    return [round(clamp(v), 1) for v in p]


def zone_of(p):
    if p["cat"] in ("frontend", "virtual-X"):
        return "client"
    if p["cat"] == "virtual-Z":
        return "external"
    if p["cat"] == "worker":
        return "worker"
    return "internal"


# --------------------------------------------------------------------------
# Grouping of systems without a repo by provider
# --------------------------------------------------------------------------
TWO_LEVEL_TLDS = {"com.ve", "gob.ve", "co.uk", "org.uk", "com.br", "com.ar", "com.mx", "com.co", "com.pe", "com.au"}
ROLE_SUFFIXES = ("-batch", "-reports", "-sso", "-api", "-web", "-ui", "-db")


def registrable_domain(host):
    """Registrable domain: last 2 labels (3 if the TLD has two levels)."""
    parts = host.lower().split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in TWO_LEVEL_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host.lower()


def internal_stem(host):
    """Internal systems share one domain, so they are grouped by their name without role suffix."""
    parts = host.lower().split(".")
    name = parts[0]
    for suf in ROLE_SUFFIXES:
        if name.endswith(suf) and len(name) > len(suf):
            name = name[: -len(suf)]
    return ".".join([name] + parts[1:]) if len(parts) > 1 else name


def group_of(host, axis):
    return internal_stem(host) if axis == "Y" else registrable_domain(host)


# --------------------------------------------------------------------------
# Level 1 -> points and merged vectors
# --------------------------------------------------------------------------
def build_points(inp, warnings):
    repos = {r["id"]: r for r in inp.get("repos", [])}
    systems = {s["id"]: s for s in inp.get("systems", [])}
    for r in repos.values():
        if r.get("role") not in REPO_COLOR:
            raise ValueError(f"repo {r['id']}: invalid role {r.get('role')!r}")
    for s in systems.values():
        if s.get("axis") not in AXIS_COLOR:
            raise ValueError(f"system {s['id']}: invalid axis {s.get('axis')!r}")
    node_of = {sid: group_of(sid, s["axis"]) for sid, s in systems.items()}
    groups = {}
    for sid, s in systems.items():
        g = groups.setdefault(node_of[sid], {"id": node_of[sid], "axis": s["axis"], "hosts": []})
        g["hosts"].append(sid)
    axis_of = {g["id"]: g["axis"] for g in groups.values()}

    merged = {}
    for e in inp.get("vectors", []):
        src, tgt = e["source"], e["target"]
        if (src not in repos and src not in systems) or (tgt not in repos and tgt not in systems):
            warnings.append(f"connection {src} -> {tgt} skipped: one end is not in repos/systems")
            continue
        s2, t2 = node_of.get(src, src), node_of.get(tgt, tgt)
        key = (s2, t2, e.get("protocol", "http"))
        merged[key] = merged.get(key, 0) + int(e.get("endpoints", 1))
    vectors = [{"source": s, "target": t, "protocol": p, "endpoints": n} for (s, t, p), n in sorted(merged.items())]

    counts = {rid: [0, 0, 0] for rid in repos}
    refs = {g: set() for g in groups}
    for e in vectors:
        for me, other in ((e["source"], e["target"]), (e["target"], e["source"])):
            if me in repos:
                ax = axis_of.get(other)
                k = 0 if ax == "X" else 2 if ax == "Z" else 1
                counts[me][k] += e["endpoints"]
                if other in refs:
                    refs[other].add(me)
    points = []
    for rid in sorted(repos):
        r = repos[rid]
        c = counts[rid]
        dom = CAT[r["role"]][2]
        touched = any(c)
        documented = bool(r.get("documented", True)) or touched
        if touched and r.get("documented", True) is False:
            warnings.append(f"repo {rid} is marked as not documented but it has connections: treated as documented")
        points.append({"id": rid, "type": "repo", "cat": r["role"], "counts": c, "documented": documented,
                       "pos": base_position(rid, r["role"], c, c[dom])})
    for gid in sorted(groups):
        g = groups[gid]
        cat = "virtual-" + g["axis"]
        points.append({"id": gid, "type": "virtual", "cat": cat, "axis": g["axis"], "hosts": sorted(g["hosts"]),
                       "counts": [0, 0, 0], "pos": base_position(gid, cat, [0, 0, 0], len(refs[gid]))})
    return points, vectors, axis_of


# --------------------------------------------------------------------------
# Volume fill: every zone is a box that is filled evenly, without overlaps
# --------------------------------------------------------------------------
SEP_FLOOR, SEP_MAX, FILL = 5.5, 20.0, 0.7
SPRING, ITERATIONS = 0.03, 600

# peg: axis stuck to the zone's plane (thickness grows with the number of points); free: ranges of the other axes.
# The four boxes are disjoint from each other and from the database ring near the origin.
ZONES = {
    "client":   dict(peg=2, peg0=CLIENT_PLANE,   tk=5.0, tmin=8, tmax=30, free={0: (30, 100), 1: (5, 75)}),
    "external": dict(peg=0, peg0=EXTERNAL_PLANE, tk=5.0, tmin=8, tmax=28, free={1: (0, 52), 2: (36, 100)}),
    "worker":   dict(peg=0, peg0=1,              tk=3.2, tmin=6, tmax=20, free={1: (56, 100), 2: (8, 70)}),
    "internal": dict(peg=None, box={0: (38, 96), 1: (40, 100), 2: (38, 96)}),
}


def _prod(rng):
    a = 1.0
    for lo, hi in rng.values():
        a *= (hi - lo)
    return a


def _fit(zone, n):
    z = ZONES[zone]
    if z["peg"] is None:
        box = dict(z["box"])
        sep = min(SEP_MAX, (FILL * _prod(box) / max(n, 1)) ** (1 / 3))
        return box, max(SEP_FLOOR, sep), None, sep < SEP_FLOOR
    area = _prod(z["free"])
    T = min(z["tmax"], max(z["tmin"], z["tk"] * n ** (1 / 3)))
    sep = min(SEP_MAX, (FILL * area * T / max(n, 1)) ** (1 / 3))
    if sep < 9 and T < z["tmax"]:
        T = z["tmax"]
        sep = min(SEP_MAX, (FILL * area * T / max(n, 1)) ** (1 / 3))
    return z["free"], max(SEP_FLOOR, sep), T, sep < SEP_FLOOR


def _spread_targets(pts, box, peg, peg0, T, sep):
    """Even initial positions that keep the order of importance: per free axis, 50% rank + 50% normalized value."""
    n = len(pts)
    out = [[0.0, 0.0, 0.0] for _ in pts]
    for k in range(3):
        lo, hi = box[k]
        if k == peg:
            for idx, p in enumerate(pts):
                out[idx][k] = peg0 + T * ((idx * 0.6180339887 + jitter(p["id"])) % 1.0)
            continue
        m = min(sep * 0.5, (hi - lo) / 4)
        lo, hi = lo + m, hi - m
        vals = [p["pos"][k] for p in pts]
        mn, mx = min(vals), max(vals)
        order = sorted(range(n), key=lambda i: (vals[i], fnv1a(pts[i]["id"] + str(k))))
        rank = {i: r for r, i in enumerate(order)}
        for i in range(n):
            r = rank[i] / (n - 1) if n > 1 else 0.5
            v = (vals[i] - mn) / (mx - mn) if mx > mn else 0.5
            out[i][k] = lo + (hi - lo) * (0.5 * r + 0.5 * v)
    return out


def _relax(pts, box, sep, target, init):
    n = len(pts)
    pos = [list(p) for p in init]
    for _ in range(ITERATIONS):
        force = [[0.0, 0.0, 0.0] for _ in range(n)]
        worst = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                d = [pos[i][k] - pos[j][k] for k in range(3)]
                dd = math.sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2])
                if dd >= sep:
                    continue
                if dd < 1e-6:
                    a = 2 * math.pi * (fnv1a(pts[i]["id"] + pts[j]["id"]) % 360) / 360
                    d, dd = [math.cos(a), 0.3, math.sin(a)], 1.0
                push = (sep - dd) / 2
                worst = max(worst, sep - dd)
                for k in range(3):
                    u = d[k] / dd * push
                    force[i][k] += u
                    force[j][k] -= u
        for i in range(n):
            for k in range(3):
                pos[i][k] += force[i][k] + SPRING * (target[i][k] - pos[i][k])
                lo, hi = box[k]
                pos[i][k] = min(max(pos[i][k], lo), hi)
        if worst < 0.05:
            break
    return pos


def layout_volume(points):
    info = {}
    for zone in ("client", "external", "worker", "internal"):
        pts = sorted([p for p in points if p["type"] != "database" and zone_of(p) == zone], key=lambda p: p["id"])
        n = len(pts)
        if not n:
            continue
        z = ZONES[zone]
        rng, sep, T, overflow = _fit(zone, n)
        box = {0: (0, 100), 1: (0, 100), 2: (0, 100)}
        for k, (lo, hi) in rng.items():
            box[k] = (lo, hi)
        if z["peg"] is not None:
            box[z["peg"]] = (z["peg0"], z["peg0"] + T)
        init = _spread_targets(pts, box, z["peg"], z.get("peg0"), T, sep)
        pos = _relax(pts, box, sep, init, init)
        for p, q in zip(pts, pos):
            p["pos"] = [round(clamp(v), 1) for v in q]
        achieved = min((math.dist(pts[i]["pos"], pts[j]["pos"]) for i in range(n) for j in range(i + 1, n)), default=99.0)
        info[zone] = {"n": n, "sep": round(sep, 1), "achieved": round(achieved, 1),
                      "thickness": None if T is None else round(T, 1), "overflow": bool(overflow or achieved < 6.0)}
    return info


# --------------------------------------------------------------------------
# Databases: a zone of their own next to the origin, filled in 3D like every other zone
# --------------------------------------------------------------------------
# The box starts a little away from the origin and rises like a column: it is the only region of the cube that no other
# zone uses (client x >= 30, external z >= 36, worker y >= 56). More used databases sit lower, less used ones higher.
DB_BOX = {0: (8, 26), 1: (6, 50), 2: (8, 30)}
DB_SEP_MAX, DB_SEP_FLOOR = 24.0, 6.0
ORBIT_FACTOR = 0.42          # the largest electron orbit is at most 42% of the distance to the nearest neighbour


def place_databases(dbs, repo_ids, warnings):
    dbs = sorted(dbs, key=lambda d: d["id"])
    n = len(dbs)
    if not n:
        return [], None
    uses = []
    for d in dbs:
        used = sorted({x for x in d.get("repos", []) if x in repo_ids})
        for x in d.get("repos", []):
            if x not in repo_ids:
                warnings.append(f"database {d['id']}: repo {x} is not in repos, ignored")
        uses.append(used)
    lo, hi = min(len(u) for u in uses), max(len(u) for u in uses)
    pts = []
    for d, used in zip(dbs, uses):
        norm = 0.5 if hi == lo else (len(used) - lo) / (hi - lo)
        pts.append({"id": d["id"], "used": used, "d": d, "electrons": 3 if hi == lo else round(1 + 4 * norm),
                    "pos": [DB_BOX[0][0] + (DB_BOX[0][1] - DB_BOX[0][0]) * jitter(d["id"] + "x"),
                            DB_BOX[1][0] + (DB_BOX[1][1] - DB_BOX[1][0]) * (1 - norm),          # the more used, the lower
                            DB_BOX[2][0] + (DB_BOX[2][1] - DB_BOX[2][0]) * jitter(d["id"] + "z")]})
    vol = _prod(DB_BOX)
    sep = max(DB_SEP_FLOOR, min(DB_SEP_MAX, (FILL * vol / n) ** (1 / 3)))
    init = _spread_targets(pts, DB_BOX, None, None, None, sep)
    pos = _relax(pts, DB_BOX, sep, init, init)
    for p, q in zip(pts, pos):
        p["pos"] = [round(clamp(v), 1) for v in q]
    achieved = min((math.dist(pts[i]["pos"], pts[j]["pos"]) for i in range(n) for j in range(i + 1, n)), default=99.0)
    out = []
    for p in pts:
        d = p["d"]
        near = min((math.dist(p["pos"], q["pos"]) for q in pts if q is not p), default=None)
        orbit = round(ORBIT_FACTOR * near, 1) if near is not None else 14.0
        out.append({"id": d["id"], "type": "database", "engine": d.get("engine", ""), "name": d.get("name", d["id"]),
                    "repos": p["used"], "electrons": p["electrons"], "orbit": orbit, "color": "gold", "pos": p["pos"]})
    info = {"n": n, "sep": round(sep, 1), "achieved": round(achieved, 1), "thickness": None,
            "overflow": bool(achieved < DB_SEP_FLOOR - 0.5)}
    return out, info


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def run(inp):
    warnings = []
    points, vectors, axis_of = build_points(inp, warnings)
    info = layout_volume(points)
    repo_ids = {p["id"] for p in points if p["type"] == "repo" and p["documented"]}
    dbs, db_info = place_databases(inp.get("databases", []), repo_ids, warnings)
    if db_info:
        info["data"] = db_info

    zone = {p["id"]: zone_of(p) for p in points}
    out_pts = []
    for p in points + dbs:
        q = {"id": p["id"], "type": p["type"], "pos": p["pos"],
             "export": {"pos_x": p["pos"][2], "pos_y": p["pos"][1], "pos_z": p["pos"][0]}}          # the swap X/Z lives here
        if p["type"] == "repo":
            q.update(role=p["cat"], color=REPO_COLOR[p["cat"]], count_client=p["counts"][0], count_internal=p["counts"][1],
                     count_external=p["counts"][2])
            if not p["documented"]:
                q["documented"] = False                                  # drawn hollow and dotted
            elif p["cat"] in ("frontend", "mvc-monolith"):
                q["entry_point"] = True                                  # where the client interacts: drawn with a ring
        elif p["type"] == "virtual":
            q.update(role="external", axis=p["axis"], color=AXIS_COLOR[p["axis"]], hosts=p["hosts"])
        else:
            q.update(engine=p["engine"], name=p["name"], repos=p["repos"], electrons=p["electrons"], orbit=p["orbit"], color="gold")
        out_pts.append(q)
    out_vec = []
    for e in vectors:
        s, t = e["source"], e["target"]
        ax = "X" if axis_of.get(s) == "X" or axis_of.get(t) == "X" else "Z" if axis_of.get(t) == "Z" else "Y"
        v = {"id": f"{s}->{t}:{e['protocol']}", "source": s, "target": t, "protocol": e["protocol"], "axis": ax,
             "endpoints": e["endpoints"]}
        if zone.get(s) == "client" and axis_of.get(t) == "Z":
            v["direct"] = True
        out_vec.append(v)
    links = [{"source": r, "target": d["id"], "type": "data"} for d in dbs for r in d["repos"]]
    for z, i in info.items():
        if i["overflow"]:
            warnings.append(f"zone {z}: {i['n']} points do not fit with a separation of at least 6 "
                            f"(achieved {i['achieved']}); enlarge its box in ZONES or split the workspace")
    return {"layout_version": LAYOUT_VERSION, "points": out_pts, "vectors": out_vec, "links": links,
            "zones": info, "warnings": warnings}


def selftest():
    inp = {
        "repos": [{"id": "org/front-web", "role": "frontend"}, {"id": "org/api-a", "role": "backend"},
                  {"id": "org/api-b", "role": "backend"}, {"id": "org/worker-x", "role": "worker"},
                  {"id": "org/api-legacy", "role": "backend", "documented": False}],
        "systems": [{"id": "api.pay.io", "axis": "Z"}, {"id": "files.pay.io", "axis": "Z"}, {"id": "core.bank.com", "axis": "X"},
                    {"id": "core-banking.acme.local", "axis": "Y"}, {"id": "core-banking-batch.acme.local", "axis": "Y"}],
        "vectors": [{"source": "org/front-web", "target": "org/api-a", "protocol": "http", "endpoints": 4},
                    {"source": "org/api-a", "target": "api.pay.io", "protocol": "http", "endpoints": 2},
                    {"source": "org/api-a", "target": "files.pay.io", "protocol": "http", "endpoints": 1},
                    {"source": "core.bank.com", "target": "org/api-b", "protocol": "soap", "endpoints": 3},
                    {"source": "org/api-b", "target": "core-banking.acme.local", "protocol": "soap", "endpoints": 2},
                    {"source": "org/api-b", "target": "core-banking-batch.acme.local", "protocol": "soap", "endpoints": 1},
                    {"source": "org/api-a", "target": "org/worker-x", "protocol": "queue-kafka", "endpoints": 2}],
        "databases": [{"id": "postgres://db/a", "engine": "postgresql", "name": "a", "repos": ["org/api-a", "org/api-b"]},
                      {"id": "redis://cache/0", "engine": "redis", "name": "cache", "repos": ["org/api-b"]}],
    }
    a, b = run(inp), run(inp)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), "not deterministic"
    ids = {p["id"] for p in a["points"]}
    assert "pay.io" in ids and "api.pay.io" not in ids, "external hosts must be grouped by provider"
    assert "core-banking.acme.local" in ids and "core-banking-batch.acme.local" not in ids, "internal stems must be grouped"
    merged = [v for v in a["vectors"] if v["target"] == "pay.io"]
    assert len(merged) == 1 and merged[0]["endpoints"] == 3, "connections must be merged with their weight"
    pos = [p["pos"] for p in a["points"]]
    assert all(0 <= c <= 100 for q in pos for c in q), "positions must be in 0..100"
    dmin = min(math.dist(pos[i], pos[j]) for i in range(len(pos)) for j in range(i + 1, len(pos)))
    assert dmin >= 6, f"points overlap (dmin={dmin})"
    assert a["links"] and not a["warnings"], a["warnings"]
    dbs = [p for p in a["points"] if p["type"] == "database"]
    for d in dbs:
        assert all(DB_BOX[k][0] <= d["pos"][k] <= DB_BOX[k][1] for k in range(3)), "database outside its box"
        near = min(math.dist(d["pos"], e["pos"]) for e in dbs if e is not d)
        assert d["orbit"] <= ORBIT_FACTOR * near + 0.05, "orbit crosses a neighbour"
    ghost = next(p for p in a["points"] if p["id"] == "org/api-legacy")
    assert ghost.get("documented") is False and "entry_point" not in ghost, "a repo not documented yet must be flagged"
    assert next(p for p in a["points"] if p["id"] == "org/front-web").get("entry_point") is True, "entry point flag"
    front = next(p for p in a["points"] if p["id"] == "org/front-web")
    assert front["export"]["pos_x"] == front["pos"][2] and front["export"]["pos_z"] == front["pos"][0], "swap X/Z"
    print(f"selftest ok: {len(a['points'])} points, {len(a['vectors'])} vectors, dmin={round(dmin, 1)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Kiro Allspark cube layout")
    ap.add_argument("--input")
    ap.add_argument("--output")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.input and a.output):
        ap.error("--input and --output are required")
    try:
        inp = json.load(open(a.input, encoding="utf-8"))
        out = run(inp)
    except (OSError, ValueError, KeyError) as e:
        print(f"invalid input: {e}", file=sys.stderr)
        return 1
    json.dump(out, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out['points'])} points, {len(out['vectors'])} vectors, {len(out['links'])} links -> {a.output}")
    for w in out["warnings"]:
        print("warning:", w, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
