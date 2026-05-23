# Issue tracker

**Current**: local TODO file (`TODO.md`) — formal tracker not yet wired.

## Status

| Tracker | Status | Notes |
|---|---|---|
| Orchestra MCP | not wired | future option for multi-session task coordination |
| Linear | not used | — |
| Jira | not used | — |
| GitHub Issues | reserved | will be enabled when repo goes public on `github.com/pollmevals` |
| Local `TODO.md` | **active** | single-user / single-machine until v0.2 launch |

## Convention

Until a formal tracker is wired, track tasks in `TODO.md` at the repo root using this format:

```markdown
- [ ] [ARTIFACT-ID] short description (status: blocked/in-progress/review)
- [x] [PRD-001] example completed task
```

If a task has no matching forgeplan artifact, omit the `[ARTIFACT-ID]` prefix and tag instead:

```markdown
- [ ] (chore) update Moon toolchain to latest stable
```

## Migration triggers

Switch to a real tracker when **any** of:

- A second contributor joins (single-user TODO no longer enough).
- Tasks span >2 weeks (need due dates + reminders).
- Need stakeholder visibility (PRD reviewers, sponsors).
- A weekly run cadence starts (need scheduled work items).

Default recommendation when migrating: **GitHub Issues** (free, public, integrates with `gh` CLI used elsewhere). Linear if private-only.

## Sync with forgeplan

When a tracker is wired:

1. `forgeplan new prd "..."` → create matching tracker task `[PRD-NNN] description`
2. `forgeplan activate <id>` → mark tracker task Done
3. Tracker offline → record sync intent in `TODO.md` and reconcile later
