# EXP-20260830 Phase 3 — Restart-safe stability runner smoke tests

**Status:** `PASSED` for runner readiness; 24-hour gate not evaluated  
**Data cut-off:** 2026-08-30T11:43:52Z  
**Capital/orders:** none; public read-only market data only

## Hypothesis and pre-run checks

Hypothesis: the long-run collector can checkpoint useful uptime and coverage, issue heartbeat,
periodically reconcile replayed state with REST, and resume the same run after process interruption
without reusing pre-reconnect book state.

The runner is ready to start the 24-hour test only if short probes demonstrate:

- 12/12 authoritative books and nonzero real deltas;
- periodic checkpoints and REST anchors;
- zero delta-before-base and replay-top contract violations;
- successful restart from the same summary with a new connection/full-book base; and
- raw files separated by connection without overwrite.

Short probes cannot pass the 86,400-second stability gate.

## 25-second operational smoke

- Full books: 12/12.
- Price-change events / applied changes: 36 / 72.
- Heartbeat PING/PONG: 2/2.
- Checkpoints ready: 4/4.
- REST anchors: 2, covering 24 asset comparisons.
- REST hash-or-top matches: 24/24.
- Connection/replay errors: 0/0.
- Useful ready uptime: 98.674%; the roughly 0.33-second initial base acquisition is material only
  because this probe lasted 25 seconds.

The result correctly emitted `accepted=false`: it did not meet the immutable minimum elapsed time
of 86,400 seconds.

## Interruption/resume smoke

A separate 20-second target run was interrupted after approximately five seconds and resumed from
its last atomic checkpoint using `--resume`.

- The resumed process preserved the original start and target-end timestamps.
- It created connection 2 and acquired 12 fresh full books; total full-book events became 24.
- Six ready checkpoints were retained across the two processes.
- No delta-before-base, advertised-top or connection error was recorded.
- No raw connection file was overwritten.
- Metrics between the last checkpoint and forced process termination are conservatively absent.
  With 60-second production checkpoints, unexpected hard termination can therefore lose at most
  approximately one checkpoint interval of aggregate counters, while already flushed raw frames
  remain on disk.

This short resume test had no scheduled REST anchor after restart and correctly remained
`accepted=false` because it lasted only 20 seconds.

## Metric definitions locked for the long run

- **Useful uptime:** seconds during which the current connection has authoritative full books for
  every selected asset, divided by wall-clock elapsed seconds.
- **Checkpoint coverage:** 60-second checkpoints with every selected asset ready, divided by all
  scheduled checkpoints written.
- **REST anchor match:** asset comparisons where replay state matches fresh REST by exact hash or
  executable top of book.
- **Gap diagnostic:** maximum local receipt-time gap between consecutive frames. It is not a server
  sequence-gap proof because the public protocol exposes no validated resumable sequence here.
- **Raw bytes:** UTF-8 bytes of flushed immutable WebSocket envelope lines; REST-anchor storage is
  measured from persisted files at final analysis.

## Decision

The runner-readiness smoke is `PASSED`. It authorizes starting—not passing—the registered 24-hour
capture. Production parameters are 12 assets, 86,400 seconds, 60-second checkpoint, 300-second REST
anchor, 15-second initial-base timeout and exponential reconnect backoff capped at 30 seconds.
