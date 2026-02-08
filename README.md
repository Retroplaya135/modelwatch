<div align="center">
  <img src="docs/cover.png" alt="Modelwatch" width="100%">
  <h3>Repeatable snapshots of a changing public model catalog.</h3>
  <p>
    <img alt="Status: version 0.1" src="https://img.shields.io/badge/status-v0.1-6d28d9">
    <img alt="Python 3.11 or newer" src="https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python&logoColor=white">
    <img alt="Runtime: standard library" src="https://img.shields.io/badge/runtime-standard_library-334155">
    <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-0f766e">
  </p>
  <p>
    <a href="#overview">Overview</a> ·
    <a href="#processing-model">Processing model</a> ·
    <a href="#quick-start">Quick start</a> ·
    <a href="#verification">Verification</a> ·
    <a href="#scope-and-limitations">Limitations</a>
  </p>
</div>

## Overview

Modelwatch turns OpenRouter's changing public model catalog into dated, reviewable files. It is intended for documentation, experiments, and engineering notes that need to preserve which zero-priced entries were visible at a particular time instead of relying on a live catalog that may change between runs.

The tool has three jobs:

- fetch the current public catalog and export the entries that match its free-model rules;
- render a saved catalog response without making another network request;
- convert a supported copied-text list into a compact Markdown reference.

Acquisition and rendering are separate on purpose. A response can be captured once, reviewed as source data, and exported repeatedly with a fixed timestamp. That makes a comparison explainable: the committed snapshot records what the upstream catalog said, while the command and timestamp explain how the local representation was produced.

Modelwatch uses no provider credentials and has no runtime dependencies outside the Python standard library. It records catalog claims; it does not benchmark models, send inference requests, or decide whether a model is suitable for a workload.

## Processing model

| Stage | Responsibility |
| --- | --- |
| Acquire | Read a local JSON response or request the public catalog over HTTPS with a bounded response size and timeout. |
| Validate | Require an HTTP success, JSON content type, valid UTF-8 JSON, a top-level object, and a `data` array containing objects. |
| Classify | Include entries whose ID ends in `:free`, or whose prompt and completion prices both parse to zero. |
| Normalize | Retain stable fields for identity, provider, context, description, pricing, architecture, and per-request limits. |
| Order | Sort by provider, model name, and model ID so source order cannot create noisy diffs. |
| Export | Write a timestamped JSON record and a compact Markdown table to the requested directory. |

The fetch path sends an explicit user agent, rejects non-JSON responses, and stops reading after five megabytes. The export path normalizes the timestamp to UTC and uses it in both filenames and content. A caller-supplied timestamp therefore makes the same input produce the same pair of files.

## Implemented capabilities

### Catalog snapshots

The JSON export retains the fields needed for later inspection rather than flattening the response into a display-only table. Each model may include its ID, display name, inferred provider, description, context length, prompt/completion/image/request prices, modality information, tokenizer, instruction type, and per-request limits.

The Markdown export is intentionally smaller. It shows provider, model name, context length, and modality so a snapshot remains readable in a pull request. Markdown cells are escaped before rendering.

### Free-entry classification

An entry is selected when either of these rules is true:

1. its model ID ends in `:free`; or
2. both prompt and completion price values are present and numerically equal to zero.

String and numeric zero values are treated equivalently. Boolean and malformed values are not. The `:free` suffix is accepted independently of the price object because that is an upstream catalog convention, not a billing guarantee.

### Copied-text cleanup

The cleaner accepts one model per line with an optional `(free) <size> tokens` marker. It can retain an announced removal date, numbered category labels, and the remaining description while stripping copied bullet markers and normalizing whitespace. The grammar is intentionally specific; unsupported page layouts should fail visibly rather than be guessed into plausible output.

## Quick start

Modelwatch requires Python 3.11 or newer. Install it from a checkout; the repository does not imply a package-index release.

