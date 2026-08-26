from click.testing import CliRunner

from vbagent.cli.authoring import author
from vbagent.cli.main import main


def test_author_is_exposed_as_top_level_command():
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "author" in result.output


def test_catalogs_lists_only_real_builtin_catalogs():
    result = CliRunner().invoke(author, ["catalogs"])

    assert result.exit_code == 0
    assert "jee_main" in result.output
    assert "neet" in result.output
    assert "physics" in result.output
    assert "jee_advanced" not in result.output


def test_preflight_resolves_scope_and_writes_no_run(tmp_path):
    plan_path = tmp_path / "plan.json"
    result = CliRunner().invoke(
        author,
        [
            "preflight",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--topic", "projectile motion",
            "--count", "6",
            "--type", "mcq_sc:2",
            "--type", "integer:1",
            "--difficulty", "4:1",
            "--difficulty", "7:1",
            "--diagram-ratio", "0.5",
            "--save", str(plan_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Items: 6" in result.output
    assert "integer=2" in result.output
    assert "mcq_sc=4" in result.output
    assert plan_path.exists()
    assert not (tmp_path / ".vbagent_authoring.db").exists()


def test_preflight_reports_ambiguous_topic_without_traceback():
    result = CliRunner().invoke(
        author,
        [
            "preflight",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--topic", "Position-time graph, speed and velocity",
        ],
    )

    assert result.exit_code != 0
    assert "Error: topic" in result.output
    assert "is ambiguous" in result.output
    assert "Traceback" not in result.output


def test_run_can_create_durable_plan_without_calling_api(tmp_path):
    output = tmp_path / "authoring"
    result = CliRunner().invoke(
        author,
        [
            "run",
            "--exam", "jee_main",
            "--subject", "physics",
            "--chapter", "kinematics",
            "--topic", "projectile motion",
            "--count", "2",
            "--output", str(output),
            "--no-start",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Durable run" in result.output
    assert (output / ".vbagent_authoring.db").exists()
