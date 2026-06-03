# HANDOFF — 2026-06-03 (harness batch session)

> Pick-up doc for a fresh session. **Continues** `HANDOFF-2026-06-03.md` (which
> ended with "harness batch = next task"). This session DID the harness batch:
> the leaderboard went from **2 → 8 harness columns**. Read this, then
> `forgeplan health`, `git log --oneline -15`, and the memory notes
> `research-cli-harness-execution` (all recipes + the tool-parser finding) +
> `project-executor-build-plan` (the v0.2 plan).

---

## 1. TL;DR — where we are

POLLMEVALS evaluates **stacks = model × harness × scaffolding (L0–L8)**. The
public board now shows a **real** leaderboard from a live executor + judge panel.

- **board.json on main**: `45 cells, 32 scored`, **8 harness columns** — raw-llm
  (L0) · goose (L2) · aider (L4) · opencode (L4) · crush (L2) · PI (L2) · gptme
  (L4) · mini-swe (L7). One task scored: `be_01_jwt_auth`.
- **The harness FRAMEWORK is complete.** Adding a harness is now a proven
  ~1-hour slice (image + recipe + stack.yaml + a scored run). 8 done, the
  pattern is mechanical.
- **This session's merges: #53** goose · **#54** opencode + the config_files
  launcher · **#55** crush · **#56** cline (recipe; column deferred) · **#57**
  PI + gptme + mini-SWE wave.
- **The next phase is v0.2** (scale + judge rigor) — see §3. It's a
  methodology-bump + a big re-score, deserves a clean session.

---

## 2. The harness × model COMPAT MATRIX — and the key finding

