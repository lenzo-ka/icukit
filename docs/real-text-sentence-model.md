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
documents. Pruning and feature selection used held-out development documents
only. English EWT was excluded because its text descends from LDC2012T13.
Google TN select shards were opened only after the variant was fixed; test
shards 95--99 remained closed.

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

The comparison below uses the first 2,000 production chunks from select shard
90 under each detokenizer. Latency is the median of three sequential `glue2`
production-path trials over 482,868 tokens. Cuts are relative reductions in
source-record seam-break error; a negative cut is a regression. This bounded
comparison selected the variant for the full D1 rerun; it is not the D1 table.

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

On a 24,234-token, 126,823-character long-document benchmark, the default took
12.702 µs/token and the selected tree took 14.394 µs/token (1.13x). Across five
fresh processes, median construction plus the first 247-token call was 36.06 ms
for the default and 38.84 ms for the selected tree. The first call itself was
0.702 ms and 1.948 ms, respectively.

## Full D1

The final D1 rerun used the production `SentenceOverride` path on all select
shards 90--94 under both detokenizers. The blocked lower bound resamples the
five shards. Test shards 95--99 stayed closed.

| Detokenizer | Default errors (FP/FN) | Model errors (FP/FN) | Relative cut | One-sided 95% shard-blocked lower bound |
|---|---:|---:|---:|---:|
| `glue2` | 380,578 (217,384/163,194) | 270,841 (69,544/201,297) | 28.834% | 28.699% |
| `space` | 438,243 (306,918/131,325) | 273,055 (114,262/158,793) | 37.693% | 37.578% |

The packaged artifact is 11,091 compressed bytes after canonical metadata and
gzip encoding. The measured endpoint is source-record seam-break error, not
general sentence-break error.

## Decision and licensing

The model is material as an opt-in: it produces a large and consistent seam
error reduction, remains under 2x the shipped default on the select benchmark,
is close to the default on a long document, and adds only 11,091 bytes. That
judgment is separate from the positive numeric D1 bound. It does not justify
making the model a default.

The bundled `NOTICE` and `REAL_TEXT_RECEIPT.json` identify the GUM documents,
source URLs, source-specific CC BY or CC BY-SA terms, and Hansard's Open
Parliament Licence. The artifact is offered under CC BY-SA 4.0 as a
conservative distribution choice. Release remains subject to seat review of
whether the CC BY-SA inputs make the model Adapted Material, whether
ShareAlike is legally required, and whether the attribution is sufficient.
