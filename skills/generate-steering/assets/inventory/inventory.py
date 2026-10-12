#!/usr/bin/env python3
"""Free, deterministic inventory of a workspace for kiro-allspark.

Python standard library only (no installs, no network, no model calls).
It never fails: every per-repo problem is recorded as a warning and the run
always finishes and writes its result.

What it does, per repo:
  * discovers the repos (multi-root config -> .git folders -> steering cross-check)
  * detects the stack (manifest files) and a role HINT (find-connections decides)
  * counts lines of code (non-blank) and shows progress in real time (stderr)
  * detects which protocols are present (only to weight the credit estimate)
  * finds internal imports toward sibling repos (native Python `ast` for .py,
    regex for JS/TS)
  * draws an ASCII folder tree
  * computes BASE credits: (lines / 1000) x complexity factor
  * suggests a conservative .kiroignore (never writes it)
  * optionally writes tech.md / structure.md / a product.md skeleton, only
    where they do not exist yet

Result: <workspace>/.kiro/allspark/inventory.json (local working artifact).
"""
import argparse
import ast
import fnmatch
import json
import os
import re
import sys
import time

INVENTORY_VERSION = "1.0.0"

EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "bin", "obj", "out",
    ".venv", "venv", "env", "__pycache__", "coverage", ".next", ".nuxt",
    ".angular", ".gradle", ".idea", ".vscode", "vendor", ".pytest_cache",
    ".mypy_cache", ".tox", ".cache", ".turbo", "site-packages", ".kiro",
}

SOURCE_EXT = {
    ".ts": "typescript", ".tsx": "typescript", ".js": "typescript",
    ".jsx": "typescript", ".mjs": "typescript", ".cjs": "typescript",
    ".vue": "typescript", ".svelte": "typescript",
    ".py": "python", ".java": "java", ".kt": "java", ".cs": "csharp",
    ".rb": "ruby", ".go": "go", ".php": "php",
}
PRESCAN_LANGS = {"typescript", "python", "java", "csharp", "ruby"}
MAX_FILE_BYTES = 2 * 1024 * 1024

# Complexity factor per protocol. HTTP, webhooks and gRPC/Kafka come from the
# design; SOAP, queues (RabbitMQ) and S3 are assumptions, adjustable here and
# echoed in the JSON output (credits.factors) so nothing is hidden.
FACTORS = {
    "http": 1.0, "soap": 1.0, "s3": 1.0,
    "webhook": 1.1,
    "grpc": 1.3, "kafka": 1.3, "rabbitmq": 1.3,
}
LEVEL_MULTIPLIER = {"L1": 1, "L2": 2, "L3": 4}

PROTOCOL_MARKERS = {
    "grpc": re.compile(r"(?i)\bgrpc\b|@grpc/|\.proto\b"),
    "kafka": re.compile(r"(?i)\bkafka"),
    "rabbitmq": re.compile(r"(?i)\bamqp|rabbitmq|\bpika\b|\bbunny\b"),
    "soap": re.compile(r"(?i)\bsoap\b|\bwsdl\b|\bzeep\b|\bsavon\b"),
    "webhook": re.compile(r"(?i)webhook"),
    "s3": re.compile(r"(?i)\bs3client\b|client-s3|\bboto3\b.*s3|aws-sdk.*s3|AmazonS3"),
    "http": re.compile(r"(?i)\baxios\b|\bfetch\(|requests\.|httpx|HttpClient|RestTemplate|"
                       r"WebClient|Faraday|HTTParty|Net::HTTP|@(Get|Post|Put|Delete)\b|"
                       r"app\.(get|post|put|delete)\(|\bFeignClient"),
}

FRONTEND_DEPS = {"react", "react-dom", "vue", "@angular/core", "svelte", "next", "nuxt", "solid-js"}
SERVER_DEPS = {"express", "@nestjs/core", "fastify", "koa", "hapi", "@hapi/hapi"}
WORKER_DEPS = {"bull", "bullmq", "agenda", "bee-queue", "kafkajs", "amqplib"}
FULLSTACK_DEPS = {"next", "nuxt", "@remix-run/node", "sveltekit"}

