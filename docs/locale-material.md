# Locale material

Locale material is data you supply at runtime for a locale where ICU lacks a capability. This page is its specification: format `icukit-locale-material` version 1, versioned with icukit. icukit loads material only when you pass it, refuses it unless every witness it carries passes, adds its readers beside ICU's without replacing them, ships none, and labels it `user` in every availability report. Version 1 has one kind, `rbnf-spellout`: ICU rule-based number format rule text, exactly as ICU reads it. This format is a draft and not yet stable.

This release provides the loader and the reader; joining gangs and availability reports are separate changes.

## Version 1 envelope

A file is one UTF-8 JSON object. Its required keys are `schema_version`, `kind`,
`locale`, `rules`, `provenance`, and `witnesses`; `near_misses` is optional, and no
other key is allowed. `schema_version` is the integer `1`. `kind` is
`rbnf-spellout`. `locale` is a non-root canonical ICU base locale name without
keywords. `rules` is a non-empty array of strings, joined with `"\n"` before ICU
reads it.

`provenance` has a required non-empty string `source`, and may have string
`license`, `retrieved`, and `note` fields. It has no other fields. Provenance is
reported with the loaded material but is excluded from the material object's Python
hash.

Each witness uses only `id`, `text`, `text_sha256`, `locale`, `labels`, and
`x-icukit`; `id`, `text`, and `locale` are required. IDs match
`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$` and are unique across witnesses and near
misses. `text` is raw and is never normalized. Optional `text_sha256` is the
lowercase SHA-256 hexadecimal digest of its UTF-8 bytes. A witness locale equals the
material locale or is its descendant.

`labels` is an array of `{start, end, class}` objects with optional `text` and
`scheme`. Offsets are Unicode code-point indices, half-open `[start, end)`, with
`0 <= start < end <= len(text)`. An echoed `text` must equal that slice. `class` is
non-empty; `scheme`, when present, is `icukit-type`.

`x-icukit` contains exactly `values`, an array of `{start, end, type, value}` objects
with optional echoed `text`. Extents follow the same rules and must equal a label
extent whose `class` is the value's `type`. For spell-out, `value` is
`{"kind":"number","decimal":"<integer string>","currency":null}`. Label classes
and value types must name readers proved by this material. A witness with neither a
label nor a value witnesses nothing and is refused. A witness record can be lifted
into a richer internal corpus record by adding keys only; its shared field names and
semantics do not change.

A label-only witness certifies that its reader finds a reading at the declared extent
and type; it does not certify a particular value. The cardinal rule set must have at
least one value witness, which certifies both exact formatting and recovered value.

`near_misses` is an array of objects having exactly `id`, `text`, `locale`, and
`type`. Its ID and locale follow the witness rules. The type must name one of this
material's proved readers. A near miss fails when its entire text is read; a partial
reading is allowed.

## Readers and rule sets

The public rule set whose name contains `spellout` and `cardinal`, but none of
`ordinal`, `year`, or `verbose`, always yields the `number:spellout` reader. Another
public rule set whose name contains `cardinal`, `ordinal`, or `year` yields a reader
only when a witness names its type. Its type is `number:spellout:<name>`, where
`<name>` is the rule-set name without its leading `%` and `spellout-`; for example,
`%spellout-ordinal` yields `number:spellout:ordinal`.
Two selected public rule sets may not yield the same reader type; such material is
refused as `AMBIGUOUS_RULESET`, with both rule-set names in the refusal.

The default spell-out reader deliberately does not read a lone word for 0 through 9,
because those words are often ambiguous in running text, and surrounding words do not
change that. A one-word reading of 0 through 9 therefore cannot be a witness; use a
value written with more than one word, or 10 or above.

## Complete synthetic example

This complete example is the synthetic `qaa` conformance fixture. It describes no
language.

