# Deterministic prescan (steps 2.B.0 and 2.B.1)

## Why it exists

The most expensive part of Phase 2 was mechanical: finding in the code every
`@Post('confirm')`, every `restTemplate.postForEntity(...)`, every
`producer.send({ topic })`. That requires no judgment, only recognizing code
structures. Since v1.10.0 that search is done by **a fixed Python script
that Kiro runs** (`assets/prescan/prescan.py`), with real AST parsing
(tree-sitter), not text search. Kiro receives a list of **candidates**
already located (file, line, value) and spends its reasoning only on what
does need it: resolving domains, classifying axes, discarding false
positives and validating in reverse (step 2.B.2 onwards).

The mapping is still **complete and without sampling**: the script walks all
the files of the repo. What changes is who does the mechanical search.

## Where it lives

```
skills/find-connections/assets/prescan/
├── prescan.py          ← single engine; Kiro runs it from the command line
├── requirements.txt    ← pinned versions (tree-sitter + 6 grammars)
├── manifest.json       ← tech.md stack → languages → extensions
├── queries/            ← one .scm query per grammar (generic forms)
│   ├── typescript.scm  (also TSX and JavaScript)
│   ├── python.scm
│   ├── java.scm
│   ├── csharp.scm
│   └── ruby.scm
└── rules/              ← rules per framework, as data
    ├── typescript.json (NestJS, Express, Angular/React, axios, fetch, kafkajs, amqplib, gRPC, S3)
    ├── python.json     (Django, Flask, FastAPI, requests/httpx, zeep, pika, kafka, Celery, boto3)
    ├── java.json       (Spring MVC, Feign, RestTemplate, WebClient, Spring-WS, Kafka, Rabbit, gRPC, S3)
    ├── csharp.json     (ASP.NET, minimal APIs, HttpClient, WCF, gRPC, Confluent, RabbitMQ, MassTransit, S3)
    └── ruby.json       (Rails routes, Faraday, HTTParty, Net::HTTP, Savon, Bunny, Sidekiq)
```

**Why `.scm` per grammar and rules in JSON.** A tree-sitter query only
compiles against one grammar, so there cannot be one `.scm` per framework
that works for Java and TypeScript at the same time. Each `.scm` captures
generic forms with the same names in all languages (`annotation`, `call`,
`new`, `pair`, `inheritance`), and each framework's rules say which names
to look for in those forms. Adding a new framework means editing a JSON,
without touching the engine.

## Step 2.B.0 — Prepare the environment (once per workspace)

Kiro runs it before the first prescan of the workspace, and again only if
`--verify` fails or `requirements.txt` changes:

```bash
# 1. Python 3.10 or higher
python3 --version            # Windows: py -3 --version

# 2. Isolated environment inside the workspace (never in the system Python)
python3 -m venv .kiro/allspark/.venv-prescan

# 3. Pinned dependencies
.kiro/allspark/.venv-prescan/bin/pip install -r <skill>/assets/prescan/requirements.txt
#    Windows: .kiro\allspark\.venv-prescan\Scripts\pip install -r ...

# 4. Verification: loads the 7 grammars and compiles the queries
.kiro/allspark/.venv-prescan/bin/python <skill>/assets/prescan/prescan.py --verify
```

- **Isolated**: everything stays in the workspace's `.kiro/allspark/`
  (~30 MB), which `generate-steering` adds to `.kiroignore`. It does not
  touch the machine's Python.
- **Only needs PyPI** (or the company's internal mirror, via
  `PIP_INDEX_URL`/`pip.conf`). The grammars come precompiled inside each
  package: they download nothing at runtime.
- **If any step fails** (no Python 3.10+, no access to PyPI, `--verify`
  errors out): the prescan is **unavailable for this run** and Kiro does
  the full manual reading of all repos, as before v1.10.0. It never blocks
  Phase 2. The user is told which step failed and the exact message, so
  they can decide whether to install something.

## Step 2.B.1 — Run the prescan (per repo)

After 2.A (role already defined), one command per repo:

```bash
.kiro/allspark/.venv-prescan/bin/python <skill>/assets/prescan/prescan.py \
  --repo <repo-path> \
  --id org/repo-name \
  --stack <stack from tech.md, several separated by commas> \
  --role <role from 2.A> \
  --output .kiro/allspark/prescan/<repo-slug>.json \
  --cache
```