PY_FRAMEWORKS = {"django": "Django", "flask": "Flask", "fastapi": "FastAPI", "celery": "Celery"}


def log(msg):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def read_text(path, limit=MAX_FILE_BYTES):
    try:
        if os.path.getsize(path) > limit:
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def read_json(path):
    text = read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except ValueError:
        # JSONC (comments / trailing commas), as used by .code-workspace
        cleaned = re.sub(r"(?m)^\s*//.*$", "", text)
        cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
        try:
            return json.loads(cleaned)
        except ValueError:
            return None


# ---------------------------------------------------------------- discovery

def discover_repos(workspace, warnings):
    """Multi-root config -> .git folders -> steering cross-check."""
    ws = os.path.abspath(workspace)
    found = {}
    source = "git-folders"

    for name in sorted(os.listdir(ws)):
        if name.endswith(".code-workspace"):
            data = read_json(os.path.join(ws, name))
            if isinstance(data, dict):
                for fol in data.get("folders", []):
                    p = fol.get("path") if isinstance(fol, dict) else None
                    if p:
                        full = os.path.normpath(os.path.join(ws, p))
                        if os.path.isdir(full):
                            found[full] = "multi-root"
                            source = "multi-root"
    kiro_ws = os.path.join(ws, ".kiro", "settings", "workspace.json")
    data = read_json(kiro_ws) if os.path.isfile(kiro_ws) else None
    if isinstance(data, dict):
        for fol in data.get("folders", []):
            p = fol.get("path") if isinstance(fol, dict) else None
            if p:
                full = os.path.normpath(os.path.join(ws, p))
                if os.path.isdir(full):
                    found[full] = "multi-root"
                    source = "multi-root"

    if not found:
        for root, dirs, _ in os.walk(ws):
            if ".git" in dirs or os.path.isfile(os.path.join(root, ".git")):
                found[root] = "git"
                dirs[:] = []  # do not descend into a repo
                continue
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

    # cross-check: steering present but repo not discovered => discovery gap
    for root, dirs, _ in os.walk(ws):
        if os.path.isdir(os.path.join(root, ".kiro", "steering")):
            if not any(root == r or root.startswith(r + os.sep) for r in found):
                warnings.append("steering found in %s but the repo was not discovered; "
                                "review discovery" % os.path.relpath(root, ws))
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
    return sorted(found), source


# ------------------------------------------------------------------ ignore

def _glob_regex(pattern):
    """gitignore glob -> regex: '*' and '?' never cross '/', '**' does."""
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


class Ignore:
    """.kiroignore reader with gitignore semantics: last matching pattern wins,
    '!' re-includes, a leading or inner '/' anchors to the repo root, a trailing
    '/' matches directories only. A re-include cannot rescue a path whose parent
    directory is excluded (the walk prunes excluded directories)."""

    def __init__(self, repo):
        self.rules = []  # (negated, dir_only, anchored, regex)
        text = read_text(os.path.join(repo, ".kiroignore"))
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            neg = line.startswith("!")
            if neg:
                line = line[1:]
            dir_only = line.endswith("/")
            body = line.rstrip("/")
            anchored = body.startswith("/") or "/" in body
            body = body.lstrip("/")
            if body:
                self.rules.append((neg, dir_only, anchored, _glob_regex(body)))
        self.active = bool(self.rules)

    def skip(self, rel, is_dir=False):
        ignored = False
        base = rel.rsplit("/", 1)[-1]
        for neg, dir_only, anchored, rx in self.rules:
            if dir_only and not is_dir:
                continue
            if rx.match(rel if anchored else base):
                ignored = not neg
        return ignored


# --------------------------------------------------------------- stack/role

