# Namespace verification and integration handoff

Verified locally on 2026-10-31. No producer release or production regeneration is claimed. The original local-only checks below are supplemented by the completed [Online Boutique live Neo4j run](10-online-boutique-neo4j-verification.md), including its three follow-up fixes. The combined review findings were addressed in one final fixwave and passed scoped re-review. All five branches are pushed and PR delivery is complete; no merge or release was performed.

## Reproduce the coordinated smoke

From the workspace root, with the reviewed local producer installations and overrides:

```sh
source /private/tmp/namespace-toolchains/sdk-env.sh
PYTHONPATH=python-sdk python-sdk/.venv/bin/python architecture/codeanalyzer/rfc/assets/10-namespace-smoke.py
cd python-sdk
CLDK_SKIP_JAVA_E2E=1 .venv/bin/python -m pytest tests -q
```

Use the SDK venv directly. `uv run` would restore the older published producer pins.
The smoke creates temporary source projects and caches, invokes each actual local producer through the SDK at L2, and reads the emitted model. It covers Python, Java, TypeScript, JavaScript and Go: explicit `online-boutique/currencyservice`, sibling `paymentservice` with the same filename, omitted defaults (`can://inventory/inventory`), and raw punctuation `!'()*~%` plus Unicode. Twenty cases passed, checking integer envelope marker 2, raw metadata, every canonical ID/reference's owner, all 60 emitted canonical call endpoint references against entity IDs, and exact SDK module-ID preservation. The tiny Java L2 projects emitted a declared-edge fallback: RTA was unavailable because the existing BuildProject.GRADLE_CMD was null. This smoke establishes identity/reference integrity, not full Java RTA completeness; strict compiled WALA was verified separately below. This is a JSON/local smoke; graph projection and broader entity families are covered by the producer suites below. No released binary was substituted. L1 also passed before strengthening the smoke to L2.

## Delivered pull requests

