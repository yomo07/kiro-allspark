#!/usr/bin/env python3
"""Reach of the entry points of a workspace (phase 2.B of find-connections).

An entry point is a repo where the client interacts: a `frontend` or an `mvc-monolith`. This script answers two
questions from the prescan results, without reading any source code and without spending a single token:

  1. Which repos of the workspace does each entry point reach? (who serves each of its calls)
  2. How much would it cost to document each one?

It crosses the OUTBOUND candidates of every repo with the INBOUND candidates of the others:
  - http / soap / webhook: normalized path (parameters become *), method when both are known, or a known domain;
  - queues:                same topic or queue name (the producer reaches the consumer);
  - grpc:                  same service name;
and follows those links from each entry point (breadth first). What cannot be resolved to a repo of the workspace
is an external system, exactly as in the rest of the power.

Pure Python standard library (3.8+). Same input -> same output.

Usage:
  reach.py --prescan-dir .kiro/allspark/prescan --output .kiro/allspark/reach.json [--roles roles.json] [--domains domains.json]
  reach.py --selftest

  roles.json   { "org/front-web": "frontend", ... }            (optional: the prescan JSON already carries the role)
  domains.json { "api.acme.internal": "org/api-payments" }     (optional: a host or a suffix `*.acme.internal` -> repo)

Exit codes: 0 ok, 1 invalid input.
"""
import argparse
import glob
import json
import os
import re
import sys

REACH_VERSION = "1.0.0"
ENTRY_ROLES = ("frontend", "mvc-monolith")

# Cost model. The first is measured (size of the prescan JSON / 4); the others are assumptions and are reported as such.
TOKENS_PER_CANDIDATE = 100        # measured on real repos
OUT_TOKENS_PER_CANDIDATE = 15     # assumption: connections written to the MOC per candidate read, after grouping
OUT_TOKENS_PER_SECOND = 60        # assumption: writing speed of the model
TOKENS_PER_LINE_OF_CODE = 10      # assumption: reading raw code (Levels 2 and 3)

GENERIC_PATHS = {"/", "/health", "/healthz", "/ping", "/status", "/metrics", "/favicon.ico", "/login", "/logout"}
ROLE_SUFFIXES = ("-api", "-service", "-svc", "-web", "-app", "-backend", "-worker")


def norm_path(value):
    """Normalized path of a URL or route: no scheme, host or query; parameters become '*'."""
    v = str(value).strip().strip("`\"'")
    v = re.sub(r"^\$\{[^}]*\}", "", v)                               # `${environment.apiUrl}/x` -> `/x`
    v = re.sub(r"^[a-z][a-z0-9+.-]*://[^/]*", "", v, flags=re.I)     # scheme://host
    v = v.split("?")[0].split("#")[0]
    v = re.sub(r"\$\{[^}]*\}|\{[^}/]*\}|:[A-Za-z_]\w*|<[^>/]*>", "*", v)
    segs = [s for s in v.lower().split("/") if s]
    segs = ["*" if re.fullmatch(r"\d+", s) else s for s in segs]
    return "/" + "/".join(segs)


def _seg_eq(a, b):
    return a == b or a == "*" or b == "*"


def path_match(out_path, in_path):
    """'high' if the paths are equal, 'medium' if one is the tail of the other (at least 2 segments), else None."""
    if out_path in GENERIC_PATHS or in_path in GENERIC_PATHS:
        return None
    a, b = [s for s in out_path.split("/") if s], [s for s in in_path.split("/") if s]
    if not a or not b:
        return None
    n = min(len(a), len(b))
    if n == 1 and len(a) != len(b):
        return None
    if all(_seg_eq(x, y) for x, y in zip(a[-n:], b[-n:])):
        return "high" if len(a) == len(b) else "medium"
    return None


def service_key(value):
    last = re.split(r"[./:]", str(value).strip())[-1].lower()
    return re.sub(r"(client|stub|grpc|implbase|service)$", "", last) or last


def short_name(repo):
    n = repo.split("/")[-1].lower()
    for suf in ROLE_SUFFIXES:
        if n.endswith(suf) and len(n) > len(suf):
            return n[: -len(suf)]
    return n


