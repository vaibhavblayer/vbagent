# Syllabus-driven problem authoring

VBAgent has one authoritative workflow for creating exam problems from a
syllabus. The CLI, Python API, paper workflow, chat tool, and MCP tool all build
the same immutable `AuthoringRequest` and use the same durable authoring ledger.

## What acceptance means

A draft is not counted as a created problem. Each candidate must pass, in
order:

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
can resume safely. A command exits non-zero if any requested item exhausts its
attempts as `rejected` or `failed`; the durable run remains available for
inspection and resumption.

## Built-in and custom syllabuses

List the catalogs bundled with the installed release:

```bash
vbagent author catalogs
```

The current built-ins are versioned JEE Main Physics and NEET Physics 2026
snapshots. For another exam or subject, pass a versioned JSON catalog with
`--syllabus`. Custom catalogs fail closed unless they declare both the allowed
question types and a response-format description. A minimal catalog looks like
this:

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
the bundled 2026 profiles, JEE Main Physics permits `mcq_sc` and `integer`, while
NEET Physics permits `mcq_sc`.

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

The ledger stores each immutable item specification once and keeps the run
header compact. A no-API benchmark with 10,000 planned items completes planning
and durable insertion in roughly two seconds on a development machine. Actual
throughput is dominated by the seven or eight independent model calls plus a
real LaTeX compile per attempt. For portfolios larger than one operational
window, use deterministic chapter/topic runs and resume them independently;
this bounds API budgets, failure remediation, and review queues without losing
cross-run coverage balancing or novelty checks.

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
