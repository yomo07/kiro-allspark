# Connections MOC schema

The MOC (map of connections) documents, for each repo in the workspace,
**what it connects to**: its role and all of its connections to other repos
in the workspace, to client systems and to third parties, at the level of
domain, service, topic or bucket. It does not document the internal workings
of the code: only the connections.

There are two files:

| File | What it documents |
|---|---|
| `.kiro/steering/moc.md` (per repo) | Repo role and all its connections |
| `.kiro/moc.md` (per workspace) | Roles of all repos, systems without a repo and summary of the last run |

## Per-repo MOC — `.kiro/steering/moc.md`

```markdown
---
inclusion: manual
---
# MOC — Connections

## Repo role
- role: backend             # frontend | backend | mvc-monolith | worker
- evidence: Spring Boot, controllers/ and services/, no views

## Detected connections

- domain: provider-x.com
  type: soap
  direction: outbound
  source: wsdl-local
  axis: Z
  status: confirmed
  detection_source: prescan       # prescan | manual
  endpoints: 3                    # candidates grouped into this connection

- domain: quoter.internal
  type: http
  direction: outbound
  target_repo: org/quoter
  source: service-name-match
  axis: Y
  status: confirmed
  reverse_validation: validated

- grpc_service: scoring.v1.ScoringService
  host: scoring.internal:9090
  type: grpc
  direction: outbound
  target_repo: org/scoring
  source: proto-local
  axis: Y
  status: confirmed
  reverse_validation: no-target-evidence

- topic: payments.confirmed
  broker: kafka.internal
  type: queue-kafka            # queue-rabbitmq | queue-kafka
  direction: outbound          # producer → consumer
  target_repo: org/notifier-worker
  source: config-non-secret
  axis: Y
  status: confirmed
  reverse_validation: validated

- domain: system.clientbank.com
  type: http
  direction: inbound
  source: override
  axis: X
  status: confirmed

- bucket: third-party-assets
  type: s3
  source: unresolved
  axis: Z
  status: confirmed-default

- webhook: payment-notifications
  type: webhook
  source: unresolved
  axis: Z
  status: confirmed-default

## Count by axis
- count_X:
- count_Y:
- count_Z:

## Count by protocol
- http:
- soap:
- grpc:
- queue:
- webhook:
- s3:

## Computed position
- x:
- y:
- z:
```

`status` values: `confirmed`, `confirmed-default` (the chain was exhausted
without resolving → Z external, no intermediate state).

`detection_source` says how the connection was found: `prescan`
(candidate from the JSON in `.kiro/allspark/prescan/`, classified by Kiro) or
`manual` (manual reading of the code: repo without prescan, stack in
`stacks_without_pattern`, or a connection the script did not see). Many
`manual` connections in a covered stack are a sign that a rule is missing.
`endpoints` is the number of candidates grouped into that domain connection.

`reverse_validation` only appears on connections with `target_repo` (both
sides are repos in the workspace): `validated` or `no-target-evidence` (see
`reverse-validation.md`). It is not a connection status — the axis does not
change.

## Per-workspace MOC — `.kiro/moc.md`

```markdown
---
inclusion: manual
---
# MOC — Workspace

## Roles
| repo | role | evidence |
|---|---|---|

## Referenced virtual points (external role, no repo in this workspace)
-

## Internal connections without evidence at the target
-

## Last run of find-connections
- date:
- scanned repos:
- new repos pending notification (outside `allspark/repos-master.yaml`):
```

Scoping note: `axis: Z` in a repo's MOC means "external to what this
workspace can see", not necessarily external to the company's whole
universe — another workspace with more context may resolve it differently.
That is why each entry carries `source`, so that when merging against the
shared vault a workspace with more information can reclassify without
blindly overwriting what another team put there.

## Multi-team merge between vaults

Two or more teams can share the same Obsidian vault (via git or another
sync mechanism) and each one can map its repos independently and
incrementally — the universe becomes clearer piece by piece, never in a
single run. The central risk is that one team wipes out another team's
progress when syncing. Rules:

- **Merge granularity = per file, not per whole vault.** Each point note
  (repo or system without a repo) lives in its own file with a
  deterministic ID. A merge never replaces the whole vault end to end
  — it combines file by file, and two teams mapping different repos
  never touch the same file.
- **An existing note is not regenerated from scratch by another team.** If
  team B finds that team A already mapped a repo, it treats that note as
  the base and only adds what is missing (e.g. a new vector) or updates
  specific fields, preserving what was already there.
- **A real conflict (both teams edited the same file differently since the
  last sync) is reported, not resolved arbitrarily.** "The newest version"
  is not chosen and nothing is silently overwritten — both versions are
  listed and human confirmation is requested on which prevails or how to
  combine them.
- **A note's vectors are merged by union, not by replacement** — if the
  local vault does not know a connection that the remote vault does have,
  it is added; neither side loses anything.
- **Nothing is silently deleted:** if a sync no longer finds a point or a
  vector that the vault did have, it is marked
  `status: not-detected-last-run` for review.
- **Post-merge verification:** compare the number of nodes and vectors
  before and after the sync. Any drop must be explainable.
