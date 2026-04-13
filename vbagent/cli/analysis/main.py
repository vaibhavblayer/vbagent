"""Analysis command group."""

import click

from vbagent.cli.analysis.exam_analysis import analysis as exam_analysis_cmd
from vbagent.cli.analysis.syllabus import syllabus as syllabus_cmd


@click.group()
def analysis():
    """Exam analysis and syllabus tools.
    
    Generate topic-wise concept summaries and view syllabus information.
    """
    pass


# Register subcommands
analysis.add_command(exam_analysis_cmd, name="generate")
analysis.add_command(syllabus_cmd, name="syllabus")
