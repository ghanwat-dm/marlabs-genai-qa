# Test Strategy

## 1. Offline deterministic evaluation

The baseline gate uses Python assertions only. No API key or model is required. Deterministic checks cover response contract, caller identity, tenant/role isolation, approved-only and effective-date rules, generation context, citation identity and quote integrity, required facts, prohibited claims, provider trace behavior, and invalid-request no-generation behavior.

The evaluator derives expected results from the request + caller lookup + policy corpus + contract. It never assigns PASS/FAIL by recording ID.

## 2. Optional DeepEval evaluation

DeepEval is deliberately supplementary. Set `ENABLE_DEEPEVAL=1` only when a DeepEval-compatible LLM provider is configured. The wrapper includes Answer Relevancy, Faithfulness, Contextual Relevancy, and a GEval semantic-equivalence check. DeepEval does not decide authorization, dates, HTTP codes, citation exactness, retry counts, or error mapping.

## 3. RAG validation

For each request the evaluator independently derives the eligible and relevant context IDs. It then compares trace `model_context_ids` against that set. Cross-tenant, cross-role, Draft, expired, or future context is a deterministic failure. Retrieval ranking quality beyond the supplied traces is not proven offline.

## 4. Citation validation

A citation is checked for: known chunk ID, policy eligibility for the trusted caller, exact quote equality with the corpus, and expected evidence alignment. Semantic claim support can additionally be evaluated with DeepEval, but exact corpus identity and authorization remain deterministic.

## 5. Semantic evaluation

Exact full-answer matching is not used. The offline checker validates structured required facts, including concept and INR amount. It permits wording changes such as "annual limit", "yearly cap", and "Indian rupees" when required meaning is preserved. Prohibited claim patterns independently reject approval/payment/remaining-balance/action assertions.

## 6. Evaluator self-test

Three deliberately faulty variants verify that the evaluator catches wrong citations, unsupported payment guarantees, and unauthorized tenant context. Two meaning-preserving variants verify that wording differences are accepted.

## 7. Future live tests - NOT_RUN / FUTURE LIVE TEST

| Area | Test design | Needed evidence/instrumentation |
|---|---|---|
| Latency | Measure p50/p95/p99 end-to-end and generation duration against timeout | Live endpoint, synchronized timestamps, load tool |
| Load | Ramp RPS and identify saturation/error point | Production-like environment, load generator, metrics |
| Concurrency | Parallel callers across tenants/roles, verify no context bleed | Correlated request/trace IDs |
| Availability | Sustained health/error-rate observation | Service metrics, uptime window |
| Provider timeout | Force >2000 ms provider response | Injectable/stub provider or fault proxy |
| Provider unavailable | Simulate provider connection/service failure | Fault injection |
| Malformed output | Return syntactically/structurally malformed model response | Controlled provider stub |
| Retry behavior | Verify exactly one attempt under failure | Model-call counter/trace |
| Production retrieval | Inspect top-k candidates vs sent generation context | Retrieval and post-filter traces |
| Production model behavior | Repeated semantic/security evaluation | Fixed dataset + live model |
| Model version changes | A/B old vs new version | Version pinning + run metadata |
| Prompt changes | Compare prompt versions on fixed data | Prompt version in trace |
| Policy corpus changes | Recompute expected results and regression scope | Corpus version/hash |
| Observability | Verify request, caller, policy, provider, latency, error fields without sensitive leakage | Structured logs/traces |

## 8. Model / prompt regression strategy

Keep a versioned golden dataset containing the supplied recordings, candidate-created fault fixtures, meaning-preserving variations, boundary-date cases, isolation attacks, conflict cases, and unsupported-evidence cases. For every model/prompt change, run deterministic checks on every case and repeated semantic runs for non-deterministic outputs. Compare distributions and individual regressions, then conduct targeted human review for security-, money-, and conflict-related changes.

Thresholds should be metric-specific and calibrated against labeled examples rather than chosen as an overall quality score. Deterministic security/contract checks are hard gates. LLM metric thresholds are advisory until validated against human judgments.

**Human PASS + Automated FAIL:** inspect the exact rule, confirm expected-result derivation, check whether the assertion is too narrow (for example, a valid paraphrase), add the case to semantic-variation fixtures, and fix the evaluator only if the product behavior is supported by policy.

**Human FAIL + Automated PASS:** identify the missing rule or semantic pattern, preserve the failed response as a new evaluator regression fixture, update the smallest defensible assertion, and rerun all self-tests to avoid overfitting.
