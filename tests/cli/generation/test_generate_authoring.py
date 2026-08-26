from unittest.mock import patch

from click.testing import CliRunner

from vbagent.cli.generation.generate import generate


def test_topic_generation_requires_explicit_syllabus_identity():
    result = CliRunner().invoke(generate, ["--topic", "projectile motion"])

    assert result.exit_code == 2
    assert "requires --exam, --subject, and --chapter" in result.output


@patch("vbagent.cli.generation.generate._run_canonical_topic_authoring")
def test_topic_generation_routes_only_to_canonical_authoring(mock_run):
    result = CliRunner().invoke(
        generate,
        [
            "--topic", "projectile motion",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--type", "integer",
            "--difficulty", "hard",
            "--count", "20",
            "--no-diagram",
            "--seed", "99",
        ],
    )

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["exam"] == "jee_main"
    assert kwargs["subject"] == "physics"
    assert kwargs["chapter"] == "kinematics"
    assert kwargs["count"] == 20
    assert kwargs["diagram"] is False


def test_syllabus_authoring_cannot_bypass_independent_solution_or_durability():
    base = [
        "--topic", "projectile motion",
        "--exam", "jee_main",
        "--subject", "physics",
        "--chapter", "kinematics",
    ]
    no_solve = CliRunner().invoke(generate, [*base, "--no-solve"])
    no_cache = CliRunner().invoke(generate, [*base, "--no-cache"])

    assert no_solve.exit_code == 2
    assert "independent solution is an acceptance gate" in no_solve.output
    assert no_cache.exit_code == 2
    assert "durable syllabus authoring" in no_cache.output


@patch("vbagent.cli.generation.generate._run_canonical_topic_authoring")
def test_topic_authoring_defaults_to_exam_compatible_single_choice(mock_run):
    result = CliRunner().invoke(
        generate,
        [
            "--topic", "projectile motion",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
        ],
    )

    assert result.exit_code == 0, result.output
    assert mock_run.call_args.kwargs["question_type"] == "mcq_sc"