def load_prescan(directory):
    data = {}
    for f in sorted(glob.glob(os.path.join(directory, "*.json"))):
        if os.path.basename(f).startswith("_"):
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict) and "candidates" in d and d.get("repo"):
            data[d["repo"]] = d
    return data


def build_edges(prescan, domains):
    """edges[a][b] = best link (via, confidence) from repo a to repo b; unresolved[a] = outbound calls with no repo."""
    inbound_http, inbound_queue, inbound_grpc = [], [], []
    for repo, d in prescan.items():
        for c in d["candidates"]:
            if c["direction"] not in ("inbound", "declaration"):
                continue
            p = c["protocol"]
            if p in ("http", "soap", "webhook") and c["direction"] == "inbound":
                path = c.get("path") or c.get("route") or c.get("raw_value")
                if path:
                    inbound_http.append((repo, norm_path(path), (c.get("method") or "").upper()))
            elif p.startswith("queue"):
                name = c.get("topic") or c.get("queue") or c.get("raw_value")
                if name and c["direction"] == "inbound":
                    inbound_queue.append((repo, str(name).lower()))
            elif p == "grpc":
                inbound_grpc.append((repo, service_key(c.get("service") or c.get("raw_value")), str(c.get("service") or c.get("raw_value"))))
    short = {repo: short_name(repo) for repo in prescan}
    order = {"high": 2, "medium": 1}
    edges, unresolved = {}, {}

    def link(a, b, via, conf):
        if a == b:
            return
        cur = edges.setdefault(a, {}).get(b)
        if cur is None or order[conf] > order[cur["confidence"]]:
            edges[a][b] = {"via": via, "confidence": conf}

    for a, d in sorted(prescan.items()):
        unresolved[a] = 0
        for c in d["candidates"]:
            if c["direction"] != "outbound":
                continue
            p, found = c["protocol"], False
            if p in ("http", "soap", "webhook"):
                path = c.get("path") or norm_path(c.get("raw_value", ""))
                method = (c.get("method") or "").upper()
                if path and path != "/":
                    for b, ip, im in inbound_http:
                        if method and im and method != im:
                            continue
                        conf = path_match(norm_path(path), ip)
                        if conf:
                            link(a, b, f"{p} {method + ' ' if method else ''}{ip}", conf)
                            found = True
                host = (c.get("host") or "").lower()
                if host:
                    for pat, b in domains.items():
                        if b in prescan and (host == pat or (pat.startswith("*.") and host.endswith(pat[1:]))):
                            link(a, b, f"{p} host {host}", "high")
                            found = True
                    label = host.split(".")[0]
                    for b, sn in short.items():
                        if b != a and sn and label in (sn, sn + "-api", sn + "-service", "api-" + sn):
                            link(a, b, f"{p} host {host}", "medium")
                            found = True
            elif p.startswith("queue"):
                name = str(c.get("topic") or c.get("queue") or c.get("raw_value") or "").lower()
                for b, iname in inbound_queue:
                    if name and name == iname:
                        link(a, b, f"queue {name}", "high")
                        found = True
            elif p == "grpc":
                raw = str(c.get("service") or c.get("raw_value") or "")
                key = service_key(raw)
                for b, ikey, iraw in inbound_grpc:
                    if key and key == ikey:
                        link(a, b, f"grpc {iraw}", "high" if raw.split(".")[-1] == iraw.split(".")[-1] else "medium")
                        found = True
            else:
                continue
            if not found:
                unresolved[a] += 1
    return edges, unresolved


def reach_from(entry, edges):
    seen, order, frontier, depth = {entry}, [], [entry], 0
    while frontier:
        depth += 1
        nxt = []
        for a in frontier:
            for b, e in sorted(edges.get(a, {}).items()):
                if b not in seen:
                    seen.add(b)
                    order.append({"repo": b, "depth": depth, "via": e["via"], "confidence": e["confidence"], "from": a})
                    nxt.append(b)
        frontier = nxt
    return order


