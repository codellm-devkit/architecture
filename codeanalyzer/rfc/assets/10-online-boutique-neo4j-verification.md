# Online Boutique: live Neo4j namespace verification

Verified 2026-10-31. **PASS for the tested namespace, URI resolution and canonical deduplication workflow, after fixing three defects found by this live run.** All service reads used the SDK Neo4j backends; no SDK JSON/local backend was used.

## Clone and database

- Upstream: [GoogleCloudPlatform/microservices-demo](https://github.com/GoogleCloudPlatform/microservices-demo/tree/c7cb6d5bfd6ea3aed768634ebbcb98cb7a523712). Cloned over SSH as `git@github.com:GoogleCloudPlatform/microservices-demo.git` into `/Users/rkrsn/workspace/codellm-devkit/online-boutique`.
- Source revision: `c7cb6d5bfd6ea3aed768634ebbcb98cb7a523712`. All supported services were projected into **one** Neo4j Community 5.26.0 database, `neo4j`, under namespace `online-boutique`.
- Bolt: `bolt://127.0.0.1:17687`. The temporary instance is running, binds only to loopback, and has authentication disabled. The SDK configs use the placeholder defaults `neo4j`/`neo4j`; this is a fresh isolated test instance, not an existing database.
- Installation/data/logs: `/private/tmp/online-boutique-namespace-check/neo4j-community-5.26.0`. HTTP is disabled. Neo4j was run directly without Docker, with a verified official tarball SHA-256 `ad8ac3398606145502b8f489530bbd39333707ae4668156af16b6086b5b037d7`.
- The main namespace owns **67,898 nodes** and **217,873 outgoing relationships**. The whole database has **69,246 nodes** and **220,842 relationships**, including shared package nodes and two namespace-control copies of currencyservice. There are 11 real service scopes plus those two controls.

## Supported services

C# `cartservice` was skipped. JavaScript is handled by the TypeScript/JavaScript analyzer. Generated protobuf source is included where discovered after builds.

| Service | Analyzer language | SDK modules | SDK declarations with canonical IDs | Result |
|---|---|---:|---:|---|
| currencyservice | JavaScript | 2 | 15 | Pass |
| paymentservice | JavaScript | 4 | 32 | Pass |
| checkoutservice | go | 4 | 470 | Pass |
| frontend | go | 10 | 522 | Pass |
| productcatalogservice | go | 5 | 457 | Pass |
| shippingservice | go | 5 | 455 | Pass |
| emailservice | python | 5 | 97 | Pass |
| loadgenerator | python | 1 | 12 | Pass |
| recommendationservice | python | 5 | 88 | Pass |
| shoppingassistantservice | python | 1 | 3 | Pass |
| adservice | java | 12 | 3154 | Pass |

Every SDK view's module IDs exactly equal the modules linked from its corresponding live application anchor. Reconstructed declaration IDs are nonempty and retain that service's full canonical root. SDK attachment/read checks left database node and relationship counts unchanged.

## Checks performed against the database

- All 11 anchors have integer `identity_version: 2`, raw `identity_namespace: online-boutique`, and the expected application name and canonical root.
- Currency `server.js:28` returns module scope, no callable and no callable/body node ID. Payment `server.js:28` returns its own `HipsterShopServer.constructor`. Currency line 92 resolves to its own `_loadProto`. Reversing backend construction/order preserves these results.
- Another service's full URI is rejected before path normalization. Same application name `currencyservice` in `namespace-verification-control` stays isolated. Omitting namespace emits and reads `can://currencyservice/currencyservice` correctly.
- A real database `UNWIND [currency ID, payment ID, currency ID]` plus canonical-ID matching and `DISTINCT` yields exactly two modules. A finding whose module ID is currency's joins to exactly currency's module. No private integration ingestion code was substituted into this assertion.
- Zero duplicate canonical IDs and zero canonical relationships crossing service roots in the main namespace. Shared `pkg:` nodes are intentionally outside that cross-service assertion.
- Payment constructor's two calls to the same `loadProto` target at lines 28 and 29 retain two distinct canonical body-node IDs: `.../constructor@28:20` and `.../constructor@29:15`.
- Eager regeneration of currencyservice leaves node and outgoing-relationship counts in the other **12 scopes** unchanged, including the other ten real services and both namespace controls.

## Three defects found and fixed

1. TS/JS graph projection parsed the former URI layout and wrote `javascript/server.js` as the module key. The SDK consequently missed a stored `server.js`. Projection now takes the authoritative relative key directly from `symbol_table`.
2. TS/JS class rows lacked private module ownership. Eager per-module reconciliation deleted those shared-upserted class nodes before recreating their method edges. Types now carry their owning module, preserving the class and its edges.
3. Python SDK graph reconstruction discarded existing IDs on modules, classes and callables. It now copies their actual stored canonical IDs unchanged.

Fixes are committed and independently reviewed in [TS/JS PR #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220) (`6d80997`) and [SDK PR #440](https://github.com/codellm-devkit/python-sdk/pull/440) (`928ce57`). Regression tests were observed failing before the changes and passing afterwards.

## Environment and semantic analysis

- Node 24.22.2 supplies npm for JavaScript dependency materialization (`npm ci --ignore-scripts`); the first run without npm continued with partial types. Final projections used installed dependencies.
- Go 1.26.10 with `GOTOOLCHAIN=local`: all four Go services passed `--strict` full-depth live projection. The source's suggested Go 1.27.1 toolchain initially produced partial-types/SSA warnings with this analyzer; aligning the toolchain removed those warnings. This does not modify the source go.mod files.
- Java 21.0.13 and Gradle 8.14.5: `bash ./gradlew classes --no-daemon` completed successfully, followed by strict schema-v2 full-depth live projection. The upstream Gradle wrapper is checked in without execute permission; invoking it through bash and putting the downloaded Gradle distribution on PATH avoids changing the tracked wrapper mode. The initial graph was degraded; the final strict graph was regenerated after the build setup.
- Neo4j 5.26.0 runs on the existing Java 17 runtime ([official compatibility table](https://neo4j.com/docs/operations-manual/current/installation/requirements/)). No application microservices were deployed or business RPCs exercised; this verifies the analyzer/graph/SDK workflow.

## Automated verification

- TS/JS namespace and Neo4j suites: **70 passed, 23 skipped**, 11,368 assertions. Typecheck and native build passed.
- SDK focused Python identity/scope checks: **88 passed**.
- Full available SDK suite after fixes: **1,952 passed, 422 skipped, 10 warnings**, **85.34% coverage**, 79.86 seconds. Existing slow Java-native E2E gate retained. These skips are not claimed as passing Docker tests; the custom live database checks above ran separately.
- Read-only live verifier: all 11 SDK views, canonical module equality, positive/negative source lookup, reverse order, joins, duplicate IDs, cross-service edges and read-only counts passed. Control verifier: two namespace cases, foreign namespace rejection, distinct real call sites and other-scope preservation passed.

## Reproduce or inspect

```sh
source /private/tmp/online-boutique-namespace-check/env.sh
python-sdk/.venv/bin/python architecture/codeanalyzer/rfc/assets/10-online-boutique-neo4j-check.py
```

The standalone [live verifier](10-online-boutique-neo4j-check.py) reads the database only. It accepts `NEO4J_URI`, `NEO4J_DATABASE`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and optional `ONLINE_BOUTIQUE_RESULT` for its verification-results output. That output is test evidence, not an analyzer JSON input.

A projection has this shape (omit analysis-level selectors for full-depth graph emission):

```sh
codeanalyzer-typescript/dist/cants -i online-boutique/src/currencyservice \
  -o /private/tmp/online-boutique-namespace-check/output/currencyservice \
  --namespace online-boutique --app-name currencyservice --emit neo4j \
  --neo4j-uri "$NEO4J_URI" --neo4j-database neo4j --eager

GOTOOLCHAIN=local /private/tmp/namespace-toolchains/cango \
  -i online-boutique/src/checkoutservice --namespace online-boutique \
  --app-name checkoutservice --emit neo4j --strict \
  --neo4j-uri "$NEO4J_URI" --neo4j-database neo4j

python-sdk/.venv/bin/canpy --no-ray -i online-boutique/src/recommendationservice \
  --namespace online-boutique --app-name recommendationservice --emit neo4j \
  --neo4j-uri "$NEO4J_URI" --neo4j-database neo4j

"$JAVA_HOME/bin/java" -Xmx2g -jar codeanalyzer-java/build/libs/codeanalyzer-3.3.4.jar \
  --schema v2 --strict -i "$PWD/online-boutique/src/adservice" \
  -f "$PWD/online-boutique/src/adservice" --namespace online-boutique \
  --app-name adservice --emit neo4j --neo4j-uri "$NEO4J_URI" --neo4j-database neo4j
```

Raw logs, per-service projection commands, native artifact manifest and before/after control counts are under `/private/tmp/online-boutique-namespace-check`; a [compact evidence archive](10-online-boutique-neo4j-evidence.zip) accompanies this report. Analyzer intermediates can exist on disk; all validation and SDK reads above use Neo4j.

## Source provenance

| Repository | Tested HEAD |
|---|---|
| online-boutique | `c7cb6d5bfd6ea3aed768634ebbcb98cb7a523712` |
| codeanalyzer-python | `b6599662ee17947bedc4231fa1b0875c2d172999` |
| codeanalyzer-typescript | `6d8099711049f0c415ec6e1656b273d06bf73f38` |
| codeanalyzer-java | `89b95237ee2623dfdf84ddd6e71f07ab2472699b` |
| codeanalyzer-go | `f66a589c1e2f4dc0ed373f4811a0dbe8f22b3d13` |
| python-sdk | `928ce570038ff6000b92f928287a2641bac5bba6` |

TS/JS rebuilt binary SHA-256: `62d358dfd4aac13d9c015c67335c586348c907a6f405a7229d5c5a4c342c1485`. The other native artifacts remain those recorded in the earlier [namespace verification](10-namespace-verification.md); Python producer and SDK run directly from their editable source checkouts.

## Remaining limits

- SDK PR #440 remains Draft until compatible producer releases exist, its published pins/lock are updated, and installed-package validation passes. This run uses the reviewed local builds, not the old published pins.
- Private integration scanner routing/index/finding-join code was not available. The SDK and actual database equality-join tests passed; downstream code still has to retain those canonical IDs.
- A currency-only fresh TS/JS database initially fails the SDK relationship fingerprint because it contains no `TS_HAS_METHOD`. This 11-service database contains methods and passes. General sparse-graph attachment remains a separate known limitation; these results do not claim every possible smaller graph attaches.
- The module-scope currency result includes `module_source_unavailable`, reflecting existing graph-to-model source hydration limits; it does not return another service's callable. Namespace and source-position ownership assertions above passed.
- The graph is retained for inspection in a temporary directory; this is not a production deployment or a release.


## Published release follow-up

The coordinated releases are now published: SDK2.1.0 with Python/TypeScript1.7.0, Java3.4.0 and Go0.3.0. The earlier Draft/release-blocked statements above record the pre-release stage; that release gate is complete. See the [release record](10-namespace-releases.md) for published-wheel validation and final test evidence. Downstream integration adoption and the documented sparse-graph/source-hydration limits remain separate.
