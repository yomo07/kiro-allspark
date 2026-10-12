# Entry points — experience first, one entry point at a time

## Principle

The purpose of this power is to document, **in natural language and for both
Kiro and people**, how the client experiences the service: what they see, what
they do, and what happens behind. Developers already know how the system
works inside; what nobody has written down is the experience of the person
who uses it. That is why the unit of work is **an entry point**, not the
workspace, and why the documentation is built **from the entry point inward**.

Mapping the whole workspace is not forbidden — it is **not recommended**, and
the power says so before spending anything (see "The soft gate" below). It is
the most expensive way to get the least useful result: a map of everything
with no story about how anyone uses it.

## What is an entry point

A repo where the client interacts:

| Role | Why |
|---|---|
| `frontend` | The client uses its screens |
| `mvc-monolith` | The client uses its views, and its server side is part of the same repo |

A backend that receives calls directly from systems of the client is **not**
an entry point: it is reached like any other backend, from the entry point
that uses it. If a workspace has no `frontend` or `mvc-monolith` at all,
Kiro says so and asks the user to designate one repo as the entry point
(`entry_point: true` in `roles.yaml`).

## The flow

1. **Roles** (phase 2.A, only `tech.md` and `structure.md`, no code scan):
   Kiro lists the entry points it found.
2. **Prescan of every repo** (2.B.1): the script is the cheap part of the
   work — about 50,000 lines per second — so it runs on the whole workspace.
3. **Reach** (2.B.1b): `assets/reach/reach.py` crosses the outbound calls of
   each repo with the inbound ones of the others (route, topic, gRPC service,
   domain) and answers, for each entry point, **which repos it reaches and how
   much it would cost to document them**. It reads no source code and uses no
   tokens.
4. **Choice**: Kiro shows that table and asks which entry point to document.
5. **Wave walk** (2.B.2): Kiro classifies the entry point, resolves where its
   calls go, classifies the repos it reached, and so on until no new repo
   appears. Only what the entry point reaches is classified and documented.
6. **MOC and export** (2.D–2.F) for what was reached; the rest of the
   repos of the workspace stay in the cube as **not documented yet**.
7. **Level 2, the module** (Phase 3), module by module, written from the
   experience (see `experience-docs.md`).

## The soft gate — when the user asks for the whole workspace

It never blocks. Before scanning anything beyond the chosen entry point,
Kiro shows the cost and recommends the alternative; the user decides:

```
You asked for the whole workspace: 40 repos, 1,200,000 lines.
Kiro would read about 960,000 tokens of candidates and write ~120,000
(roughly 35 minutes of writing), for a map with no story about how anyone
uses it. Recommended: start from one entry point.
  front-web      reaches 11 repos    ~310,000 tokens to read
  portal-staff   reaches  7 repos    ~190,000 tokens to read
Continue with the whole workspace anyway? (yes / choose an entry point)
```

The numbers come from `reach.json`. The same soft gate applies when a
"document everything" request arrives in any other phase: same message, same
two answers.

## The wave walk

- **Wave 0** — the entry point: its candidates are classified (Kiro) and
  grouped into MOC connections, as always (`resolution-chain.md`,
  `axis-classification.md`).
- **Next wave** — the repos to which those connections resolve, using the
  edges of `reach.json` (`high` confidence as they are; `medium` are checked
  in the code at their evidence). Each new repo is classified in turn.
- **Stop** — when no new repo appears. Between waves, **only if** the next
  one has more than 8 repos or would read more than 200,000 tokens, Kiro
  stops with one line — "wave 2: 11 repos, ~240,000 tokens; continue?" — so
  the user can stop or narrow it.
- **Asynchronous paths** are followed too: a queue reaches the repo that
  consumes its topic, and a gRPC call the repo that implements the service.
- **What resolves to no repo of the workspace is external** (axis Z,
  confirmed by default), exactly as in the rest of the power.
- **Reverse validation** (2.C) applies only among the repos reached; the
  others keep no `reverse_validation` value.
- **A repo already documented from another entry point** is not redone: if
  its MOC is current (`source_hash`), the wave skips it and only adds the
  connections this entry point brings. Backends shared by several entry
  points are documented once.

## What the cube shows

Every repo of the workspace is in the cube. The ones already documented are
solid; **the ones not documented yet are small, hollow and dotted**, so the
coverage can be read at a glance and the first thing a newcomer sees is how
much is still to tell. The entry points that are documented carry a ring.
Positions are recomputed from everything documented so far, so points move a
little when more of the workspace is documented (deterministically).

## Cost model

| Quantity | Value | Origin |
|---|---|---|
| Prescan speed | ~50,000 lines/s | measured (PetClinic, NestJS, Django) |
| Tokens to read one candidate | ~100 | measured (size of the JSON / 4) |
| Tokens written per candidate read | ~15 | assumption (connections after grouping) |
| Writing speed of the model | ~60 tokens/s | assumption |
| Tokens to read raw code (Levels 2–3) | ~10 per line | assumption |

`reach.json` carries these figures and labels which are measured and which
are assumptions. They are an estimate to decide with, not a promise: the
real cost depends on the model and on the code.
