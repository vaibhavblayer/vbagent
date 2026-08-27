# Syllabus-driven problem authoring

VBAgent has one authoritative workflow for creating exam problems from a
syllabus. The CLI, Python API, paper workflow, and typed MCP server all enter the
same authoring application service and use the same durable authoring ledger.
MCP accepts a safe public intent and resolves protected catalog, coverage, path,
and lineage fields inside that service.

## What acceptance means

A delivered draft is distinct from a validated problem. To count as accepted
coverage, each candidate must pass, in order:

1. deterministic LaTeX and question-type structure checks;
2. routed diagram generation when the specification requires one;
3. an independent solution;
4. independent subject and question-type classification;
5. answer agreement/adjudication;
6. exact exam, chapter, topic, concept, and format alignment;
7. independent difficulty assessment;
8. a real `pdflatex` compilation;
9. reviewer approval; and
10. accepted-only novelty checks across prior runs using the same syllabus
    snapshot.

Failed candidates are retried up to `--max-attempts`. Only accepted artifacts
count toward coverage. Runs, attempts, gate evidence, token usage, and artifacts
are stored under the output directory with a SQLite ledger, so interrupted runs
can resume safely. Exhausted attempts that contain a question become
`needs_review`, not an automatic final rejection. The author can keep the draft,
request a revision, approve it when all required checks pass, or reject it.
Keeping a draft preserves it without certifying it. Failed, rejected, or
review-pending items make the CLI exit non-zero; deliberately requested
solution-free drafts do not.

## Choose components now or add them later

The question is always included. Solutions and conceptual ideas are independent
options on `author plan` and `author run`:

| Requested output | Flags |
|---|---|
| Question, solution, and idea | Default |
| Question and solution | `--no-idea-component` |
| Question and idea | `--no-solution` |
| Question only | `--no-solution --no-idea-component` |

A solution-free request skips the independent solver and solution-dependent
checks, instead of generating a solution and hiding it. Structure and compilation
are checked, but the result is marked `draft`, contributes no accepted coverage,
and has no certified answer key. Its PDF is explicitly labelled unverified.

Add missing components to existing numbered files:

```bash
# Add missing solutions; preserve all existing question/idea text
vbagent author complete --run-id RUN_ID --solution --no-idea-component \
  --output agentic/authoring

# Add missing ideas without requesting solutions
vbagent author complete --run-id RUN_ID --no-solution --idea-component \
  --output agentic/authoring
```

Use repeatable `--spec-id` to select individual items. Completion creates an
audited child run; it does not regenerate questions, replace existing solutions
or alternate methods, remove existing components, or allocate new problem
numbers. Full solution completion runs the normal acceptance checks. An
unsuccessful addition is saved for review without replacing the earlier human
copy. Referring to an older run resolves the latest saved component revision.

## Built-in and custom syllabuses

List the catalogs bundled with the installed release:

```bash
vbagent author catalogs
```

The bundled official 2026 snapshots cover every Paper 1/Test subject:

- JEE Main: Mathematics, Physics, and Chemistry;
- NEET (UG): Physics, Chemistry, and Biology (Botany and Zoology scope).

The source syllabus and exam-pattern PDFs are linked in catalog inspection
output and were reverified on 2026-08-27. For another exam or subject, pass a
versioned JSON catalog with `--syllabus`. Custom catalogs fail closed unless
they declare both the allowed question types and a response-format description.
A minimal catalog looks like this:

```json
{
  "metadata": {
    "exam": "my_exam",
    "subject": "chemistry",
    "version": "2026.1",
    "source_url": "https://example.edu/official-syllabus.pdf",
    "verified_at": "2026-08-26",
    "allowed_question_types": ["mcq_sc", "subjective"],
    "exam_pattern_description": "Four-option single-correct MCQs and written open-response questions.",
    "exam_pattern_source_url": "https://example.edu/official-pattern.pdf",
    "exam_pattern_verified_at": "2026-08-26"
  },
  "chapters": [
    {
      "id": "my_exam.chemistry.equilibrium",
      "title": "Equilibrium",
      "topics": [
        {
          "id": "my_exam.chemistry.equilibrium.ionic",
          "title": "Ionic equilibrium",
          "aliases": ["pH and buffers"]
        }
      ]
    }
  ]
}
```

Stable IDs, the catalog SHA-256, version, allowed formats, exam-pattern rule,
and source URLs are copied into every generation specification and accepted
paper entry. Unsupported formats fail during preflight, before an API call. In
the bundled 2026 profiles, every JEE Main Paper 1 subject permits `mcq_sc` and
`integer`, while every NEET subject permits `mcq_sc` only.

