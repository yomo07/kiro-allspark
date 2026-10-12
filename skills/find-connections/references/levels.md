# Levels 2, 3 and 4 — vocabulary, the cross-repo rule and database access

The formats live in `moc-schema.md` (folders, front matter, templates) and the
writing guide in `experience-docs.md`. This file only adds what those do not
say: the vocabulary, how credits gate a promotion, what happens when a module
reaches another repo, and Level 4.

## Vocabulary

- **Module** (Level 2): a functionality the client perceives as one thing
  (Sign in, Pay an order, Issue an invoice), **shared across repos**. It is
  written as the ordered `Path` it follows through the points of the cube
  (client → internal → optionally external), one step per point with a short
  note. A point may repeat (a webhook that comes back). A module that only
  touches one point is a *local module*. The 3D view draws the `Path` as a
  numbered trail.
- **Endpoint** (Level 3): one endpoint, front and back, with its `Hops` and
  its data access. The 3D view draws it as a strand inside its module.
- **Database access** (Level 4, optional): see below.

A module belongs to an entry point: its **owner** note lives in the repo
where the client enters (a `frontend` or an `mvc-monolith`) and carries the
`Path`.

## Credit gate

Promoting anything above Level 1 always goes through the line-count gate of
Phase 3 (Step 0). Next to the lines, show the **base credits** of the chosen
scope: `lines / 1000` × the protocol factor, with Level 2 = L1 × 2 and Level 3
= L1 × 4 (`generate-steering/references/credits.md`). They are a model-agnostic
reference: the user multiplies them by the model they run in Kiro. The power
never names models or multipliers. Level 4 has no formula yet: show only the
lines involved.

## Modules that reach other repos

While documenting a module in repo X, a step may land in repo Y. Three layers,
always in this order:

1. **Detect** — record Y's part as a *candidate* with state `candidate`.
2. **Confirm** — ask: "Document Y's part of this module too? (yes / no)".
   Show the lines involved and the base credits first (credit gate).
3. **Link** — on yes, write Y's part note (the same `module:` id, `role: part`,
   one `part:` line saying what that repo does for the module) and link both
   notes in the MOC, in both directions.

Rules:

- If Y already has a note for that module id → only link; never overwrite
  (merge, never replace). The `Path` stays in the owner note: part notes
  never carry or rewrite the order.
- States: `candidate` → `documented`.

## Level 4 — database access

Opt-in like Levels 2 and 3 (explicit selection and credit gate). It documents
how the steps of a module touch the database: which database, which entities
and which operations. In the cube the database is a `type: database` point (a
gold nucleus near the origin with 1 to 5 electrons = how many repos use it),
each repo that uses it has a `links[]` entry with a `label` ("Session
storage"), and the module step that touches it is a normal step whose `point`
is the database ("Stores the order").

The id is `engine://host/name`. Credentials, connection strings and secrets
never go into notes or into the export (the same masking as the prescan).
`database.md` stays on-demand: it is only written when the team asks for it.
