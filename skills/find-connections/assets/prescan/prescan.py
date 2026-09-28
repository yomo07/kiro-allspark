#!/usr/bin/env python3
"""Deterministic prescan of kiro-allspark (step 2.B.1 of find-connections).

Kiro runs it, not a model: it walks a repo, parses the code with tree-sitter
and applies rules declared as data (rules/<language>.json) to produce a list
of connection CANDIDATES (HTTP, SOAP, gRPC, queues, webhooks, S3). It does not
classify axes nor resolve domains: Kiro does that afterwards (2.B.2).

Usage:
  prescan.py --repo PATH --stack nestjs[,spring] --role backend --output PATH.json [--id org/repo] [--cache]
  prescan.py --verify     # installed dependencies and versions (step 2.B.0)
  prescan.py --stacks     # supported stacks

Exit codes:
  0  scan complete (at least one stack with a pattern)
  2  no declared stack has a pattern: the JSON is written anyway (contracts and
     config) and Kiro falls back to manual reading for that repo
  1  real error (dependencies, arguments, missing repo)
"""
import argparse
import fnmatch
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

PRESCAN_VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Fixed exclusions (on top of the repo's .kiroignore and .gitignore)
# --------------------------------------------------------------------------
EXCLUDED_DIRS = {
    ".git", "node_modules", "dist", "build", "target", "out", "bin", "obj",
    "vendor", "venv", ".venv", "env", "__pycache__", ".next", ".nuxt",
    "coverage", ".gradle", ".idea", ".vscode", ".kiro", "tmp", "log", "logs",
    # tests and test doubles: they are not real connections of the repo
    "test", "tests", "__tests__", "spec", "__mocks__", "mocks", "fixtures",
    "e2e", "testdata",
}
TEST_FILES = [
    "*.spec.*", "*.test.*", "test_*.py", "*_test.py", "*Test.java", "*Tests.java",
    "*IT.java", "*Test.cs", "*Tests.cs", "*_spec.rb", "*_test.rb", "conftest.py",
]
# Never opened: they may contain real secrets
SECRET_FILES = [
    ".env", ".env.local", ".env.*.local", ".env.production", ".env.development",
    ".env.staging", ".env.test", "*.pem", "*.key", "*.p12", "*.pfx", "*.jks",
    "id_rsa*", "secrets.*", "credentials*",
]
ALLOWED_ENV = [".env.example", ".env.sample", ".env.template", ".env.dist",
               "*.env.example", "*.env.sample"]

# Non-secret config files read in the config pass (step 3 of the chain)
CONFIG_PATTERNS = [
    "application*.yml", "application*.yaml", "application*.properties",
    "bootstrap*.yml", "bootstrap*.yaml", "appsettings*.json",
    "docker-compose*.yml", "docker-compose*.yaml", "compose*.yml", "compose*.yaml",
    "environment*.ts",
] + ALLOWED_ENV
CONFIG_DIRS = {"k8s", "kubernetes", "deploy", "deployment", "helm", "charts",
               "manifests", "infra", "config", "conf"}
CONFIG_EXT_IN_DIRS = (".yml", ".yaml", ".json", ".toml", ".properties")

CONTRACT_PATTERNS = ["*.wsdl", "*.xsd", "openapi*.yml", "openapi*.yaml", "openapi*.json",
                     "swagger*.yml", "swagger*.yaml", "swagger*.json",
                     "asyncapi*.yml", "asyncapi*.yaml", "asyncapi*.json"]

SECRET_KEY = re.compile(r"(?i)(pass(word)?|pwd|secret|token|api[_-]?key|apikey|private[_-]?key|credential|client[_-]?secret)")
USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/@\"']+@")
DB_SCHEMES = re.compile(r"(?i)^(jdbc:|postgres(ql)?://|mysql://|mariadb://|mongodb(\+srv)?://|redis://|rediss://|sqlserver://|oracle:)")

CLASS_TYPES = {"class_declaration", "interface_declaration", "class_definition",
               "abstract_class_declaration", "record_declaration", "struct_declaration",
               "enum_declaration"}
STRING_TYPES = {"string", "template_string", "string_literal", "interpolated_string_expression",
                "verbatim_string_literal", "raw_string_literal"}
INTERPOLATION_TYPES = {"template_substitution", "interpolation"}
CONTENT_TYPES = {"string_fragment", "string_content", "string_literal_content", "escape_sequence"}
NUMBER_TYPES = {"number", "integer", "decimal_integer_literal", "integer_literal", "float"}
LIST_TYPES = {"list", "array", "array_initializer", "element_value_array_initializer",
              "tuple", "array_creation_expression", "implicit_array_creation_expression",
              "initializer_expression", "collection_expression"}
CALL_TYPES = {"call", "call_expression", "invocation_expression", "method_invocation",
              "new_expression", "object_creation_expression"}

VERBS = ("get", "post", "put", "patch", "delete", "head", "options")

