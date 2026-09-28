# Team notification and repo master registry

This model is a **suggested starting point**, not a rigid rule or a
block — Kiro Allspark is an open power and each team can adapt
this in its own way. The underlying idea is not to restrict who can touch
the Allspark, but for **the team to find out** when something changes, so
that a single shared Allspark does not silently drift out of sync between
teams.

There is no admin array or Git-validated user that approves — anyone
on the team can run any operation.

## Repo master registry (`allspark/repos-master.yaml`)

```yaml
repos:
  - org/repo-name-1
  - org/repo-name-2
```

- List of repos (identified by their real name in Git — see
  `axis-classification.md` of `find-connections`) that the team formally
  recognizes as part of its universe.
- A repo discovered in the workspace that is not in this list is marked
  as a **new repo, pending notification** (Phase 1 of
  `find-connections`) — it is not blocked, and nothing is assumed about its
  classification. Anyone can add it to the master registry; the power
  **suggests** telling the team when this is done and, if the user wants,
  helps draft the notice. It never blocks the action if the user prefers
  not to notify.
