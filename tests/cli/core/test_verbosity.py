"""Core CLI verbosity defaults and telemetry integration."""

import io

from rich.console import Console

from vbagent.cli.common import configure_cli_verbosity
from vbagent.cli.core.classify import classify
from vbagent.cli.core.process import run
from vbagent.cli.core.scan import scan
from vbagent.ui.logging import (
    agent_logging_context,
    capture_agent_logging_context,
)


def _verbose_option(command):
    return next(parameter for parameter in command.params if parameter.name == "verbose")


def test_core_commands_are_verbose_by_default_with_quiet_opt_out():
    for command in (classify, scan, run):
        option = _verbose_option(command)
        assert option.default is True
        assert "--verbose" in option.opts
        assert "--quiet" in option.secondary_opts
        assert "-q" in option.secondary_opts


def test_cli_verbosity_controls_agent_telemetry_context():
    output = Console(file=io.StringIO())

    with agent_logging_context(output_console=output):
        assert configure_cli_verbosity(None, None, False) is False
        assert capture_agent_logging_context().quiet is True

        assert configure_cli_verbosity(None, None, True) is True
        assert capture_agent_logging_context().quiet is False
