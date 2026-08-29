# Experiment Planning and Project Memory Protocol

## 1. Purpose

This file defines how every research experiment in this repository must be planned, executed, documented, updated, and committed.

The goal is to create a durable project memory that makes it possible to answer, months later:

- What did we test?
- Why did we test it?
- Which data and code versions did we use?
- What did we expect before seeing the result?
- What actually happened?
- Which approaches failed, and why?
- Which decisions changed the roadmap?
- Can another person reproduce the result from the repository?

An experiment is not complete when code finishes running. It is complete only when its plan, evidence, status, decision, and Git history are up to date.

This protocol supplements the root `AGENTS.md`. If the two files conflict, the root `AGENTS.md` takes precedence.

## 2. Core principle

Every experiment must begin with a written, testable plan **before** inspecting the final result.

The plan must separate:

1. what was known before the experiment,
2. what was decided before the experiment,
3. what was observed during execution,
4. what was concluded after evaluation.

Never rewrite history to make a failed experiment look successful. Failed, inconclusive, or abandoned work is valuable project memory and must remain visible.

## 3. When an experiment plan is required

Create a dedicated experiment plan when work includes one or more of the following:

- evaluating a new data source,
- testing a market, city, station, or lead-time segment,
- comparing forecasting models,
- adding or removing features,
- changing calibration methods,
- testing a trading signal,
- modifying fee, slippage, latency, fill, or execution assumptions,
- running a backtest or paper-trading evaluation,
- changing risk sizing or portfolio constraints,
- investigating a material anomaly or failed result,
- making a decision that could change project scope or live-trading readiness.

A separate experiment is usually not required for:

- spelling or formatting corrections,
- mechanical refactors with no behavioral change,
- dependency metadata changes,
- documentation-only clarification that does not change a research decision.

When uncertain, prefer creating the experiment record.

## 4. Directory and naming convention

Every experiment must live in its own directory:

```text
docs/
  experiments/
    EXP-YYYYMMDD-short-slug/
      PLAN.md
      artifacts.md          # Optional artifact index
```

Example:

```text
docs/experiments/EXP-20260903-nbm-baseline/PLAN.md
```

Rules:

- The experiment ID is immutable.
- Use the date the plan was first created, not the date it completed.
- The slug must be short, lowercase, and hyphen-separated.
- Never reuse an experiment ID.
- Never rename a completed experiment directory unless the old path is preserved through Git history and all references are updated.
- Large datasets and binary outputs do not belong in `docs/`; link to their manifest or artifact location.

## 5. Allowed experiment statuses

Every `PLAN.md` must contain exactly one current status:

| Status | Meaning |
|---|---|
| `DRAFT` | Plan is being written; execution must not start |
| `READY` | Hypothesis, data, metrics, gates, and phases are pre-registered |
| `IN_PROGRESS` | One and only one phase is actively being executed |
| `BLOCKED` | Work cannot continue; blocker and unblock condition are documented |
| `PASSED` | Pre-registered acceptance criteria were met |
| `FAILED` | Pre-registered acceptance criteria were not met |
| `INCONCLUSIVE` | Evidence is insufficient to accept or reject the hypothesis |
| `DEFERRED` | Work is intentionally postponed with a documented reason |
| `CANCELLED` | Experiment is stopped because it is invalid, unsafe, or no longer relevant |
| `SUPERSEDED` | A newer experiment replaces this one; replacement ID is linked |

Status rules:

- Do not use subjective labels such as `MOSTLY_DONE`, `LOOKS_GOOD`, or `SUCCESSFUL_SO_FAR`.
- `PASSED` means the pre-registered gate passed, not merely that the code ran.
- `FAILED` does not mean the engineering work was poor; it means the tested hypothesis or acceptance gate failed.
- `BLOCKED` must state the exact missing input and the condition that will unblock it.
- A terminal status must include a final decision and follow-up action.

