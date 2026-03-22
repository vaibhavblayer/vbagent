"""Pipeline engine for VBAgent.

Modular pipeline for processing question images through classification,
scanning, TikZ generation, solution orchestration, and variant generation.

Modules:
    io      - File I/O helpers (save results, insert TikZ, merge metadata)
    stages  - Individual pipeline stage functions
    runner  - Pipeline runners (process_image_unified, process_tex_item, etc.)
"""

from vbagent.pipeline.io import (
    merge_metadata_into_latex,
    insert_tikz_into_latex,
    save_pipeline_result,
    save_pipeline_result_organized,
    get_base_name,
)
from vbagent.pipeline.runner import (
    process_image_unified,
    process_tex_item,
    process_generated_problem,
    generate_alternate_solution,
)

__all__ = [
    "merge_metadata_into_latex",
    "insert_tikz_into_latex",
    "save_pipeline_result",
    "save_pipeline_result_organized",
    "get_base_name",
    "process_image_unified",
    "process_tex_item",
    "process_generated_problem",
    "generate_alternate_solution",
]
