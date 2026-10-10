# English real-text sentence model

`en-real-cart@1` is an opt-in English sentence-breaking base. It never changes
the locale default. It receives ICU sentence candidates after token integrity
and the shipped English exception list, and it can only retain or suppress
those candidates.

```python
from icukit import Breaker

sentences = Breaker("en_US", base="en-real-cart@1").break_sentences(text)
```

The model is bound at load time to its byte digest, deployment version, feature
schema, ICU version, Unicode version, and token profile.

## Selection

The tree was fitted on eligible GUM and UK House of Commons Hansard training
documents. Pruning and feature selection first used held-out development
documents only. English EWT was excluded because its text descends from
LDC2012T13. The first 2,000 chunks of Google TN select shard 90 were then
opened and used to select the packaged variant. Those shard-90 measurements
are exploratory. Only after that choice was fixed were select shards 91--94
opened for the independent confirmatory D1. Test shards 95--99 remained closed.

Pruning alone did not materially reduce the artifact because the 112-feature
schema dominated its size. This is the held-out accuracy-versus-size curve for
minimum leaf size 10. Errors include the fixed 20-boundary candidate ceiling.

| Maximum depth | Compressed bytes | Development errors |
|---:|---:|---:|
| 2 | 17,567 | 60 |
| 3 | 17,627 | 57 |
| 4 | 17,727 | 46 |
| 5 | 17,865 | 50 |
| 6 | 17,956 | 46 |
| 7 | 18,030 | 46 |
| 8 | 18,101 | 37 |
| 9 | 18,159 | 33 |
| 10 | 18,210 | 33 |

The full tree's held-out permutation test identified eight useful features.
Retraining on those eight preserved its 33 development errors and removed
costly zero-importance features. Instrumented production calls identified
`text@run-1` (29.75 µs/call), `run.shape.cased@-2` (32.57 µs/call),
`shape.cased@-3` (25.00 µs/call), and `shape.coarse@-3` (23.72 µs/call) as the
largest feature-extraction costs on the measured sample. The selected schema
keeps `text@run-1` because it had the largest permutation effect and drops the
three costly shape features that had no retained value.

## Variant comparison

The exploratory comparison below uses the first 2,000 production chunks from
select shard 90 under each detokenizer. Its latency values came from three
sequential `glue2` production-path trials over 482,868 tokens. Cuts are
relative reductions in source-record seam-break error; a negative cut is a
regression. This comparison selected the packaged variant and is not
independent confirmatory evidence. The latency column is retained as historical
selection context; host contention made its absolute values unsuitable for the
authoritative latency comparison below.

| Variant | Compressed bytes | µs/token | Default multiple | `glue2` cut | `space` cut |
|---|---:|---:|---:|---:|---:|
| Shipped default | 0 | 8.362 | 1.00x | 0.00% | 0.00% |
| Full depth-10 tree | 18,211 | 35.452 | 4.24x | 23.10% | 29.90% |
| Full tree, flat evaluator | 16,435 | 32.135 | 3.84x | 23.10% | 29.90% |
| Depth-8 pruning | 18,101 | 30.582 | 3.66x | 19.74% | -28.12% |
| No character-window features | 17,214 | 33.146 | 3.96x | 26.34% | 4.64% |
| Permutation top eight, flat evaluator | 11,936 | 11.502 | 1.38x | 27.07% | 36.28% |

The production evaluator already gangs the work that can be shared: ICU
candidates and tokenization are each computed once, exception matches are
looked up from the same scan, and the model is evaluated only for candidates
left undecided by the exception list. On 500 profiled chunks, exceptions
decided 287 of 10,454 candidates before the tree. Compiling the full tree to a
flat equality evaluator reduced median latency by 9.4%. Feature caching reduced
the selected tree from 12.042 to 11.502 µs/token, a further 4.5%.