Phase statuses use the narrower set `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `PASSED`, `FAILED`, or `DEFERRED`. An experiment may be `IN_PROGRESS` while completed phases are `PASSED`; exactly one unfinished phase may be `IN_PROGRESS`.

## 6. Mandatory experiment lifecycle

Every experiment follows the lifecycle below.

### Stage 0 — Create the plan

Before implementation or final-data inspection:

1. Assign an experiment ID.
2. State a single primary hypothesis.
3. Define the economic or research motivation.
4. Define the baseline and counterfactual.
5. Register required data and availability timestamps.
6. Register primary and secondary metrics.
7. Set acceptance, rejection, and inconclusive criteria.
8. Split the work into ordered phases.
9. Document leakage, execution, and data-quality risks.
10. Set status to `READY` only when the plan is executable.
11. Commit the plan before running the decisive analysis.

### Stage 1 — Validate inputs

Validate that:

- required datasets exist,
- timestamps have the intended semantics,
- schemas match their contracts,
- units, timezones, DST, station IDs, and market IDs are correct,
- missingness and duplicates are measured,
- the planned sample size is still feasible,
- the test period has not been used for model selection.

If input validity fails, mark the phase `BLOCKED` or `FAILED`; do not silently repair the data and continue.

### Stage 2 — Implement the minimum reproducible experiment

- Build the simplest analysis that can test the hypothesis.
- Keep raw data immutable.
- Record config, dataset, feature, and code versions.
- Add tests for economically critical calculations.
- Avoid adding unregistered features or segments after seeing results.
- Record deviations immediately in the plan.

### Stage 3 — Evaluate against the registered gate

- Compute the pre-registered primary metric first.
- Compare against all registered baselines.
- Report uncertainty, not only point estimates.
- Break down results by relevant city, station, lead time, season, price band, and execution regime.
- Measure concentration, multiple-testing exposure, and robustness.
- Evaluate economic significance separately from statistical significance.

### Stage 4 — Stress test

Where applicable, test:

- fee and slippage increases,
- lower fill probability,
- additional latency,
- zero maker rebate,
- provider/model version changes,
- missing or stale data,
- station/rule changes,
- removal of the most profitable dates or segments,
- cluster-bootstrap uncertainty.

### Stage 5 — Close and propagate the decision

1. Assign `PASSED`, `FAILED`, or `INCONCLUSIVE` using the registered gate.
2. Write the final conclusion in plain language.
3. Separate observed facts from interpretation.
4. Record what should be kept, changed, retired, or tested next.
5. Link all artifacts.
6. Update `PROJECT_PLAN.md` and its Decision Log.
7. Commit the completed experiment record with the relevant code and tests.

## 7. Phase rules

Every experiment must be divided into phases. Each phase must contain:

- objective,
- status,
- required inputs,
- concrete tasks,
- output artifacts,
- verification checks,
- entry criteria,
- exit criteria,
- measured result,
- decision,
- next action.

Only one phase may be `IN_PROGRESS` at a time.

At the end of every phase, before starting the next phase:

1. update the phase status,
2. check completed tasks,
3. record actual metrics and evidence,
4. document deviations and unexpected findings,
5. update risks and assumptions,
6. state whether the exit criteria passed,
7. update the overall experiment status,
8. specify the next smallest action,
9. update `PROJECT_PLAN.md` if the finding affects project scope, gates, risks, or priorities,
10. create a Git commit.

Do not leave several completed phases marked `IN_PROGRESS` and update them retrospectively at the end.

## 8. Pre-registration standard

Before viewing the final evaluation result, the plan must specify:

- primary hypothesis,
- unit of analysis,
- population and exclusions,
- train/validation/test dates or the rule that determines them,
- baseline models,
- primary metric,
- secondary metrics,
- economic cost assumptions,
- sample-size or effective-sample-size expectation,
- acceptance threshold,
- rejection threshold,
- inconclusive region,
- segmentation allowed in the primary analysis,
- multiple-testing treatment,
- missing-data policy,
- outlier/anomaly policy,
- random seed or reproducibility rule,
- stress-test scenarios.

If a threshold cannot yet be chosen because input data has not been characterized, register the exact preliminary analysis that will determine it. Once fixed, commit the threshold before the decisive test.

Post-hoc analysis is allowed only when clearly labeled `EXPLORATORY`. It cannot convert a failed primary experiment into a passed experiment. A promising exploratory result must become a new experiment ID and be tested out of sample.

## 9. Evidence standard

Claims must point to evidence that can be found from the plan.

Each experiment should link to relevant:

- source code,
- config files,
- dataset manifests,
- schema versions,
- notebooks,
- tables and plots,
- test commands and results,
- model artifacts,
- logs or run IDs,
- commit hashes,
- external primary documentation.

Do not use terminal output as the only durable evidence.

Minimum result record:

```text
Data cut-off:
Dataset version:
Code commit:
Config/run ID:
Sample size:
Effective sample size or clustering unit:
Primary metric result:
Baseline result:
Uncertainty interval:
Economic assumptions:
Known limitations:
```

## 10. Project-memory rules

The experiment history is append-oriented.

- Do not delete failed hypotheses.
- Do not erase old metric values when a rerun changes them.
- Add a new dated update and explain the reason for the rerun.
- Mark invalid results as `INVALIDATED`; link the finding that invalidated them.
- Mark replaced decisions as `SUPERSEDED`; link the replacing experiment or decision.
- Preserve material deviations from the original plan.
- Record null results and data-access failures.
- Link related experiment IDs in both directions.
- Distinguish `Observed`, `Inferred`, and `Unknown` statements.

Every `PLAN.md` must include an append-only Update Log and Decision Log.

## 11. Git and commit protocol

### Required commit points

Create a commit at minimum:

1. when the experiment plan becomes `READY`,
2. after each phase reaches a terminal phase status,
3. when a blocker materially changes the plan,
4. when thresholds or scope are changed,
5. when the experiment is closed.

### Commit content

A phase-completion commit should include, as applicable:

- updated `PLAN.md`,
- code/config changes,
- tests,
- lightweight evidence artifacts,
- updated `PROJECT_PLAN.md`.

Do not commit:

- credentials or tokens,
- private keys,
- personal access details,
- large raw datasets without an approved storage policy,
- generated caches,
- notebook secrets,
- unlicensed proprietary data.

### Commit message format

Use the experiment ID in every experiment commit:

```text
experiment(EXP-YYYYMMDD-slug): register plan
experiment(EXP-YYYYMMDD-slug): complete phase 1 data validation
experiment(EXP-YYYYMMDD-slug): record blocked data source
experiment(EXP-YYYYMMDD-slug): close as inconclusive
```

Commit rules:

- One commit should represent one coherent research transition.
- Do not bundle unrelated experiments.
- Never rewrite published experiment history merely to hide a failure.
- Before committing, inspect `git diff`, run relevant tests, and verify no secret or large-data file is staged.
- Commit author must use the repository owner's configured identity.
- Push only when the remote and authentication are intentionally configured.

## 12. Relationship with `PROJECT_PLAN.md`

`PROJECT_PLAN.md` is the project-level roadmap. Individual `PLAN.md` files are experiment-level memory.

Update `PROJECT_PLAN.md` whenever an experiment:

- changes a phase or gate status,
- changes city, station, market, or provider scope,
- adds or retires a primary hypothesis,
- changes a risk assessment,
- changes the next priority,
- affects live-readiness or capital risk,
- produces a decision that other experiments depend on.

The project plan should contain a short decision and link to the detailed experiment. Do not duplicate every experiment detail in the project plan.

## 13. Experiment index

Maintain an index at `docs/experiments/README.md` once the first experiment is created.

The index must contain:

| Experiment ID | Title | Status | Started | Completed | Primary decision | Plan |
|---|---|---|---|---|---|---|

Update the index in the same commit as any experiment status change.

## 14. `PLAN.md` required template

Use the following structure for every experiment. Sections may be expanded but not silently removed. Use `Not applicable — <reason>` when a section does not apply.

```markdown
# EXP-YYYYMMDD-short-slug — Experiment title