# Source extensions of languages the prescan has no grammar for. If a repo has
# them, the language is added to stacks_without_pattern even if tech.md did not
# declare it (e.g. a Spring repo written in Kotlin), so it is never missed.
UNSUPPORTED_EXT = {
    ".kt": "kotlin", ".kts": "kotlin", ".go": "go", ".php": "php", ".scala": "scala",
    ".rs": "rust", ".ex": "elixir", ".exs": "elixir", ".swift": "swift", ".dart": "dart",
    ".groovy": "groovy", ".vb": "vbnet", ".fs": "fsharp",
}


# --------------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------------
def rel(path, base):
    return os.path.relpath(path, base).replace(os.sep, "/")


def matches(name_or_path, patterns):
    base = name_or_path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(base, p) or fnmatch.fnmatch(name_or_path, p) for p in patterns)


def mask(text):
    t = USERINFO.sub(r"\1***@", text)
    t = re.sub(r"(?i)((?:pass(?:word)?|pwd|secret|token|api[_-]?key|apikey)\s*[:=]\s*)(['\"]?)[^\s'\",;)]+",
               r"\1\2***", t)
    return t


def method_from_name(name):
    s = re.sub(r"<.*", "", name).lower()
    s = s.replace("_", "")
    for v in VERBS:
        if s == v or s.startswith(v) or s.endswith(v) or s.startswith("map" + v) or s.startswith("http" + v):
            return v.upper()
    return "*"


def verbs_from_text(text):
    found = [v.upper() for v in VERBS if re.search(r"(?i)\b" + v + r"\b", text)]
    return ",".join(found) if found else None


def host_of(value):
    value = (value or "").lstrip("'\"`f")
    m = re.match(r"(?i)^[a-z][a-z0-9+.-]*://([^/\s?#]+)", value or "")
    if m:
        return m.group(1).split("@")[-1]
    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}|[A-Za-z0-9-]+\.internal|localhost)(:\d{2,5})?$", value or "")
    if m:
        return value
    return None


def join_paths(*parts):
    segs = [p.strip("/") for p in parts if p and p.strip("/")]
    return "/" + "/".join(segs)


