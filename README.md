# Polymarket Weather Quant Research

Data-driven research into whether selected Polymarket daily weather markets contain a repeatable, execution-aware probability edge for a small-capital niche strategy.

This project does not assume that an edge exists. Its purpose is to test that claim with timestamp-correct forecasts, station-specific observations, executable order-book prices, realistic fees/fills, and walk-forward out-of-sample evaluation.

## Research principles

- Preserve point-in-time correctness and data provenance.
- Optimize net expected value, not forecast accuracy alone.
- Use executable bid/ask depth rather than displayed midpoint prices.
- Pre-register hypotheses, metrics, and decision gates.
- Keep failed and inconclusive experiments as project memory.
- Do not enable live trading before the project readiness gates pass.

Read [AGENTS.md](AGENTS.md), [PROJECT_PLAN.md](PROJECT_PLAN.md), and [docs/agents.md](docs/agents.md) before making material changes.

## Repository layout

```text
configs/                 Versioned runtime and experiment configuration
data/                    Raw, interim, processed, and external data layers
docs/                    Research-memory and experiment-planning standards
experiments/             Machine-readable experiment registry
notebooks/               Reproducible exploration and presentation notebooks
reports/                 Durable research, data-quality, and backtest reports
src/weather_quant/       Production Python package
tests/                   Unit, contract, and smoke tests
```

Raw and generated datasets are ignored by Git. Their manifests and schemas should be committed instead.

## Environment

Python 3.9 or newer is required. The project uses a `src/` package layout and keeps runtime dependencies minimal during bootstrap.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[dev]'
```

## Verification

The bootstrap smoke test uses only the Python standard library:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The smoke test verifies the minimal config → normalization → feature → evaluation path. It is infrastructure verification, not evidence of a trading edge.

## Experiment workflow

Material research work must be registered under:

```text
docs/experiments/EXP-YYYYMMDD-short-slug/PLAN.md
```

Each phase must update status, evidence, decision, and next action before the corresponding Git commit. See [docs/agents.md](docs/agents.md) for the required template and lifecycle.

## Safety

- Never commit credentials, wallet material, API tokens, private keys, or proprietary data.
- Never use reanalysis or revised forecasts as point-in-time forecasts.
- Never treat paper trading as live evidence.
- No live orders are authorized by this repository bootstrap.

## Current status

Phase 0 — research and reproducibility infrastructure. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the active gate and next action.