**Status:** `DRAFT`
**Owner:** Abdullah Sezdi
**Created:** YYYY-MM-DD
**Last updated:** YYYY-MM-DD
**Project phase:** Phase N
**Related hypotheses:** HN
**Related experiments:** None
**Data cut-off:** Not set
**Decision commit:** Not yet available

## 1. Executive summary

What this experiment will decide and why that decision matters.

## 2. Primary hypothesis

One falsifiable sentence.

## 3. Motivation and economic mechanism

- Expected source of edge or research value:
- Why the effect may exist:
- Why the market may not already price it:
- Expected edge decay:
- Capacity constraints:

## 4. Scope

### Included

- Markets:
- Cities/stations:
- Date range:
- Lead times:

### Excluded

- Explicit exclusions and reasons:

## 5. Unit of analysis and sample

- Unit of analysis:
- Sampling rule:
- Expected sample size:
- Clustering unit:
- Exclusion rule:
- Survivorship-bias control:

## 6. Data contract and provenance

| Dataset | Source | Version | Availability timestamp | Required fields | Known limitations |
|---|---|---|---|---|---|

### Data-quality gates

- [ ] Timestamp semantics verified
- [ ] Timezone and DST verified
- [ ] Units and station mapping verified
- [ ] Missingness measured
- [ ] Duplicates measured
- [ ] Leakage checks passed
- [ ] Rule and outcome mapping manually sampled

## 7. Experimental design

- Train period:
- Validation period:
- Locked test period:
- Walk-forward protocol:
- Random seed:
- Missing-data policy:
- Outlier/anomaly policy:
- Multiple-testing policy:

## 8. Baselines and counterfactuals

| ID | Baseline | Rationale | Implementation/version |
|---|---|---|---|

## 9. Methods

Describe models, features, transformations, calibration, and execution assumptions precisely enough to reproduce them.

## 10. Metrics and pre-registered decision gates

### Primary metric

