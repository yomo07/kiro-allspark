# Documenting the experience — writing guide for Levels 2 and 3

The documentation this power writes is for **Kiro and for people**, in
natural language, following the structure of Kiro's steering. Its job is not
to explain the code — the developers know it — but to explain **how the
client consumes the service**: what they see, what they do, what they get,
and, in plain words, what happens behind.

## The rules

1. **Start from the person, not from the code.** A feature is something the
   client can do or get ("pay a bill", "check in at the kiosk"), never a
   folder or a class. Its name is the name the client would give it.
2. **Plain language, in the language of the conversation.** No code
   identifiers in headings or sentences; when a name helps a developer find
   the code, it goes in parentheses at the end: "the customer confirms the
   payment (`POST /payments/confirm`)".
3. **Two voices, in order:** first what the client **sees and does**, then
   what **happens behind**. Behind means services, providers and data in
   words: "the payments service asks the card provider to authorize it and
   records the result".
4. **One summary per module and per endpoint.** One sentence, at most 200
   characters, active voice, from the client's point of view. It is written
   in the `summary` of the document's frontmatter and is **the same text**
   the 3D view shows (see "Concordance" below). If it is wrong here, it is
   wrong there: there is no second copy.
5. **Follow Kiro's structure.** A Level 2 file is one steering doc per
   module (`inclusion: auto`, so Kiro loads it when someone asks how the
   client does that) with all its endpoints inside, in `product/features/`
   mirrored from `structure.md`, linked from the repo's `product.md`. Do not
   invent a new layout and do not create a file per endpoint.
6. **Do not repeat Level 1.** The MOC already lists the connections;
   here they are told as part of a story, once.

## How to find the experience in a front

The prescan does not read screens, so Kiro reads the front's code **at the
feature being promoted**, looking for:

- the routes or screens of the feature (router files, page components);
- what the person can do in them: forms, buttons, actions, menus;
- the texts the person reads (labels and i18n keys are the best source of
  the real names);
- which service call each action fires (the evidence `file:line` of the
  prescan points straight to it).

In an `mvc-monolith` the same applies to views and controllers.

## Level 2 — a module, in the client's words

```markdown
---
inclusion: auto
name: front-web-paying-a-bill
description: "Customers pay a bill in three steps; the payment is authorized with the card provider and they get a receipt. Use when asking how a customer pays a bill in front-web."
summary: Customers pay a bill in three steps; the payment is authorized with the card provider and they get a receipt.
---
# Paying a bill

## What the customer does
1. Opens "Pay" and chooses the bill.
2. Reviews the amount and confirms.
3. Gets the receipt on screen and by email.

## What happens behind
The payments service asks the card provider to authorize the charge,
records the result and sends the receipt through the notification service.
```

The sections of the real template are in `moc-schema.md`; this example shows
the tone.

## Endpoints inside the module — one action of the client

Each endpoint is a `###` subsection of the module file, not a file of its own:

```markdown
### Confirming the payment (`POST /payments/confirm`)
summary: The customer confirms the payment and the card provider authorizes it.

**When it happens.** When the customer presses "Confirm" on the review screen.

**What it does.** Checks the bill is still open, asks the card provider to
authorize the charge and records the result.
```

`Hops` and `Data access` (lists of ids) stay at the end of each subsection:
they are the data the 3D view draws, not prose.

## What to avoid

| Do not write | Write instead |
|---|---|
| "The `PaymentsController` delegates to `ChargeService`" | "The payments service charges the card" |
| "Endpoint POST /payments/confirm" as a heading | "Confirming the payment" as a heading |
| A table of every field of a payload | What the client needs to provide, in a sentence |
| Everything the service can do | Only what this entry point's client does |

## Concordance with the 3D view

The documentation and the visualization are two readings of the same data,
not two copies:

| In the documentation | In the 3D view |
|---|---|
| Level 2 file of a module (`summary`, and its `description`, which starts with it) | The tree of that module (Modules view) and its text in the side panel; the same sentence decides when Kiro loads the file |
| `###` subsection of an endpoint inside the module (`summary`, `Hops`, `Data access`) | The strand of that endpoint (Detail view), its tooltip and its text in the side panel |
| `Hops` of the endpoints of the module | The hops the module's tree is built from: if they are not in the file, they are not drawn |
| Global view: counts per color and the total | Computed from the Level 1 connections (`endpoints` of each vector); they are not written in any document |
| Entry point documented in the MOC | Point with a ring |
| Repo of the workspace without MOC | Small hollow dotted point |
| Path of the document (`doc`) | "Read more: …" under the text in the side panel |

Verification (see `SKILL.md`): **no module in the 3D view without a
document, no document without a module**, and every `summary` of the export
is the one of its file or of its endpoint subsection.
