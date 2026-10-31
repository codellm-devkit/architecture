# Coordinated namespace minor releases

Released and verified on 2026-10-31. All five task PRs are merged; all five stable releases are published on GitHub and PyPI. The additional TypeScript release-preparation PR #222 is also merged.

| Repository | Stable release | Package | Tag commit |
|---|---|---|---|
| codeanalyzer-python | [1.7.0](https://github.com/codellm-devkit/codeanalyzer-python/releases/tag/v1.7.0) | [PyPI](https://pypi.org/project/codeanalyzer-python/1.7.0/) | `b4f22ee0` |
| codeanalyzer-typescript | [1.7.0](https://github.com/codellm-devkit/codeanalyzer-typescript/releases/tag/v1.7.0) | [PyPI](https://pypi.org/project/codeanalyzer-typescript/1.7.0/) | `1f901935` |
| codeanalyzer-java | [3.4.0](https://github.com/codellm-devkit/codeanalyzer-java/releases/tag/v3.4.0) | [PyPI](https://pypi.org/project/codeanalyzer-java/3.4.0/) | `ad74b884` |
| codeanalyzer-go | [0.3.0](https://github.com/codellm-devkit/codeanalyzer-go/releases/tag/v0.3.0) | [PyPI](https://pypi.org/project/codeanalyzer-go/0.3.0/) | `f6014573` |
| python-sdk | [2.1.0](https://github.com/codellm-devkit/python-sdk/releases/tag/v2.1.0) | [PyPI](https://pypi.org/project/cldk/2.1.0/) | `f1386518` |

The remaining feature PRs were squash-merged with concise subjects (`feat: add application identity namespaces` for the producers; `feat: scope SDK identities by namespace` for the SDK). The TypeScript feature PR had already been merged and its published history was retained; its release preparation uses `chore: release 1.7.0`. No history was rewritten or force-pushed.

## Compatibility and installation

SDK2.1.0 pins Python/TypeScript1.7.0, Java3.4.0 and Go0.3.0. Both dependency declarations and uv.lock were updated through the existing uv workflow. Release notes call out the new `can://<namespace>/<application>` roots and source regeneration for existing outputs; no alias or in-place ID translation is provided.

```sh
pip install 'cldk[all]==2.1.0'
```

The five local product checkouts are on main and synchronized with origin. The normal SDK workspace venv is synchronized to the new frozen lockfile. Temporary prototype binary overrides were removed from the local SDK environment helper; the tested published packages supply the analyzers.

## Verification

- Python full suite including the previously heavy CLI/Ray cases:568 passed,27 skipped;79.47%coverage.
- TypeScript full suite:405 passed,23 skipped;typecheck passed. Release-preparation CI, including its Docker bolt suite, passed.
- Java preflight:638 tests,0 failures/errors,17 skips; one Docker-initialization integration class excluded locally. The3.4.0 fat JAR was built and checked; actual live strict graph projection was verified separately.
- Go full suite passed. Both CI Go configurations and lint passed. The obsolete CLI test matcher was updated for fact-discriminated Cypher relationships; assertions of L3/L4 behavior were retained.
- SDK fresh Python3.11 environment with actual published producer wheels, no local binary overrides:1960 passed,414 skipped,7 warnings;85.48%coverage. The six initial failures were stale Java/TS version expectations, updated to the released pins. No analysis fixtures were relabeled.
- A fresh SDK wheel candidate was installed with all extras outside the source checkout; all11 supported Online Boutique services were reprojected into the same Neo4j database using the four published analyzers. Java and Go used strict full-depth projection.
- The SDK was then forcibly reinstalled from PyPI as cldk2.1.0, with no local-wheel direct URL remaining, and the live verifier was run again. Current results and the compact evidence archive accompany this report.
- GitHub release workflows and Java's separate PyPI publisher completed successfully. Stable release metadata, PyPI versions/wheel availability and tag targets were checked directly.

All earlier [live verification](10-online-boutique-neo4j-verification.md) assertions apply: exact canonical module identity, service and namespace rejection, original currency/payment source-position regression, reverse backend order, deduplication/equality joins and read-only SDK attachment. The graph remains at bolt://127.0.0.1:17687, database neo4j, local-only authentication disabled, with11 service scopes and2 namespace controls.

## Scope of the fix

The SDK previously accepted a service-prefixed scanner path by filename suffix inside another service's backend. Scope-bound resolution, canonical module indexes and canonical-ID reconstruction now preserve ownership. The original live currency/payment lookup passes.

Consumer applications must also retain canonical IDs in their own module inventories and finding joins. This release does not certify unavailable downstream application code. The existing sparse-TypeScript-graph fingerprint and module-source hydration limitations remain as documented in the live report. These limits are separate from the completed package release gates.

A [release evidence archive](10-namespace-release-evidence.zip) retains public release metadata, tag/merge proofs, package-install checks, test logs and installed-package live checks. Private issue contents are excluded.


## Final PyPI SDK check

The SDK was reinstalled directly from PyPI (`cldk2.1.0`, no local-wheel direct URL). All11 live SDK views passed again:69,250 database nodes and220,842 relationships including the two control namespaces; zero duplicate canonical IDs or cross-service canonical relationships. No additional graph writes occurred during the read-only verification.