[Python #235](https://github.com/codellm-devkit/codeanalyzer-python/pull/235), [TS/JS #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220), [Java #275](https://github.com/codellm-devkit/codeanalyzer-java/pull/275), [Go #41](https://github.com/codellm-devkit/codeanalyzer-go/pull/41), and [SDK #440 (Draft)](https://github.com/codellm-devkit/python-sdk/pull/440). George's three existing PRs were updated in place. SDK issue [#435](https://github.com/codellm-devkit/python-sdk/issues/435) remains open with the release, live-check and downstream integration obligations.

## Source and artifact provenance

| Repository | Reviewed source HEAD |
|---|---|
| python-sdk | `d2256fb728f19bb456d1226a1ba1d5ff4afe19a8` |
| codeanalyzer-python | `b6599662ee17947bedc4231fa1b0875c2d172999` |
| codeanalyzer-typescript | `9658f895e3e75d683a0c00c87069934ddf2966fa` |
| codeanalyzer-java | `89b95237ee2623dfdf84ddd6e71f07ab2472699b` |
| codeanalyzer-go | `f66a589c1e2f4dc0ed373f4811a0dbe8f22b3d13` |

Python analyzer 1.6.2 is installed editable from this reviewed checkout. Java wheel label 3.3.4 is a local build, not a newly published namespace-compatible release. The Java artifact was built from `cbfbd01dd9ed3f5bfca51237487d0273f4eff4ec`; its reviewed HEAD adds only contract documentation/tests, so producer behavior is identical and no rebuild was needed. TS/Go are native builds from the listed sources:

- codeanalyzer-typescript: `/Users/rkrsn/workspace/codellm-devkit/codeanalyzer-typescript/dist/cants`, SHA-256 `94a1a8206148451d57ca3b1335f115d1aca87b0f785790bbb04b86893268696e`.
- codeanalyzer-java: `/private/tmp/namespace-toolchains/wheels/codeanalyzer_java-3.3.4-py3-none-any.whl`, SHA-256 `c6a507da15ceaaf4ef43182d538cf1cebacaf8a1b02b82dfdd5c38361890d894`.
- codeanalyzer-go: `/private/tmp/namespace-toolchains/cango`, SHA-256 `881307dd51a1068bee53bbf5a91b4ff4c5984080ea0a5704634861acdf04c867`.

The existing published SDK dependency pins and lockfile remain unchanged. No compatible release pins have been invented. The SDK PR must remain Draft and release blocked until real compatible producer releases exist, its pins/lock are updated through the package workflow, and installed-package validation passes. The separate SDK PR #439 Go-version update is preserved and does not establish namespace readiness.

## Original local verification and limits (before the live follow-up)

Producer results are reused from their scoped reports, rather than repeating full suites without source changes:

- Python: 548 passed, 27 skipped, 5 heavyweight CLI cases deselected; focused identity/schema/projection 77 passed, 25 container skips. Heavyweight Ray/Flask/requests cases remain gated.
- TS/JS: full 399 passed, 23 skipped; explicit-empty CLI fix subsequently 71 passed and typecheck passed.
- Java: available full 635 tests, 17 skipped; unfiltered attempt had one Docker initialization failure. Subsequent v1/v2 cleanup fix 16 passed. Realworld submodule gate unavailable.
- Go: full suite passed before review fixes; core/Neo4j fix verification 175 pass events. Sibling-file same-position regression from upstream merge passed.
- Final bounded SDK suite: **1949 passed, 422 skipped, 10 warnings**, **85.34% coverage**, 74.60 seconds (75.22 seconds including runner); exit 0 under the 240-second cap. Existing `CLDK_SKIP_JAVA_E2E=1` gate retained.
- Final fixwave: Python focused Bolt/scope/artifact/schema **34 passed**; Go `go test ./internal/neo4j` passed; SDK focused identity/scope **142 passed, 1 skipped**; Java strict-contract **3 passed**. Native Go rebuilt from its new HEAD before rerunning the L2 smoke: **20 cases / 60 endpoints passed**. Logs: `/private/tmp/final-{python-green,go-green,sdk-focused,java-contract,native-smoke,sdk-full}.log`.
- SDK Task 7: 596 passed, 2 skipped relevant tests; 163 focused passed. Canonical-ID joins remain correct in both backend orders and two genuine call sites survive.
- Compiled Java L4 source-derived corpus was generated separately with Maven 3.9.16/JDK 17.0.21 and strict WALA, including 118 visited callables and 320 points-to edges. No engine-free Java success is substituted.

Docker/Neo4j is unavailable. No live projection, live equality join, or live cleanup-preservation pass is claimed. Fake-driver tests cover read-only attachment, exact anchors, namespace/application/language rejection, canonical joins, and selected cleanup parameters; producer reconciliation tests cover unrelated/shared data preservation where their runtime gates permit. Private integration index/finding joins remain external work tracked through public SDK issue #435, not proved by SDK tests.

All six golden fixture copies have SHA-256 `6bb6e909079045600ddb06606ca5d9c8f84eb30bf7f5bbc634213c3363a695b0`. `git diff --check` passed in all five repositories. Parent RFC/plan/artifacts are local reviewable files because the workspace parent is not a Git repository.

## Original Online Boutique check instructions (now executed in the follow-up run)

Use the source HEADs/artifact hashes above until compatible releases exist. Clone Online Boutique yourself and prepare each service's language/build dependencies. Project each selected service into the same fresh test database, choosing its directory basename as `--app-name` and `--namespace online-boutique`. Use `cants` for currencyservice/paymentservice (JavaScript), `canpy` for Python services, `java -jar codeanalyzer-java/build/libs/codeanalyzer-3.3.4.jar --schema v2` for adservice (Java), and `cango` for the Go services. Other languages need their own compatible producers and are outside this delivery. Each CLI supports this shape (do not add `-a` to graph emission; it selects full depth):

```sh
cants -i "$BOUTIQUE/src/currencyservice" --app-name currencyservice --namespace online-boutique --emit neo4j --neo4j-uri "$NEO4J_URI" --neo4j-user "$NEO4J_USERNAME" --neo4j-password "$NEO4J_PASSWORD" --neo4j-database "$NEO4J_DATABASE"
cants -i "$BOUTIQUE/src/paymentservice" --app-name paymentservice --namespace online-boutique --emit neo4j --neo4j-uri "$NEO4J_URI" --neo4j-user "$NEO4J_USERNAME" --neo4j-password "$NEO4J_PASSWORD" --neo4j-database "$NEO4J_DATABASE"
```

The reviewed READMEs confirm all four launchers accept `-i`, `--app-name`, `--namespace`, `--emit neo4j`, and the four `--neo4j-*` connection flags above. Repeat that command shape with the appropriate producer and service for the remaining supported service directories. These commands populate the selected application and retain normal producer reconciliation semantics. Then run this read-only SDK script with the same database environment:

```python
import os
from cldk import CLDK
from cldk.analysis.commons.backend_config import Neo4jConnectionConfig

def attach(service):
    return CLDK.typescript(backend=Neo4jConnectionConfig(
        uri=os.environ["NEO4J_URI"], username=os.environ["NEO4J_USERNAME"],
        password=os.environ["NEO4J_PASSWORD"], database=os.environ["NEO4J_DATABASE"],
        namespace="online-boutique", application_name=service,
    ))

currency, payment = attach("currencyservice"), attach("paymentservice")
for service, analysis in [("currencyservice", currency), ("paymentservice", payment)]:
    modules = analysis.get_modules()
    root = f"can://online-boutique/{service}/"
    assert modules and all(module.id.startswith(root) for module in modules)
    assert any(module.id.endswith("/server.js") for module in modules)
    result = analysis.locate("server.js", 28)
    assert result.node_id is None or result.node_id.startswith(root)
    print(service, result)
# At the fixture's source revision, currency line 28 has no callable and payment
# line 28 has its constructor; inspect source if upstream positions have changed.
try:
    currency.locate("can://online-boutique/paymentservice/javascript/server.js", 28)
except ValueError:
    pass
else:
    raise AssertionError("foreign service URI was accepted")
```

Confirm both Application anchors carry integer `identity_version: 2` and raw `identity_namespace: online-boutique`; run canonical equality joins in the downstream integration as a separate check. The supported-service version of this workflow has now been executed; current results and limits are in the Online Boutique live follow-up report.

## Decision ledger annex

The following records preserve every ledger Ruling in original order. Costs describe consequences if the decision is wrong, not observed failures.

1. Ruling: The workspace parent cannot host Git-native SDD artifacts; use the SDK's ignored SDD directory with the absolute workspace plan path — preserves one ledger without initializing a repository.

   Cost if wrong: Lost review/provenance history.

2. Ruling: Product code uses dedicated existing PR/feature branches in the supplied checkouts — user requested repurposing these branches; no main-branch implementation.

   Cost if wrong: Branch history or unrelated changes lost.

3. Ruling: The selected plan's identity_version 2 is the ownership-contract marker; schema_version stays 2.0.0. No suffix redesign.

   Cost if wrong: Incompatible readers accept stale ownership.

4. Ruling: Public issue creation and PR updates are authorized by the user's Plannotator feedback (“Please create issue in python-sdk and in the codeanalyzer-* repos ... Make the change, and create/update PRs.”). Do not publish private links/details, force-push, merge, or release.

   Cost if wrong: Unintended publication or history mutation.

5. Ruling: Integration repositories are absent. Complete available producers and SDK, and track/report the private join/index adoption separately.

   Cost if wrong: End-to-end fix falsely claimed.

6. Ruling: Remove Python PR legacy can://artifact/<app>/ automatic cleanup while retaining selected-root artifact reconciliation — legacy retirement belongs to explicit regeneration, avoiding cross-namespace deletion.

   Cost if wrong: Unrelated legacy graph data deleted.

7. Ruling: Producer/SDK file inventories are audit targets: do not create cosmetic changes in files that already consume canonical parent IDs correctly. Report any listed file left unchanged with the verified forwarding invariant. This follows the narrow RFC and avoids gratuitous edits; missing necessary propagation remains a defect.

   Cost if wrong: Missing propagation overlooked.

8. Ruling: Permit a minimal Python import-resolver key-form correction exposed by the namespace emission fixture — input-relative keys are required by the RFC, and emitted resolved_module references must stay coherent. Cover both pre-existing absolute-key and relative-key forms; no inference/suffix redesign. Cost if wrong: local import-edge regression caught by dedicated RED/GREEN tests and task review.

   Cost if wrong: Local import joins fail.

9. Ruling: Offline Cypher export validates incoming scope/marker before producing output, but must not invent unvalidated failure-expression guards for an existing DB. Connected Bolt/SDK/loader validates existing anchors; offline snapshot execution is explicit regeneration. No APOC or speculative divide-by-zero mechanism.

   Cost if wrong: Offline export emits unreliable guards or overwrites unvalidated legacy state.

10. Ruling: Go Emit/EmitTo replace existing appName string parameter with named v2.Identity, preserving every trailing argument type/order. Identity is resolved once before emission; no positional insertion of namespace among existing strings.

   Cost if wrong: Positional API arguments misbind identity.

11. Task 5 rulings: RenderCypher returns (string,error) through internal callers/EmitNeo4j, with invalid input rejected before filesystem creation/truncation; no panic or empty-success result. Existing ordinary RowBuilder property last-write-wins is retained: property refinement is not an identity collision. Canonical-ID keys and label union required; identity/ownership mismatches fail at validated write/read boundaries. Earlier generic-conflict phrasing was overbroad, not a new reconciliation feature requirement. Task7 module-index contradictory file-key diagnostic remains explicit.

   Cost if wrong: Property refinement regresses or canonical collisions hide.

12. Task 5: fix round1/5 active original implementer; FIX_BASE8fabbf69a11c2c3a338ee60577ca300c52280165. P2 direct WriteOutput prevalidation, and persistence collapse of retained site/context facts. Ruling: shared deterministic private relationship fact discriminator may be added to this unreleased breaking graph contract, preserving original _k and public URI suffixes; must work identically in Cypher/Bolt with schema documentation.

   Cost if wrong: Distinct site/context evidence collapses on persistence.

13. Ruling: permit explicit GoType kind literal defined (and necessary declared fields) to consume actual current reviewed Go output, with focused regression; not arbitrary string/Any or type API redesign. Minimal compatibility for currentGo adoption.

   Cost if wrong: Current Go output cannot be read or model becomes overbroad.

14. Ruling: minimal PyCallsite dataclass compatibility uses dataclasses.replace rather than obsolete model_copy; optional TSApplication.name models real producer display field for lossless roundtrip. No broad type looseness.

   Cost if wrong: Python callsite clone fails or TS display metadata is lost.

15. Task6review: specissues/qualityneedsfixes, Important staleTS live gate/cleanup APP_ID. Fixround1 active originalimplementer BASE315eeae. Minor(deferred finalwave): strictfloat2.0 marker coercion before validate_identity; duplicatePython scopefixture setup. Ruling: brief file list followed actual facade ownership rather than no-op __init__/abstractbackend edits; reviewer verified sole direct abstractcaller Java is wired, no demonstrated missing API. Live Neo4j remains explicitly unavailable, cannotverify item accounted.

   Cost if wrong: A real API forwarding omission escapes review.


16. Ruling: Task 8 includes independent whole-branch review and delivery as its planned step 4; the final combined review serves that review gate and judges the verification handoff, avoiding a duplicate documentation-only review.

   Cost if wrong: documentation gaps may need follow-up if the broad review misses them.

17. Final review ruling: reject incompatible existing selected anchors read-only before DDL/upsert in both Python Bolt paths and Go. Require exact integer 2 and raw owner metadata matching the canonical selected root; absence is a fresh first push. Strict marker validation must happen before Pydantic coercion for fresh models as well as caches, including the SDK-reexported Python application model.

   Cost if wrong: stale descendants could be retained after overwriting contradictory ownership, or fresh/local acceptance would differ from cache acceptance. Focused RED/GREEN and fake-driver no-write ordering tests cover these boundaries; live runtime remains unavailable.

18. Final Java ruling: preserve the current strict canonical node property contract this iteration, including ordinary display properties. Correct the class documentation and pin rejection with a test; no production behavior change was made because review established no ordinary projector trigger. The existing native artifact is behavior-identical to the reviewed docs/test HEAD.

   Cost if wrong: callers relying on ordinary property refinement may need a targeted follow-up. This risk is disclosed; no demonstrated source-level regression is claimed.

19. Delivery ruling: keep SDK issue #435 open for downstream integration indexes/joins; its PR body uses a non-closing reference. Go introduces namespace without claiming a prior workspace-root option. SDK remains Draft/release blocked; published pins and lockfile are unchanged.

   Cost if wrong: downstream integration work could be closed prematurely, or an incompatible SDK package could be treated as ready.

## Review evidence archive

The completed plan ledger, scoped reports, final review/fix review, exact diff ranges, artifact provenance and verified PR heads are preserved in [the review evidence archive](10-namespace-review-evidence.zip). The completed temporary SDD workspace was removed after archival; product branches and checkouts are retained for review.


## Published release follow-up

The coordinated releases are now published: SDK2.1.0 with Python/TypeScript1.7.0, Java3.4.0 and Go0.3.0. The earlier Draft/release-blocked statements above record the pre-release stage; that release gate is complete. See the [release record](10-namespace-releases.md) for published-wheel validation and final test evidence. Downstream integration adoption and the documented sparse-graph/source-hydration limits remain separate.