def run(prescan, roles=None, domains=None):
    roles, domains = roles or {}, domains or {}
    role_of = {r: roles.get(r) or d.get("role") for r, d in prescan.items()}
    edges, unresolved = build_edges(prescan, domains)
    entries = sorted(r for r, ro in role_of.items() if ro in ENTRY_ROLES)
    size = {r: (d.get("summary", {}).get("lines_scanned", 0), d.get("summary", {}).get("candidates", len(d["candidates"])))
            for r, d in prescan.items()}
    out, reached_by = [], {}
    for e in entries:
        reached = reach_from(e, edges)
        repos = [e] + [x["repo"] for x in reached]
        lines = sum(size[r][0] for r in repos)
        cands = sum(size[r][1] for r in repos)
        for x in reached:
            reached_by.setdefault(x["repo"], []).append(e)
        written = cands * OUT_TOKENS_PER_CANDIDATE
        out.append({"repo": e, "role": role_of[e], "reached": reached,
                    "totals": {"repos": len(repos), "lines": lines, "candidates": cands,
                               "tokens_read": cands * TOKENS_PER_CANDIDATE, "tokens_written": written,
                               "minutes_writing": round(written / OUT_TOKENS_PER_SECOND / 60, 1),
                               "tokens_to_read_raw_code_if_promoted": lines * TOKENS_PER_LINE_OF_CODE},
                    "unresolved_outbound": sum(unresolved[r] for r in repos)})
    reached_any = {x["repo"] for ep in out for x in ep["reached"]} | set(entries)
    whole = {"repos": len(prescan), "lines": sum(v[0] for v in size.values()), "candidates": sum(v[1] for v in size.values())}
    whole["tokens_read"] = whole["candidates"] * TOKENS_PER_CANDIDATE
    whole["tokens_written"] = whole["candidates"] * OUT_TOKENS_PER_CANDIDATE
    whole["minutes_writing"] = round(whole["tokens_written"] / OUT_TOKENS_PER_SECOND / 60, 1)
    return {"reach_version": REACH_VERSION, "entry_points": out,
            "shared": {r: sorted(v) for r, v in sorted(reached_by.items()) if len(v) > 1},
            "not_reached": sorted(r for r in prescan if r not in reached_any),
            "whole_workspace": whole,
            "assumptions": {"tokens_per_candidate": f"{TOKENS_PER_CANDIDATE} (measured)",
                            "out_tokens_per_candidate": f"{OUT_TOKENS_PER_CANDIDATE} (assumption)",
                            "out_tokens_per_second": f"{OUT_TOKENS_PER_SECOND} (assumption)",
                            "tokens_per_line_of_code": f"{TOKENS_PER_LINE_OF_CODE} (assumption)",
                            "note": "an estimate, not a measurement: the real cost depends on the model and on the code"}}


