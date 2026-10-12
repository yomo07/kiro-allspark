# Loading strategy — steering for multi-repo workspaces

In a workspace with many repos, every repo brings its own steering. If each
repo's `tech.md`, `structure.md` and `product.md` used `inclusion: always`, a
workspace with 10 repos would load 30 documents into **every** interaction,
even when you only work on one repo: context spent for nothing, and Kiro mixing
the conventions of one repo with another. This power avoids it by choosing an
inclusion mode per document.

## Kiro's inclusion modes

| Mode | When it loads | Front matter |
|---|---|---|
| `always` | Every interaction | `inclusion: always` |
| `fileMatch` | When a file matching the pattern is being worked on | `inclusion: fileMatch` + `fileMatchPattern` |
| `manual` | When referenced with `#name` in chat (also a `/` command) | `inclusion: manual` |
| `auto` | When the request matches its `description` (like skills) | `inclusion: auto` + `name` + `description` |

## What this power uses

| Document | Where | Mode | Why |
|---|---|---|---|
| **Workspace index** `allspark-index.md` | `.kiro/steering/` of the workspace root | `always` | The only one always loaded, and it is short: one line per repo (role, stack, entry point or not) and the names to ask for its docs. Kiro knows what exists without loading it. |
| `product.md`, `tech.md`, `structure.md` of each repo | the repo's `.kiro/steering/` | `auto` | Loaded when the request is about that repo or its stack |
| `moc.md` (Level 1) of each repo | the repo's `.kiro/steering/` | `auto` | For "what does X connect to?" questions |
| Level 2 — a module (its endpoints and data access inside) | `product/features/...` | `auto` | Its `description` starts with the `summary` of the experience: loaded when someone asks how the client does that |
| Base files (`layout.md`, `sidebar.md`...) | `product/features/` | `manual` | Reached from the modules |
| `database.md` | the repo's `.kiro/steering/` | `manual` (as before) | On demand only |

`fileMatch` is not used as the base: its patterns are not documented for
multi-root workspaces, and it has been reported not to trigger from the
global steering folder.

## Names — unique across the workspace

Every repo has a `tech.md`: with `auto` and with `#name` the `name` must be
unique, so the power never uses the bare file name.

```
name = <repo>-<doc>                     # e.g. api-payments-tech, front-web-product, api-payments-moc
       <org>-<repo>-<doc>                # only if two repos of the workspace share the same <repo>
Level 2:  <repo>-<module-slug>           # e.g. front-web-paying-a-bill
```

Lowercase, digits and hyphens only; at most 64 characters (the repo part is
shortened first if needed). The name is also what the user types after `#`.

## Descriptions — what decides when an `auto` document loads

Kiro loads an `auto` document when the request matches its description, so
the description names **the repo, its role and its stack**, and says **when to
use it**. One or two sentences, at most 300 characters, in English (the
language of the files), without invented facts:

```yaml
# tech.md
description: "Stack and conventions of api-payments, a NestJS backend (TypeScript, PostgreSQL). Use when writing, reviewing or running code in api-payments."
# structure.md
description: "Folder layout, layers and features of api-payments (NestJS backend). Use when locating files or adding code to api-payments."
# product.md
description: "What api-payments is for and who uses it: payment processing for the web and kiosk fronts. Use when asking what api-payments does or why."
# moc.md
description: "Connections of api-payments: which repos, providers and databases it talks to. Use when asking what api-payments connects to or what breaks if it fails."
# Level 2
description: "Customers pay a bill in three steps and get a receipt. Use when asking how a customer pays a bill in front-web."
```

A Level 2 description **starts with the `summary`** of the file, word for
word, followed by "Use when asking how …": the same sentence the 3D view shows,
so the documentation, the visualization and what Kiro loads agree.

## The workspace index — `allspark-index.md`

Written by `generate-steering` (one line per repo, upsert) and completed by
`find-connections` (entry points, and the MOC name once it exists). It lives
in the `.kiro/steering/` that Kiro loads for the whole workspace: the root of
the workspace; in a multi-root workspace, the folder that holds the
workspace's `.kiro/` (the same place as `.kiro/moc.md`). It must stay short:
about one line per repo.

```markdown
---
inclusion: always
---
# Workspace index (Kiro Allspark)

Repos of this workspace. Each one has its own steering, loaded only when the
request is about it; ask for one explicitly with `#name`.

| repo | role | stack | entry point | steering |
|---|---|---|---|---|
| front-web | frontend | Angular | yes, documented | #front-web-product · #front-web-tech · #front-web-structure · #front-web-moc |
| api-payments | backend | NestJS | — | #api-payments-product · #api-payments-tech · #api-payments-structure · #api-payments-moc |
| legacy-reports | backend | Java | — | #legacy-reports-tech · #legacy-reports-structure (not documented yet) |
```

## Updating existing steering

A repo generated by an older version has `inclusion: always` in its base
docs. `generate-steering` offers to **optimize the loading**: it rewrites only
the front matter (`inclusion`, `name`, `description`) of `product.md`,
`tech.md` and `structure.md`, keeps the content untouched, and creates or
updates the index. It lists what it changed. A file whose `inclusion` was set
by hand to something else (e.g. `fileMatch`) is left as it is and reported.

## If `auto` is not available

`auto` is recent. If the Kiro version in use does not support it (the
document never appears among the included ones), switch those documents to
`manual`: the names stay the same, the index lists them, and they are pulled
with `#name`. The index is the part that keeps working in every version.
