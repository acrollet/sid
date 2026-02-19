# Pippin Improvement Plan

Recommendations for making Pippin more effective as an AI-agent bridge to the iOS Simulator. Organized into independent workstreams that can be tackled in any order, though the suggested priority reflects impact.

## Priority Order

| # | Workstream | File | Impact | Effort |
|---|-----------|------|--------|--------|
| 1 | [Preserve UI hierarchy in inspect](#1-hierarchy) | [01-hierarchy.md](01-hierarchy.md) | Critical | Medium |
| 2 | [Fix subcommand help](#2-help) | [02-subcommand-help.md](02-subcommand-help.md) | High | Small |
| 3 | [Composite context command](#3-context) | [03-context-command.md](03-context-command.md) | High | Medium |
| 4 | [Consistent exit codes & error model](#4-errors) | [04-error-model.md](04-error-model.md) | High | Small |
| 5 | [Multi-simulator support](#5-device) | [05-device-targeting.md](05-device-targeting.md) | Medium | Small |
| 6 | [Smarter element matching](#6-matching) | [06-element-matching.md](06-element-matching.md) | Medium | Medium |
| 7 | [Action feedback loop](#7-feedback) | [07-action-feedback.md](07-action-feedback.md) | Medium | Small |
| 8 | [Code quality & housekeeping](#8-housekeeping) | [08-housekeeping.md](08-housekeeping.md) | Low | Small |

## Guiding Principles

- **One call should be enough to orient.** AI agents burn tokens and latency on every round-trip. Minimize the number of calls needed to understand the current state.
- **Structure over flatness.** Hierarchy, breadcrumbs, and parent-child relationships are how both humans and AIs reason about UIs.
- **Fail loudly, fail consistently.** Every command should use exit codes and structured error output the same way, so the agent can programmatically detect and recover from failures.
- **Don't break existing workflows.** New flags and commands are additive. Where defaults change, the old behavior should remain available via a flag.