The earlier 8.362 µs/token default measurement and the later 2.234 µs/token
measurement used the same Python 3.12 interpreter, production code, shard-90
sample, and sequential harness. The first run showed large cross-trial
variation: one variant ranged from 20.37 to 36.44 µs/token, and the long-document
default ranged from 10.77 to 14.23 µs/token. The later rerun was much faster.
Because the code, interpreter, data, and exception-list path were unchanged,
the approximately fourfold default difference came from host contention made
visible by the system-grouped harness, not warm caches. Each whole-text call
creates fresh token and feature caches; grouping all trials by system also
could not control order or host load.

The authoritative rerun used a fresh process for each paired measurement,
alternated default-first and model-first order, and reports the median of seven
runs. “Cold” means fresh objects with no untimed production call. “Warm” adds
one untimed paired call before measurement. The sample is the same 2,000
shard-90 `glue2` chunks; the long document joins its first 100 chunks. These
latency measurements remain exploratory because shard 90 selected the variant.
The run began at a 7.15 one-minute load average on a 12-logical-CPU host; paired
ordering was used because unrelated host work could not be stopped or inspected.

| Workload | State | Default µs/token | `en-real-cart@1` µs/token | Multiple |
|---|---|---:|---:|---:|
| Select sample | Cold | 2.379 | 5.427 | 2.28x |
| Select sample | Warm | 2.678 | 6.123 | 2.29x |
| Long document | Cold | 4.032 | 9.115 | 2.26x |
| Long document | Warm | 4.032 | 8.715 | 2.16x |

The model is plainly at least twice as slow as the default on all four
authoritative comparisons. The cheapest measured optimization now caches a
feature after its first read on a candidate path and reads only the requested
character property instead of constructing a full class window. Compared with
the licensing rerun, the median multiple fell from 2.71x to 2.28x on the cold
sample and from 2.39x to 2.26x on the cold long document, but it remains above
2x. Getting below 2x requires further per-feature work, led by the remaining
`shape.cased@1`, `text@run-1`, and `sentence_break.first@1` costs (8.33, 7.55,
and 6.97 µs per instrumented read on 500 chunks), or sharing their token/run
state with the exception-list pass instead of deriving it again for model
candidates.

## Confirmatory D1

The independent D1 uses the production `SentenceOverride` path on select shards
91--94 under both detokenizers, excluding shard 90 entirely. The blocked lower
bound resamples those four shards. Test shards 95--99 stayed closed.

| Detokenizer | Default errors (FP/FN) | Model errors (FP/FN) | Relative cut | One-sided 95% shard-blocked lower bound |
|---|---:|---:|---:|---:|
| `glue2` | 303,630 (173,350/130,280) | 216,261 (55,419/160,842) | 28.775% | 28.634% |
| `space` | 349,680 (244,934/104,746) | 217,694 (90,984/126,710) | 37.745% | 37.659% |

For continuity, the earlier production-path totals over shards 90--94 were
28.834% (`glue2`) and 37.693% (`space`), with one-sided lower bounds of
28.699% and 37.578%. They include the selection shard and are exploratory.

The packaged artifact is 11,091 compressed bytes after canonical metadata and
gzip encoding. The measured endpoint is source-record seam-break error, not
general sentence-break error.

## Decision and licensing

The model is material as an opt-in: it produces a large and consistent seam
error reduction and adds only 11,091 bytes. It is at least twice as slow as the
shipped default in the authoritative latency rerun. That judgment is separate
from the positive numeric D1 bound and does not justify making the model a
default.

The bundled `NOTICE` and `REAL_TEXT_RECEIPT.json` identify the GUM documents,
source URLs, source-specific CC BY or CC BY-SA terms, and Hansard's Open
Parliament Licence. The artifact is offered under CC BY-SA 4.0 as a
conservative distribution choice. Release remains subject to seat review of
whether the CC BY-SA inputs make the model Adapted Material, whether
ShareAlike is legally required, and whether the attribution is sufficient.
