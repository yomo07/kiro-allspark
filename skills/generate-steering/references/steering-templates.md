# Steering doc templates

All use standard Kiro frontmatter. **None of the per-repo docs is `always`**:
in a multi-repo workspace that would load every repo's docs into every
interaction. They are `auto` with a unique `name` and a `description` that
names the repo, its role and its stack; only the short workspace index is
`always`. Rules, name format and examples in `loading-strategy.md`.

## product.md

```markdown
---
inclusion: auto
name: <repo>-product
description: "What <repo> is for and who uses it: <one line>. Use when asking what <repo> does or why."
---
# Product

## Purpose
- What the repo does, in one or two lines

## Users
- Who uses it (end client, internal team, other systems)

## Main features
-

## Business context
- Where it fits in the company's product (optional)
```

## tech.md

```markdown
---
inclusion: auto
name: <repo>-tech
description: "Stack and conventions of <repo>, a <framework> <role> (<language>, <main datastore>). Use when writing, reviewing or running code in <repo>."
---
# Tech Stack

## Language / runtime
-

## Main framework
-

## Key dependencies
-

## Build / test tools
-
```

## structure.md

```markdown
---
inclusion: auto
name: <repo>-structure
description: "Folder layout, layers and features of <repo> (<framework> <role>). Use when locating files or adding code to <repo>."
---
# Repo structure

## Folder organization
-

## Layers / architectural patterns
-

## Naming conventions
-

## Features (real hierarchy, base of product/features/)
- path/to/feature — what it is, in one line
  (list the feature tree exactly as it is in the code; it is the mold that
  find-connections replicates in product/features/ for Levels 2 and 3)

## UI base pieces (if the repo has a UI)
- layout, sidebar, header, navigation — path of each one

## Screens and user flows (frontends and monoliths)
- screen or flow — route — what the client does there, in a few words
  (find-connections starts from here when it documents the experience of the client)

## Data access (used to identify the databases of Level 1)
- ORM / data layer: (e.g. TypeORM, Prisma, Hibernate/JPA, Django ORM, Entity Framework)
- where repositories or queries live: path

## Role signals
- Own UI: yes/no — exposes endpoints: yes/no — consumes queues or jobs: yes/no
  (find-connections decides the role from this: frontend, backend,
  mvc-monolith or worker)
```

## .kiroignore

Standard patterns. If the file already exists, only the missing lines are
added (line-by-line merge); it is never replaced.

```
# dependencies and build output
node_modules/
dist/
build/
target/
bin/
obj/
.venv/
__pycache__/
coverage/

# local secrets
.env
.env.local

# kiro-allspark: prescan environment and results (working artifacts)
.kiro/allspark/
```

## database.md (ON-DEMAND, not automatic)

Only generated if the session prompt explicitly asks for it.

```markdown
---
inclusion: manual
name: <repo>-database
---
# Database

## Engine
-

## Main schema
-
```

## allspark-index.md (workspace, the only one `always`)

In the `.kiro/steering/` of the workspace root (multi-root: the folder that
holds the workspace's `.kiro/`). One line per repo, upserted: a repo's line
is added or replaced, never the others. Keep it short.

```markdown
---
inclusion: always
---
# Workspace index (Kiro Allspark)

Repos of this workspace. Each one has its own steering, loaded only when the
request is about it; ask for one explicitly with `#name`.

| repo | role | stack | entry point | steering |
|---|---|---|---|---|
| <repo> | <role> | <framework> | <yes / yes, documented / —> | #<repo>-product · #<repo>-tech · #<repo>-structure |
```
