# Default unit widening results

Measured 2026-10-13 against `origin/main` at
`15006737101e28b97d07b686c3f0ab21ec6d8fab`, with Python 3.13.15, ICU 78.3,
and PyICU 2.16.2.

## Selection rule

The default single-unit selection is now the ordered union of:

1. CLDR's world and read-region preferences;
2. every ICU `duration`, `digital`, and `frequency` single unit, excluding the
   duplicate `-person` durations;
3. ICU's `volt`, `micrometer`, and `nanometer` units; and
4. icukit's locale-curated composed units.

Mixed units and duration-order runs are unchanged. Passing `units=` still replaces
the complete default unit selection; `units=()` opts out of unit readers.

ICU exposes 235 non-currency, non-mixed single units. Selecting all of them was
rejected because it exceeded the cost bound: on the pinned 2,000-row set, median
total time rose 13.1% and median per-row p50 rose 16.6%. Across the multilingual
running-text sets, total time rose 9.4%-28.5% and p50 rose 11.9%-27.6%. Cold build
time rose 6.1%-42.4% by locale.

The selected seven units are `hertz`, `kilohertz`, `megahertz`, `gigahertz`,
`volt`, `micrometer`, and `nanometer`. They retain 16,974 of the full inventory's
19,929 weighted English-census gains (85.2%) when the guarded voltage symbol is
included.

## ICU formatter evidence

Each witness below was written by ICU in the named locale and read whole by the
new default. Voltage uses the wide form because the single-letter `V` form is
guarded.

| Locale | Frequency | Voltage | Micrometer | Nanometer |
|---|---|---|---|---|
| `en_US` | `900 MHz` | `5 volts` | `10μm` | `530nm` |
| `de_DE` | `900 MHz` | `5 Volt` | `10 μm` | `530 nm` |
| `fr_FR` | `900 MHz` | `5 volts` | `10 μm` | `530 nm` |
| `ja_JP` | `900 MHz` | `5 ボルト` | `10μm` | `530nm` |
| `ru_RU` | `900 МГц` | `5 вольт` | `10 мкм` | `530 нм` |
| `zh_CN` | `900 MHz` | `5伏特` | `10μm` | `530nm` |

## Ambiguity guard

Ambiguous surfaces are absent from ordinary `measure:<unit>` readers and remain
reachable through `measure:ambiguous-unit:<unit>`. `guarded=True` adds the guarded
readers for the selected units; `AMBIGUOUS_UNIT_FAMILY` makes the complete ICU
ambiguous inventory independently selectable.

The 6,863-sentence, 550,688-character running-text sample supplied these collision
witnesses for the full inventory:

| Guarded form | Unit | Observed collision |
|---|---|---|
| `in` in German | inch | `2007 in` before a German prepositional phrase, 5 cases |
| `G` | g-force | `iPhone 3G`, 1 case |
| `'`, `"`, and doubled quote forms | arc-minute, arc-second | quotation punctuation after years and numbers |
| `st` | stone | English ordinals such as `21st` and `31st`, 2 cases |
| all point forms | point | ordinary `10 points`, 1 case |
| `F`, `K`, `S`, `H` | farad, kelvin, siemens, henry | a status field, download sizes, a URL query, and `24H` service |
| `/em` | per-em | a URL path, 1 case |
| `mil` outside Nordic languages | Scandinavian mile | Spanish “25 thousand,” 1 case |
| per-part forms | per-part | Spanish `por parte`, 1 case |
| `V` | volt | guarded by the single-letter rule; no collision occurred in this sample |

`A`, `T`, and `W` produced no collision witness in the sampled running text and are
not new selection gains, so they retain their existing behavior. The ordinary
default added zero detections on all 6,863 sampled sentences. Every guarded form
remains explicitly reachable.

## Coverage

### All-locale ICU differential

For all 906 ICU locale identifiers, the differential formatted the value 5 for
each newly selected unit in ICU wide, short, and narrow widths. It found 16,814
newly whole cases and zero losses against the previous selection.

| Unit | Newly whole canonical cases |
|---|---:|
| hertz | 2,675 |
| kilohertz | 2,675 |
| megahertz | 2,675 |
| gigahertz | 2,675 |
| micrometer | 2,673 |
| nanometer | 2,673 |
| volt | 768 |

The six requested sample locales each gained 19-21 canonical cases and lost none.
The smaller voltage count is intentional: single-letter `V` cases are available
only through the guarded type.