The **product** (user's framing) is the compat matrix: *which harness, with which
model, solves the task — to find a CHEAP model + harness that matches an EXPENSIVE
model, so you don't buy expensive models.* A thin/failed cell is honest DATA.

Results on `be_01` (the 4 coder models each harness was first run on):

| harness | scored | layer | note |
|---|---|---|---|
| aider | 4/4 | L4 | most tolerant (text edit-format) |
| goose | 3/4 | L2 | codestral fail |
| crush | 3/4 | L2 | devstral fail |
| opencode | 1/4 | L4 | needs native tool_calls |
| PI | 3/4 | L2 | **native-tool models only** (devstral/codestral/qwen3-235b) |
| gptme | 1/4 | L4 | no turn cap → verify-loop timeouts |
| mini-swe | 2/4 | L7 | textbased loop |
| cline | 0/4 | L2 | column deferred (proxy responses-API friction) |

### ★ THE TOOL-CALL-PARSER FINDING (explains the whole matrix)

A model's **proxy/vLLM backend** decides whether it emits **native OpenAI
`tool_calls`** vs **text-format** tool calls (XML / markdown fences):

- **qwen3-coder-30b emits TEXT** (its OpenRouter backend has no
  `--tool-call-parser`) → **native-tool harnesses (opencode, PI) no-op on it**
  (this is why opencode is 1/4!).
- **Native-tool models on our proxy**: `devstral`, `codestral`, `qwen3-235b`,
  `glm-4-32b` (verified via a raw `/v1/chat/completions` probe).
- **Text-tolerant harnesses** (aider edit-format, goose, crush, gptme,
  mini-SWE-with-`litellm_textbased`) work on text-format models.

→ Run native-tool harnesses (opencode/PI) ONLY on native-tool models; text-
tolerant ones on the coders. The fix (enable the vLLM tool-parser) is on the
OpenRouter side, out of our control — so prefer the text-tolerant harnesses for
those models.

---

## 3. THE ACTIVE NEXT PHASE — v0.2 "sweet-spot finder" (4 axes)

A coherent methodology + scale phase. **It's a MethodologyVersion bump → re-scores
the whole board**, so do it in a clean session with an ADR first.

1. **ADR methodology-v0.2** (do FIRST — `forgeplan new adr`, run FPF per
   [[feedback-adi-fpf-on-disputes]]): **stronger + more judges** (user emphasized
   2×) — the MOST powerful models (claude-opus-4-8 / gpt-5-full / gemini-2.5-pro),
   a 5-judge panel; **more criteria** incl. **linting + typing**. NOTE: the
   methodology ALREADY defines automatic `lint` + `type_safety` metrics
   (CONTEXT.md coding formula: 0.10 lint + 0.10 type_safety) — be_01 is judge-only
   now, so wire the deterministic eslint/tsc metrics in AND add linting to the
   judge rubric.
2. **`--fill-missing` mode** in `build_real_board.py` — run ONLY un-scored
   (model, stack) cells (today's `--add-stack` re-runs a whole column = wasteful
   $). This is the lever to fill the grid cheaply.
3. **Fill the grid** — every harness × every viable model + **stronger OpenRouter
   models** (cheap→frontier coders, curated so the sweet-spot is visible). Honest
   "—" where the tool-parser finding says a harness can't run a model.
4. **Vendor trio** (recipes ready, see §5): **codex** via codex-relay on OPEN
   models · **claude-code** × claude-opus-4-8 · **gemini-2.5-pro** × goose.

**Self-judging rule (clarified with the user):** the cardinal sin is a model
judging the EXACT same model. A candidate CAN be from a judge's family — so
`claude-opus-4-8` candidate + `claude-sonnet-4-6` judge is fine (opus ≠ sonnet),
**no panel change needed** for the vendor trio.

---

## 4. HOW TO ADD A HARNESS (the proven pattern, ~1h)

1. **Image** — `infra/docker/harness-<cli>/Dockerfile`, mirror an existing one:
   - slim base (`python:3.12-slim` for pip/Go-binary harnesses; `node:22-slim`
     for npm harnesses — note node already has a uid-1000 `node` user, reuse it;
     python has none → `useradd --create-home --uid 1000 harness`).
   - install the CLI **pinned** (direct binary download for Go/Rust binaries —
     the official installer scripts often lack the arm64 asset; npm/pip for the
     rest). Pre-bake anything fetched at runtime (the sandbox has NO egress except
     the proxy — e.g. gptme's tiktoken cache).
   - git + identity + `safe.directory /workspace`; CMD = a version probe.
   - `make harness-image-<cli>` target.
2. **Smoke FIRST, in isolation** (the risky part is the recipe, not the image):
   `docker run --network=pollmevals-sandbox --cap-drop=ALL ... -v <tmp>:/workspace
   -e LITELLM_MASTER_KEY=<from .env> <image> <headless cmd> "Create hello.txt ..."`
   → confirm the file lands in the **mounted** /workspace on a **capable** model
   (qwen3-coder-30b for text-tolerant; devstral for native-tool). Iterate.
3. **Recipe** — `_<cli>_invocation` in `apps/eval-core-py/src/orchestrator/
   stack_executor.py` → add to `_PROVEN_RECIPES`, remove from `_PENDING_RECIPES`.
   `ProxyInvocation(env, config_files, extra_args, prompt_args)`. Put ALL flags in
   the recipe (stack.yaml `args: []`) to avoid duplication. Config files ride
   `config_files` (the launcher writes them into /workspace BEFORE the base commit
   → harness finds them + excluded from the patch). Keep the harness's runtime
   state (sessions/db/trajectory) OUT of /workspace (/tmp or $HOME).
4. **stack.yaml** — `stacks/<cli>/stack.yaml` (command + L-layers). `validate-
   stacks` must pass.
5. **Tests** — a recipe-proven test + update `supported_harnesses`. `moon run
   eval-core-py:test` green; `ruff` + `mypy --strict` clean.
6. **Run** — add to `build_real_board.py` `_STACK_MODELS` (the model list — use the
   tool-parser finding) → `python build_real_board.py --add-stack <cli> --confirm-
   spend` merges the column into board.json (no re-spend on the rest).
7. **Verify** (Playwright) → PR → squash-merge.

### ⚡ Parallelize via agents (the big speed/context win)

The slow part is per-harness **recipe discovery** (iterative Docker debugging —
crush took ~6 iterations, cline several). **Delegate build+smoke to N concurrent
general-purpose agents** — they do the Docker debugging in THEIR context (offloads
it from yours), each returns the proven Dockerfile + recipe + smoke result. You
(lead) integrate the shared files (stack_executor.py / Makefile / tests) + run the
scored runs SERIALLY (board.json + proxy/judges + Docker memory can't parallelize).
Used this session for the Cline/pi/gptme/mini-SWE wave — it works. Limit to ~3-4
concurrent (Docker-VM memory; 2g/container; no obs stack). Agents read the key from
the absolute `.env` path and write to the shared cwd (not worktrees).

---

## 5. VENDOR TRIO — recipes (ready; build next)

- **codex** (image built, branch `feat/harness-codex`): responses-only +
  emits OpenAI-native tools (`web_search`/`namespace`) the open backend rejects
  (#18330 WONTFIX; OpenRouter doesn't dodge it). **Fix = `codex-relay` sidecar**
  (`pip install codex-relay`, MetaFARS/codex-relay) in the sandbox net: translates
  Responses→Chat + strips tools via `CODEX_RELAY_TOOL_DENYLIST=web_search,namespace,
  datetime,image_generation,view_image`. Point codex's config.toml at the relay
  (`wire_api=responses`, base_url=relay). Then codex runs OPEN models → no
  self-judging. (Alt: native OpenAI key, model `gpt-5.4-mini`.)
- **claude-code**: native Claude via OUR proxy works (`ANTHROPIC_BASE_URL=proxy
  ANTHROPIC_API_KEY=$LITELLM_MASTER_KEY claude --bare -p "<prompt>" --model
  claude-opus-4-8 --permission-mode acceptEdits --allowedTools "Read,Edit,Write,
  Bash" --max-turns 30 --output-format json`). **`--output-format json` returns
  `total_cost_usd` → real cost!** Use `claude-opus-4-8` (≠ the claude-sonnet
  judge → existing panel works). **Add claude-opus-4-8 to the proxy's `/v1/messages`
  route** in `infra/litellm-config.yaml` first (sonnet-4-6 is already on it; opus
  needs adding). qwen breaks claude-code (32MB bug) — Claude/GPT/Gemini only.
- **gemini**: gemini-CLI is **retiring 2026-06-18** (closed Antigravity, no BYO-
  endpoint) → DROP the CLI. Run **`gemini-2.5-pro` (not a judge) × goose** (an
  agnostic harness) for a clean Gemini-model column instead.

---

## 6. DEV WORKFLOW (non-negotiable)

- **Branch per slice** (one harness or wave = one branch/PR). Never commit to
  `main` (red-line). Fewer, larger PRs.
- **lefthook pre-commit** runs secret-scan / format-py / format-ts / `moon
  :typecheck` (only when .ts/.tsx staged) / forgeplan-validate. **Never
  `--no-verify`** (red-line).
- **Board run cheatsheet** (prereqs: `make stack-up` [NOT obs-up — OOM] +
  `make sandbox-net-up` + `make harness-image-<cli>`):
  ```
  uv run --project apps/eval-core-py python apps/eval-core-py/scripts/build_real_board.py --add-stack <cli> --confirm-spend
  #   or --fill <models>  (re-run named models on raw-llm, merge)
  ```
  `--add-stack` merges ONE harness column (cells + harness metadata) into
  board.json. `max_concurrent=3`. Real $ (judges ~$0.04/eval); flag the cost.
- **Verify viz in a clean browser (Playwright)** before merge (source of truth
  for hydration; extensions cause false errors → `suppressHydrationWarning`).
- **forgeplan artifacts via MCP only**. Sub-agents can orphan files / run in
  worktrees → do sensitive writes (forgeplan, board) in the main thread.

---

## 7. HARD-WON GOTCHAS (do not re-learn)

- **Tool-parser finding** (§2) — the master gotcha. Native-tool vs text-format.
- **arm64 binaries**: official installer scripts (goose `download_cli.sh`) fall
  back to mirrors lacking the arm64 asset → **download the pinned tarball
  directly** (arch via BuildKit `TARGETARCH`). codex = musl (static, runs on
  glibc); crush/goose = direct release binary.
- **no-egress runtime baking**: the sandbox reaches ONLY the proxy. Anything a CLI
  fetches at runtime FAILS → bake it at build (gptme's tiktoken `cl100k/o200k`
  cache; npm/pip providers). opencode's built-in `openai` provider is bundled (no
  fetch); its `@ai-sdk/openai-compatible` would fetch (avoid).
- **config location is usually $HOME, not /workspace** — pi (`PI_CODING_AGENT_DIR`),
  crush (`CRUSH_GLOBAL_CONFIG` is a DIRECTORY!), gptme ($HOME, so use env-only).
  Point the config env at /workspace OR use env-only.
- **secrets not in files**: pass the key as a literal `$LITELLM_MASTER_KEY` /
  `"$LITELLM_MASTER_KEY"` the in-container shell/CLI expands — never write the
  key into a config file (crush/cline/pi do this).
- **runtime state out of /workspace** so it's not in the patch: crush
  (`CRUSH_GLOBAL_DATA=/tmp`), cline (data-dir default ~/.cline), mini-swe
  (`-o /tmp/...`). pi config rides config_files (pre-base → not in diff).
- **exit codes are unreliable** — the PATCH is the signal (cline wraps `|| true`;
  pi/gptme exit 0 on no-op; gptme/cline timeout-kill still yields a valid patch
  written before the verify loop). Don't add an exit-code gate.
- **headless guards**: goose `GOOSE_DISABLE_KEYRING=1` + `GOOSE_MODE=auto`;
  mini-swe `MSWEA_CONFIGURED=true` + `MSWEA_COST_TRACKING=ignore_errors` (proxy $0
  → else RuntimeError); codex `--dangerously-bypass-approvals-and-sandbox` (its own
  sandbox needs caps we drop). mini-swe `--environment-class local` (NO nested
  Docker). mini-swe: any `-c` REPLACES the default config → re-add the builtin first.
- **cost=$0 on all harness cells** — harness self-report metering only works for
  aider (it prints a Tokens line). The real fix = **proxy-side cost
  reconciliation**: LiteLLM `/spend/logs` returns real per-request tokens by
  `model_group`; apply our `_PRICING`. CAVEAT: needs pagination + a flush-delay
  (latest calls aren't logged immediately) → its own slice. Renders honestly as
  "—" (`formatCost(0)`).
- **Docker (macOS)**: socket `~/.docker/run/docker.sock` (auto-discovered). `make
  stack-up` ONLY (obs-up OOMs everything). Proxy restart after editing
  litellm-config → poll `/health/readiness` (30-60s warm; "Remote end closed" is
  warming, not a bug). DON'T restart the proxy while a scored run is using it.
- **Next.js hydration**: NEVER `toLocaleString()` in a rendered component (server
  locale ≠ browser) → deterministic grouping regex. `uv sync --all-extras` (bare
  prunes dev extra → mypy loses pydantic → 74 spurious errors blocking TS commits).

---

## 8. KEY FILES (map)

- **Executor**: `apps/eval-core-py/src/orchestrator/stack_executor.py` (8 recipes
  in `_PROVEN_RECIPES`, `_write_config_files` launcher, `DockerHarnessLauncher`),
  `stack_caller.py`, `stack_scoring.py`, `grid_runner.py`, `judge_panel.py`
  (`_EVAL_ASYNC_LOCK`).
- **Board**: `apps/eval-core-py/src/leaderboard/board.py` (`_STACK_FAMILY`,
  `_LAYER_ORDER`, unknown stacks → "agnostic"). TS mirror `apps/site/src/lib/
  board.ts`. Honest cost: `apps/site/src/lib/format.ts` `formatCost`.
- **Run**: `apps/eval-core-py/scripts/build_real_board.py` (`_STACK_MODELS`,
  `--add-stack`, `--fill`; ADD `--fill-missing` for v0.2).
- **Harness images**: `infra/docker/harness-{aider,goose,opencode,crush,cline,pi,
  gptme,mini-swe}/`. **Stacks**: `stacks/<cli>/stack.yaml`. **Makefile** harness
  targets. **Proxy**: `infra/litellm-config.yaml` (17 models + 3 judges).
- **Memory**: `research-cli-harness-execution` (ALL recipes + the tool-parser
  finding + the vendor recipes), `project-executor-build-plan` (v0.2 plan).
- **codex WIP**: branch `feat/harness-codex` (image built, recipe blocked → relay).

---

## 9. ONE-PARAGRAPH MISSION

Prove the thesis with numbers: *a cheap model with the right harness beats an
expensive one without it.* The unit is **harness × model**, scored per task on
quality / cost / reliability with a no-self-judging median panel + Krippendorff α
gate. The harness framework is DONE (8 columns). v0.2 fills the grid + upgrades
the judges (stronger models + more criteria) so the **sweet-spot** — the cheapest
(model × harness) matching an expensive model — becomes visible. Be honest with
the numbers (show "—" for unscored/unmetered, never fake a cell), keep the
methodology load-bearing (ADR for v0.2), and grow by running more harnesses ×
more models × more task types.