```json
{
  "schema_version": 1,
  "kind": "rbnf-spellout",
  "locale": "qaa",
  "rules": [
    "%spellout-cardinal:",
    "-x: minus >>;",
    "0: zero; 1: one; 2: two; 3: three; 4: four; 5: five; 6: six; 7: seven; 8: eight; 9: nine;",
    "10: ten; 11: eleven; 12: twelve; 13: thirteen; 14: fourteen; 15: fifteen; 16: sixteen; 17: seventeen; 18: eighteen; 19: nineteen;",
    "20: twenty[->>]; 30: thirty[->>]; 40: forty[->>]; 50: fifty[->>]; 60: sixty[->>]; 70: seventy[->>]; 80: eighty[->>]; 90: ninety[->>];",
    "100: << hundred[ >>];",
    "1000: << thousand[ >>];",
    "1000000: << million[ >>];",
    "1000000000: << billion[ >>];",
    "1000000000000: << trillion[ >>];",
    "1000000000000000: =#,##0=;"
  ],
  "provenance": {
    "source": "icukit test fixture",
    "license": "CC0-1.0",
    "note": "Synthetic conformance material: English-shaped rules under the private-use language code qaa. Not a description of any language."
  },
  "witnesses": [
    {
      "id": "qaa-w1",
      "text": "one hundred forty-five goats",
      "text_sha256": "ddd14c7c9d7316d5334ff2e0bcab1ca5b9114abcb6c0103bc6254cdaa24a629c",
      "locale": "qaa",
      "labels": [
        {
          "start": 0,
          "end": 22,
          "text": "one hundred forty-five",
          "class": "number:spellout",
          "scheme": "icukit-type"
        }
      ],
      "x-icukit": {
        "values": [
          {
            "start": 0,
            "end": 22,
            "type": "number:spellout",
            "value": {
              "kind": "number",
              "decimal": "145",
              "currency": null
            }
          }
        ]
      }
    },
    {
      "id": "qaa-w2",
      "text": "twenty-three",
      "locale": "qaa",
      "labels": [
        {
          "start": 0,
          "end": 12,
          "class": "number:spellout",
          "scheme": "icukit-type"
        }
      ],
      "x-icukit": {
        "values": [
          {
            "start": 0,
            "end": 12,
            "type": "number:spellout",
            "value": {
              "kind": "number",
              "decimal": "23",
              "currency": null
            }
          }
        ]
      }
    }
  ],
  "near_misses": [
    {
      "id": "qaa-n1",
      "text": "hundred forty-five",
      "locale": "qaa",
      "type": "number:spellout"
    }
  ]
}
```

## Loading material

Pass a path or a parsed mapping to `load_locale_material`. A failed load returns no
partial material; inspect every refusal to fix the file.

```python
from icukit.material import MaterialLoadError, load_locale_material

try:
    material = load_locale_material("qaa-spellout.json")
except MaterialLoadError as error:
    for refusal in error.refusals:
        print(refusal.code, refusal.detail)
else:
    print(material.digest, material.rulesets)
```

## Using material

Pass loaded material explicitly when building a gang. Applicable material readers are
added beside ICU's readers; they do not replace them.

```python
from icukit.engine import generated_detectors
from icukit.material import load_locale_material

m = load_locale_material("qaa-spellout.json")
detectors = generated_detectors("qaa", material=[m])
```

The command-line equivalent accepts one or more `--material` paths:

```console
ik detect --locale qaa --material qaa-spellout.json -t 'one hundred forty-five goats'
```

## Validation and identity

Loading is transactional. Duplicate JSON keys and non-finite numbers are refused.
The complete envelope is checked before semantic checks begin. ICU then compiles the
rules; a public cardinal spell-out rule set must exist and must format 0 through 1000
to 1001 distinct case-folded strings. Every declared value must format to its exact
witness extent, and the material reader must find every label and value in the whole
witness text at that exact extent and type (and recover the declared value). Formatting
and reading use each witness's declared locale, including descendant locales. Every near
miss is read in its declared locale as well. Any failure refuses the whole file, and the
exception lists every refusal found in that phase.

The refusal codes are `INVALID_JSON`, `INVALID_KEY`, `INVALID_SCHEMA_VERSION`,
`INVALID_KIND`, `INVALID_LOCALE`, `INVALID_RULES`, `INVALID_PROVENANCE`,
`INVALID_WITNESS`, `INVALID_NEAR_MISS`, `RBNF_SYNTAX`,
`NO_CARDINAL_RULESET`, `AMBIGUOUS_RULESET`, `NOT_INJECTIVE`, `NO_WITNESS`,
`WITNESS_FORMAT_FAILED`, `WITNESS_READ_FAILED`, and `NEAR_MISS_READ`.

Identity is the content digest:

```python
(
    "sha256:"
    + sha256(
        json.dumps(
            parsed_object,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
)
```

Whitespace and JSON object-key order therefore do not affect identity; any content
change does. The format's locale applicability rule follows fallback downward only:
material for `yo` applies to `yo`, `yo_NG`, and `yo_BJ`, while material for `yo_NG`
does not apply to `yo`. Future gang integration is specified to add material readers
beside ICU's readers, and future availability integration is specified to label
application material as `user`; neither integration is part of this release. No
material is bundled in the wheel or source distribution. Version 1 accepts no
pronunciation material.
