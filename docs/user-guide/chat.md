# Natural-language authoring with MCP

VBAgent exposes durable problem authoring through Model Context Protocol (MCP).
Use either the built-in transparent terminal host or any external MCP-capable
host. Manual `vbagent author`, `vbagent chat`, and MCP tools use the same typed
application service, SQLite ledger, agent roles, quality gates, and accepted
artifacts.

## Use the built-in CLI chat

```bash
vbagent chat --output agentic/authoring
```

The configured default model (normally GPT-5.6 Luna) interprets natural
language at medium reasoning by default and invokes functions generated directly
from FastMCP discovery. Use `--reasoning-effort high` for more controller reasoning
or `--reasoning-effort low` to prioritize response speed; these settings do not
change the authoring agents. Medium and high are supported by
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna). Use
`--model gpt-5.6-terra` or `--model gpt-5.6-sol` when you deliberately want a
stronger chat model. The chat model does not generate problem artifacts; the
existing authoring agents still own every generation and quality stage.

The shell renders immediately without importing the Agents SDK, starting
FastMCP, or generating tool schemas. Those components initialize on the first
message or command that needs them. The chat model uses OpenAI tool search with
two deferred namespaces of fewer than ten functions each, so only relevant
tool definitions enter model context. See the
[official tool-search guide](https://developers.openai.com/api/docs/guides/tools-tool-search).

The terminal labels turns as `You:` and `VBAgent:` and renders their content,
every MCP tool call, validation error, and detached-worker I/O as formatted
JSON. Agent events are real objects with `event`, `agent`, `task`, and
`input`/`output` fields, not a JSON string containing another terminal panel.
Multiline content is displayed as `{"format": "text", "lines": [...]}` (or
`"format": "latex"` for LaTeX); the raw log preserves the original strings. The display has
no padded nested panels and never double-escapes the content.
Ordinary conversational answers are intentionally brief and avoid
decorative notation or LaTeX unless requested. Model/token usage stays on one
small line; `--verbose` restores profile/domain details.

The terminal applies the original message's intent after the deterministic plan.
An explicit request to create, generate, author, make, or produce problems
authorizes an immediate background start and emits a JSON event explaining that
decision. Plan/preflight/preview, show-before-starting, and ambiguous requests
emit one specific approval question and wait for `yes`, `confirm`, or `go ahead`.
Reply `no` or `not yet` to decline without cancelling the durable run.
The confirmation dispatches
without a second model turn or nested prompt. A live bottom toolbar polls SQLite
and shows the current item/stage, draft and accepted counts, checks in progress,
retry count, and short run ID. `drafted 3/5` means three distinct items have
produced a draft, including drafts that later need retries; `accepted 1/5`
means one has passed every required gate. Acceptance updates per item, not only
at run completion. Retrying items show the attempt number and latest failed
gate; `/status` includes the full failure reason. Default worker I/O streaming
prints new detached-agent input/output above the
prompt safely. A direct instruction to start or resume the identified run,
or compile existing results, authorizes that action during the same controller
turn. Permission is bound to that action and run; it does not carry over to later
requests or authorize review, rejection, or cancellation. If approval is needed,
the host asks the actual question and accepts ordinary yes/no replies. `/approve`
and `/decline` remain optional aliases. Terminal input never blocks inside an asynchronous tool call.
`--yes` is the explicit non-interactive override.

Useful terminal commands are `/tools`, `/status [RUN_ID]`, `/logs [RUN_ID]`,
`/results [RUN_ID]`, `/confirm [RUN_ID]`, `/approve`, `/decline`, `/clear`, and
`/exit`. A bare
`confirm` approves the displayed proposal, including a pending tool call;
`/confirm RUN_ID` starts a
persisted pending plan after reconnecting. Press Up to recall older submitted
messages and Down to move toward newer messages or restore a blank draft. A
single Ctrl+C cancels the active request and closes chat cleanly. Input history
is kept in memory for the current process and is not written to disk. For one
turn, use:

```bash
vbagent chat --message "Plan 20 JEE Main kinematics problems"
```

Single-turn mode does not approve consequential calls unless `--yes` is also
present. Planning never needs that flag because it makes no model calls.

### Compile existing problems or a selected subset

Say `Compile this to main.tex and PDF` for an immediate rebuild. To select human
files, say `Only include problems 6 and 7`. The controller uses the existing
`authoring_start` tool with `confirmed=true`, `rebuild_only=true`, and
`problem_numbers=[6, 7]`; no extra tool or second approval is needed for that
explicit interactive instruction. These are the numbers in
`agentic/generated/problem_6.tex` and `problem_7.tex`, not run-local ordinals.
Other source files remain untouched. A missing or unapproved selected problem
fails the rebuild rather than silently producing a different selection, and the
previous root document is preserved.

The same operation is available manually:

```bash
vbagent author continue --run-id RUN_ID --rebuild-only \
  --problem-number 6 --problem-number 7
```

The output is root-level `main.tex`, `main.pdf`, and `answer_key.tex`. A rebuild
is reported as a document build, never as a newly started generation. Active
workers already assemble these files automatically on completion. Saying
`Compile after completion` acknowledges that behavior; it does not authorize
starting a pending generation. If it has not started, chat asks directly whether
to start it.

## Start the server

The normal transport is stdio:

```bash
vbagent mcp --output agentic/authoring
```

Configure that command in an MCP-capable host:

```json
{
  "mcpServers": {
    "vbagent-authoring": {
      "command": "vbagent",
      "args": ["mcp", "--output", "agentic/authoring"]
    }
  }
}
```

The output directory is fixed when the server starts. Tool callers cannot pass
arbitrary output or syllabus paths. This keeps natural-language calls inside
one controlled authoring workspace. Built-in JEE Main catalogs cover
Mathematics, Physics, and Chemistry; built-in NEET catalogs cover Physics,
Chemistry, and Biology. Use the manual CLI for a custom catalog file.

For a local HTTP client, `--transport sse` and `--transport streamable-http`
are also available and bind to `127.0.0.1:8000` by default. Do not expose an
unauthenticated local server to a public network.

## Conversation workflow

Ask the MCP host naturally, for example:

> Plan 40 JEE Main Physics questions from Kinematics, balanced between
> projectile motion and relative velocity, with 30 single-correct MCQs and 10
> integer questions, mostly medium with some hard questions, and 20% diagrams.

Or target a narrow Mathematics concept using its familiar name:

> Plan one JEE Main Mathematics single-correct MCQ on the greatest integer
> function, and keep that phrase as a required concept.

The server instructions guide the host through this sequence:

1. search directly when exam and subject are known, or list catalogs first only
   when either is missing or ambiguous;
2. request chapter summaries only when search needs browsing or disambiguation;
3. request a bounded topic page only for the selected chapter;
4. create a deterministic plan without model calls;
5. show the resolved distributions, warnings, and estimated model-call count;
6. treat a direct creation instruction as authorization, otherwise ask for
   confirmation;
7. start a detached durable worker only after that authorization;
8. poll status and page through item summaries;
9. read selected authored content with its accepted/draft/review status, and
   inspect detailed evidence only when needed;
10. inspect bounded worker-agent I/O without treating terminal logs as state.

Planning persists the immutable run but spends no model tokens. The start and
resume tools require `confirmed=true`; this means the host has a direct user
instruction for the action or a later explicit confirmation. Calls without
either form of authorization fail.
Workers continue after the MCP connection closes, and reconnecting clients can
recover progress from the run ID.

The existing authoring completion path—not an additional MCP tool—publishes
numbered problem files and assembles `main.tex`, extracts `answer_key.tex`, and
compiles `main.pdf`. With the default workspace they are written directly to:

```text
agentic/generated/problem_1.tex
agentic/generated/problem_1.json
agentic/generated/problem_2.tex
main.tex
answer_key.tex
main.pdf
```

`authoring_status` returns that directory plus `manifest.json`, build status,
and the exact root-level main/answer/PDF paths. The built-in chat monitors a
detached run and, after the worker finishes this assembly, displays the full
LaTeX and tells the user where it was saved. It automatically displays at most
20 artifacts for a large run; `/results RUN_ID` deliberately streams every
authored artifact in full, with its validation status. Review-pending files are
preserved but excluded from the root PDF. At the end, chat asks the author to
keep, revise, or reject those drafts; explicit approval still requires passing
checks.

Natural-language requests can select components independently: “Create five
questions with ideas, no solutions yet” sets `include_solution=false`, while
“Include solutions but no ideas” sets `include_idea=false`. Solution-free items
skip solver calls, remain visibly unverified, and do not count as accepted
coverage. “Add solutions to those problems” uses the existing `authoring_plan`
tool with `complete_run_id` (and optional `complete_spec_ids`), then the existing
start tool. Missing components are added to the same numbered files while
existing content and immutable evidence are preserved. No extra MCP tool is
required. To republish an old run without model calls, use `authoring_start`
with `rebuild_only=true` and normal authorization.

## Authoring tools

| Tool | Purpose |
|------|---------|
| `authoring_list_catalogs` | List installed exam/subject catalogs and allowed formats |
| `authoring_search_catalog` | Resolve familiar chapter/topic wording with a compact result |
| `authoring_inspect_catalog` | Inspect provenance and chapter summaries without subject-wide topics |
| `authoring_list_topics` | Page topics from one selected chapter only |
| `authoring_plan` | Persist a creation plan or plan missing components for `complete_run_id` |
| `authoring_start` | Start a confirmed plan in a detached worker, or rebuild with no generation calls |
| `authoring_status` | Read live run/item stages, counts, failures, coverage, usage, lease state, and generated main/answer/PDF paths |
| `authoring_list_items` | Read a bounded page of item metadata |
| `authoring_cancel` | Request durable cooperative cancellation |
| `authoring_resume` | Resume a cancelled run after direct or later authorization |
| `authoring_review` | Keep, revise, approve, or reject a review-pending item with a reason |
| `authoring_plan_variants` | Plan controlled variants of an accepted parent |
| `authoring_read_final` | Read complete LaTeX, saved path, and validation status for one authored item |
| `authoring_read_evidence` | Read one item's immutable attempts and gates |
| `authoring_read_worker_log` | Page through raw detached-agent input/output |

Every tool has a generated input schema, output schema, and MCP annotations.
Domain failures return `isError=true` with a structured error code and message;
they are not successful text responses containing an `Error:` prefix.

Large item bodies are excluded from list responses by default. Use pagination,
then read one of these resource templates when needed:

```text
vbagent://authoring/runs/{run_id}/items/{spec_id}/final
vbagent://authoring/runs/{run_id}/items/{spec_id}/evidence
```

`final` includes validation status: accepted, intentional draft, or review-pending.
It never labels incomplete or failed checks as accepted. `evidence` contains the immutable spec,
attempt candidates, and ordered gate results for audit and repair.

## Model routing and cache behavior

With an external client, the conversational model belongs to that MCP host.
With `vbagent chat`, it is the explicit `--model` chat agent. In both cases it
interprets the request and calls tools; it does not generate the problems
itself. VBAgent routes the actual authoring stages through configured agents:

- GPT-5.6 Luna for classification, review, and other high-volume checks;
- GPT-5.6 Terra for ideas and controlled variants;
- GPT-5.6 Sol for independent solutions and complex diagrams.

Those calls use the normal VBAgent runner, including profile-aware key rotation,
stable prompt-cache affinity, failover, token accounting, and per-profile/cache-
domain telemetry. `authoring_status` reports the aggregate cache hit/write rates
for the durable run.

Worker logs are stored at `runs/{run_id}/worker.log` and retain complete,
base64-sanitized agent input/output as JSONL records for local audit. The CLI
decodes complete events across log-page boundaries before rendering them once,
and can also read older text/panel logs. `/logs` reads the next page; completed
runs drain remaining log pages before showing their final code. Successful HTTP
diagnostic lines are hidden unless verbose; errors remain visible.
MCP protocol output remains
on stdout; server logs use stderr and detached worker output never corrupts the
stdio protocol.