def detect_stack(repo):
    stack = {"languages": [], "frameworks": [], "deps": [], "manifests": [], "has_views": False}

    def add(lst, v):
        if v not in lst:
            lst.append(v)

    pkg = read_json(os.path.join(repo, "package.json"))
    if isinstance(pkg, dict):
        add(stack["manifests"], "package.json")
        deps = {}
        deps.update(pkg.get("dependencies") or {})
        deps.update(pkg.get("devDependencies") or {})
        stack["deps"] = sorted(deps)
        add(stack["languages"], "typescript" if ("typescript" in deps or
            os.path.isfile(os.path.join(repo, "tsconfig.json"))) else "javascript")
        names = {"@nestjs/core": "NestJS", "express": "Express", "fastify": "Fastify",
                 "@angular/core": "Angular", "react": "React", "vue": "Vue", "next": "Next.js",
                 "nuxt": "Nuxt", "svelte": "Svelte", "kafkajs": "kafkajs", "amqplib": "amqplib",
                 "bull": "Bull", "bullmq": "BullMQ"}
        for dep, label in names.items():
            if dep in deps:
                add(stack["frameworks"], label)

    for fname in ("requirements.txt", "pyproject.toml", "Pipfile", "setup.py"):
        text = read_text(os.path.join(repo, fname)).lower()
        if text:
            add(stack["manifests"], fname)
            add(stack["languages"], "python")
            if fname == "requirements.txt":
                for line in text.splitlines():
                    m = re.match(r"\s*([a-z0-9][a-z0-9._-]*)", line)
                    if m and not line.lstrip().startswith(("#", "-")):
                        add(stack["deps"], m.group(1))
            for key, label in PY_FRAMEWORKS.items():
                if re.search(r"(^|[\s\"'=,\[-])%s([\s\"'=<>~!\],;]|$)" % key, text):
                    add(stack["frameworks"], label)

    for fname in ("pom.xml", "build.gradle", "build.gradle.kts"):
        text = read_text(os.path.join(repo, fname))
        if text:
            add(stack["manifests"], fname)
            add(stack["languages"], "java")
            if "spring" in text.lower():
                add(stack["frameworks"], "Spring")

    for name in os.listdir(repo):
        if name.endswith((".csproj", ".sln")):
            add(stack["manifests"], name)
            add(stack["languages"], "csharp")
            if name.endswith(".csproj") and re.search(r"Microsoft\.NET\.Sdk\.Web|AspNetCore",
                                                      read_text(os.path.join(repo, name))):
                add(stack["frameworks"], "ASP.NET")
    if os.path.isfile(os.path.join(repo, "Gemfile")):
        add(stack["manifests"], "Gemfile")
        add(stack["languages"], "ruby")
        gem = read_text(os.path.join(repo, "Gemfile")).lower()
        if "rails" in gem:
            add(stack["frameworks"], "Rails")
        if "sidekiq" in gem:
            add(stack["frameworks"], "Sidekiq")
    if os.path.isfile(os.path.join(repo, "go.mod")):
        add(stack["manifests"], "go.mod")
        add(stack["languages"], "go")

    for v in ("views", "templates", "Views", "app/views"):
        if os.path.isdir(os.path.join(repo, v)) or os.path.isdir(os.path.join(repo, "src", v)):
            stack["has_views"] = True
    return stack


def role_hint(stack):
    deps = set(stack["deps"])
    fw = set(stack["frameworks"])
    signals = []
    ui = bool(deps & FRONTEND_DEPS) or "Angular" in fw
    server = bool(deps & SERVER_DEPS) or bool(fw & {"NestJS", "Express", "Fastify", "Django",
                                                    "Flask", "FastAPI", "Spring", "ASP.NET", "Rails"})
    queue = bool(deps & WORKER_DEPS) or bool(fw & {"Celery", "Sidekiq"})
    if ui:
        signals.append("UI framework")
    if server:
        signals.append("HTTP server framework")
    if queue:
        signals.append("queue/job library")
    if stack["has_views"]:
        signals.append("views/templates folder")
    if deps & FULLSTACK_DEPS or (server and stack["has_views"]) or "Rails" in fw and stack["has_views"]:
        return "mvc-monolith", signals
    if ui and not server:
        return "frontend", signals
    if server and not ui:
        return "backend", signals
    if queue and not server and not ui:
        return "worker", signals
    if ui and server:
        return "mvc-monolith", signals
    return "unknown", signals


