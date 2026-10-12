---
name: find-connections
description: "Documents how the client experiences the service, in natural language, starting from the entry points (frontends and monoliths) and following what each one reaches. Defines the role of each repo, scans its connections and the databases it uses with a deterministic Python prescan, computes what each entry point reaches and what documenting it would cost (reach.py), validates connections from both ends and writes the Level 1 MOC for what was reached. On demand, after a confirmed line count, promotes to Level 2, the module, in a single consolidated step (its endpoints with their hops and data access, the databases and providers it touches and the shared functionalities it reuses). Positions come from a deterministic script (layout.py). Compiles the export (allspark.md) and offers (yes/no) the 3D view of generate-visual. It recommends against mapping the whole workspace. Requires generate-steering first."
---

# find-connections

Documents the connections of each repo in a **two-level MOC** — see
`references/moc-schema.md` for the full format:

- **Level 1 (mandatory):** role of the repo, all its connections at the
  domain, service, topic or bucket level, and **the databases it uses**, for
  the whole workspace (`.kiro/steering/moc.md`).
- **Level 2 (optional, per module, consolidated):** a module and **everything
  under it in a single step and a single file** — the experience of the
  client, each of its endpoints with its hops and its data access, the
  databases and external providers it touches, and the shared
  functionalities it reuses — inside `.kiro/steering/product/features/`,
  mirrored from `structure.md`. Only after a line-count gate with explicit
  confirmation. There is no separate Level 3 or Level 4 to promote afterwards.

From these MOCs the export `allspark/export/allspark.md` is compiled, which
represents the application universe as an XYZ cube. The cube is read at
three views over the same points:

- **Global (Level 1):** repos (colored by type), systems without a repo
  (grouped by provider, colored by axis) and database nuclei near the origin,
  with the connections drawn as bundles per pair of zones, the number of
  endpoints of each color on its bundle and one large vector with the total;
- **Modules (Level 2):** one tree per promoted module, from the client to
  the externals and the database;
- **Detail (endpoints of a module):** one strand per endpoint of the open
  module.

Modules and endpoints are not points: they are drawn over the points that
already exist. The positions of all points are computed by a script
(`assets/layout/layout.py`), never by hand.

This skill is manual; it does not run as an automatic part of
`generate-steering`.

## The principle — experience first, one entry point at a time

The purpose is to document, in natural language and for both Kiro and
people, **how the client consumes the service**; the developers already know
how it works inside. So the work starts from an **entry point** — a
`frontend` or an `mvc-monolith`, where the client interacts — and goes
inward, instead of mapping the whole workspace:

- Kiro lists the entry points, **computes what each one reaches and what it
  would cost** (`assets/reach/reach.py`, no tokens spent) and asks which one to
  document. It does not map the whole workspace unless the user insists, and
  it **recommends against it** with the numbers first (the soft gate).
- Only the repos an entry point reaches are classified and documented. The
  rest stay in the cube as **not documented yet**.
- Level 2 is written from the experience of the client (what they
  see and do, then what happens behind), in the language of the
  conversation.
- The documentation and the 3D view are two readings of the same data: same
  summaries, same hops, same coverage.

Details in `references/entry-points.md` and `references/experience-docs.md`.

## Phase 1 — Preliminary scan (lightweight)

**Repo discovery — do not rely on a single top-level directory listing.**
A shallow `list directory` misses repos nested in subfolders or added after
the workspace was configured. Use as the source of truth, in this order:

1. The Kiro workspace multi-root configuration (if it exists), which already
   explicitly declares each root/repo.
2. If there is no explicit multi-root configuration, recursively search for
   `.git` folders across the entire workspace tree — each one marks the root
   of a real repo, regardless of the nesting depth.
3. Cross-check against the repos that already have `.kiro/steering/`
   generated (by `generate-steering`) — if a repo has steering docs but did
   not show up in the previous discovery, it is a sign that discovery failed
   and needs to be reviewed.

Go through the repos found this way and determine, for each one, whether it
already has a valid `.kiro/steering/moc.md`.

- If it already has a valid MOC → it is skipped, regardless of whether the
  repo changed since the last `generate-steering` run. The only criterion is
  "does a valid MOC exist?", not the state of tech/structure.
- If it does not have a valid MOC → it goes to the steering docs gate below
  before it can enter the Phase 2 pending list.

**MANDATORY GATE — basic steering docs before anything else.** No repo
enters the Phase 2 pending list without already having the two basic
steering docs generated by `generate-steering`: `.kiro/steering/tech.md` and
`.kiro/steering/structure.md`. This is not a suggestion or an optional
check: `find-connections` depends on both to be efficient —