Catalog inspection reports both the installed JSON snapshot hash
(`source_sha256`) and the downloaded official PDF hash
(`official_source_sha256`), so content changes and upstream-document changes
remain distinguishable.

## Preflight before spending API calls

Preflight resolves the exact syllabus scope and shows the complete distribution
without calling a model:

```bash
vbagent author preflight \
  --exam jee_main \
  --subject physics \
  --chapter kinematics \
  --topic "Projectile Motion" \
  --count 20 \
  --type mcq_sc:3 \
  --type integer:1 \
  --difficulty medium:3 \
  --difficulty hard:1 \
  --diagram-ratio 0.25 \
  --seed 42
```

Omit `--topic` to balance the batch across all topics in the selected chapter.
Chapter and topic names, stable IDs, and unique aliases are accepted; ambiguous
or missing values fail before generation.

`--diagram-ratio` controls diagrams required by the problem statement. An
independent solution may still include a concise explanatory visual when it
improves the reasoning; that does not turn the question into a diagram-dependent
item.

## Run and resume a large batch

```bash
vbagent author run \
  --exam jee_main \
  --subject physics \
  --chapter kinematics \
  --count 200 \
  --type mcq_sc:3 \
  --type integer:1 \
  --difficulty 3:1 \
  --difficulty 5:2 \
  --difficulty 8:1 \
  --cognitive apply:2 \
  --cognitive analyze:1 \
  --representation numerical:2 \
  --representation graphical:1 \
  --diagram-ratio 0.2 \
  --concurrency 6 \
  --max-attempts 3 \
  --output agentic/authoring
```

Use the printed run ID for operations:

```bash
vbagent author status --run-id RUN_ID --output agentic/authoring
vbagent author continue --run-id RUN_ID --output agentic/authoring
vbagent author cancel --run-id RUN_ID --output agentic/authoring
```

Human-readable files are published separately from attempts and audit evidence:

```text
project/
├── agentic/
│   ├── generated/
│   │   ├── problem_1.tex
│   │   ├── problem_1.json
│   │   ├── problem_2.tex
│   │   ├── problem_2.json
│   │   └── manifest.json
│   └── authoring/runs/RUN_ID/  # Immutable attempts and build reports
├── main.tex
├── answer_key.tex
└── main.pdf
```

Each problem TeX contains all its selected elements; IDs, specification, status,
and gate evidence live in its JSON sidecar. Numbering is stable across runs and
rebuilds. Existing unowned numbers are skipped, and manual edits are never
silently overwritten. Root documents are replaced only when they are still
VBAgent-managed and a new compilation succeeds.

VBAgent reuses its existing CLI assembler, answer extractor, and PDF compiler.
`main.tex` uses a `\foreach` list and relative `\input` paths to the numbered
files. Accepted items and intentionally solution-free drafts enter the PDF;
review-pending and author-rejected files remain available but are excluded.
Draft PDFs and answer keys carry an explicit unverified warning. A compile
failure preserves problem files and the last successful root bundle; the
internal `publication/build.json` and `author status` report the error.

Rebuild or migrate an existing run without any generation API calls:

```bash
vbagent author continue --run-id RUN_ID --rebuild-only --output agentic/authoring
```

This also restores legacy machine-only rejections to the author review queue.
It preserves explicit human rejections and all old files and attempt evidence.

