# Module lookup can resolve a scanner path to the wrong service when file keys overlap

## Problem

Module lookup can lose service ownership when several services in one application contain the same project-relative file key.

For example, the Online Boutique microservice application contains currencyservice and paymentservice. Each service is analyzed from its own source directory:

```text
online-boutique/
  src/currencyservice/server.js
  src/paymentservice/server.js
```

The analyzers already emit distinct service-qualified module IDs:

```text
can://currencyservice/javascript/server.js
can://paymentservice/javascript/server.js
```

However, both modules have the local key `server.js`. `cldk.analysis.commons.keys.resolve_module_key` accepts a caller path when it ends with a known local key. Consequently, `currencyservice/server.js` resolves to `server.js` in both services' backends. Local path normalization does not establish which service owns the original scanner path.

A multi-service caller that probes every backend and accepts the first callable can therefore select paymentservice code for a currencyservice source position. Indexes that deduplicate by local filename hide the distinct owners, and filename-tail joins can attach a finding to both modules.

## Minimal reproduction

The shared helper demonstrates the ownership loss without needing a database:

```python
from cldk.analysis.commons.keys import resolve_module_key

currency_keys = ["server.js"]
payment_keys = ["server.js"]

assert resolve_module_key("currencyservice/server.js", currency_keys) == "server.js"
assert resolve_module_key("currencyservice/server.js", payment_keys) == "server.js"
```

To reproduce the downstream failure, use two fixture files with these source ranges:

| Service | File | Callable range | Meaning of line 28 |
|---|---|---|---|
| currencyservice | `server.js` | `_loadProto`, starting at line 91 | Module scope; no callable contains it |
| paymentservice | `server.js` | `HipsterShopServer.constructor`, lines 24–34 | Inside the constructor |

Route the scanner position `src/currencyservice/server.js:28` through paymentservice first using filename-suffix matching. It can be attributed to the paymentservice constructor even though the source position belongs to currencyservice. These ranges form the regression fixture; the helper reproduction alone does not exercise callable selection.

## Expected behavior

- Resolve an ordinary SDK request within one selected namespace and analyzed application, retaining its language view.
- Preserve a canonical module ID through lookup, indexing, analysis, deduplication, and finding joins. A relative filename is a lookup key within a binding, not a cross-service identity.
- Route scanner paths using declared service/source-root mappings. Reject a conflicting owner; report ambiguous or missing ownership instead of trying every backend.
- Return the currencyservice module-scope/no-callable result for its line 28. Never substitute paymentservice's constructor.
- Preserve both modules in combined indexes, and join resolved module/callable references by canonical ID equality.
- Verify local/Neo4j parity and independence from backend iteration order.

The proposed qualified identity is:

```text
can://online-boutique/currencyservice/javascript/server.js
can://online-boutique/paymentservice/javascript/server.js
```

Adding a namespace segment alone does not fix a consumer that drops service ownership.

## Existing implementation work to repurpose and extend

The workspace-root PRs contain related input validation, path handling, emission, and regression-test work:

- [Java #275](https://github.com/codellm-devkit/codeanalyzer-java/pull/275)
- [TypeScript/JavaScript #220](https://github.com/codellm-devkit/codeanalyzer-typescript/pull/220)
- [Python #235](https://github.com/codellm-devkit/codeanalyzer-python/pull/235)

Extend that work for namespace/application-qualified identity and scoped SDK lookup. Workspace-relative paths can support scanner mapping; they must not replace explicit application ownership.