# ------------------------------------------------------------------ scanning

def count_lines(path):
    """Non-blank lines; binary files (NUL byte in the first KB) count as 0."""
    try:
        with open(path, "rb") as f:
            if b"\0" in f.read(1024):
                return 0
            f.seek(0)
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def walk_repo(repo, ign, progress_name):
    """Yield (rel_posix, abs) for every source candidate, honoring exclusions."""
    for root, dirs, files in os.walk(repo):
        rel_root = os.path.relpath(root, repo).replace(os.sep, "/")
        kept = []
        for d in dirs:
            if d in EXCLUDED_DIRS:
                continue
            rel = d if rel_root == "." else rel_root + "/" + d
            if ign.active and ign.skip(rel, True):
                continue
            kept.append(d)
        dirs[:] = sorted(kept)
        for fname in sorted(files):
            rel = fname if rel_root == "." else rel_root + "/" + fname
            if ign.active and ign.skip(rel):
                continue
            yield rel, os.path.join(root, fname)


def py_imports(text):
    names = []
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return names
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.append((a.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.append((node.module, node.lineno))
    return names


JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(?\s*|require\(\s*)['"]([^'"]+)['"]""")


def js_imports(text):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in JS_IMPORT.finditer(line):
            spec = m.group(1)
            if not spec.startswith("."):
                out.append((spec, i))
    return out


def norm(name):
    name = name.lower().replace("@", "").replace("/", "-").replace("_", "-")
    return name.strip("-")


def scan_repo(repo, ws, sibling_names, started):
    """Count lines, detect protocols, collect internal imports and file tree data."""
    name = os.path.basename(repo.rstrip(os.sep))
    ign = Ignore(repo)
    loc_by_lang, loc_by_top = {}, {}
    file_count = 0
    protocols = {}
    internal = []
    tree_entries = {}
    warnings = []
    last_report = time.time()
    total = 0
    sibling_keys = {norm(s): s for s in sibling_names if s != name}

    for rel, abspath in walk_repo(repo, ign, name):
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
        tree_entries.setdefault(parent, []).append(rel.rsplit("/", 1)[-1])
        ext = os.path.splitext(rel)[1].lower()
        lang = SOURCE_EXT.get(ext)
        if rel.endswith(".proto"):
            protocols["grpc"] = protocols.get("grpc", 0) + 1
        if not lang:
            continue
        try:
            if os.path.getsize(abspath) > MAX_FILE_BYTES:
                warnings.append("skipped (too large): " + rel)
                continue
        except OSError:
            continue
        n = count_lines(abspath)
        file_count += 1
        total += n
        loc_by_lang[lang] = loc_by_lang.get(lang, 0) + n
        top = rel.split("/")[0] if "/" in rel else "(root)"
        loc_by_top[top] = loc_by_top.get(top, 0) + n

        text = read_text(abspath)
        for proto, rx in PROTOCOL_MARKERS.items():
            if rx.search(text):
                protocols[proto] = protocols.get(proto, 0) + 1
        if sibling_keys and text:
            imports = py_imports(text) if lang == "python" else (
                js_imports(text) if lang == "typescript" else [])
            for mod, line in imports:
                parts = mod.split("/")
                scoped = "/".join(parts[:2]) if mod.startswith("@") else parts[0]
                keys = (norm(scoped), norm(parts[1]) if mod.startswith("@") and len(parts) > 1 else "",
                        norm(mod.split(".")[0]))
                for k in keys:
                    if k in sibling_keys:
                        internal.append({"to_repo": sibling_keys[k], "file": rel,
                                         "line": line, "module": mod})
                        break
        if time.time() - last_report > 2:
            log("  [%s] %d lines so far (%.0fs)" % (name, total, time.time() - started))
            last_report = time.time()
    return {
        "lines": total, "files": file_count, "loc_by_language": loc_by_lang,
        "loc_by_top_folder": dict(sorted(loc_by_top.items(), key=lambda kv: -kv[1])),
        "protocols": dict(sorted(protocols.items(), key=lambda kv: -kv[1])),
        "internal_imports": internal[:200],
        "ignore_active": ign.active,
        "_tree": tree_entries,
    }, warnings


def ascii_tree(tree_entries, name, max_depth=3, per_dir=20, max_lines=150):
    """Standard ASCII tree: directories first; capped so it stays cheap."""
    children = {}
    for parent, files in tree_entries.items():
        children.setdefault(parent, {"dirs": set(), "files": []})["files"].extend(files)
        parts = parent.split("/") if parent else []
        for i in range(len(parts)):
            up = "/".join(parts[:i])
            children.setdefault(up, {"dirs": set(), "files": []})["dirs"].add(parts[i])
    lines = [name + "/"]

    def render(path, prefix, depth):
        if len(lines) >= max_lines:
            return
        node = children.get(path, {"dirs": set(), "files": []})
        dirs = sorted(node["dirs"])
        files = sorted(node["files"]) if depth < max_depth else []
        items = [("d", d) for d in dirs] + [("f", f) for f in files]
        shown = items[:per_dir]
        hidden = len(items) - len(shown)
        for idx, (kind, item) in enumerate(shown):
            last = idx == len(shown) - 1 and hidden == 0
            lines.append(prefix + ("└── " if last else "├── ") + item + ("/" if kind == "d" else ""))
            if kind == "d":
                sub = (path + "/" + item) if path else item
                if depth + 1 < max_depth:
                    render(sub, prefix + ("    " if last else "│   "), depth + 1)
        if hidden > 0:
            lines.append(prefix + "└── … (+%d more)" % hidden)

    render("", "", 0)
    if len(lines) >= max_lines:
        lines.append("… (tree truncated)")
    return "\n".join(lines)


def suggest_kiroignore(repo, stack):
    """Conservative whitelist: only folders that really exist. Never written."""
    candidates = ["src", "lib", "app", "pages", "components", "modules", "services",
                  "controllers", "routes", "api", "server", "client", "packages", "internal", "cmd"]
    present = [c for c in candidates if os.path.isdir(os.path.join(repo, c))]
    if "java" in stack["languages"] and os.path.isdir(os.path.join(repo, "src", "main")):
        present = [p for p in present if p != "src"] + ["src"]
    root_files = [m for m in stack["manifests"]] + ["README.md", "tsconfig.json"]
    root_files = [f for f in dict.fromkeys(root_files) if os.path.isfile(os.path.join(repo, f))]
    lines = ["# kiro-allspark suggestion (conservative whitelist, gitignore syntax)",
             "# Review it before using it. If your Kiro version does not honor",
             "# negation (!), use the standard exclusion list instead.",
             "/*"]
    lines += ["!/%s/" % p for p in present]
    lines += ["!/%s" % f for f in root_files]
    lines += ["!/.kiro/", ".kiro/allspark/"]
    return {"folders_found": present, "content": "\n".join(lines) + "\n"}


# ------------------------------------------------------------------ credits

def credit_row(lines, protocols):
    detected = [p for p in protocols if p in FACTORS] or ["http"]
    factor = max(FACTORS[p] for p in detected)
    l1 = round(lines / 1000.0 * factor, 2)
    return {"factor": factor, "factor_protocols": detected,
            "L1": l1, "L2": round(l1 * LEVEL_MULTIPLIER["L2"], 2),
            "L3": round(l1 * LEVEL_MULTIPLIER["L3"], 2)}


def markdown_table(repos):
    rows = ["| Repo | Role (hint) | Lines | Factor | L1 | L2 | L3 |",
            "|---|---|---:|---:|---:|---:|---:|"]
    t = {"L1": 0, "L2": 0, "L3": 0}
    for r in repos:
        c = r["credits"]
        rows.append("| %s | %s | %s | %.1f | %s | %s | %s |" % (
            r["name"], r["role_hint"], format(r["lines"], ","), c["factor"],
            c["L1"], c["L2"], c["L3"]))
        for k in t:
            t[k] += c[k]
    rows.append("| **Total** | | %s | | %s | %s | %s |" % (
        format(sum(r["lines"] for r in repos), ","),
        round(t["L1"], 2), round(t["L2"], 2), round(t["L3"], 2)))
    return "\n".join(rows)


# ------------------------------------------------------------ steering docs

TREE_START = "<!-- allspark:tree:start -->"
TREE_END = "<!-- allspark:tree:end -->"


def write_if_missing(path, content, force, written, skipped):
    if os.path.exists(path) and not force:
        skipped.append(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    written.append(path)


ROLE_WORD = {"frontend": "frontend", "backend": "backend", "mvc-monolith": "MVC monolith",
             "worker": "worker", "unknown": "repo"}


def slugify(text, limit=64):
    out = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return (out or "repo")[:limit].strip("-")


def stack_phrase(info):
    s = info["stack"]
    main = (s["frameworks"] or s["languages"] or [""])[0]
    langs = ", ".join(s["languages"])
    role = ROLE_WORD.get(info["role_hint"], "repo")
    return ("%s %s" % (main, role)).strip() if main else role, langs


def front_matter(info, doc, description):
    """Loading strategy of the power: never `always` per repo; `auto` with a unique name and a description."""
    name = slugify(info["name"], 40) + "-" + doc
    desc = " ".join(description.split())[:300].replace('"', "'")
    return ["---", "inclusion: auto", "name: " + name, 'description: "%s"' % desc, "---"]


def tech_md(info):
    s = info["stack"]
    repo = info["name"]
    phrase, langs = stack_phrase(info)
    fm = front_matter(info, "tech", "Stack and conventions of %s, a %s%s. Use when writing, reviewing or running code in %s." % (
        repo, phrase, " (%s)" % langs if langs else "", repo))
    lines = fm + ["# Tech Stack", "",
             "## Language / runtime"]
    lines += ["- " + l for l in s["languages"]] or ["-"]
    lines += ["", "## Main framework"]
    lines += ["- " + f for f in s["frameworks"]] or ["-"]
    lines += ["", "## Key dependencies"]
    deps = [d for d in s["deps"] if not d.startswith("@types/")][:15]
    lines += ["- " + d for d in deps] or ["-"]
    lines += ["", "## Build / test tools", "- manifests: " + (", ".join(s["manifests"]) or "-"), ""]
    return "\n".join(lines)


def structure_md(info, tree):
    tops = [t for t in info["loc_by_top_folder"] if t != "(root)"][:8]
    phrase, _ = stack_phrase(info)
    fm = front_matter(info, "structure", "Folder layout, layers and modules of %s (%s). Use when locating files or adding code to %s." % (
        info["name"], phrase, info["name"]))
    lines = fm + ["# Repo structure", "",
             "## Folder tree", TREE_START, "```text", tree, "```", TREE_END, "",
             "## Folder organization", "-", "", "## Layers / architectural patterns", "-", "",
             "## Naming conventions", "-", "", "## Main modules"]
    lines += ["- %s/ — (%s lines)" % (t, format(info["loc_by_top_folder"][t], ",")) for t in tops] or ["-"]
    sig = ", ".join(info["role_signals"]) or "none detected"
    lines += ["", "## Role signals",
              "- Detected by the inventory: %s (hint: %s; find-connections decides the role)" % (
                  sig, info["role_hint"]), ""]
    return "\n".join(lines)


def product_md(info, repo):
    purpose = "-"
    readme = read_text(os.path.join(repo, "README.md"))
    for para in re.split(r"\n\s*\n", readme):
        p = para.strip()
        if p and not p.startswith(("#", "!", "[", "<", "```", "|", "-")):
            purpose = " ".join(p.split())[:300]
            break
    tops = [t for t in info["loc_by_top_folder"] if t != "(root)"][:8]
    what = (" " + purpose.rstrip(".") + ".") if purpose != "-" else ""
    fm = front_matter(info, "product", "What %s is for and who uses it:%s Use when asking what %s does or why." % (
        info["name"], what or " (to be filled in).", info["name"]))
    lines = fm + ["# Product", "", "## Purpose", "- " + purpose, "",
             "## Users", "-", "", "## Modules",
             "<!-- hierarchy mirrors structure.md; fill each module in one line, never invent -->"]
    lines += ["- %s/ — -" % t for t in tops] or ["-"]
    lines += ["", "## Business context", "-", ""]
    return "\n".join(lines)


INDEX_HEAD = ["---", "inclusion: always", "---", "# Workspace index (Kiro Allspark)", "",
              "Repos of this workspace. Each one has its own steering, loaded only when the",
              "request is about it; ask for one explicitly with `#name`.", "",
              "| repo | role | stack | entry point | steering |", "|---|---|---|---|---|"]


def update_index(ws, infos, written):
    """Upsert one row per repo in <workspace>/.kiro/steering/allspark-index.md; rows of other repos are kept."""
    path = os.path.join(ws, ".kiro", "steering", "allspark-index.md")
    rows, order = {}, []
    for line in read_text(path).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 5 and cells[0] not in ("repo", "---"):
            rows[cells[0]] = cells
            order.append(cells[0])
    for info in infos:
        name, slug = info["name"], slugify(info["name"], 40)
        phrase, langs = stack_phrase(info)
        steering = " · ".join("#%s-%s" % (slug, d) for d in ("product", "tech", "structure"))
        if info["has_steering"].get("moc.md"):
            steering += " · #%s-moc" % slug
        old = rows.get(name)
        entry = old[3] if old and old[3].lower().startswith("yes") else (
            "candidate" if info["role_hint"] in ("frontend", "mvc-monolith") else "—")
        rows[name] = [name, info["role_hint"], (info["stack"]["frameworks"] or info["stack"]["languages"] or ["-"])[0], entry, steering]
        if name not in order:
            order.append(name)
    body = INDEX_HEAD + ["| " + " | ".join(rows[n]) + " |" for n in order] + [""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(body))
    written.append(path)


def refresh_tree(path, tree):
    text = read_text(path)
    if TREE_START in text and TREE_END in text:
        head, rest = text.split(TREE_START, 1)
        _, tail = rest.split(TREE_END, 1)
        new = head + TREE_START + "\n```text\n" + tree + "\n```\n" + TREE_END + tail
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new)
        return True
    return False


# ---------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="kiro-allspark workspace inventory (free, never fails)")
    ap.add_argument("--workspace", default=".", help="workspace root")
    ap.add_argument("--repo", action="append", help="limit to these repo folders (repeatable)")
    ap.add_argument("--output", help="inventory.json path (default <workspace>/.kiro/allspark/inventory.json)")
    ap.add_argument("--depth", type=int, default=3, help="ASCII tree depth (default 3)")
    ap.add_argument("--write-steering", action="store_true",
                    help="write tech.md / structure.md / product.md where they do not exist, and upsert allspark-index.md")
    ap.add_argument("--force", action="store_true", help="with --write-steering: overwrite existing docs")
    ap.add_argument("--table", action="store_true", help="print the credits table (markdown) to stdout")
    args = ap.parse_args()

    started = time.time()
    ws = os.path.abspath(args.workspace)
    warnings, errors = [], []
    result = {"inventory_version": INVENTORY_VERSION, "workspace": ws, "status": "ok",
              "repos": [], "warnings": warnings, "errors": errors,
              "credits": {"formula": "(lines / 1000) x complexity factor; L2 = L1 x 2; L3 = L1 x 4",
                          "unit": "base credits (reference; multiply by the model you use in Kiro)",
                          "factors": FACTORS}}
    try:
        if args.repo:
            repos = [os.path.abspath(r) for r in args.repo if os.path.isdir(r)]
            source = "explicit"
        else:
            repos, source = discover_repos(ws, warnings)
        result["discovery"] = source
        names = [os.path.basename(r.rstrip(os.sep)) for r in repos]
        log("allspark inventory: %d repo(s) found (%s)" % (len(repos), source))
        for repo in repos:
            name = os.path.basename(repo.rstrip(os.sep))
            try:
                log("scanning %s ..." % name)
                stack = detect_stack(repo)
                hint, signals = role_hint(stack)
                scan, w = scan_repo(repo, ws, names, started)
                warnings += ["%s: %s" % (name, x) for x in w]
                tree = ascii_tree(scan.pop("_tree"), name, max_depth=args.depth)
                info = {"name": name, "path": os.path.relpath(repo, ws).replace(os.sep, "/"),
                        "stack": {k: v for k, v in stack.items() if k != "has_views"},
                        "role_hint": hint, "role_signals": signals}
                info.update(scan)
                info["credits"] = credit_row(scan["lines"], scan["protocols"])
                info["has_steering"] = {f: os.path.isfile(os.path.join(repo, ".kiro", "steering", f))
                                        for f in ("tech.md", "structure.md", "product.md", "moc.md")}
                info["has_kiroignore"] = os.path.isfile(os.path.join(repo, ".kiroignore"))
                info["kiroignore_suggestion"] = suggest_kiroignore(repo, stack)
                info["ascii_tree"] = tree
                if args.write_steering:
                    written, skipped = [], []
                    sd = os.path.join(repo, ".kiro", "steering")
                    write_if_missing(os.path.join(sd, "tech.md"), tech_md(info), args.force, written, skipped)
                    sp = os.path.join(sd, "structure.md")
                    if os.path.exists(sp) and not args.force:
                        if refresh_tree(sp, tree):
                            written.append(sp + " (tree refreshed)")
                        else:
                            skipped.append(sp)
                    else:
                        write_if_missing(sp, structure_md(info, tree), True, written, skipped)
                    write_if_missing(os.path.join(sd, "product.md"), product_md(info, repo),
                                     args.force, written, skipped)
                    info["steering_written"] = [os.path.relpath(p.split(" (")[0], ws) for p in written]
                    info["steering_skipped"] = [os.path.relpath(p, ws) for p in skipped]
                result["repos"].append(info)
                log("  %s: %s lines, role hint: %s, L1 = %s base credits" % (
                    name, format(info["lines"], ","), hint, info["credits"]["L1"]))
            except Exception as exc:  # never fail: record and continue
                errors.append("%s: %s" % (name, exc))
                result["status"] = "partial"
    except Exception as exc:
        errors.append("workspace: %s" % exc)
        result["status"] = "partial"

    if args.write_steering and result["repos"]:
        try:
            idx_written = []
            update_index(ws, result["repos"], idx_written)
            result["index_written"] = [os.path.relpath(p, ws) for p in idx_written]
        except Exception as exc:
            warnings.append("workspace index not written: %s" % exc)

    result["totals"] = {
        "lines": sum(r["lines"] for r in result["repos"]),
        "L1": round(sum(r["credits"]["L1"] for r in result["repos"]), 2),
        "L2": round(sum(r["credits"]["L2"] for r in result["repos"]), 2),
        "L3": round(sum(r["credits"]["L3"] for r in result["repos"]), 2)}
    result["seconds"] = round(time.time() - started, 1)

    out = args.output or os.path.join(ws, ".kiro", "allspark", "inventory.json")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        log("inventory written: " + out)
    except OSError as exc:
        errors.append("could not write output: %s" % exc)
        sys.stdout.write(json.dumps(result, ensure_ascii=False))
    if args.table and result["repos"]:
        sys.stdout.write(markdown_table(result["repos"]) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # last resort: never crash
        sys.stderr.write("inventory ended with an error (partial): %s\n" % exc)
        sys.exit(0)