```bash
git clone https://github.com/Retroplaya135/modelwatch.git
cd modelwatch
python -m pip install .

modelwatch export tests/fixtures/catalog.json \
  --out-dir snapshots \
  --generated-at 2026-01-01T00:00:00Z

modelwatch fetch --out-dir snapshots
modelwatch clean catalog.txt catalog.md
```

`export` expects an input object containing a `data` array, as shown in [the synthetic fixture](tests/fixtures/catalog.json). `fetch` reads the current public endpoint directly. `clean` reads plain text and writes a Markdown list in the supported format.

## Practical usage

Use local export when reproducibility matters. Save the unmodified catalog response, inspect it, then pass an explicit `--generated-at` value. Reusing that source file and timestamp replaces the same output names with byte-stable content. If the timestamp is omitted, Modelwatch records the current UTC time, making the snapshot unique to that run.

The JSON and Markdown files serve different review needs. Keep the Markdown version when the goal is a human-readable inventory. Keep the JSON version when downstream work needs architecture, detailed pricing fields, descriptions, or request-limit metadata. Neither file should contain provider credentials or private responses.

Treat changes as upstream observations. A model appearing in one snapshot and disappearing in the next says that the catalog changed; it does not establish why, whether access was account-specific, or whether the entry was usable throughout the interval. For billing-sensitive work, inspect the exported pricing fields and current provider terms at the point of use.

Existing output files are overwritten when their generated timestamp produces the same filename. Choose a new timestamp to preserve another observation, or place separate runs in different directories.

## Verification

```bash
python -m unittest discover -s tests -v
```

The current suite has seven focused tests covering equivalent zero-price forms, response-contract validation, deterministic export and Markdown escaping, copied-text parsing, empty-input behavior, local export without a network request, and CLI command behavior. Network access is replaced with synthetic responses so the suite remains stable and credential-free.

The tests do not call the live catalog. A successful test run proves the local classification, validation, rendering, and command contracts against fixtures; it does not prove that the upstream endpoint is reachable or unchanged.

## Repository map

| Path | Responsibility |
| --- | --- |
| `src/modelwatch/catalog.py` | Fetching, validation, free-entry classification, normalization, sorting, and export. |
| `src/modelwatch/cleaner.py` | Parsing and rendering the supported copied-text format. |
| `src/modelwatch/cli.py` | Argument parsing and the `fetch`, `export`, and `clean` commands. |
| `src/modelwatch/__main__.py` | `python -m modelwatch` entry point. |
| `tests/fixtures/catalog.json` | Small synthetic catalog used by command and export tests. |
| `tests/` | Catalog, cleaner, and CLI verification. |

## Scope and limitations

Modelwatch currently targets OpenRouter's public catalog schema and endpoint. It does not provide a generic provider adapter, authenticated catalog access, inference, health checks, quality evaluation, routing analysis, or cost tracking. It does not verify advertised context windows, practical rate limits, regional availability, or actual charges.

The zero-price rules are descriptive, not contractual. A `:free` identifier or zero-valued catalog fields may still be subject to provider policies, quotas, routing changes, or removal. Snapshots should never be used as the only control for spend-sensitive automation.

The copied-text cleaner is not an HTML scraper and does not attempt to understand arbitrary pasted content. The fetcher validates structure but preserves upstream descriptions as external text; consumers should escape them for their own output context. Export and clean commands write to caller-selected paths and may replace existing files.

## Documentation

- [Synthetic catalog fixture](tests/fixtures/catalog.json)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Contributing, security, and license

Keep network calls out of tests, use synthetic catalog objects, and assert output changes when modifying filenames or Markdown rendering. Classification changes need fixtures for both accepted and rejected values. See [CONTRIBUTING.md](CONTRIBUTING.md) before changing the catalog contract.

Report response-validation, output-path, or rendering vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not include API keys, account data, or private provider payloads in issues.

Modelwatch is available under the [MIT License](LICENSE).