`author status` reports both creation progress and durable cache telemetry:
token-level cache hit/write percentages, request-level hit percentage when the
SDK provides individual request entries, the GPT-5.6 effective input multiplier,
profile failovers, and cache rates/request counts by API profile and cache domain. The
authoring adapters use the same agents as the regular workflows, and the base
runner automatically supplies their stable prompt-cache contract. Configure
profile domains and high-volume cache sharding in the
[configuration guide](../getting-started/configuration.md#openai-prompt-caching-and-profile-rotation).

With `--human-review`, otherwise-passing candidates stop in `needs_review`:

```bash
vbagent author review \
  --run-id RUN_ID \
  --spec-id SPEC_ID \
  --approve \
  --reason "Checked wording, answer, and diagram" \
  --output agentic/authoring
```

Approval re-runs accepted-only novelty before promoting the artifact.
It cannot override failed or missing checks. For exhausted candidates, choose:

```bash
vbagent author review --run-id RUN_ID --spec-id SPEC_ID --decision keep \
  --reason "Keep this draft for later" --output agentic/authoring
vbagent author review --run-id RUN_ID --spec-id SPEC_ID --decision revise \
  --reason "Use the requested inverse-image method" --output agentic/authoring
vbagent author review --run-id RUN_ID --spec-id SPEC_ID --decision reject \
  --reason "Author chose not to use this problem" --output agentic/authoring
```

Revision queues one additional attempt with the author's feedback. Use
`author continue` to run it. Rejection is recorded, not deletion of the draft.

The ledger stores each immutable item specification once and keeps the run
header compact. A no-API benchmark with 10,000 planned items completes planning
and durable insertion in roughly two seconds on a development machine. Actual
throughput is dominated by the seven or eight independent model calls plus a
real LaTeX compile per attempt. For portfolios larger than one operational
window, use deterministic chapter/topic runs and resume them independently;
this bounds API budgets, failure remediation, and review queues without losing
cross-run coverage balancing or novelty checks.

## Natural-language creation through MCP

Use the transparent built-in CLI host with the same fixed workspace:

```bash
vbagent chat --output agentic/authoring
```

The CLI shows controller/tool input and output, model/cache telemetry, and new
detached-agent I/O, and locally approves consequential calls. To use another
MCP-capable host, start the standalone server:

```bash
vbagent mcp --output agentic/authoring
```

The host model turns natural language into typed calls, but VBAgent remains the
authority for catalogs, planning, execution, and acceptance. A normal exchange
searches or inspects the catalog, calls `authoring_plan` without model requests,
and shows the estimated cost and distribution. A direct creation instruction
then starts automatically; plan-only or ambiguous intent waits for confirmation.
In both cases `authoring_start` receives `confirmed=true` only after that user
authorization is established.

MCP starts a detached worker, so status, cancellation, and item pagination remain
responsive during long runs and the run continues across client disconnects.
Tool failures are marked as MCP errors with structured codes. Accepted LaTeX and
per-attempt evidence are exposed as resources instead of embedding thousands of
candidates in one response. See [Natural-language authoring with MCP](chat.md)
for configuration, tools, resources, and model routing.

## Controlled variants

Variants can only descend from an accepted canonical parent in the same ledger.
Raw TeX or images are not accepted as unchecked parents.

```bash
vbagent variant \
  --parent-spec-id SPEC_ID \
  --type numerical \
  --type context \
  --count 8 \
  --output agentic/authoring
```

Parent artifact hashes, lineage roots/depth, syllabus identity, and per-parent
fan-out limits are checked transactionally. Each child passes the full
acceptance pipeline independently. Controlled variants currently support
Physics single-correct MCQs because the underlying variant prompts are scoped to
that contract. Numerical variants intentionally retain the parent's conceptual
blueprint, so novelty requires an exact artifact change plus different numerical
values and recalculation. Context, conceptual, and calculus variants must also
be blueprint-novel after excluding their immediate parent. The reviewer sees
both parent and child.

## Paper creation

The paper workflow consumes accepted authoring artifacts; it does not have a
second generator:

```bash
vbagent paper generate \
  --exam jee_main \
  --subject physics \
  --chapter kinematics \
  --topic "Projectile Motion" \
  --type mcq_sc \
  --count 20 \
  --concurrency 4 \
  --paper-dir ./jee-kinematics
```

Replaying the same run is idempotent by specification ID. A paper refuses to mix
accepted items from different exam, subject, or syllabus snapshots.

## Python API

```python
from vbagent.authoring import AuthoringRequest, execute_authoring

request = AuthoringRequest(
    exam="jee_main",
    subject="physics",
    chapter="kinematics",
    topics=["Projectile Motion"],
    count=20,
    question_types={"mcq_sc": 3, "integer": 1},
    difficulties={5: 3, 8: 1},
    diagram_ratio=0.25,
    seed=42,
)

execution = execute_authoring(
    request,
    "agentic/authoring",
    max_attempts=3,
    concurrency=4,
)

print(execution.plan.plan_id)
print(execution.stats)
print(execution.accepted_candidates)
```

Use `plan_authoring()` when only an immutable plan is needed, and
`execute_variants()` for accepted-parent variants.

## Media-derived generation

`vbagent generate -i`, `--from-ideas`, and `--from-scans` remain media/idea
transformation workflows. They do not claim syllabus coverage. For any problem
that must count against an exam syllabus, use `author run`, topic-scoped
`generate`, `paper generate`, or the authoring API with exact exam, subject, and
chapter identity.