def selftest():
    def cand(protocol, direction, **kw):
        return dict(protocol=protocol, direction=direction, confidence="high", **kw)
    prescan = {
        "org/front-web": {"repo": "org/front-web", "role": "frontend", "summary": {"lines_scanned": 1000, "candidates": 4}, "candidates": [
            cand("http", "outbound", raw_value="/api/payments/confirm", method="POST", path="/api/payments/confirm"),
            cand("http", "outbound", raw_value="`${environment.apiUrl}/api/payments/history`", method="GET"),
            cand("http", "outbound", raw_value="https://maps.vendor.com/v1/geocode", host="maps.vendor.com"),
            cand("http", "outbound", raw_value="https://api.acme.internal/v2/rates", host="api.acme.internal", method="GET")]},
        "org/api-payments": {"repo": "org/api-payments", "role": "backend", "summary": {"lines_scanned": 5000, "candidates": 5}, "candidates": [
            cand("http", "inbound", raw_value="/api/payments/confirm", method="POST", path="/api/payments/confirm"),
            cand("http", "inbound", raw_value="/api/payments/history", method="GET", path="/api/payments/history"),
            cand("http", "outbound", raw_value="https://api.payvendor.com/charge", host="api.payvendor.com", method="POST"),
            cand("queue-kafka", "outbound", raw_value="payments.confirmed", topic="payments.confirmed"),
            cand("grpc", "outbound", raw_value="process.env.SCORING_HOST", service="ScoringService")]},
        "org/worker-notifier": {"repo": "org/worker-notifier", "role": "worker", "summary": {"lines_scanned": 800, "candidates": 2}, "candidates": [
            cand("queue-kafka", "inbound", raw_value="payments.confirmed", topic="payments.confirmed"),
            cand("http", "outbound", raw_value="https://sms.vendor.com/send", host="sms.vendor.com")]},
        "org/api-scoring": {"repo": "org/api-scoring", "role": "backend", "summary": {"lines_scanned": 2000, "candidates": 1}, "candidates": [
            cand("grpc", "inbound", raw_value="ScoringService", service="ScoringService")]},
        "org/api-quotes": {"repo": "org/api-quotes", "role": "backend", "summary": {"lines_scanned": 3000, "candidates": 1}, "candidates": [
            cand("http", "inbound", raw_value="/quotes/{id}", method="GET", path="/quotes/{id}")]},
        "org/api-unrelated": {"repo": "org/api-unrelated", "role": "backend", "summary": {"lines_scanned": 9000, "candidates": 3}, "candidates": [
            cand("http", "inbound", raw_value="/reports/monthly", method="GET", path="/reports/monthly")]},
    }
    a = run(prescan)
    b = run(prescan)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True), "not deterministic"
    ep = a["entry_points"][0]
    reached = {x["repo"]: x for x in ep["reached"]}
    assert set(reached) == {"org/api-payments", "org/worker-notifier", "org/api-scoring"}, set(reached)
    assert reached["org/api-payments"]["depth"] == 1 and reached["org/api-payments"]["confidence"] == "high"
    assert reached["org/worker-notifier"]["depth"] == 2 and reached["org/worker-notifier"]["via"].startswith("queue"), "a queue must reach its consumer"
    assert reached["org/api-scoring"]["depth"] == 2, "gRPC by service name"
    assert "org/api-unrelated" in a["not_reached"] and "org/api-quotes" in a["not_reached"], a["not_reached"]
    assert ep["unresolved_outbound"] == 4, ep["unresolved_outbound"]       # maps, api.acme.internal, payvendor, sms: all external
    b2 = run(prescan, domains={"api.acme.internal": "org/api-quotes"})
    assert "org/api-quotes" in {x["repo"] for x in b2["entry_points"][0]["reached"]}, "domains map"
    assert ep["totals"]["repos"] == 4 and ep["totals"]["lines"] == 8800, ep["totals"]
    assert a["whole_workspace"]["repos"] == 6 and ep["totals"]["tokens_read"] < a["whole_workspace"]["tokens_read"]
    assert norm_path("`${environment.apiUrl}/api/payments/history`") == "/api/payments/history"
    assert norm_path("https://x.io/users/42/orders/{id}?a=1") == "/users/*/orders/*"
    assert path_match("/health", "/health") is None, "generic paths must not link repos"
    print(f"selftest ok: front-web reaches {len(reached)} of 5 repos, {len(a['not_reached'])} not reached, deterministic")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Reach of the entry points of a workspace")
    ap.add_argument("--prescan-dir")
    ap.add_argument("--output")
    ap.add_argument("--roles")
    ap.add_argument("--domains")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.prescan_dir and a.output):
        ap.error("--prescan-dir and --output are required")
    try:
        prescan = load_prescan(a.prescan_dir)
        if not prescan:
            raise ValueError(f"no prescan JSON found in {a.prescan_dir}")
        roles = json.load(open(a.roles, encoding="utf-8")) if a.roles else None
        domains = json.load(open(a.domains, encoding="utf-8")) if a.domains else None
        out = run(prescan, roles, domains)
    except (OSError, ValueError, KeyError) as e:
        print(f"invalid input: {e}", file=sys.stderr)
        return 1
    json.dump(out, open(a.output, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for ep in out["entry_points"]:
        t = ep["totals"]
        print(f"{ep['repo']} ({ep['role']}): reaches {t['repos'] - 1} repos, {t['lines']:,} lines, {t['candidates']} candidates, "
              f"~{t['tokens_read']:,} tokens to read, ~{t['minutes_writing']} min writing")
    w = out["whole_workspace"]
    print(f"whole workspace: {w['repos']} repos, {w['lines']:,} lines, {w['candidates']} candidates, "
          f"~{w['tokens_read']:,} tokens to read, ~{w['minutes_writing']} min writing -> {a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