### English census

The census contains 45,607 distinct retained measure forms and 1,370,166 weighted
tokens. The ordinary widened default gained 14,812 weighted whole readings and
lost none:

| Selection | Weighted gain | Witnesses |
|---|---:|---|
| frequency family | 11,439 | `50 Hz` (204), `60 Hz` (183), `2.4 GHz` (137), `900 MHz` (111) |
| nanometer | 2,758 | `100 nm` (95), `30 nm` (91), `10 nm` (91) |
| micrometer | 615 | `10 μm` (40) |

Opting into guarded readers adds the 2,162 voltage-symbol gains, including `750 V`
(90), `16V` (89), and `12V` (83). The complete guarded family also exposes 541
stone/ordinal collision readings, so the intentionally permissive guarded census
gain is 17,515 rather than the selected units' 16,974.

## Performance

All final running measurements warmed both gangs on every row, then used five
interleaved repetitions. Russian used five independently constructed interleaved
pairs to keep each probe bounded. Negative small deltas are measurement noise, not
claimed speedups.

| Locale | Rows | p50 main/new | p50 delta | p99 delta | Total delta | Detections main/new |
|---|---:|---:|---:|---:|---:|---:|
| `en_US` | 2,000 | 2.773 / 2.749 ms | -0.9% | -5.3% | -3.0% | 3,440 / 3,440 |
| `de_DE` | 977 | 3.152 / 3.203 ms | +1.6% | +1.2% | +1.0% | 513 / 513 |
| `fr_FR` | 416 | 3.871 / 3.912 ms | +1.1% | +2.9% | +0.8% | 499 / 499 |
| `ja_JP` | 543 | 1.238 / 1.253 ms | +1.2% | -3.6% | +0.7% | 291 / 291 |
| `ru_RU` | 2,000 | 7.335 / 7.336 ms | +0.0% | +0.4% | +0.6% | 1,189 / 1,189 |
| `zh_CN` | 500 | 1.340 / 1.342 ms | +0.1% | +0.7% | +2.2% | 864 / 864 |

The largest median p50 increase is 1.6%, below the 5% target. The original pinned
2,000-row sample was available for the full-inventory rejection trial above but was
removed by its owner before the final subset run. The retained 2,000-row English
running-text set is therefore the final subset's 2,000-row measurement.

Cold construction used seven fresh processes per mode and locale, with alternating
mode order. RSS is the median increase in process maximum RSS after imports.

| Locale | Build main/new | Build delta | RSS main/new | RSS delta |
|---|---:|---:|---:|---:|
| `en_US` | 1.510 / 1.524 s | +0.9% | 64.12 / 64.20 MiB | +0.08 MiB |
| `de_DE` | 0.754 / 0.752 s | -0.2% | 54.86 / 54.97 MiB | +0.11 MiB |
| `fr_FR` | 0.759 / 0.761 s | +0.2% | 51.88 / 52.44 MiB | +0.56 MiB |
| `ja_JP` | 0.755 / 0.759 s | +0.5% | 49.50 / 49.56 MiB | +0.06 MiB |
| `ru_RU` | 1.700 / 1.718 s | +1.1% | 620.94 / 621.22 MiB | +0.28 MiB |
| `zh_CN` | 0.835 / 0.851 s | +1.9% | 50.73 / 50.78 MiB | +0.05 MiB |

## Validation

The branch merged `origin/main` at `d1cdcbbe9cd8312328064013b8265136cebedc50`
after the implementation commits. The resulting merge commit is `e3075f4`.

| Check | Result |
|---|---|
| `ruff check .` | passed |
| `ruff format --check .` | passed, 260 files already formatted |
| `python docs/generate.py --check` | passed, documentation up to date |
| default pytest selection | 4,921 passed, 16 skipped, 3 expected xfails, 108 slow tests deselected; no failures |
| `pytest -m slow` selection | all 108 passed |

The default selection ran as 134 per-file shards. Slow tests ran in bounded node
chunks; two aggregate chunks reached the 120-second probe ceiling, so their 12
nodes were rerun individually and all passed. This preserves the complete pytest
selections while keeping every probe within the required bound.

Commits before this evidence update:

- `a3d0147` — `Widen default unit selection`
- `c895365` — `Document widened unit coverage`
- `e3075f4` — merge `origin/main`
- `26ab4e6` — `Update unit reader contract fixtures`
