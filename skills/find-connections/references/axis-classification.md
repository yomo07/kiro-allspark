# Axis classification

## Definitions

- **X — Client**: every domain/endpoint/bucket that belongs to a system
  owned by an Acme client (who consumes the final service and pays Acme
  for it). The direction of the call does not matter — both "the repo
  calls the client" and "the client calls the repo" weigh toward X.

- **Y — Main provider (Acme)**: every domain/endpoint/bucket that belongs
  to another repo within the universe of Acme applications. Internal,
  service-to-service traffic. It is the only axis where the source/target
  is "ourselves". It resolves directly (step 4 of the chain) if the
  identifier matches a repo in the workspace.

- **Z — External providers**: every domain/endpoint/bucket that belongs to
  a third party that Acme hires or integrates in order to provide its
  service (Acme pays that entity, not the other way around).

## X vs Z disambiguation rule

The criterion is the contractual relationship, not the technical form of
the call:

- Does Acme bill/serve that entity? → **X**
- Does Acme pay/hire that entity in order to operate? → **Z**

It cannot be reliably automated — it normally needs to be resolved in
`domains.yaml` (overrides), because the code does not expose who pays
whom.

## There is no dual role

The same domain is never a client and an external provider at the same
time. In case of real ambiguity, it is treated as **client**.

## Front without intermediate backend

When a repo with role `frontend` (see `repo-roles.md`) calls a domain directly without going through an
Acme backend of its own, the connection is classified **Z, external,
confirmed** — directly, with no special mark or intermediate state. The
workspace is the boundary that decides everything: if the domain is not
mapped to any repo within this workspace, it is external, period. It does
not matter whether the backend that "should" intermediate actually exists
but outside the scope of this workspace, or whether it is real technical
debt (a front hitting an external system directly) — the power does not
distinguish those two causes nor flag them for review, because
distinguishing them would require information the workspace does not have.
Defining that scope once removes the uncertainty instead of dragging it
along as a pending state.

If later the missing backend is added to the workspace (new repo), the
**virtual-point→real-point merge** rule applies (see below) — not a manual
reclassification.

## Repo identity — real name in Git

Every repo is identified, for the purposes of domain resolution (step 4 of
the chain) and of workspace membership, by its **real name in Git** (the
remote, typically `org/repo-name`) — never by a local alias, a folder
name, or whatever the team informally calls it. It is the same identifier
already used as the deterministic point ID in the export (see
`export-format.md`).

## S3 storage (own rule)

1. The bucket owner resolves to a workspace repo → **Y**
2. The owner resolves to an entity known through overrides → **X or Z**
   according to the contractual map
3. Nothing resolves → default **Z**, external, confirmed directly

## gRPC

Same treatment as HTTP: the `.proto` service resolves to the repo that
implements it (step 4 of the chain) → **Y**; if there is no repo that
implements it in the workspace → **Z** by default. From a `frontend`
(gRPC-web) the front without intermediate backend rule applies.

## Message queues (RabbitMQ, Kafka)

1. The topic/queue has a producer **and** a consumer within the workspace →
   **Y**, vector producer → consumer.
2. The broker or topic resolves to an entity known through overrides → **X
   or Z** according to the contractual map (e.g. a topic published by a
   client).
3. Nothing resolves → default **Z**, external, confirmed directly.

The broker itself (the RabbitMQ/Kafka server) is not a point: the points
are the repos that produce and consume. A virtual point is only created
when one end of the conversation (producer or consumer) is not in the
workspace.

## Webhooks

Same directional treatment as HTTP/SOAP (they go through the full chain,
including the front without backend check). Their default when not
resolved is **Z, external, confirmed directly** — same as S3 and as
HTTP/SOAP: the three connection types share the same default when the
chain is exhausted without resolving anything. There is no intermediate
"pending" state for any type — the workspace is the boundary that decides
everything (see "Front without intermediate backend" above).

## Virtual point that becomes a real point (merge)

Specific reclassification case: a domain that today is a virtual point
(without its own repo, typically axis Z or Y) turns out to have, in a later
run, a real repo that implements it — because it was added to the
workspace. A new point is not created in parallel to the virtual one — they
are merged:

1. **Detection**: when resolving a repo (new or re-scanned), cross-check
   its domain/service name against the virtual points already existing in
   the export. Match → triggers a merge, not the creation of a new point.
2. **Vector redirection**: all vectors that pointed to the virtual point
   (from any repo) are redirected to the new real point. The merge is never
   silent: it is reported at the end of Phase 2 as virtual id → real id (see
   "Virtual point merged into a real point" in `export-format.md`).
3. **Repositioning**: the real point recalculates its position with the
   formula of its real category (according to the role assigned to it in
   step 2.A — `repo-roles.md` — and the table in `position-formula.md`),
   not with the virtual point one — the anchor and the pure extreme change.
4. **It is one operation**: it touches at the same time the export and the
   MOC of each repo that pointed to the virtual point (to update the id in
   their connections), so no connection is left naming a point that no
   longer exists.