# --------------------------------------------------------------------------
# Repo ignore rules (.kiroignore / .gitignore — simple, documented support)
# --------------------------------------------------------------------------
class IgnoreRules:
    def __init__(self, repo, warnings):
        self.patterns = []
        self.negations = 0
        for name in (".kiroignore", ".gitignore"):
            p = os.path.join(repo, name)
            if not os.path.isfile(p):
                continue
            for line in open(p, encoding="utf-8", errors="replace"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("!"):
                    self.negations += 1
                    continue
                self.patterns.append(line)
        if self.negations:
            warnings.append(f"{self.negations} negations (!pattern) in .gitignore/.kiroignore are not supported: those files stay excluded")

    def ignores(self, rel_path, is_dir):
        for p in self.patterns:
            dir_only = p.endswith("/")
            q = p.strip("/")
            if dir_only and not is_dir and not any(
                    fnmatch.fnmatch(seg, q) for seg in rel_path.split("/")[:-1]) and not rel_path.startswith(q + "/"):
                continue
            if fnmatch.fnmatch(rel_path, q) or fnmatch.fnmatch(rel_path, q + "/*") or rel_path.startswith(q + "/"):
                return True
            if "/" not in q and any(fnmatch.fnmatch(seg, q) for seg in rel_path.split("/")):
                return True
            if fnmatch.fnmatch(rel_path, "*/" + q) or fnmatch.fnmatch(rel_path, "**/" + q):
                return True
        return False


# --------------------------------------------------------------------------
# tree-sitter engine
# --------------------------------------------------------------------------
class Language:
    def __init__(self, name, conf, ts):
        self.name = name
        module = importlib.import_module(conf["module"])
        self.lang = ts.Language(getattr(module, conf["function"])())
        self.parser = ts.Parser(self.lang)
        query = open(os.path.join(HERE, "queries", conf["query"]), encoding="utf-8").read()
        self.query = ts.Query(self.lang, query)
        self.cursor_cls = ts.QueryCursor
        data = json.load(open(os.path.join(HERE, "rules", conf["rules"]), encoding="utf-8"))
        self.rules = data["rules"]
        for r in self.rules:
            for k in ("object_regex", "types_regex", "names_regex", "methods_regex", "bases_regex"):
                if k in r:
                    r["_" + k] = re.compile(r[k])


class SourceFile:
    """Context of a parsed file: source bytes and extraction helpers."""

    def __init__(self, source):
        self.b = source

    def txt(self, n):
        return self.b[n.start_byte:n.end_byte].decode("utf-8", errors="replace") if n is not None else ""

    # ---- values --------------------------------------------------------
    def value(self, n):
        """(text, is_literal). Literal = string without interpolation, or a number."""
        if n is None:
            return None, False
        t = n.type
        if t == "simple_symbol":
            return self.txt(n).lstrip(":"), True
        if t in NUMBER_TYPES:
            return self.txt(n), True
        if t in STRING_TYPES or (t == "string" and n.children):
            if any(c.type in INTERPOLATION_TYPES for c in n.children):
                return self.txt(n), False
            parts = [self.txt(c) for c in n.children if c.type in CONTENT_TYPES]
            if not parts and n.child_count == 0:
                return self.txt(n).strip("'\"`"), True
            return "".join(parts), True
        if t in LIST_TYPES:
            vals = [self.value(c) for c in n.named_children]
            lits = [v for v, ok in vals if ok and v is not None]
            if lits and len(lits) == len([v for v in vals if v[0] is not None]):
                return ",".join(lits), True
            return self.txt(n), False
        if t in ("argument", "attribute_argument", "element_value") and n.named_children:
            return self.value(n.named_children[-1])
        if t in CALL_TYPES:
            # unwrap URI("..."), new Uri("..."), URI.create("...")
            args = n.child_by_field_name("arguments")
            if args is not None:
                pos, _ = self.args(args)
                if len(pos) == 1:
                    v, ok = self.value(pos[0])
                    if ok:
                        return v, True
        return self.txt(n), False

    def args(self, n):
        """(positional, named) arguments of an argument list in any language."""
        pos, kw = [], {}
        if n is None:
            return pos, kw
        for c in n.named_children:
            t = c.type
            if t in ("comment", "line_comment", "block_comment"):
                continue
            if t == "keyword_argument":
                kw[self.txt(c.child_by_field_name("name"))] = c.child_by_field_name("value")
            elif t == "element_value_pair":
                kw[self.txt(c.child_by_field_name("key"))] = c.child_by_field_name("value")
            elif t == "pair":
                k = c.child_by_field_name("key")
                kw[self.txt(k).rstrip(":").strip("'\":")] = c.child_by_field_name("value")
            elif t == "hash":
                for p in c.named_children:
                    if p.type == "pair":
                        kw[self.txt(p.child_by_field_name("key")).rstrip(":").strip("'\":")] = p.child_by_field_name("value")
            elif t == "argument":
                name = c.child_by_field_name("name")
                vals = [x for x in c.named_children if x != name]
                if name is not None and vals:
                    kw[self.txt(name)] = vals[-1]
                elif vals:
                    pos.append(vals[-1])
            elif t == "attribute_argument":
                children = c.named_children
                if children and children[0].type in ("name_equals", "name_colon"):
                    ident = children[0].named_children[0] if children[0].named_children else children[0]
                    kw[self.txt(ident)] = children[-1]
                elif children:
                    pos.append(children[-1])
            else:
                pos.append(c)
        return pos, kw

    def object_pairs(self, nodes):
        """key:value pairs of JS object literals passed as arguments."""
        kw = {}
        for n in nodes:
            if n is not None and n.type == "object":
                for p in n.named_children:
                    if p.type == "pair":
                        kw[self.txt(p.child_by_field_name("key")).strip("'\"")] = p.child_by_field_name("value")
                    elif p.type == "shorthand_property_identifier":
                        kw[self.txt(p)] = p
        return kw


def owner_of(node):
    """Node an annotation/decorator belongs to (method, class or function)."""
    p = node.parent
    if p is None:
        return None
    if p.type in ("modifiers", "attribute_list"):
        p = p.parent
    if p is None:
        return None
    if p.type == "class_body":
        s = node.next_named_sibling
        while s is not None and s.type == "decorator":
            s = s.next_named_sibling
        return s
    if p.type == "export_statement":
        for c in p.named_children:
            if c.type in CLASS_TYPES or c.type == "class":
                return c
    if p.type == "decorated_definition":
        return p.child_by_field_name("definition")
    return p


def container_of(node):
    n = node.parent if node is not None else None
    while n is not None and n.type not in CLASS_TYPES:
        n = n.parent
    return n


class Scanner:
    def __init__(self, repo, languages, warnings):
        self.repo = repo
        self.languages = languages
        self.warnings = warnings
        self.candidates = []
        self.django_warning = False

    # -------------------------------------------------------------------
    def scan_file(self, path, lang):
        with open(path, "rb") as f:
            source = f.read()
        tree = lang.parser.parse(source)
        A = SourceFile(source)
        rel_path = rel(path, self.repo)
        found = lang.cursor_cls(lang.query).matches(tree.root_node)

        forms = {"annotation": [], "call": [], "new": [], "pair": [], "inheritance": []}
        for _, caps in found:
            for form in forms:
                if form in caps:
                    d = {"node": caps[form][0]}
                    for k, v in caps.items():
                        if k.startswith(form + "."):
                            d[k.split(".", 1)[1]] = v[0]
                    forms[form].append(d)
                    break

        # index of annotations by owner (for prefixes and Feign clients)
        annotations_by_owner = {}
        for m in forms["annotation"]:
            owner = owner_of(m["node"])
            m["owner"] = owner
            m["name_txt"] = A.txt(m.get("name"))
            if owner is not None:
                annotations_by_owner.setdefault(owner.id, []).append(m)

        used = set()  # (node.id, group)
        seen = set()
        for rule in lang.rules:
            if "files" in rule and not matches(rel_path, rule["files"]):
                continue
            form = rule["form"]
            for m in forms[form]:
                node = m["node"]
                group = rule.get("group")
                if group and (node.id, group) in used:
                    continue
                c = self.apply(rule, m, A, annotations_by_owner)
                if c is None:
                    continue
                if group:
                    used.add((node.id, group))
                line = node.start_point[0] + 1
                key = (line, c["protocol"], c["direction"], c["raw_value"])
                if key in seen:
                    continue
                seen.add(key)
                line_text = source.split(b"\n")[node.start_point[0]].decode("utf-8", errors="replace").strip()
                c["evidence"] = {"file": rel_path, "line": line, "snippet": mask(line_text)[:160]}
                c["rule"] = rule["id"]
                c["chain_step"] = 1
                if rule["id"] == "py.django.url" and b"include(" in source:
                    self.django_warning = True
                self.candidates.append(postprocess(c))

    # -------------------------------------------------------------------
    def apply(self, r, m, A, annotations_by_owner):
        form = r["form"]
        name = obj = None
        pos, kw = [], {}
        if form == "annotation":
            name = m["name_txt"]
            if "names" in r and name not in r["names"]:
                return None
            if "_names_regex" in r and not r["_names_regex"].search(name):
                return None
            if r.get("methods_only") and (m["owner"] is None or m["owner"].type in CLASS_TYPES):
                return None
            pos, kw = A.args(m.get("args"))
        elif form == "call":
            name = re.sub(r"<.*", "", A.txt(m.get("method")))
            obj_node = m.get("object")
            obj = A.txt(obj_node) if obj_node is not None else None
            if "methods" in r and name not in r["methods"]:
                return None
            if "_methods_regex" in r and not r["_methods_regex"].search(name):
                return None
            if r.get("no_object") and obj is not None:
                return None
            if "_object_regex" in r and (obj is None or not r["_object_regex"].search(obj)):
                return None
            in_dec = m["node"].parent is not None and m["node"].parent.type == "decorator"
            if bool(r.get("in_decorator", False)) != in_dec:
                return None
            pos, kw = A.args(m.get("args"))
            kw = {**A.object_pairs(pos), **kw}
        elif form == "new":
            name = A.txt(m.get("type"))
            if "_types_regex" in r and not r["_types_regex"].search(name):
                return None
            pos, kw = A.args(m.get("args"))
            kw = {**A.object_pairs(pos), **kw}
        elif form == "pair":
            name = A.txt(m.get("key")).strip("'\"")
            if name not in r.get("keys", []):
                return None
        elif form == "inheritance":
            name = A.txt(m.get("base"))
            if "_bases_regex" in r and not r["_bases_regex"].search(name):
                return None

        ctx = {"A": A, "m": m, "pos": pos, "kw": kw, "name": name, "object": obj}
        value, literal = self.resolve_value(r.get("value", []), ctx)
        if value is None:
            if r.get("requires_value", True):
                return None
            value, literal = "", True

        value_filter = r.get("value_filter")
        if value_filter and not passes_filter(value_filter, value, literal):
            return None
        mark = r.get("mark_if_arg")
        mark_ok = False
        if mark and len(pos) > mark["arg"] and pos[mark["arg"]].type in CALL_TYPES:
            fn = pos[mark["arg"]].child_by_field_name("function")
            mark_ok = fn is not None and A.txt(fn).split(".")[-1] in mark["calls"]

        c = {"protocol": r["protocol"], "direction": r["direction"], "raw_value": value,
             "confidence": r.get("confidence") or confidence_of(r, value, literal)}

        # HTTP method
        if r["protocol"] == "http" or "method" in r:
            spec = r.get("method")
            method = None
            if isinstance(spec, dict):
                for k in spec.get("kwarg", []):
                    if k in kw:
                        method = verbs_from_text(A.txt(kw[k]))
                        break
                if method is None and spec.get("fallback") == "name":
                    method = method_from_name(name or "")
            elif spec == "name":
                method = method_from_name(name or "")
            if method:
                c["method"] = method

        # class / block prefixes and declarative clients (Feign)
        if form == "annotation" and m.get("owner") is not None:
            cont = container_of(m["owner"])
            cont_annotations = annotations_by_owner.get(cont.id, []) if cont is not None else []
            inv = r.get("invert_if_container")
            client = next((a for a in cont_annotations if inv and a["name_txt"] in inv["names"]), None)
            prefix = ""
            for a in cont_annotations:
                if a["name_txt"] in r.get("container_prefix", []):
                    ppos, pkw = A.args(a.get("args"))
                    pv, plit = self.resolve_value([{"kwarg": ["value", "path"]}, {"arg": 0}],
                                                  {"A": A, "pos": ppos, "kw": pkw, "m": a, "name": None, "object": None})
                    if pv:
                        prefix = pv
                        literal = literal and plit
            if client is not None:
                cpos, ckw = A.args(client.get("args"))
                base, blit = self.resolve_value(inv["base"], {"A": A, "pos": cpos, "kw": ckw, "m": client,
                                                              "name": None, "object": None})
                c["direction"] = "outbound"
                c["path"] = join_paths(prefix, value)
                c["raw_value"] = (base or "") + c["path"]
                c["confidence"] = "high" if (blit and base and host_of(base)) else "uncertain"
                c["note"] = f"declarative client @{client['name_txt']}: the base URL comes from the annotation or the config"
            elif c["direction"] == "inbound" and r["protocol"] == "http":
                c["path"] = join_paths(prefix, value)
                c["raw_value"] = c["path"]
                c["confidence"] = "high" if literal else "uncertain"
        if r.get("block_prefix"):
            prefixes = []
            n = m["node"].parent
            while n is not None:
                if n.type == "call":
                    met = n.child_by_field_name("method")
                    if met is not None and A.txt(met) in r["block_prefix"]:
                        ppos, _ = A.args(n.child_by_field_name("arguments"))
                        if ppos:
                            prefixes.insert(0, A.value(ppos[0])[0] or "")
                n = n.parent
            c["path"] = join_paths(*prefixes, value)
            c["raw_value"] = c["path"]
        elif r["protocol"] == "http" and c["direction"] == "inbound" and "path" not in c:
            if value.startswith("^"):
                c["path"] = value
                c["note"] = "route expressed as a regex"
            else:
                c["path"] = join_paths(value)
            c["raw_value"] = c["path"]
        if r["protocol"] == "http" and c["direction"] == "inbound":
            c.setdefault("method", "*")

        # service field for gRPC with a constructor
        if "service" in r:
            s, _ = self.resolve_value([r["service"]], ctx)
            if s:
                c["service"] = s
        if mark_ok:
            c["note"] = mark["note"]
            c["confidence"] = mark.get("confidence", c["confidence"])
            c["is_prefix"] = True
        if r.get("note"):
            c.setdefault("note", r["note"])
        return c

    # -------------------------------------------------------------------
    def resolve_value(self, specs, ctx):
        A, pos, kw = ctx["A"], ctx["pos"], ctx["kw"]
        for e in specs:
            v, lit = None, False
            if "arg" in e:
                if len(pos) > e["arg"]:
                    v, lit = A.value(pos[e["arg"]])
                    if v is not None and "pattern" in e:
                        mm = re.search(e["pattern"], v)
                        v, lit = (mm.group(1), True) if mm else (v, lit)
            elif "kwarg" in e or "key" in e:
                for k in e.get("kwarg", []) + e.get("key", []):
                    if k in kw and kw[k] is not None:
                        v, lit = A.value(kw[k])
                        break
            elif "pair_value" in e:
                v, lit = A.value(ctx["m"].get("value"))
            elif "owner" in e:
                d = ctx["m"].get("owner")
                nm = d.child_by_field_name("name") if d is not None else None
                if nm is not None:
                    v, lit = A.txt(nm), True
            elif "text" in e:
                src = {"method": ctx.get("name"), "object": ctx.get("object"),
                       "type": ctx.get("name"), "base": ctx.get("name")}.get(e["text"])
                if e["text"] == "generic":
                    mm = re.search(r"<\s*([\w.]+)", A.txt(ctx["m"].get("method")))
                    src = mm.group(1) if mm else None
                if src:
                    if "pattern" in e:
                        mm = re.search(e["pattern"], src.split(".")[-1] if e["text"] != "object" else src)
                        v = mm.group(1) if mm else None
                    else:
                        v = src
                    lit = v is not None
            elif "join" in e:
                if len(pos) + len(kw) < e.get("min_args", 0):
                    continue
                parts, lit = [], True
                for sub in e["join"]:
                    sv, sl = self.resolve_value([sub], ctx)
                    if sv is None:
                        parts = None
                        break
                    if sv != "":
                        parts.append(sv)
                    lit = lit and sl
                if parts:
                    v = e.get("sep", "/").join(parts)
            if v is not None:
                return v, lit
        return None, False


def passes_filter(value_filter, value, literal):
    if value_filter == "literal":
        return literal and bool(value)
    if value_filter == "wsdl":
        return "wsdl" in (value or "").lower()
    if value_filter == "path":
        return (not literal) or value.startswith("/")
    if value_filter == "url-or-path":
        if literal:
            return value.startswith("/") or re.match(r"(?i)^[a-z][a-z0-9+.-]*://", value) is not None
        return "/" in value or re.search(r"(?i)(url|uri|endpoint|base|host|api|http)", value) is not None
    return True


def confidence_of(r, value, literal):
    if not literal:
        return "uncertain"
    if r["protocol"] in ("http", "soap", "webhook") and r["direction"] == "outbound":
        return "high" if host_of(value) else "uncertain"
    return "high"


def postprocess(c):
    v = c.get("raw_value") or ""
    if c["protocol"] == "http" and "wsdl" in v.lower():
        c["protocol"] = "soap"
    if c["protocol"] == "http" and c["direction"] == "inbound" and "webhook" in v.lower():
        c["protocol"] = "webhook"
    h = host_of(v)
    has_scheme_or_port = re.match(r"(?i)^[a-z][a-z0-9+.-]*://", v) or re.search(r":\d{2,5}(/|$)", v)
    if h and (c["protocol"] in ("http", "soap", "webhook", "grpc") or has_scheme_or_port):
        c["host"] = h
    if c["protocol"] in ("http", "webhook", "soap") and c["direction"] == "outbound" and v.startswith("/"):
        c.setdefault("path", v.split("?")[0])
    field = {"grpc": "service", "queue-kafka": "topic", "queue-rabbitmq": "queue", "queue": "topic",
             "s3": "bucket"}.get(c["protocol"])
    if c["protocol"].startswith("queue") and ("host" in c or re.search(r"(?i)(host|broker|bootstrap|server)", c.get("config_key") or "")):
        field = "broker"
    if c["protocol"] == "grpc" and "host" in c:
        field = None
    if field and field not in c and (c["confidence"] == "high" or field == "broker"):
        c[field] = v
    return c


# --------------------------------------------------------------------------
# Non-AST passes: contracts (.proto and specs) and non-secret config
# --------------------------------------------------------------------------
def proto_pass(path, repo):
    txt = open(path, encoding="utf-8", errors="replace").read()
    no_comments = re.sub(r"//[^\n]*|/\*.*?\*/", "", txt, flags=re.S)
    package = re.search(r"\bpackage\s+([\w.]+)\s*;", no_comments)
    pkg = package.group(1) + "." if package else ""
    out = []
    for sm in re.finditer(r"\bservice\s+(\w+)\s*\{(.*?)\n\s*\}", no_comments, flags=re.S):
        line = txt[:txt.find("service " + sm.group(1))].count("\n") + 1
        rpcs = re.findall(r"\brpc\s+(\w+)\s*\(", sm.group(2))
        out.append({
            "protocol": "grpc", "direction": "declaration", "service": pkg + sm.group(1),
            "raw_value": pkg + sm.group(1), "rpcs": rpcs, "confidence": "high", "chain_step": 2,
            "rule": "contract.proto",
            "note": "service declared in a versioned .proto: Kiro decides whether the repo implements or consumes it",
            "evidence": {"file": rel(path, repo), "line": line, "snippet": f"service {sm.group(1)} {{ ... }}"},
        })
    return out


def protocol_from_config(key, value):
    k, v = key.lower(), value.lower()
    if v.startswith(("amqp://", "amqps://")) or re.search(r"rabbit|amqp", k):
        return "queue-rabbitmq"
    if v.startswith("kafka://") or re.search(r"kafka|bootstrap|broker", k):
        return "queue-kafka"
    if v.startswith(("grpc://", "grpcs://")) or "grpc" in k:
        return "grpc"
    if "wsdl" in v or "soap" in k or "wsdl" in k:
        return "soap"
    if "webhook" in k:
        return "webhook"
    if re.search(r"bucket|s3", k) and not v.startswith("http"):
        return "s3"
    return "http"


DB_KEY = re.compile(r"(?i)(^|[._-])(database|datasource|db|postgres(ql)?|mysql|mariadb|mongo(db)?|redis|sql|jdbc|oracle)([._-]|$)")
SECRET_DOC = re.compile(r"(?im)^\s*kind:\s*(Secret|SealedSecret|ExternalSecret)\s*$")


def config_pass(path, repo):
    rel_path = rel(path, repo)
    out = []
    stack = []  # (indent, key) for YAML key paths
    is_yaml = path.endswith((".yml", ".yaml"))
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    # YAML documents of kind Secret are not read (per document, separated by ---)
    skip = set()
    if is_yaml:
        start = 0
        for j in range(len(lines) + 1):
            if j == len(lines) or lines[j].strip() == "---":
                if SECRET_DOC.search("\n".join(lines[start:j])):
                    skip.update(range(start, j))
                start = j + 1
    for i, line in enumerate(lines, start=1):
        if i - 1 in skip:
            continue
        raw = line.rstrip("\n")
        if not raw.strip() or raw.strip().startswith(("#", "//")):
            continue
        m = re.match(r"^(\s*)[\"']?([\w.\-\[\]]+)[\"']?\s*[:=]\s*(.*)$", raw)
        key, value_txt = "", ""
        if m:
            indent, key, value_txt = len(m.group(1)), m.group(2), m.group(3).strip()
            if is_yaml:
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                key_path = ".".join([k for _, k in stack] + [key])
                if value_txt == "" or value_txt in ("|", ">"):
                    stack.append((indent, key))
                    continue
                key = key_path
        if SECRET_KEY.search(key) or DB_KEY.search(key):
            continue
        values = re.findall(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s\"'<>,}]+", raw)
        if not values and value_txt:
            v = value_txt.strip().strip("'\",").strip()
            if re.search(r"(?i)(host|address|url|uri|endpoint|server|broker|bootstrap|brokers|queue|topic|exchange|bucket)", key) \
                    and re.match(r"^[\w.-]+(:\d{2,5})?(,[\w.-]+(:\d{2,5})?)*$", v) and not re.match(r"^\d+$", v) \
                    and v.lower() not in ("true", "false", "null", "none", "localhost"):
                values = [v]
        for v in values:
            if DB_SCHEMES.match(v):
                continue
            v_clean = USERINFO.sub(r"\1***@", v).rstrip(".;")
            with_scheme = "://" in v_clean
            c = {"protocol": protocol_from_config(key, v_clean), "direction": "outbound",
                 "raw_value": v_clean, "config_key": key or None,
                 "confidence": "high" if with_scheme else "uncertain", "chain_step": 3, "rule": "config.non-secret",
                 "evidence": {"file": rel_path, "line": i, "snippet": mask(raw.strip())[:160]}}
            if re.search(r"(?i)(queue|topic|exchange)", key) and "://" not in v_clean and ":" not in v_clean:
                c["protocol"] = "queue-kafka" if "topic" in key.lower() else "queue-rabbitmq"
                c["confidence"] = "high"
            if not with_scheme and c["confidence"] == "uncertain":
                c["note"] = "protocol inferred from the config key name"
            out.append(postprocess(c))
    return out


# --------------------------------------------------------------------------
# Repo walk
# --------------------------------------------------------------------------
def walk_repo(repo, ign, max_bytes, warnings):
    for root, dirs, files in os.walk(repo):
        r_rel = rel(root, repo)
        r_rel = "" if r_rel == "." else r_rel
        dirs[:] = sorted(d for d in dirs
                         if d not in EXCLUDED_DIRS
                         and not (r_rel == "" and d == ".kiro")
                         and not ign.ignores((r_rel + "/" + d).lstrip("/"), True))
        for a in sorted(files):
            rel_path = (r_rel + "/" + a).lstrip("/")
            path = os.path.join(root, a)
            if matches(rel_path, SECRET_FILES) and not matches(rel_path, ALLOWED_ENV):
                continue
            if matches(rel_path, TEST_FILES) or ign.ignores(rel_path, False):
                continue
            try:
                if os.path.getsize(path) > max_bytes:
                    warnings.append(f"skipped due to size (> {max_bytes // 1024} KB): {rel_path}")
                    continue
            except OSError:
                continue
            yield path, rel_path


def is_config(rel_path):
    if matches(rel_path, CONFIG_PATTERNS):
        return True
    segs = rel_path.split("/")
    return any(s in CONFIG_DIRS for s in segs[:-1]) and rel_path.endswith(CONFIG_EXT_IN_DIRS) \
        and not matches(rel_path, ["package*.json", "tsconfig*.json", "angular.json", "*.lock*", "composer.json"])


def cache_key(repo, stacks, role, repo_id, max_kb):
    try:
        head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        status = subprocess.run(["git", "-C", repo, "status", "--porcelain"], capture_output=True, text=True, timeout=30)
        if head.returncode != 0:
            return None
    except (OSError, subprocess.SubprocessError):
        return None
    h = hashlib.sha256()
    for part in (PRESCAN_VERSION, head.stdout, status.stdout, ",".join(stacks), role or "",
                 repo_id or "", str(max_kb)):
        h.update(part.encode() + b"\0")
    # manifest.json (languages, stacks, rules_version) also invalidates the cache
    h.update(open(os.path.join(HERE, "manifest.json"), "rb").read())
    for folder in ("rules", "queries"):
        for f in sorted(os.listdir(os.path.join(HERE, folder))):
            h.update(open(os.path.join(HERE, folder, f), "rb").read())
    return h.hexdigest()[:24]


def role_warnings(role, cands):
    code = [c for c in cands if c["chain_step"] == 1]
    http_in = [c for c in code if c["protocol"] in ("http", "webhook") and c["direction"] == "inbound"]
    queue_in = [c for c in code if c["protocol"].startswith("queue") and c["direction"] == "inbound"]
    out = []
    if role == "frontend" and http_in:
        out.append(f"frontend role with {len(http_in)} inbound HTTP routes: check whether the right role is mvc-monolith")
    if role == "backend" and not [c for c in code if c["direction"] == "inbound"]:
        out.append("backend role with no inbound connection detected: check the role or the declared stack")
    if role == "worker" and http_in:
        out.append(f"worker role with {len(http_in)} inbound HTTP routes (may be a health check): check the role")
    if role == "worker" and not queue_in:
        out.append("worker role with no queue consumers detected: check the role or the declared stack")
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def load_manifest():
    return json.load(open(os.path.join(HERE, "manifest.json"), encoding="utf-8"))


def verify():
    M = load_manifest()
    ok = True
    try:
        import tree_sitter as ts
        from importlib.metadata import version
        print(f"python {sys.version.split()[0]}  tree-sitter {version('tree-sitter')}  prescan {PRESCAN_VERSION}")
    except Exception as e:  # noqa: BLE001
        print(f"MISSING tree-sitter: {e}")
        return 1
    for name, conf in M["languages"].items():
        try:
            Language(name, conf, ts)
            print(f"  {name}: ok")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  {name}: ERROR {type(e).__name__}: {e}")
    return 0 if ok else 1


class ArgumentParser(argparse.ArgumentParser):
    """argparse exits with 2 on bad arguments, which collides with the
    documented meaning of 2 (no stack with rules). Invocation errors exit 1."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        sys.exit(1)


def main():
    ap = ArgumentParser(description="Deterministic prescan of kiro-allspark")
    ap.add_argument("--repo")
    ap.add_argument("--id")
    ap.add_argument("--stack", help="one or more, comma-separated (from tech.md)")
    ap.add_argument("--role", choices=["frontend", "backend", "mvc-monolith", "worker"])
    ap.add_argument("--output")
    ap.add_argument("--cache", action="store_true")
    ap.add_argument("--max-kb", type=int, default=1024)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--stacks", action="store_true")
    a = ap.parse_args()

    if sys.version_info < (3, 10):
        print("prescan requires Python 3.10 or later", file=sys.stderr)
        return 1
    M = load_manifest()
    if a.verify:
        return verify()
    if a.stacks:
        for s, ls in sorted(M["stacks"].items()):
            print(f"{s}: {', '.join(ls)}")
        return 0
    if not (a.repo and a.stack and a.output):
        ap.error("--repo, --stack and --output are required")
    repo = os.path.abspath(a.repo)
    if not os.path.isdir(repo):
        print(f"repo not found: {repo}", file=sys.stderr)
        return 1

    stacks = [s.strip().lower() for s in a.stack.split(",") if s.strip()]
    known = [s for s in stacks if s in M["stacks"]]
    without_pattern = [s for s in stacks if s not in M["stacks"]]

    key = cache_key(repo, stacks, a.role, a.id, a.max_kb) if a.cache else None
    if key and os.path.isfile(a.output):
        try:
            previous = json.load(open(a.output, encoding="utf-8"))
            if previous.get("cache_key") == key:
                print(f"cache is current: {a.output}")
                return 0 if known else 2
        except (OSError, ValueError):
            pass

    try:
        import tree_sitter as ts
    except ImportError as e:
        print(f"tree-sitter is missing ({e}); run step 2.B.0", file=sys.stderr)
        return 1

    t0 = time.time()
    warnings = []
    lang_names = []
    for s in known:
        for l in M["stacks"][s]:
            if l not in lang_names:
                lang_names.append(l)
    languages, by_ext = {}, {}
    for l in lang_names:
        try:
            languages[l] = Language(l, M["languages"][l], ts)
        except Exception as e:  # noqa: BLE001
            print(f"could not load the {l} grammar: {e}", file=sys.stderr)
            return 1
        for ext in M["languages"][l]["extensions"]:
            by_ext[ext] = languages[l]

    ign = IgnoreRules(repo, warnings)
    scanner = Scanner(repo, languages, warnings)
    extra, contracts = [], []
    scanned = 0
    undeclared = {}  # language without grammar -> number of files found
    for path, rel_path in walk_repo(repo, ign, a.max_kb * 1024, warnings):
        ext = os.path.splitext(path)[1].lower()
        if ext in UNSUPPORTED_EXT:
            lang = UNSUPPORTED_EXT[ext]
            undeclared[lang] = undeclared.get(lang, 0) + 1
        if path.endswith(".proto"):
            extra.extend(proto_pass(path, repo))
            contracts.append(rel_path)
            continue
        if matches(rel_path, CONTRACT_PATTERNS):
            contracts.append(rel_path)
        if is_config(rel_path):
            extra.extend(config_pass(path, repo))
            if ext not in by_ext:
                continue
        if ext in by_ext:
            try:
                scanner.scan_file(path, by_ext[ext])
                scanned += 1
            except Exception as e:  # noqa: BLE001
                warnings.append(f"could not parse {rel_path}: {type(e).__name__}: {e}")

    for lang, n in sorted(undeclared.items()):
        if lang not in without_pattern:
            without_pattern.append(lang)
            warnings.append(f"{n} {lang} source file(s) found and not scanned (no grammar): read by hand")

    if scanner.django_warning:
        warnings.append("Django: include() prefixes are not composed; routes stay relative to their urls.py")

    candidates = sorted(scanner.candidates + extra, key=lambda c: (c["evidence"]["file"], c["evidence"]["line"]))
    summary = {"files_scanned": scanned, "candidates": len(candidates), "by_protocol": {}, "by_confidence": {}}
    for c in candidates:
        k = f"{c['protocol']}:{c['direction']}"
        summary["by_protocol"][k] = summary["by_protocol"].get(k, 0) + 1
        summary["by_confidence"][c["confidence"]] = summary["by_confidence"].get(c["confidence"], 0) + 1
    summary["duration_ms"] = int((time.time() - t0) * 1000)

    output = {
        "repo": a.id or os.path.basename(repo),
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool": {"prescan": PRESCAN_VERSION, "rules": M.get("rules_version")},
        "declared_stack": stacks,
        "stacks_without_pattern": without_pattern,
        "role": a.role,
        "cache_key": key,
        "summary": summary,
        "contracts": sorted(set(contracts)),
        "candidates": candidates,
        "role_warnings": role_warnings(a.role, candidates),
        "warnings": warnings,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=1)
    print(f"{output['repo']}: {len(candidates)} candidates in {scanned} files -> {a.output}")
    if without_pattern:
        print(f"stacks without pattern: {', '.join(without_pattern)}", file=sys.stderr)
    return 0 if known else 2


if __name__ == "__main__":
    sys.exit(main())