- Metric:
- Acceptance threshold:
- Rejection threshold:
- Inconclusive region:

### Secondary metrics

- Metric and purpose:

### Economic assumptions

- Executable price definition:
- Fee schedule/version:
- Slippage:
- Latency:
- Fill model:
- Rebate assumption:

## 11. Risks and invalidation conditions

| Risk | Detection | Mitigation | Invalidation condition |
|---|---|---|---|

## 12. Phased execution plan

### Phase 0 — Pre-registration

**Status:** `IN_PROGRESS`

- Objective:
- Entry criteria:
- Tasks:
  - [ ] Task
- Outputs:
- Verification:
- Exit criteria:
- Actual result: Pending
- Decision: Pending
- Next action:

### Phase 1 — Data validation

**Status:** `NOT_STARTED`

- Objective:
- Entry criteria:
- Tasks:
- Outputs:
- Verification:
- Exit criteria:
- Actual result: Pending
- Decision: Pending
- Next action: Pending

### Phase 2 — Implementation

**Status:** `NOT_STARTED`

Use the same required phase fields.

### Phase 3 — Evaluation

**Status:** `NOT_STARTED`

Use the same required phase fields.

### Phase 4 — Stress testing and closeout

**Status:** `NOT_STARTED`

Use the same required phase fields.

## 13. Results

### Primary result

Pending.

### Segment results

Pending.

### Robustness and stress tests

Pending.

### Deviations from plan

None at registration.

## 14. Interpretation

### Observed

Pending.

### Inferred

Pending.

### Unknown

Pending.

## 15. Final decision

- Final status: Pending
- Gate outcome: Pending
- What changes in the project: Pending
- What does not change: Pending
- Follow-up experiment: Pending

## 16. Artifact index

| Artifact | Path/run ID | Version/commit | Purpose |
|---|---|---|---|

## 17. Update Log — append only

### YYYY-MM-DD — Plan created

- Previous status: None
- New status: `DRAFT`
- Work completed:
- Evidence:
- Deviations:
- Blockers:
- Next action:

## 18. Decision Log — append only

### ED-0001 — YYYY-MM-DD — Initial registration

- Decision:
- Evidence available at decision time:
- Alternatives considered:
- Consequence:
- Revisit condition:
```

## 15. Phase completion checklist

Before marking any phase complete:

- [ ] The plan reflects what was actually done.
- [ ] Required tasks are checked or explicitly deferred.
- [ ] Data and code versions are recorded.
- [ ] Primary metrics are recorded where applicable.
- [ ] Evidence artifacts are linked.
- [ ] Unexpected findings and deviations are documented.
- [ ] Exit criteria have an explicit pass/fail/inconclusive result.
- [ ] The next action is singular and actionable.
- [ ] Overall experiment status is updated.
- [ ] Experiment index is updated.
- [ ] `PROJECT_PLAN.md` is updated if project-level consequences exist.
- [ ] Relevant tests pass.
- [ ] Staged files contain no secrets or inappropriate data.
- [ ] A coherent commit is created with the experiment ID.

## 16. Experiment closeout checklist

Before closing an experiment:

- [ ] Primary hypothesis has a clear disposition.
- [ ] Primary gate is evaluated without post-hoc rewriting.
- [ ] Economic and statistical significance are separated.
- [ ] Confidence interval or uncertainty is reported.
- [ ] Segment concentration is reported.
- [ ] Stress tests are complete or explicitly not applicable.
- [ ] Limitations and unknowns are listed.
- [ ] Final status is terminal.
- [ ] Follow-up work has a new experiment ID when appropriate.
- [ ] Project Decision Log is updated.
- [ ] Final artifacts and commit hash are linked.
- [ ] Final experiment commit is created.

## 17. Anti-patterns

The following are prohibited:

- running the decisive test before registering thresholds,
- selecting the best city/segment on the test set and calling it confirmatory,
- using revised forecasts or reanalysis as if available in real time,
- treating midpoint as executable price,
- omitting failed runs from the experiment record,
- changing a failed acceptance threshold after seeing the result,
- reporting only win rate or gross P&L,
- leaving result evidence only in a notebook output or terminal,
- marking an experiment `PASSED` because implementation completed,
- starting the next phase without updating and committing the current phase,
- committing secrets, credentials, private keys, or unapproved raw data,
- rewriting published Git history to conceal an invalidated result.

## 18. Definition of done

An experiment is done only when:

- its status is terminal,
- its original plan and deviations are visible,
- its data and code lineage are reproducible,
- its registered gates are evaluated,
- its evidence is linked,
- its conclusions distinguish observation from inference,
- its effect on the project roadmap is recorded,
- its index entry is current,
- its final commit exists.
