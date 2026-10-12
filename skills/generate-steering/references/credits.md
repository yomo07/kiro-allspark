# Base credits (reference, model-agnostic)

The inventory is **free** (it runs locally in Python). Documentation by the
model is what costs credits. The power shows a **base** estimate and never
names models or multipliers: the user multiplies the base by whatever applies
to the model they run in Kiro.

```
base      = lines_of_code / 1000
L1 (repo) = base x complexity factor
L2        = L1 x 2
L3        = L1 x 4
```

Complexity factor of a repo = the highest factor among the protocols detected
in it (HTTP when none is detected):

| Protocol | Factor | Source |
|---|---:|---|
| HTTP | 1.0 | design |
| Webhooks | 1.1 | design |
| gRPC, Kafka | 1.3 | design |
| RabbitMQ (queues) | 1.3 | assumption: treated like Kafka |
| SOAP, S3 | 1.0 | assumption: treated like HTTP |

The assumed values are editable in `FACTORS` at the top of `inventory.py`
and are echoed in `inventory.json` under `credits.factors`. `reach.py`
(`find-connections`) uses the same table to price what each entry point reaches
once the prescan has run (it reads the protocols of the prescan candidates):
keep both tables in sync.

## How to present it

Show the table the script prints (`--table`) and say plainly:

> These are base credits, a reference. Multiply them by the model you use in
> Kiro to get the real cost. Scanning was free.

Level 4 (database access) has no formula yet and is not estimated.