- `tech.md` gives the stack (which prescan rules and which pattern from
  `framework-patterns.md` to use) and the first signal of the repo's role
  (step 2.A).
- `structure.md` gives the repo's folder/path organization, needed to assign
  the role (front, back, MVC monolith, worker) and to avoid walking the code
  blindly looking for connections.

Running without these two is not an acceptable partial result — it makes
Phase 2 more expensive (more tokens scanning without guidance) and produces
poorly detected connections or repos with the wrong role assigned (see
`references/repo-roles.md`).

- Repo missing either of the two → **does not enter Phase 2 pending**. It
  is reported separately, in its own list: "needs `generate-steering`
  first", stating which one is missing. The `generate-steering` command for
  that repo is suggested; the stack/structure is never assumed, nor guessed
  in order to carry on anyway.
- Repo with both present but outdated (older than the repo's last commit)
  → reported as a warning, but does not block — old steering docs are still
  a better signal than none.
- This gate is checked on every Phase 1 run, not only the first time — a
  repo added later to the workspace goes through the same check.

When finished, it reports two separate lists: repos ready and pending for
Phase 2, and repos that need `generate-steering` first. **It suggests the command** to run
`generate-steering` on those that need it and, separately, the command to
run Phase 2 on those that are already ready (or on the subset the user
indicates). It does not run anything automatically — the user decides,
because both `generate-steering` and Phase 2 are expensive in credits.

## Phase 2 — Level 1 from the entry points: define everything first, connect later

**Precondition, not optional:** it only processes repos that have already
passed the Phase 1 steering docs gate (`tech.md` and `structure.md`). If the
user asks to run Phase 2 on a repo that does not have them, scanning does
not proceed anyway — they are told which one is missing and offered to run
`generate-steering` first.

**The mapping is complete for what the chosen entry point reaches**: every
connection of those repos must be recorded in the MOC, or it does not exist
for the cube. What it does not reach is not mapped, and it
is reported as **not documented yet** rather than guessed. Mapping the whole
workspace is possible but **recommended against**, and it goes through the
soft gate of `references/entry-points.md` (cost and alternative shown first;
it never blocks).

The order of the steps is strict: **first absolutely everything is defined
(role of each repo, what is internal and what is external, what is front
and what is back) and only then are the connections generated.** The role
is not discovered on the fly while scanning.

### 2.A — Define the role of each repo (before scanning connections)

For each pending repo, with `tech.md` and `structure.md` as the source,
assign one of the roles from `references/repo-roles.md`:

- `frontend`, `backend`, `mvc-monolith` (all in one, neither pure front nor
  pure back), `worker` (processes in the background, does not serve
  requests).
- `external` is not assigned to repos: it is the role of the virtual points
  that appear in 2.B.

With the roles defined, the internal/external boundary is defined too:
**internal = every workspace repo with one of the four roles above;
external = everything that is not mapped to one of them.** Show the roles
table to the user before continuing (repo → role → evidence) — it is cheap
to review and avoids dragging a wrongly assigned role into all the
connections.

### 2.B — Exhaustive connection scan (prescan + classification)

**The scan is complete, not sampling.** It captures **absolutely every**
connection of the repo — front, back, worker and towards externals — across
all protocols:

- **HTTP/REST and SOAP** — domain only, never a specific endpoint, in the MOC.
- **gRPC** — `.proto` service + channel host. Same directional treatment
  as HTTP.
- **Message queues (RabbitMQ, Kafka)** — broker + exchange/queue/topic.
  Direction producer → consumer.
- **Webhooks** — same directional treatment as HTTP/SOAP.
- **S3 storage** — classified by bucket owner, same contractual criterion
  as a domain.

Both **outbound and inbound** connections of each repo are collected — the
inbound ones are what later make reverse validation possible.

The scan is split into a **mechanical and cheap** part run by
a script, and a **judgment** part done by Kiro. Full detail in
`references/prescan.md`.

#### 2.B.0 — Prepare the prescan environment (once per workspace)

Create `.kiro/allspark/.venv-prescan` (Python 3.10+, isolated environment),
install `assets/prescan/requirements.txt` and run `prescan.py --verify`. If
any step fails, the prescan is unavailable for this run: the exact error is
reported and all repos go through full manual reading.
It never blocks Phase 2.

#### 2.B.1 — Deterministic prescan (script, per repo)

Kiro runs `assets/prescan/prescan.py` on **every repo of the workspace** —
it is the cheap part, about 50,000 lines per second — with its stack
(`tech.md`), its role (2.A) and `--cache`, and gets
`.kiro/allspark/prescan/<repo-slug>.json`: the list of connection
**candidates** with protocol, direction, value, confidence, chain step and
`file:line` evidence. The script parses the AST of all the repo's code with
tree-sitter (it is not a text search), reads contracts (`.proto`, WSDL,
OpenAPI) and non-secret config, and never opens real `.env` files, k8s
Secrets or credential keys. This pass consumes none of Kiro's reasoning.

Pass as `--stack` only names listed by `prescan.py --stacks` (languages,
frameworks and single-language libraries like `celery`); protocols such as
`kafka` or `grpc` are not stacks.

Exit code `2` (stack without rules, e.g. Kotlin or Go) or `1` (error,
including invalid arguments): that repo goes to full manual reading in
2.B.2, reported separately. With exit `0`, any language listed in
`stacks_without_pattern` (declared, or detected by its source files, e.g.
Kotlin in a `spring` repo) is still read by hand.

#### 2.B.1b — Reach of the entry points, and the choice (script + user)

Kiro runs `assets/reach/reach.py` over `.kiro/allspark/prescan/` and gets
`.kiro/allspark/reach.json`: for each entry point, the repos it reaches
(which repo serves each of its calls: by route, topic, gRPC service or
domain), how many lines and candidates that means, and an estimate of the
tokens to read and the time to write, **with what is measured and what is an
assumption labeled**. It reads no source code and uses no tokens.

Kiro then shows the entry points with their reach and estimate and **asks
which one to document** (see the soft gate in `references/entry-points.md`
for the case where the user asks for the whole workspace). Repos that no
entry point reaches are listed apart: they are not documented unless the
user asks.

#### 2.B.2 — Candidate classification (Kiro)

**Scope:** only the chosen entry point and, wave by wave, the repos it
reaches — never the whole workspace unless the user confirmed the soft gate.
Rules of the wave walk in `references/entry-points.md`.

1. With the JSON only, apply the resolution chain (see
   `references/resolution-chain.md`) and the axis classification (see
   `references/axis-classification.md`) to the `high` confidence
   candidates, and cross candidates between workspace repos (step 4 of the
   chain: same topic, gRPC service, path).
2. For the `uncertain` ones, open the code **only at their evidence** and
   read the minimum needed to resolve the variable or confirm it is a
   network call.
3. Full manual reading (with `references/framework-patterns.md`) only for
   repos without prescan (exit 1 or 2, or failed 2.B.0) and for the part of
   a repo listed in `stacks_without_pattern`.
4. Group candidates into MOC connections (by domain, topic, service or
   bucket) and discard false positives **with a reason**.
5. Review the JSON's `role_warnings` before continuing: if the 2.A role was
   wrong, it is corrected now.

Each MOC connection records `detection_source: prescan | manual` (see
`references/moc-schema.md`). When reporting, include how many connections
were detected per protocol (HTTP, SOAP, gRPC, queue, webhook, S3) — so the
user notices if some type stayed suspiciously at zero for a repo known to
use it.

### 2.C — Reverse connection validation (internal repos)

Every connection whose source **and** target are workspace repos **reached
from the chosen entry point** is also validated from the target: if A calls B, B is searched for the route, gRPC
service or consumer that receives that call. See
`references/reverse-validation.md`. Result per connection:
`reverse_validation: validated` or `no-target-evidence` (reported
separately, does not change the axis or block). It is a cross-check of what
was already collected in 2.B, not a second pass over the code: with
prescan, the JSONs in `.kiro/allspark/prescan/` are crossed (A's outbound
paths against B's inbound ones, produced topics against consumed ones,
consumed gRPC service against implemented one).

### 2.D — Write the per-repo MOC

`.kiro/steering/moc.md` with `inclusion: auto`, a unique `name`
(`<repo>-moc`) and a `description` that names the repo (it loads only when the
request is about that repo's connections, never in every interaction), with the repo's
`role:` in the header, for **every repo in scope** and with the entry
point(s) that reach it in `Reached from`. Format in `references/moc-schema.md`.

### 2.E — Aggregate the workspace MOC

`.kiro/moc.md` at the workspace root (`inclusion: manual`, `#workspace-moc`),
and updates `allspark-index.md` (entry points marked, `#<repo>-moc` added for
each repo documented, see `skills/generate-steering/references/loading-strategy.md`),
aggregating the MOCs of the repos
documented so far, with the roles table, the **entry points** (documented or
not, with the repos each one reached) and the list of repos **not documented
yet**.

### 2.F — Compute the positions and compile the export

With the MOCs already resolved, it computes the positions and compiles
`allspark/export/allspark.md` at the workspace root (see
`references/export-format.md` for the folder and the exact format).

**Step 1 — Level 1 to JSON.** From the MOCs, write
`.kiro/allspark/level1.json`: **every repo of the workspace** with its `role`
(`documented: false` for the ones that have no MOC yet), the systems
without a repo (every host or domain of a connection that is not a workspace
repo) with their `axis`, the connections with their `endpoints`, and the
databases with the repos that use them. Format in the header of
`assets/layout/layout.py`.

**Step 2 — Run the layout script.**

```bash
python3 <skill>/assets/layout/layout.py --input .kiro/allspark/level1.json --output .kiro/allspark/layout.json
```

It groups the systems without a repo by provider, merges the connections
with their weight, computes every position (volume fill of each zone, database
nuclei with their electrons) and returns them both in semantic coordinates
(`pos`, what the repos' MOCs record) and already swapped (`export`, what
`allspark.md` carries). **Positions are never computed by hand.** Read its
`warnings`: a zone that does not fit (`overflow`) is reported to the user.
Rules in `references/position-formula.md`. If Python is not available,
report it: the repos' MOCs are written without a computed position and the
export is not generated.

**Step 3 — Write the export from `layout.json`:**

- **Points** — one per repo (its `role`, colored by type; a point with
  `documented: false` for each repo without MOC yet, which is replaced by the
  full point when it is documented), one per **provider group** of systems
  without a repo (role `external`), and one per **database** (with its `repos`
  and `electrons`).
- **Vectors** — each merged connection is a source→target vector with its
  `endpoints` weight. Trajectory of a complete process: it starts at X, goes
  through Y, Z is optional, there is never a return vector to X (it is
  implied). In the render each vector keeps the shape of its target
  (concave, arc, straight coral line or convex; see "Curved vector" in
  `position-formula.md`), and the global view groups them into bundles per
  pair of zones.
- **Databases** — each repo's `Databases used` become `data` links
  (repo → database).
- **Deterministic IDs** — per point (real Git name, e.g. `org/repo`; the
  provider group for systems without a repo; `engine://host/name` for
  databases) and per vector (source + target + protocol), so that a re-run
  upserts the same point/vector instead of duplicating it.
- **Export file** — `allspark/export/allspark.md` is regenerated with the
  complete compiled state, for `generate-visual` and any other render, from
  the `export` coordinates of `layout.json` (already swapped; see "Final axis
  transformation" in `position-formula.md`). The MOCs keep the semantic
  coordinates.

### 2.G — Offer the HTML visualization (yes/no gate)

With `allspark.md` already regenerated, ask: **"Should I generate or update
the cube's HTML visualization? (yes / no)"**. Only with an explicit "yes" is
`generate-visual` run (see `skills/generate-visual/SKILL.md`); with no
answer or with "no", no HTML is written. It is never generated as an
automatic part of this phase.

## Phase 3 — Promotion to Level 2: the module, consolidated (optional, per module, with a line gate)

### Scope — the user chooses, always starting from Level 1

Level 1 is already complete for what the chosen entry point reaches. From
there the user can promote with full flexibility of scope:

- **A single module** of an entry point (its endpoints are the Level 1
  connections it uses), or several.
- **A whole repo** (all the modules of an entry point).
- **The whole workspace.**

Promoting a module is **one operation**: it documents the module and
everything under it — its endpoints with their hops and data access, the
databases and external providers it touches and the shared functionalities
it reuses — in the same pass, with one gate and one confirmation. There is no
second promotion for endpoints and no third for data access. Nothing can be
promoted that is not in Level 1 — if it is missing, Phase 2 runs first for
that repo.

**Level 2 lives in the entry points.** A module is something the client can
do, so it belongs to a `frontend` or an `mvc-monolith`; what the backends do
appears in the `Hops` and in the "what happens behind" of the modules that
use them, not as modules of their own. It is written from the experience of
the client, in natural language, following `references/experience-docs.md`:
what the client sees and does, then what happens behind, with a
one-sentence `summary` for the module and for each endpoint.

### Step 0 — LINE-COUNT GATE (mandatory, blocking)

**It always applies when anything is promoted above Level 1, regardless of
scope** — the whole workspace or a single connection.

1. Count the lines of code involved in the chosen scope, per repo (front +
   back if the module's endpoints cross both). The count covers the whole
   module — endpoints and data access included — because that is what the
   promotion writes. Method, by scope:
   - A single module or connection → lines of the files on the source side
     that trigger it plus those on the target side that implement it (if both
     are workspace repos), using the paths in `structure.md` as a guide.
   - A repo → lines of the modules to be promoted according to `structure.md`
     (excluding what `.kiroignore` excludes: build, dependencies, generated
     files).
   - The whole workspace → the sum of all ready repos, over what Kiro sees in
     the workspace.
   - If the promotion needs its parent generated first (e.g. a module without
     its base files or its Level 1), the count includes it.
2. **Show the count on screen** before touching any file, broken down by
   repo, with the total. It is a reference of how much it will cost in
   credits, not an exact number of tokens:

   ```
   Requested promotion: Level 2 — whole workspace
   | repo              | lines  |
   |-------------------|--------|
   | org/front-web     | 18,400 |
   | org/api-payments  | 11,250 |
   | Total             | 29,650 |
   Do you confirm the promotion? (yes / no)
   ```
3. **Wait for explicit user confirmation (yes / no).** Without a "yes",
   nothing is generated. If the answer is "no", offer to reduce the scope
   (e.g. from the whole workspace to one connection) and recount; each new
   scope goes through the gate again.

The only block is the user's own confirmation against the count.

### Generation order — macro to micro

Documentation is always built from the global to the specific. A module is
never generated without its upper level:

1. **Repo global (already exists):** `product.md` (from `generate-steering`)
   + `moc.md` (global connections and databases, Phase 2).
2. **Sectioned mirroring `structure.md`:** the `product/features/` folder is
   created replicating the folder/module hierarchy that the repo's
   `structure.md` already describes — not an invented organization. First
   the **base files** the client perceives across the whole app (in
   `frontend`/`mvc-monolith` repos: `layout.md`, `sidebar.md`, and any
   equivalents such as header or navigation), then **one `.md` per
   module** (Level 2).
3. **Inside each module file, in the same pass:** the experience, the
   `Shared functionalities` it reuses (linked, not copied), one `###`
   subsection per endpoint with its **hops** and, if it touches a database,
   its **data access** (which database — engine, host and name, never
   credentials —, which entities and which operations, with `file:line`
   references), and the aggregates `Journey`, `External connections of the
   module` and `Databases touched`.

Exact paths and template in `references/moc-schema.md`; how to write it —
from the experience of the client, in natural language — in
`references/experience-docs.md`.

**Why sectioned:** the work is generated only on the chosen part of the tree —
so token spend is proportional to what the user confirmed in the gate, never
to the whole repo. The module's endpoints **start from the connections
already validated in Level 1** and then go down to the code of each endpoint.

### Steps of the promotion

1. Confirm the scope (after the gate).
2. If the base files or Level 1 are missing for that scope, generate them
   first (the gate already included them in the count).
3. Before writing each file, check whether it already exists — if so, treat
   it as the base and upsert, never rewrite from scratch. A module already
   promoted gains the endpoints that are missing; the ones it already has are
   kept. If the repo still has `functionalities/*.md` files written by 3.2.0
   or earlier, their content is merged into the module file as `###` endpoint
   subsections and the old files are **never deleted by the power**: it lists
   them so the team removes them from the repo when it decides to.
4. For each endpoint of the module: walk its code in the repo that triggers
   it and in the one that implements it, step by step — starting from that
   endpoint's evidence (`file:line`) in `.kiro/allspark/prescan/` when it
   exists, instead of searching for it — including **every connection to an
   external provider it touches along its path**, even if already counted in
   Level 1. Write its `Hops` using ids that exist in the export (repos,
   provider groups, database ids), and its `Data access` from where it reads
   or writes data (repositories, ORM calls, queries).
5. Add the pointer in the repo's Level 1 MOC (section `Promoted to Level 2`).
6. **Front matter for loading:** the module file gets `inclusion: auto`, a
   unique `name` (`<repo>-<module-slug>`) and a `description` that starts with
   its `summary`. See `skills/generate-steering/references/loading-strategy.md`.
   The entry point's line in `allspark-index.md` is marked "documented" and
   gets its `#<repo>-moc`.
7. **Export** → add the module to `modules` and each of its endpoints to
   `endpoints` (with its `summary`, `doc` — the module document —, `hops`,
   `entities` and `operations`) in `allspark/export/allspark.md`, format in
   `references/export-format.md`. The render builds the tree of each module
   from the hops of its endpoints. Every hop must use ids that are points of
   the export. **A module gets no position**: it is not a point of the cube.
8. Offer the HTML visualization with the same yes/no gate as step 2.G.

## Idempotency

Running this skill twice on the same repo state must not create duplicate
points or vectors: the deterministic IDs guarantee upsert, not insert.

**Upsert, never destructive replacement.** A re-run does NOT start from
scratch: it is a merge against the state already existing in the workspace.
Before rewriting, load `allspark/export/allspark.md` and the repos' existing
MOCs and treat them as the base. Rules:

- A node/vector that existed before and that the new run did NOT detect is
  NOT deleted silently. It is either kept, or marked
  `status: not-detected-last-run` in the repo's MOC for review — it never
  disappears without a trace. Losing nodes between runs is a bug, not a valid result.
- Reclassifying a node (changing its axis) requires traceable justification
  (evidence in code or an override in `domains.yaml`). Do not reclassify by
  intuition or merge two different nodes into one without confirming they
  have the same owner.
- Incomplete scan ≠ nonexistent node. If a repo is large and cannot be
  traced thoroughly, report the scan as partial and keep what was there
  before; do not assume that "I did not find it" means "it no longer
  exists".
- Post-run verification: compare the node/vector count against the
  previous run. If it dropped, explain each decrease (resolved, merged with
  justification, or really removed from the code) before accepting the
  output.

## Expected output

Phase 1: the two lists (ready, need `generate-steering`).

Phase 2: roles table (repo → role → evidence), prescan status (2.B.0 ok or
failed and why; per repo: candidates, % resolved without opening code,
uncertain candidates opened, discarded with reason, repos or stacks that
went through manual reading), connections detected per protocol per repo
(HTTP, SOAP, gRPC, queue, webhook, S3), internal connections `validated` vs
`no-target-evidence` (with the path/service/topic searched for), inbound
connections without a known internal source, MOCs generated/updated, and
new or updated points/vectors in the export.

Phase 2: the entry point chosen, the repos it reached with the estimate
shown, and the repos left not documented.

Phase 3: the line count shown in the gate and the user's answer, promoted
scope (connections, repos or workspace) and level, files created vs updated
(upsert), and the modules and endpoints added to the export.

Phases 2 and 3: answer to the HTML visualization gate (yes/no) and, if it was
"yes", the output of `generate-visual`.

**Mandatory verifications before considering the run finished:**

1. **No overlap:** no two points have the same rounded `(x,y,z)` triple —
   especially virtual points of the same axis (see "MANDATORY for Virtual
   categories" in `position-formula.md`). If there is overlap, fix the
   calculation before writing the export. The layout script measures the
   separation it achieved and reports a warning (`overflow`) if any zone
   ends with two points closer than 6: that warning is reported to the
   user, never ignored.
2. **Complete swap in the export:** for each point in `allspark.md`, the
   export's `pos_x` is the semantic value of External and `pos_z` that of
   Client — and the same for each arc control point. If any point was left
   with unswapped values (while the axes do have it), the export is wrong
   and is not delivered that way.
3. **Every repo with a role:** no real point is left without a `role`.
4. **Prescan reconciliation:** per repo, each JSON candidate ended up
   grouped into a MOC connection, discarded with a reason, or kept as a
   `database` candidate, recorded in the repo's `Databases used`
   (databases are never grouped into connections). A candidate
   with no destination is a lost connection: the run is not considered
   finished.
5. **Every promotion with its parent:** every module has its repo in the
   export, every endpoint its module, and every `hop` of an endpoint uses
   ids that are points of the export.
6. **No credentials:** every database id is `engine://host/name`; no
   user, password or token appears in any MOC, module document or the
   export.
7. **Entry point first:** only the repos reached from the chosen entry
   point(s) were classified and documented, unless the user confirmed the
   soft gate for the whole workspace; the repos left out are in the workspace
   MOC as not documented yet and in the export with `documented: false`.
8. **Documentation and view agree:** every module has its tree in the view and
   every tree its document ("no module without a document, no document
   without a module"); the `summary` and `doc` of each `modules` entry are
   the ones of its file, and the `summary` of each `endpoints` entry is the
   one of its `###` subsection; every module belongs to an entry point.
9. **Loading:** no document generated by the power is `inclusion: always`
    except `allspark-index.md`; every `name` is unique in the workspace; every
    Level 2 `description` starts with its `summary`.
