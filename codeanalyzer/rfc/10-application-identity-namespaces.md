---
status: accepted
date: 2026-10-31
related-adrs:
  - ../adrs/10-application-identity-namespaces.md
related-rfcs: []
implementation:
  - https://github.com/codellm-devkit/codeanalyzer-java/pull/275
  - https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220
  - https://github.com/codellm-devkit/codeanalyzer-python/pull/235
  - https://github.com/codellm-devkit/codeanalyzer-go/pull/41
  - https://github.com/codellm-devkit/python-sdk/pull/440
---

# 10: Application identity namespaces and scoped resolution

## Summary

This accepted RFC records the released first iteration of [ADR-codeanalyzer-10](../adrs/10-application-identity-namespaces.md): add `--namespace`, update application-owned URI construction and resolution across producers and consumers, and fix deduplication so same-named modules in different services remain distinct.

Ordinary SDK operations select one namespace, then one analyzed application within it, and retain its language view. The canonical application root is `can://<namespace>/<application_name>`.

The implementation repurposed and extended the existing workspace-root work in [Java PR #275](https://github.com/codellm-devkit/codeanalyzer-java/pull/275), [TypeScript/JavaScript PR #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220), and [Python PR #235](https://github.com/codellm-devkit/codeanalyzer-python/pull/235). The companion SDK work is merged in [#440](https://github.com/codellm-devkit/python-sdk/pull/440) and published as **CLDK 2.1.0**; Go is merged in [#41](https://github.com/codellm-devkit/codeanalyzer-go/pull/41). Python/TypeScript **1.7.0**, Java **3.4.0**, and Go **0.3.0** are published. The [release record](assets/10-namespace-releases.md) contains package and verification evidence. Downstream application adoption is tracked separately from completed SDK support.

## Motivation and scope

Consider the Online Boutique microservice application. Its overall application identity is the namespace `online-boutique`. Two of its services, currencyservice and paymentservice, are separate analyzed applications within that namespace:

```text
online-boutique/
  src/
    currencyservice/
      server.js
    paymentservice/
      server.js
```

The analyzer runs separately with `src/currencyservice` and `src/paymentservice` as input roots. Both runs produce the local file key `server.js`, because that key is relative to the selected service directory. Before the namespace change, the module URIs included the service name and were already distinct:

| Analyzed application | Legacy module URI | Local `file_key` / module path |
|---|---|---|
| currencyservice | `can://currencyservice/javascript/server.js` | `server.js` |
| paymentservice | `can://paymentservice/javascript/server.js` | `server.js` |

The collision appears when a consumer keeps only the last column. The SDK's pre-fix `resolve_module_key` helper accepted a path ending in a known local key. Given the scanner path `currencyservice/server.js`, both backends find the suffix `/server.js` and resolve it to their own `server.js`. The helper normalizes a path within an already selected application; it does not establish which service owns the scanner path.

A caller that asks each backend in turn can therefore return code from the wrong service. This fixture makes the failure visible:

| Scanner position | currencyservice's `server.js` | paymentservice's `server.js` |
|---|---|---|
| `src/currencyservice/server.js:28` | Line 28 is at module scope. Its first callable, `_loadProto`, starts at line 91. | Line 28 falls inside `HipsterShopServer.constructor`, whose range is lines 24–34. |

The incorrect resolution is:

```text
Scanner: src/currencyservice/server.js, line 28
  -> ask paymentservice first
  -> suffix match selects paymentservice's local key server.js
  -> locate line 28 returns paymentservice's constructor
  -> attach the currencyservice finding to the wrong callable
```

The required resolution is:

```text
Scanner: src/currencyservice/server.js, line 28
  -> declared source root selects online-boutique/currencyservice
  -> exact local key server.js selects that service's canonical module ID
  -> line 28 has no containing callable in this module
  -> return module scope / no callable; do not try paymentservice
```

Misattribution can leave downstream analysis without a valid entry point or produce an empty catalog. It also affects indexes and joins: deduplicating both modules under `server.js` hides the two owners, and joining a finding by that filename can attach it to both modules. Keeping the full canonical module ID prevents that ownership loss.

The public [SDK issue #435](https://github.com/codellm-devkit/python-sdk/issues/435) records this reproduction and expected behavior.

The original workspace-root PRs supplied reusable input validation, path handling, emission changes and tests. Their workspace-relative re-keying was replaced by explicit namespace/application identity. The released analyzers have no `--workspace-root` option or compatibility alias; file keys remain relative to the selected application input root. A namespace segment alone cannot repair a lookup or join that discards the service owner.

### First-iteration scope

The delivery has three parts:

1. Add the namespace input to the language analyzers and SDK configuration, using the ADR's defaults.
2. Update every application-owned URI producer and consumer to retain the namespace/application root through emission, lookup, analysis endpoints, graph queries, caches, and joins.
3. Deduplicate entities by their full canonical IDs, preserving distinct services even when relative paths and signatures match.

Keep existing language-specific suffixes, file keys, schemas, and analysis APIs except where adding namespace and preserving canonical references requires a change. This is the first delivery of the broader ADR. Package-release/occurrence modeling, a new symbol/configuration/external suffix grammar, producer lifecycle redesign, new source-mapping APIs, and namespace-wide search are follow-up work. Ordinary requests remain bound to one application; omitting an application must not trigger a broader search.

## Implemented first-iteration design

### Interfaces and identity

#### 1. Add the namespace input

Each analyzer adds optional `--namespace` alongside its existing `--app-name`. Keep the existing input-root argument and its language-specific spelling.

```text
application_name = supplied app-name, otherwise basename(selected input root)
namespace        = supplied namespace, otherwise resolved application_name
application_id   = can://E(namespace)/E(application_name)
```

`E` percent-encodes the UTF-8 bytes outside ASCII letters, digits, `-`, `.`, `_`, and `~`, using uppercase hex. Inputs are raw strings, not pre-escaped URI components. Names are case-sensitive; reject empty/whitespace-only values, control characters, unpaired Unicode surrogates, `/`, `\`, and the complete names `.` and `..`. Do not trim or case-fold names. Each accepted input occupies one URI segment and distinct accepted pairs must produce distinct roots.

Both root segments remain present, even when equal:

| Inputs | Application root |
|---|---|
| Root `inventory`, no identity inputs | `can://inventory/inventory` |
| Root `inventory`, app-name `catalog` | `can://catalog/catalog` |
| Namespace `online-boutique`, app-name `currencyservice` | `can://online-boutique/currencyservice` |
| Namespace `online-boutique`, root `paymentservice` | `can://online-boutique/paymentservice` |

CLDK 2.1.0 supports optional `namespace` to `CodeAnalyzerConfig`, its language subclasses, and `Neo4jConnectionConfig`. Local analyzer configuration must also carry an explicit `application_name` when overriding the project-root default; Neo4j configuration already has that selector. Resolve the pair once and forward the same values to local analyzer invocation and graph readers. Graph attachment without a project root requires an application name.

```python
currency = CLDK.typescript(
    backend=Neo4jConnectionConfig(
        uri="bolt://localhost:7688",
        namespace="online-boutique",
        application_name="currencyservice",
    )
)
```

The TypeScript facade retains its existing JavaScript/TypeScript view. A producer name does not replace a module's language: `server.js` remains JavaScript. Other facades retain their current language views.

#### 2. Update application-owned URIs everywhere

Change the common application-ID helper in each producer from `can://<application_name>` to `can://<namespace>/<application_name>`. Derive every application-owned ID from that resolved root. Consumers use the same root rather than reconstructing the old form independently.

| Identity family | First-iteration rule |
|---|---|
| Application anchor | Use the new two-segment root. |
| Modules, types, callables, fields | Place the existing language/file/symbol suffix below the new root. |
| Body nodes and parameters | Derive from the updated callable/owner ID using the existing local-key grammar. |
| Artifacts and configuration keys | Qualify the existing artifact/key IDs with the new root. |
| External symbols | Qualify existing application-owned external IDs and references with the new root. |
| Call/data-flow/taint edges and embedded references | Use the updated endpoint IDs; never retain a legacy root inside a newly emitted record. |

For example:

```text
Before:
  can://currencyservice/javascript/server.js
  can://paymentservice/javascript/server.js

After:
  can://online-boutique/currencyservice/javascript/server.js
  can://online-boutique/paymentservice/javascript/server.js
```

The relative file key remains `server.js` in each service. Selecting a namespace does not change the analyzer input boundary or prepend a repository path to the file key. Reuse the existing PRs' path validation and emission coverage without making their workspace-relative re-keying the identity mechanism. No additional root argument is required by this iteration.

`pkg:` package identities are outside this application-root change. Existing suffix-level semantic collisions within one application are separate follow-up work; adding a namespace does not claim to resolve them.

Inventory and update both construction and resolution sites:

- CLI/in-process options, ID helpers, schema validators, and JSON/Cypher/Bolt emission.
- Application-anchor lookup, descendant prefixes, module/symbol lookup, and reference reconstruction in every SDK backend.
- Call, data-flow, and taint endpoints; artifact/configuration/external references; graph loaders and finding bridges.
- Cache identity, persisted indexes, and helpers that currently assume `can://<application_name>` or fixed slash positions.

Use exact anchor equality and a trailing-slash descendant prefix (`<application_id>/`) so similarly named applications cannot overlap. Treat entity IDs as opaque handles; preserve the known owner and file key instead of guessing them from a filename tail.

#### 3. Resolve within the selected namespace and application

A full URI must belong to the selected namespace/application and supported language view. Reject a conflicting URI; do not strip its prefix and retry its local suffix.

Relative file keys resolve only inside that binding. Normalize paths within the declared application boundary and look up the exact key. For scanner paths, the integration uses its existing service/root association to select the SDK binding and derive the application-relative key. It must not ask every backend and accept the first callable.

| Input and binding | Required result |
|---|---|
| `server.js`, bound to `online-boutique/currencyservice` | Resolve only currencyservice's module. |
| Paymentservice's full module URI, bound to currencyservice | Report a scope conflict. |
| `src/currencyservice/server.js`, with a known currencyservice source root | Route to currencyservice, then resolve its local key `server.js`. |
| A scanner position whose owner cannot be established | Report missing or ambiguous ownership; do not guess from a suffix. |

Scope checking precedes local path normalization. An arbitrary service-prefixed path cannot become another service's local key merely because it ends in `/server.js`. Absolute paths require an established source root; they do not authorize unrestricted suffix matching.

For the line-28 example, currencyservice lookup returns its module-scope/no-callable result. Paymentservice's constructor remains a separate entity and is never substituted. Preserve existing locate result/exception conventions while reporting ownership conflicts clearly.

### Schema and invariants

#### 4. Fix deduplication and joins

Use the full canonical entity ID as the deduplication key at every boundary where records from multiple services or namespaces can meet. A filename, normalized path, or signature is a secondary lookup key, not a global identity.

```text
Wrong combined index:
  server.js -> one record (the other service is lost)

Required combined index:
  can://online-boutique/currencyservice/javascript/server.js -> currency module
  can://online-boutique/paymentservice/javascript/server.js  -> payment module
```

Repeated rows for the same canonical module ID collapse to one module. Two canonical IDs with the same file key remain two modules. An application-local map may still use relative keys after its binding is established; a combined map must use canonical IDs or retain the complete namespace/application/language/key tuple.

Graph queries retain the ID before applying `DISTINCT`. For example, module enumeration must return both identity and display key:

```cypher
MATCH (m)
WHERE m.id STARTS WITH $application_prefix
  AND m.file_key IS NOT NULL
RETURN DISTINCT m.id AS module_id, m.file_key AS file_key
```

Here `$application_prefix` is the resolved application root plus `/`; the concrete backend also retains its module label and language filters. `RETURN DISTINCT file_key` loses ownership and must not feed a combined index or an ambiguity check. Local and Neo4j reconstruction must use the same identity key.

Secondary indexes map a display key to a collection of canonical IDs. They must not overwrite one owner with another. An ownership check evaluates the distinct candidate IDs, rather than first collapsing them to one filename.

Finding-to-module/callable joins compare resolved canonical IDs by equality. Call/data-flow/taint node deduplication follows the same rule. Edge deduplication retains canonical source and destination IDs, relationship kind, and the existing call-site/context discriminator where applicable; two real call sites or distinct evidence records must not collapse just because their endpoints match.

#### 5. Minimal metadata and cache changes

Retain resolved namespace and application name separately in existing output metadata and application-anchor records. Use `identity_namespace` where a flat `namespace` field already has a configuration/domain meaning. Canonical entity IDs and references carry the owning scope; this iteration does not require a new universal envelope or fields repeated on every record.

Integer `identity_version: 2` is required on the existing envelopes and application anchors; raw `application_name` and `identity_namespace` are retained on applications. Existing `schema_version: "2.0.0"` is unchanged. SDK readers reject incompatible legacy outputs clearly. Do not infer compatibility from slash count. Reader attachment remains read-only.

Add resolved namespace/application to cache identity and validate cached output scope before reuse. A scope change requires regenerating every stamped ID and embedded reference. Existing producer/version/language/source/options cache distinctions remain in place. Prefix-based cleanup must use the selected application root and retain existing sibling-language/shared-record protections.

## Alternatives

| Alternative | Reason not selected |
|---|---|
| Add `--namespace` only to emission | Leaves SDK lookup, old prefix queries, deduplication, and joins inconsistent with emitted IDs. |
| Make repository-relative filenames the identity | Path shape alone does not retain namespace/application ownership. Keep existing file keys within an explicit binding. |
| Deduplicate by filename or signature | Merges distinct services and hides ambiguity even when their URIs differ. |
| Include all remaining ADR work in this delivery | Package modeling, suffix redesign, lifecycle machinery, and namespace-wide search expand the iteration beyond namespace propagation and the ownership bug. |

## Compatibility and regeneration

The root change is breaking, including default monoliths: `can://inventory/...` becomes `can://inventory/inventory/...`. Producers, SDK readers, and integrations must adopt it together. New SDK readers reject incompatible legacy output instead of silently querying an old application root.

Regenerate affected analysis files, graph projections, caches, identity indexes, and finding references from source. Rebuild derived joins with canonical IDs. Do not translate old IDs by string replacement or publish compatibility aliases. Remove obsolete affected records through the existing regeneration workflow while preserving unrelated datasets and shared entities. Rollback restores the previous outputs and matching consumers together.

## Rollout

### Implementation bases

George Safta's existing `feat/add-workspace-root` branches were repurposed in place. All three producer PRs below are merged:

| Repository / existing PR | Work to repurpose | Namespace changes |
|---|---|---|
| [Java #275](https://github.com/codellm-devkit/codeanalyzer-java/pull/275) | CLI/root validation, extraction/artifact path handling, graph reconciliation, and workspace-root regression tests. | Add the namespace option in `CodeAnalyzer`, qualify IDs through `CanId`, and update JSON/graph schemas, writers, and tests. |
| [TypeScript/JavaScript #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220) | Options, emission-time path handling, artifact reconciliation, and workspace-root tests. | Thread namespace through options, `assignIds`, and `finalizeAnalysis`; qualify IDs through `src/schema/ids.ts` and update all graph/schema consumers. |
| [Python #235](https://github.com/codellm-devkit/codeanalyzer-python/pull/235) | CLI/options, emission-time path handling, artifact reconciliation, and workspace-root tests. | Thread namespace through options/core/`assign_ids`, qualify IDs through `codeanalyzer/schema/ids.py`, and update schemas and graph writers. |

Replace workspace-prefix-based identity with the namespace/application root while retaining application-relative keys. Implementation choice for this iteration: remove the proposed `--workspace-root` option and its in-process setting from those implementation branches, and introduce `--namespace` instead. Do not retain a no-op option or add a compatibility alias for it. Remove workspace-specific containment/re-keying tests and replace them with namespace/default/scope tests; retain existing input validation, source discovery, and application-relative path coverage. Preserve unrelated fixes in those branches, including shared-artifact reconciliation. Extend the existing ID, CLI, graph-scope, and emission tests in each repository.

The SDK and Go companion changes are merged in SDK #440 and Go #41. The delivered SDK changes cover `backend_config.py`, local invocation, identity helpers, all language-specific Neo4j scopes, and module/reference reconstruction. The existing multi-application scope tests were extended with multiple namespaces and repeated file keys. Go applies the same contract in its CLI/options, `internal/schema/v2/ids.go`, and JSON/Neo4j projections.

Downstream applications must adopt the canonical-ID rule in their own inventories and joins. The scanner and graph-join adaptation described below is implemented and tested; other consumers' SDK adoption, external event producer/UI wiring and production deployment are not certified by the upstream analyzer/SDK tests.

### Delivery sequence (completed upstream)

1. Extended the referenced producer PRs with `--namespace`, common root construction and updated embedded references; applied the same contract to Go.
2. Updated SDK configuration, local invocation, Neo4j scopes, URI resolution and cache binding across supported languages.
3. Fixed canonical-ID indexes, deduplication and reference reconstruction in the SDK; downstream scanner join coverage is recorded separately below.
4. Ran namespace-isolation and wrong-service fixtures across local/JSON and Neo4j paths.
5. Regenerated verification datasets and released compatible producer/SDK versions together. Regeneration of users' existing datasets remains an upgrade operation.

## Validation

| Area | Required evidence |
|---|---|
| Inputs/defaults | Explicit and defaulted pairs resolve identically. Monoliths retain both root segments; invalid identity inputs fail. |
| Namespace isolation | Two namespaces each contain the same application, file, and signature without merged IDs or query results. |
| Service isolation | Two services in `online-boutique` each contain `server.js`; emission, lookup, and graph endpoints preserve both owners. |
| Language/backend coverage | Python, Java, TypeScript/JavaScript, and Go apply the same root rule. Local/JSON and Neo4j reads preserve equivalent IDs and scope. |
| All URI families | Modules, symbols, body nodes, artifacts, config keys, externals, and embedded references use the selected root. Existing suffix semantics remain unchanged. |
| Deduplication | Input rows `[currency URI, payment URI, currency URI]` produce exactly two modules, regardless of order. A same-name secondary index retains both IDs. |
| Graph projections | `DISTINCT` retains canonical IDs. Two real call sites remain distinct, while repeated rows for one existing edge identity collapse correctly. |
| Lookup regression | Currencyservice line 28 returns no callable; it never returns paymentservice's constructor. Reversing backend order cannot change the owner. |
| Scope conflicts | Another namespace/application's URI is rejected before suffix normalization. Unknown/ambiguous scanner ownership is diagnostic. |
| Finding joins | A currencyservice finding joins only to its canonical module/callable; same-named paymentservice code receives no extra edge. |
| Cache/regeneration | Changing scope cannot reuse IDs from another selection. Regenerated output and indexes contain no affected legacy roots. Unrelated data remains intact. |

The broader ADR's repository/service/language arrangements use selected input roots and explicit namespace/application pairs. Upstream analyzer input-root APIs are unchanged. The downstream scanner offers the explicit project mapping below; a complete deployed Concert workflow for every topology is not claimed.

## Open questions

- Resolved: integer `identity_version: 2` is required on existing envelopes and application graph anchors; raw `application_name` and `identity_namespace` remain on applications. Existing `schema_version: "2.0.0"` stays unchanged.
- Remaining adoption: inventory other consumers' combined filename indexes and `DISTINCT`/tail joins, update their SDK usage, and verify external event producer/UI wiring and production rollout. The SDK implementation/release is complete; these are downstream adoption tasks.

Follow-up iterations cover the ADR's remaining package-version identities, semantic suffix consistency, producer-contribution lifecycle, and explicit paginated namespace search.

## References

- [ADR-codeanalyzer-10: Application identity namespaces](../adrs/10-application-identity-namespaces.md).
- [SDK issue #435: Namespace-scoped module identity and resolution](https://github.com/codellm-devkit/python-sdk/issues/435).
- Existing implementation work: [Java #275](https://github.com/codellm-devkit/codeanalyzer-java/pull/275), [TypeScript/JavaScript #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220), and [Python #235](https://github.com/codellm-devkit/codeanalyzer-python/pull/235).
- Current identity helpers: [Python](../../../codeanalyzer-python/codeanalyzer/schema/ids.py), [TypeScript/JavaScript](../../../codeanalyzer-typescript/src/schema/ids.ts), and [Java](../../../codeanalyzer-java/src/main/java/com/ibm/cldk/schema/CanId.java).
- Current SDK [backend configuration](../../../python-sdk/cldk/analysis/commons/backend_config.py) and [module-key resolution](../../../python-sdk/cldk/analysis/commons/keys.py).


## Task 1 tracking and baseline evidence (2026-10-30)

- python-sdk: https://github.com/codellm-devkit/python-sdk/issues/435
- codeanalyzer-python: https://github.com/codellm-devkit/codeanalyzer-python/issues/236
- codeanalyzer-typescript: https://github.com/codellm-devkit/codeanalyzer-typescript/issues/221
- codeanalyzer-java: https://github.com/codellm-devkit/codeanalyzer-java/issues/276
- codeanalyzer-go: https://github.com/codellm-devkit/codeanalyzer-go/issues/40

Implementation and review for Tasks 1–8 are complete within the recorded validation limits. The early unavailable-toolchain observations are historical. Producer smoke, SDK results, provenance and release gates are recorded in [coordinated verification](assets/10-namespace-verification.md). All five feature PRs, including Go #41 and SDK #440, are merged and their compatible releases are published. SDK #440 is no longer Draft or release blocked; the SDK pins and lockfile use the published producer versions. Current release evidence is in the [release record](assets/10-namespace-releases.md).


## Online Boutique live verification follow-up (2026-10-31)

All 11 supported services were cloned over SSH and projected into one Neo4j database. The namespace/URI/deduplication SDK checks passed after three follow-up fixes in TS/JS #220 and SDK #440. See the [live report and reproducible verifier](assets/10-online-boutique-neo4j-verification.md) for exact revisions, environment setup, source-position assertions, namespace controls and remaining limits. The C# cartservice was skipped. Published-package release gates are complete. Downstream application adoption and production workflow verification remain distinct from this live SDK check.


## Coordinated release completion (2026-10-31)

All five implementation PRs are merged. Python/TypeScript 1.7.0, Java 3.4.0, Go 0.3.0 and CLDK 2.1.0 are published; SDK pins and lockfile use these releases. Fresh installed-package verification includes the 11-service live Neo4j workflow. See the [release record](assets/10-namespace-releases.md). This completes the package release dependency; the completed downstream scanner adaptation and remaining adoption boundaries are described next.


## Downstream scanner configuration and adoption (2026-10-31)

The scanner adaptation is implemented: it forwards `namespace` and `app_name` to Java, Python and TypeScript/JavaScript analyzers, analyzes every selected project (including multiple projects in one language), understands marked version 2 module URI roots, and preserves canonical ownership through native and declarative graph joins. Ambiguous finding matches remain unlinked. Conflicting application identities and project roots escaping the checkout, including symlink escapes, are rejected.

Analyzer dependency upgrades are code changes, not operator setup steps: the scanner pins Python/TypeScript 1.7.0 in its pyproject and lockfile and downloads Java 3.4.0 with a verified checksum. CLDK 2.1.0 is already released upstream; adoption by an external SDK consumer is a separate dependency update. This scanner does not add Go orchestration support.

### Usage: configure the namespace and service projects together

The operator supplies one namespace for the overall application and an application name for each service. No namespace or service alias is invented from Git host, owner, repository, environment or scan ID. For a monorepo:

```yaml
namespace: storefront
repos: [acme/storefront]
projects:
  acme/storefront:
    - {path: services/catalog, language: python, app_name: catalog}
    - {path: services/payments, language: javascript, app_name: payments}
```

For multiple repositories:

```yaml
namespace: storefront
repos: [acme/catalog, acme/payments]
projects:
  acme/catalog:
    - {path: '.', language: python, app_name: catalog}
  acme/payments:
    - {path: '.', language: javascript, app_name: payments}
```

Both configurations produce application roots `can://storefront/catalog` and `can://storefront/payments`. These identity snippets supplement existing authentication and output settings. Paths are relative to each selected repository. A project entry requires `path`, `language` and `app_name`; supported scanner languages are Java, Python, TypeScript and JavaScript. Different language views of one service may share its application name. Distinct service roots must have distinct application names within a namespace.

For standalone runs, set these fields in the YAML selected by `CODE_ANALYZER_CONFIG` (default `/etc/veias/config/code-analyzer.yaml`). For Concert-triggered runs, supply `namespace` and `projects` in the `JOB_EVENT` body; project-map keys remain `owner/repository` slugs while the existing event `repos` field contains repository URLs. The scanner reads the fields; the external event producer/UI must populate them. A repository without configured projects retains discovery and analyzer directory-name defaults. Omitted namespace retains the upstream default to the resolved application name.

### Verification and boundaries

- Scanner suite: **109 passed**, including configuration/event forwarding and a real Python analyzer emission.
- UKG offline suites: **360 passed, 49 skipped**.
- Isolated Neo4j ownership suites: **11 passed**, including ambiguity rejection, canonical precedence, legacy fallback and native/declarative parity.
- Real scanner invocations of released Java 3.4.0, Python 1.7.0 and TypeScript 1.7.0 emitted into a separate scratch Neo4j database; namespace/application anchors and module identities were checked by database readback.

The adapter changes were committed and pushed to their feature branch. They are not claimed merged, deployed or verified through a complete production Concert workflow. The Docker image was not built locally. External event producer/UI wiring and other consumers' SDK adoption remain outside the verified scanner change.

Source regeneration, downstream consumer adoption and operational graph verification are upgrade context, not additional steps in the scanner configuration interface. Broader ADR features—package-release/occurrence identities, semantic suffix redesign, producer lifecycle and namespace-wide search—remain deferred.
