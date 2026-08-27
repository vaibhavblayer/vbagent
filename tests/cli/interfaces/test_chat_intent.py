import pytest

from vbagent.mcp.chat_intent import classify_authoring_intent


@pytest.mark.parametrize(
    ("message", "policy"),
    [
        ("Create one kinematics problem", "create_now"),
        ("Can you generate 5 NEET MCQs?", "create_now"),
        ("Please create one problem and compile it afterward", "create_now"),
        ("Start this run now", "start_existing"),
        ("Please resume this generation", "resume"),
        ("copile this to main.tex and pdf after completion", "rebuild"),
        ("onlt include last two modulus problem, 6, 7", "rebuild"),
        ("Compile main.tex", "rebuild"),
        ("Please build the PDF", "rebuild"),
        ("Plan five questions", "confirmation_required"),
        ("Could you show me the plan?", "confirmation_required"),
        ("Create 5 problems, but show me before you start", "confirmation_required"),
        ("Don't generate any problems", "confirmation_required"),
        ("Do not compile yet", "confirmation_required"),
        ("How can this generate problems?", "unspecified"),
        ("Can it create questions?", "unspecified"),
        ("Explain how to generate problems", "unspecified"),
        ("If I say generate five problems, what happens?", "unspecified"),
        ('The agent said "create five problems"', "unspecified"),
        ("Check whether this can compile problems", "unspecified"),
        ("Start by explaining how to generate problems", "unspecified"),
        ("Continue explaining the solution", "unspecified"),
        ("Use high reasoning for problems", "unspecified"),
        ("Create one problem after I approve", "confirmation_required"),
    ],
)
def test_intent_authorizes_only_direct_requests(message, policy):
    assert classify_authoring_intent(message).policy == policy


@pytest.mark.parametrize(
    ("message", "numbers"),
    [
        ("onlt include last two modulus problem, 6, 7", (6, 7)),
        ("Only include problems 6 and 7", (6, 7)),
        ("Compile only problems 6, 7", (6, 7)),
        ("Compile only 6 and 7", (6, 7)),
        ("Compile only the last two modulus problems, 6, 7", (6, 7)),
        ("Include problem_7.tex and problem_6.tex", (7, 6)),
        ("Only include problems 6 to 8", (6, 7, 8)),
        ("Only include problems 6-8, 10", (6, 7, 8, 10)),
        ("Include only problem 6", (6,)),
        ("Only include the last two problems", None),
    ],
)
def test_selection_refers_to_human_file_numbers(message, numbers):
    intent = classify_authoring_intent(message)
    assert intent.policy == "rebuild"
    assert intent.selection_requested
    assert intent.problem_numbers == numbers


def test_compile_after_completion_does_not_authorize_generation():
    intent = classify_authoring_intent(
        "copile this to main.tex and pdf after completion"
    )
    assert intent.policy == "rebuild"
    assert intent.after_completion
    assert not intent.selection_requested


@pytest.mark.parametrize("message", ["Include all problems", "Only compile this"])
def test_compile_scope_is_not_assumed_to_be_a_numeric_subset(message):
    intent = classify_authoring_intent(message)
    assert intent.policy == "rebuild"
    assert not intent.selection_requested