| Argument | Where it comes from |
|---|---|
| `--stack` | The repo's `tech.md` (e.g. `nestjs`, `spring`, `django,celery`). `prescan.py --stacks` lists the supported ones. |
| `--role` | Step 2.A. It does not narrow the search (the mapping is complete): it is used to warn about inconsistencies, e.g. a `frontend` with inbound routes. |
| `--id` | Real Git name (the same deterministic ID as in the vault). |
| `--cache` | Reuses the JSON if the repo's commit and state did not change (see "Cache"). |

**Exit codes:**

- `0` — complete scan.
- `2` — no declared stack has rules (e.g. Kotlin, Go, PHP): the JSON is
  written anyway with contracts and config, and that repo goes to manual
  reading in 2.B.2.
- `1` — real error (dependencies, nonexistent repo): that repo goes to
  manual reading and the error is reported.

A repo with mixed stacks (e.g. `spring` + a Kotlin module) exits with `0`
and lists the unsupported ones in `stacks_without_pattern`: Kiro reads only
that part by hand.

## What it walks and what it does not

It walks the whole repo, in three passes:

1. **Code** (step 1 of the resolution chain) — AST of each file in the
   stack's language, applying the rules.
2. **Contracts** (step 2) — `.proto` (package, services and rpcs), and a
   list of the WSDL, OpenAPI/Swagger and AsyncAPI found, in `contracts`.
3. **Non-secret config** (step 3) — `application*.yml/.properties`,
   `appsettings*.json`, `docker-compose*`, `.env.example/.sample/.template`,
   `environment*.ts` and YAML/JSON inside folders `k8s/`, `deploy/`,
   `helm/`, `config/`, etc.

It never opens or reads:

- `.env`, `.env.local`, `.env.production` and similar, `*.pem`, `*.key`,
  `*.jks`, `credentials*`, `secrets.*`.
- YAML documents `kind: Secret` / `SealedSecret` / `ExternalSecret`.
- Config keys with a secret name (`password`, `token`, `api_key`,
  `secret`...) or database name (`datasource`, `db`, `postgres`,
  `redis`...: outside the cube model).
- Tests and test doubles (`*.spec.*`, `*.test.*`, `test_*.py`,
  `*Test.java`, folders `test/`, `tests/`, `__mocks__/`, `fixtures/`...),
  dependencies and build output (`node_modules/`, `target/`, `dist/`,
  `bin/`...), and everything excluded by the repo's `.kiroignore` and
  `.gitignore` (`!pattern` negations are not supported and how many there
  are is reported).
- Files larger than 1 MB (minified, generated): they are listed in
  `warnings`.

Any credential embedded in a URL (`user:password@host`) comes out masked as
`***@host`, also in the evidence snippets.

## Output — `.kiro/allspark/prescan/<repo-slug>.json`

It is a working artifact, not a steering doc: it is not promoted to the
vault or shared between teams (it stays under `.kiro/allspark/`, excluded
by `.kiroignore`).

```json
{
  "repo": "org/payments-api",
  "generated": "2026-09-26T10:00:00Z",
  "tool": { "prescan": "1.0.0", "rules": "1.0.0" },
  "declared_stack": ["nestjs"],
  "stacks_without_pattern": [],
  "role": "backend",
  "cache_key": "3f9c…",
  "summary": { "files_scanned": 42, "candidates": 17,
               "by_protocol": { "http:inbound": 3, "http:outbound": 4, "…": 0 },
               "by_confidence": { "high": 14, "uncertain": 3 }, "duration_ms": 72 },
  "contracts": ["proto/scoring.proto"],
  "candidates": [
    { "protocol": "http", "direction": "inbound", "method": "POST",
      "path": "/api/payments/confirm", "raw_value": "/api/payments/confirm",
      "confidence": "high", "chain_step": 1, "rule": "ts.nest.route",
      "evidence": { "file": "src/payments/payments.controller.ts", "line": 6,
                    "snippet": "@Post('confirm')" } },
    { "protocol": "http", "direction": "outbound", "method": "GET",
      "raw_value": "`${this.cfg.scoringUrl}/score`", "confidence": "uncertain",
      "chain_step": 1, "rule": "ts.http.client",
      "evidence": { "file": "src/payments/payments.controller.ts", "line": 9,
                    "snippet": "return this.httpService.get(`${this.cfg.scoringUrl}/score`);" } }
  ],
  "role_warnings": [],
  "warnings": []
}
```

Fields of each candidate:

| Field | Always | Meaning |
|---|---|---|
| `protocol` | Yes | `http`, `soap`, `grpc`, `queue-kafka`, `queue-rabbitmq`, `queue` (broker not determinable from the code: NestJS `@EventPattern`, Celery, Sidekiq, MassTransit), `webhook`, `s3`. |
| `direction` | Yes | `outbound`, `inbound`, or `declaration` (service from a `.proto`: Kiro decides whether the repo implements or consumes it by crossing it with the gRPC candidates). |
| `raw_value` | Yes | What was found, unresolved: URL, path, `host:port`, topic, queue, `exchange/routing-key`, bucket, service. If it depends on variables, the code text is delivered as is. |
| `confidence` | Yes | `high`: literal without variables. `uncertain`: depends on variables, config or concatenation, or the object was not recognized as a network client. |
| `chain_step` | Yes | 1 code, 2 contract, 3 config — the `resolution-chain.md` step the evidence corresponds to. |
| `rule` | Yes | ID of the rule that detected it (traceability; see `rules/*.json`). |
| `evidence` | Yes | File, line and masked snippet: Kiro goes straight there if it needs context. |
| `method`, `path` | HTTP | Method (`*` if it cannot be known) and path with the class prefixes already composed (`@Controller`, `@RequestMapping`, `[Route]`, Rails `namespace`). |
| `host` | If it could be extracted | Host (and port) from the URL or the value. |
| `service`, `topic`, `queue`, `broker`, `bucket` | Depending on protocol | Semantic field already separated. |
| `config_key` | Config | Path of the key (e.g. `spring.kafka.bootstrap-servers`). |
| `is_prefix` | Sometimes | The entry is not an endpoint but a prefix (e.g. Django's `include()`). |
| `note` | Sometimes | Clarification from the rule (e.g. "declarative @FeignClient client: the base URL comes from the config"). |

## Step 2.B.2 — What Kiro does with the candidates

1. **With the JSON only**, without opening code: apply `resolution-chain.md`
   and `axis-classification.md` to each `high` candidate (literal host,
   topic, bucket, `.proto` service), and cross candidates between workspace
   repos (same topic, same gRPC service, relative outbound path vs the
   other repo's inbound path) for step 4 of the chain.
2. **Open the code only at the evidence** of the `uncertain` candidates,
   reading the minimum around `file:line` to resolve the variable
   (`this.cfg.scoringUrl` → config → host). Never reread the whole repo for
   an uncertain candidate.
3. **Full manual reading** only for repos with exit code 2 or 1, or for the
   part of a repo in `stacks_without_pattern`.
4. **Group**: several candidates can be the same MOC connection
   (5 calls to `payments-api` = 1 connection per domain). The number of
   candidates classified per axis **is** the endpoint count
   (`count_X/Y/Z`, see `position-formula.md`).
5. **Discard with a reason**: a candidate that is not a real connection
   (string that looks like a URL, dead code, HTTP client that is actually a
   cache) is discarded with a one-line reason in the report. Never
   silently.
6. **Review `role_warnings`** before continuing: a role wrongly assigned in
   2.A is corrected there, not after classifying.

**Mandatory reconciliation** (Phase 2 verification): for each repo,
`candidates = grouped into connections + discarded with a reason`. A
candidate that does not appear on either side is a lost connection and the
run is not considered finished.

## Benefit also outside 2.B

- **2.C Reverse validation**: it becomes a cross between JSONs — A's
  outbound routes against B's inbound routes, produced topics against
  consumed ones, consumed gRPC service against implemented one. No second
  code reading.

## Cache

With `--cache`, the key combines: `HEAD` commit, `git status` (uncommitted
changes), stack, role, script version and the content of rules and
queries. If it matches the one in the existing JSON, it is not re-scanned. A
repo without git is always scanned. When in doubt, delete the JSON and
re-scan: the cache only saves time, it never decides anything.

## Adding a new framework or stack

1. If the language already exists: add rules in `rules/<language>.json`
   using the available forms (`annotation`, `call`, `new`, `pair`,
   `inheritance`) and the stack in `manifest.json`.
2. If the language is new: add the grammar to `requirements.txt`
   (pinned version, package with a precompiled wheel), the language in
   `manifest.json` and its `queries/<language>.scm` with the same capture
   names.
3. Document the pattern in `framework-patterns.md` (the human-readable
   description still lives there).
4. Test against a sample repo and bump `rules_version` in `manifest.json`
   (invalidates the caches).

As long as a stack is not in `manifest.json`, it shows up in
`stacks_without_pattern` and is read by hand: missing support is reported,
not guessed.
