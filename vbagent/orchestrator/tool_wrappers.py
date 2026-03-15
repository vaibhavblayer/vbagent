"""Tool wrapper functions for core vbagent commands.

This module provides wrapper functions that adapt existing vbagent CLI commands
into tool functions that can be registered with the ToolRegistry and called by
the orchestrator or MCP server.
"""

from pathlib import Path
from typing import Optional, Any
import json


def scan_tool(
    image: str,
    question_type: Optional[str] = None,
    output: Optional[str] = None,
    compile: bool = False
) -> dict[str, Any]:
    """Scan a physics question image to extract LaTeX.
    
    Args:
        image: Path to the physics question image file
        question_type: Override question type (skips classification).
                      Valid values: mcq_sc, mcq_mc, subjective, assertion_reason, passage, match
        output: Output TeX file path for saving results
        compile: Whether to compile LaTeX to validate
        
    Returns:
        Dictionary containing:
            - latex: Extracted LaTeX code
            - has_diagram: Whether the question has a diagram
            - diagram_description: Description of the diagram if present
            - question_type: Detected or provided question type
            - output_path: Path where output was saved (if output specified)
    """
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.content_generation.scanner import scan as scan_image, scan_with_type
    from vbagent.compile import compile_and_retry
    from vbagent.agents.quality.latex_fixer import fix_latex
    from vbagent.config import get_config
    
    # Validate image path
    image_path = Path(image)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image}")
    
    # Scan with or without classification
    if question_type:
        result = scan_with_type(image, question_type)
        detected_type = question_type
    else:
        classification = classify_image(image)
        result = scan_image(image, classification, subject=classification.subject)
        detected_type = classification.question_type
    
    latex_content = result.latex
    
    # Compile if requested
    if compile:
        subject = get_config().subject
        latex_content, _ = compile_and_retry(
            latex_content,
            retry_fn=fix_latex,
            subject=subject,
            console=None,
            verbose=False,
        )
    
    # Save to file if output specified
    output_path = None
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(latex_content)
    
    return {
        "latex": latex_content,
        "has_diagram": result.has_diagram,
        "diagram_description": result.raw_diagram_description,
        "question_type": detected_type,
        "output_path": str(output_path) if output_path else None
    }


def classify_tool(
    image: str,
    output: Optional[str] = None
) -> dict[str, Any]:
    """Classify a physics question image to extract metadata.
    
    Args:
        image: Path to the physics question image file
        output: Output JSON file path for saving results
        
    Returns:
        Dictionary containing classification metadata:
            - question_type: Type of question (mcq_sc, subjective, etc.)
            - difficulty: Difficulty level
            - topic: Main topic
            - subtopic: Subtopic
            - has_diagram: Whether question has a diagram
            - diagram_type: Type of diagram if present
            - num_options: Number of options for MCQ
            - requires_calculus: Whether calculus is required
            - confidence: Classification confidence (0-1)
            - key_concepts: List of key physics concepts
            - output_path: Path where output was saved (if output specified)
    """
    from vbagent.agents.classifier import classify as classify_image
    
    # Validate image path
    image_path = Path(image)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image}")
    
    # Run classification
    result = classify_image(image)
    
    # Save to file if output specified
    output_path = None
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.model_dump_json(indent=2))
    
    return {
        "question_type": result.question_type,
        "difficulty": result.difficulty,
        "topic": result.topic,
        "subtopic": result.subtopic,
        "has_diagram": result.has_diagram,
        "diagram_type": result.diagram_type,
        "num_options": result.num_options,
        "requires_calculus": result.requires_calculus,
        "confidence": result.confidence,
        "key_concepts": result.key_concepts,
        "output_path": str(output_path) if output_path else None
    }


def tikz_tool(
    description: Optional[str] = None,
    image: Optional[str] = None,
    tex: Optional[str] = None,
    output: Optional[str] = None,
    compile: bool = False
) -> dict[str, Any]:
    """Generate TikZ diagram code for physics diagrams.
    
    Args:
        description: Text description of the diagram to generate
        image: Path to a diagram image file
        tex: Path to TeX file with problem text
        output: Output TeX file path for saving the generated TikZ code
        compile: Whether to compile TikZ to validate
        
    Returns:
        Dictionary containing:
            - tikz_code: Generated TikZ/PGF code
            - output_path: Path where output was saved (if output specified)
    """
    from vbagent.agents.diagram.tikz import generate_tikz
    from vbagent.compile import compile_and_retry
    from vbagent.agents.quality.latex_fixer import fix_latex
    from vbagent.config import get_config
    
    # Validate that at least one input is provided
    if not image and not description and not tex:
        raise ValueError("At least one of 'description', 'image', or 'tex' must be provided")
    
    # Validate file paths
    if image:
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")
    
    # Read problem text if provided
    problem_text = None
    if tex:
        tex_path = Path(tex)
        if not tex_path.exists():
            raise FileNotFoundError(f"TeX file not found: {tex}")
        problem_text = tex_path.read_text()
    
    # Build description
    if not description and not problem_text:
        desc = "Generate TikZ code for the diagram shown in the image."
    else:
        desc = description or ""
    
    # Generate TikZ code
    tikz_code = generate_tikz(
        description=desc,
        image_path=image,
        problem_text=problem_text,
    )
    
    # Compile if requested
    if compile:
        subject = get_config().subject
        tikz_code, _ = compile_and_retry(
            tikz_code,
            retry_fn=fix_latex,
            subject=subject,
            console=None,
            verbose=False,
        )
    
    # Save to file if output specified
    output_path = None
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(tikz_code)
    
    return {
        "tikz_code": tikz_code,
        "output_path": str(output_path) if output_path else None
    }


def variant_tool(
    variant_type: str,
    tex: Optional[str] = None,
    image: Optional[str] = None,
    count: int = 1,
    output: Optional[str] = None,
    compile: bool = False
) -> dict[str, Any]:
    """Generate problem variants.
    
    Args:
        variant_type: Type of variant to generate.
                     Valid values: numerical, context, conceptual, calculus, multi
        tex: Path to TeX file containing problem(s)
        image: Path to image file (will be scanned first)
        count: Number of variants to generate per problem (default: 1)
        output: Output TeX file path for saving results
        compile: Whether to compile variants to validate
        
    Returns:
        Dictionary containing:
            - variants: List of generated variant LaTeX strings
            - variant_type: Type of variant generated
            - count: Number of variants generated
            - output_path: Path where output was saved (if output specified)
    """
    from vbagent.agents.variants.variant import generate_variant as gen_variant
    from vbagent.agents.classifier import classify
    from vbagent.agents.content_generation.scanner import scan
    from vbagent.compile import compile_and_retry
    from vbagent.agents.quality.latex_fixer import fix_latex
    from vbagent.config import get_config
    
    # Validate variant type
    valid_types = ["numerical", "context", "conceptual", "calculus", "multi"]
    if variant_type not in valid_types:
        raise ValueError(f"Invalid variant_type. Must be one of: {', '.join(valid_types)}")
    
    # Validate input
    if not image and not tex:
        raise ValueError("Either 'image' or 'tex' must be provided")
    
    # Get source LaTeX
    source_latex = ""
    if image:
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")
        
        classification = classify(image)
        scan_result = scan(image, classification)
        source_latex = scan_result.latex
    elif tex:
        tex_path = Path(tex)
        if not tex_path.exists():
            raise FileNotFoundError(f"TeX file not found: {tex}")
        source_latex = tex_path.read_text()
    
    # Generate variants
    all_variants = []
    for i in range(count):
        result = gen_variant(source_latex, variant_type, ideas_result=None)
        
        # Compile if requested
        if compile:
            subject = get_config().subject
            result, _ = compile_and_retry(
                result,
                retry_fn=fix_latex,
                subject=subject,
                console=None,
                verbose=False,
            )
        
        all_variants.append(result)
    
    # Save to file if output specified
    output_path = None
    if output and all_variants:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        combined = "\n\n% --- Variant ---\n\n".join(all_variants)
        output_path.write_text(combined)
    
    return {
        "variants": all_variants,
        "variant_type": variant_type,
        "count": len(all_variants),
        "output_path": str(output_path) if output_path else None
    }


def convert_tool(
    target_format: str,
    tex: Optional[str] = None,
    image: Optional[str] = None,
    source_format: Optional[str] = None,
    output: Optional[str] = None
) -> dict[str, Any]:
    """Convert physics questions between different formats.
    
    Args:
        target_format: Target format for conversion.
                      Valid values: mcq_sc, mcq_mc, subjective, integer, match, passage
        tex: Path to TeX file containing the question
        image: Path to physics question image (will be scanned first)
        source_format: Source format (auto-detected if not specified).
                      Valid values: mcq_sc, mcq_mc, subjective, integer, match, passage
        output: Output TeX file path for saving results
        
    Returns:
        Dictionary containing:
            - converted_latex: Converted LaTeX code
            - source_format: Source format (detected or provided)
            - target_format: Target format
            - output_path: Path where output was saved (if output specified)
    """
    from vbagent.agents.content_generation.converter import convert_format
    from vbagent.agents.classifier import classify as classify_image
    from vbagent.agents.content_generation.scanner import scan as scan_image
    import re
    
    # Validate formats
    valid_formats = ["mcq_sc", "mcq_mc", "subjective", "integer", "match", "passage"]
    if target_format not in valid_formats:
        raise ValueError(f"Invalid target_format. Must be one of: {', '.join(valid_formats)}")
    if source_format and source_format not in valid_formats:
        raise ValueError(f"Invalid source_format. Must be one of: {', '.join(valid_formats)}")
    
    # Validate input
    if not image and not tex:
        raise ValueError("Either 'image' or 'tex' must be provided")
    
    # Get source LaTeX and detect format
    source_latex = ""
    detected_format = ""
    
    if image:
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image}")
        
        classification = classify_image(image)
        scan_result = scan_image(image, classification, subject=classification.subject)
        source_latex = scan_result.latex
        
        # Map classification type to format
        format_mapping = {
            "mcq_sc": "mcq_sc",
            "mcq_mc": "mcq_mc",
            "subjective": "subjective",
            "assertion_reason": "mcq_sc",
            "passage": "subjective",
            "match": "mcq_mc",
        }
        detected_format = format_mapping.get(classification.question_type, "subjective")
    else:
        tex_path = Path(tex)
        if not tex_path.exists():
            raise FileNotFoundError(f"TeX file not found: {tex}")
        source_latex = tex_path.read_text()
        
        # Auto-detect format from LaTeX
        has_tasks = r"\begin{tasks}" in source_latex or r"\task" in source_latex
        if has_tasks:
            if re.search(r"more than one|multiple|one or more", source_latex, re.IGNORECASE):
                detected_format = "mcq_mc"
            else:
                detected_format = "mcq_sc"
        elif re.search(r"nearest integer|integer value|numerical answer", source_latex, re.IGNORECASE):
            detected_format = "integer"
        else:
            detected_format = "subjective"
    
    actual_source_format = source_format or detected_format
    
    # Convert format
    result = convert_format(source_latex, actual_source_format, target_format)
    
    # Save to file if output specified
    output_path = None
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result)
    
    return {
        "converted_latex": result,
        "source_format": actual_source_format,
        "target_format": target_format,
        "output_path": str(output_path) if output_path else None
    }


def index_metadata_tool(
    directory: str,
    recursive: bool = True
) -> dict[str, Any]:
    """Index a directory of LaTeX questions with metadata.
    
    Args:
        directory: Path to directory containing LaTeX question files
        recursive: Whether to scan subdirectories recursively (default: True)
        
    Returns:
        Dictionary containing:
            - indexed_count: Number of files indexed
            - directory: Directory that was indexed
    """
    from vbagent.metadata.store import MetadataStore
    from vbagent.config import get_config
    
    # Validate directory
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # Get database path
    db_path = Path.cwd() / ".vbagent" / "metadata.db"
    
    # Index directory
    with MetadataStore(db_path) as store:
        count = store.index_directory(dir_path, recursive=recursive)
    
    return {
        "indexed_count": count,
        "directory": str(dir_path)
    }


def query_metadata_tool(
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    chapter: Optional[str] = None,
    question_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    limit: Optional[int] = None
) -> dict[str, Any]:
    """Query questions by metadata filters.
    
    Args:
        topic: Filter by topic (exact match)
        difficulty: Filter by difficulty (easy, medium, hard)
        chapter: Filter by chapter (exact match)
        question_type: Filter by question type
        tags: Filter by tags (questions must have all specified tags)
        limit: Maximum number of results to return
        
    Returns:
        Dictionary containing:
            - questions: List of matching questions with metadata
            - count: Number of questions found
    """
    from vbagent.metadata.store import MetadataStore
    from vbagent.config import get_config
    
    # Get database path
    db_path = Path.cwd() / ".vbagent" / "metadata.db"
    
    if not db_path.exists():
        raise FileNotFoundError(
            "Metadata database not found. Run 'index_metadata' first."
        )
    
    # Query metadata
    with MetadataStore(db_path) as store:
        results = store.query(
            topic=topic,
            difficulty=difficulty,
            chapter=chapter,
            question_type=question_type,
            tags=tags,
            limit=limit
        )
    
    # Convert to dict format
    questions = [q.to_dict() for q in results]
    
    return {
        "questions": questions,
        "count": len(questions)
    }


def create_dpp_tool(
    count: int,
    strategy: str = "balanced",
    topic: Optional[str] = None,
    difficulty: Optional[str] = None,
    chapter: Optional[str] = None,
    question_type: Optional[str] = None,
    tags: Optional[list[str]] = None,
    output: Optional[str] = None,
    title: str = "Daily Practice Problem Set",
    compile: bool = False
) -> dict[str, Any]:
    """Create a Daily Practice Problem (DPP) set from the question bank.
    
    Args:
        count: Number of questions to include in DPP
        strategy: Selection strategy (balanced, topic_coverage, random)
        topic: Filter by topic
        difficulty: Filter by difficulty (easy, medium, hard)
        chapter: Filter by chapter
        question_type: Filter by question type
        tags: Filter by tags (comma-separated)
        output: Output path for main.tex file
        title: Title for the DPP document
        compile: Whether to compile DPP to PDF
        
    Returns:
        Dictionary containing:
            - main_tex_path: Path to generated main.tex file
            - pdf_path: Path to compiled PDF (if compile=True)
            - strategy_used: Selection strategy used
            - question_count: Number of questions in DPP
            - questions: List of selected questions with metadata
            - difficulty_distribution: Count by difficulty level
            - topic_distribution: Count by topic
    """
    from vbagent.dpp.builder import DPPBuilder
    from vbagent.metadata.store import MetadataStore
    from vbagent.config import get_config
    
    # Validate strategy
    valid_strategies = ["balanced", "topic_coverage", "random"]
    if strategy not in valid_strategies:
        raise ValueError(
            f"Invalid strategy: {strategy}. "
            f"Must be one of: {', '.join(valid_strategies)}"
        )
    
    # Get database path
    config = get_config()
    db_path = Path.cwd() / ".vbagent" / "metadata.db"
    
    if not db_path.exists():
        raise FileNotFoundError(
            "Metadata database not found. Run 'index_metadata' first."
        )
    
    # Build filters
    filters = {}
    if topic:
        filters["topic"] = topic
    if difficulty:
        filters["difficulty"] = difficulty
    if chapter:
        filters["chapter"] = chapter
    if question_type:
        filters["question_type"] = question_type
    if tags:
        filters["tags"] = tags
    
    # Create DPP
    with MetadataStore(db_path) as store:
        builder = DPPBuilder(store)
        
        output_path = Path(output) if output else None
        result = builder.create_dpp(
            count=count,
            strategy=strategy,
            filters=filters if filters else None,
            output_path=output_path,
            title=title
        )
    
    # Calculate distributions
    difficulty_dist = {}
    topic_dist = {}
    for q in result.questions:
        diff = q.difficulty or "unknown"
        difficulty_dist[diff] = difficulty_dist.get(diff, 0) + 1
        
        topic = q.topic or "Unknown"
        topic_dist[topic] = topic_dist.get(topic, 0) + 1
    
    response = {
        "main_tex_path": str(result.main_tex_path),
        "strategy_used": result.strategy_used,
        "question_count": len(result.questions),
        "questions": [q.to_dict() for q in result.questions],
        "difficulty_distribution": difficulty_dist,
        "topic_distribution": topic_dist
    }
    
    # Compile if requested
    if compile:
        success, output_msg = result.compile()
        if success:
            response["pdf_path"] = output_msg
            response["compilation_status"] = "success"
        else:
            response["compilation_status"] = "failed"
            response["compilation_error"] = output_msg
    
    return response


def register_core_tools(registry: "ToolRegistry") -> None:
    """Register all core vbagent tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    # Register LaTeX extraction tools
    register_latex_extraction_tools(registry)
    
    # Register export tools
    register_export_tools(registry)
    
    # Register generation tools
    register_generation_tools(registry)
    
    # Register scan tool
    registry.register(
        name="scan",
        description="Extract LaTeX from a physics question image using OCR and AI. "
                   "Automatically classifies the question type and extracts structured LaTeX code.",
        parameters={
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": "Path to the physics question image file"
                },
                "question_type": {
                    "type": "string",
                    "enum": ["mcq_sc", "mcq_mc", "subjective", "assertion_reason", "passage", "match"],
                    "description": "Override question type to skip classification. "
                                 "Valid values: mcq_sc (single correct), mcq_mc (multiple correct), "
                                 "subjective, assertion_reason, passage, match"
                },
                "output": {
                    "type": "string",
                    "description": "Output TeX file path for saving the extracted LaTeX"
                },
                "compile": {
                    "type": "boolean",
                    "description": "Whether to compile the LaTeX to validate it",
                    "default": False
                }
            },
            "required": ["image"]
        },
        function=scan_tool
    )
    
    # Register classify tool
    registry.register(
        name="classify",
        description="Classify a physics question image to extract metadata including question type, "
                   "difficulty, topic, subtopic, diagram presence, and other characteristics.",
        parameters={
            "type": "object",
            "properties": {
                "image": {
                    "type": "string",
                    "description": "Path to the physics question image file"
                },
                "output": {
                    "type": "string",
                    "description": "Output JSON file path for saving classification results"
                }
            },
            "required": ["image"]
        },
        function=classify_tool
    )
    
    # Register tikz tool
    registry.register(
        name="tikz",
        description="Generate TikZ/PGF diagram code for physics diagrams. "
                   "Can generate from image, text description, or problem text.",
        parameters={
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Text description of the diagram to generate"
                },
                "image": {
                    "type": "string",
                    "description": "Path to a diagram image file"
                },
                "tex": {
                    "type": "string",
                    "description": "Path to TeX file with problem text (generates diagram from problem)"
                },
                "output": {
                    "type": "string",
                    "description": "Output TeX file path for saving the generated TikZ code"
                },
                "compile": {
                    "type": "boolean",
                    "description": "Whether to compile the TikZ code to validate it",
                    "default": False
                }
            }
        },
        function=tikz_tool
    )
    
    # Register variant tool
    registry.register(
        name="variant",
        description="Generate problem variants with controlled modifications. "
                   "Can create numerical variants (change numbers), context variants (change scenario), "
                   "conceptual variants (change physics concept), or calculus variants (add calculus).",
        parameters={
            "type": "object",
            "properties": {
                "variant_type": {
                    "type": "string",
                    "enum": ["numerical", "context", "conceptual", "calculus", "multi"],
                    "description": "Type of variant to generate. "
                                 "numerical: change only numbers; "
                                 "context: change scenario; "
                                 "conceptual: change physics concept; "
                                 "calculus: add calculus elements; "
                                 "multi: combine multiple problems"
                },
                "tex": {
                    "type": "string",
                    "description": "Path to TeX file containing problem(s)"
                },
                "image": {
                    "type": "string",
                    "description": "Path to image file (will be scanned first)"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of variants to generate per problem",
                    "default": 1,
                    "minimum": 1
                },
                "output": {
                    "type": "string",
                    "description": "Output TeX file path for saving results"
                },
                "compile": {
                    "type": "boolean",
                    "description": "Whether to compile variants to validate them",
                    "default": False
                }
            },
            "required": ["variant_type"]
        },
        function=variant_tool
    )
    
    # Register convert tool
    registry.register(
        name="convert",
        description="Convert physics questions between different formats. "
                   "Supports conversion between MCQ (single/multiple correct), subjective, "
                   "integer type, match, and passage formats.",
        parameters={
            "type": "object",
            "properties": {
                "target_format": {
                    "type": "string",
                    "enum": ["mcq_sc", "mcq_mc", "subjective", "integer", "match", "passage"],
                    "description": "Target format for conversion. "
                                 "mcq_sc: Multiple Choice Single Correct; "
                                 "mcq_mc: Multiple Choice Multiple Correct; "
                                 "subjective: Subjective/Descriptive; "
                                 "integer: Integer Type; "
                                 "match: Match the Following; "
                                 "passage: Passage-based"
                },
                "tex": {
                    "type": "string",
                    "description": "Path to TeX file containing the question"
                },
                "image": {
                    "type": "string",
                    "description": "Path to physics question image (will be scanned first)"
                },
                "source_format": {
                    "type": "string",
                    "enum": ["mcq_sc", "mcq_mc", "subjective", "integer", "match", "passage"],
                    "description": "Source format (auto-detected if not specified)"
                },
                "output": {
                    "type": "string",
                    "description": "Output TeX file path for saving results"
                }
            },
            "required": ["target_format"]
        },
        function=convert_tool
    )
    
    # Register metadata tools
    registry.register(
        name="index_metadata",
        description="Index a directory of LaTeX questions with metadata. "
                   "Scans all .tex files and extracts metadata including chapter, topic, "
                   "difficulty, question type, and tags.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to directory containing LaTeX question files"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan subdirectories recursively",
                    "default": True
                }
            },
            "required": ["directory"]
        },
        function=index_metadata_tool
    )
    
    registry.register(
        name="query_metadata",
        description="Query questions by metadata filters. "
                   "Search the indexed question bank by topic, difficulty, chapter, "
                   "question type, or tags.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Filter by topic (exact match)"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Filter by difficulty level"
                },
                "chapter": {
                    "type": "string",
                    "description": "Filter by chapter (exact match)"
                },
                "question_type": {
                    "type": "string",
                    "description": "Filter by question type (mcq_sc, subjective, etc.)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags (questions must have all specified tags)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "minimum": 1
                }
            }
        },
        function=query_metadata_tool
    )
    
    # Register DPP tool
    registry.register(
        name="create_dpp",
        description="Create a Daily Practice Problem (DPP) set from the question bank. "
                   "Selects questions using smart strategies for balanced difficulty, "
                   "topic coverage, or random selection. Generates a LaTeX document with "
                   "all selected questions.",
        parameters={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of questions to include in DPP",
                    "minimum": 1
                },
                "strategy": {
                    "type": "string",
                    "enum": ["balanced", "topic_coverage", "random"],
                    "description": "Selection strategy. "
                                 "balanced: 40% easy, 40% medium, 20% hard; "
                                 "topic_coverage: maximize topic diversity; "
                                 "random: random selection",
                    "default": "balanced"
                },
                "topic": {
                    "type": "string",
                    "description": "Filter by topic"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Filter by difficulty level"
                },
                "chapter": {
                    "type": "string",
                    "description": "Filter by chapter"
                },
                "question_type": {
                    "type": "string",
                    "description": "Filter by question type"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags"
                },
                "output": {
                    "type": "string",
                    "description": "Output path for main.tex file (default: dpp_TIMESTAMP.tex)"
                },
                "title": {
                    "type": "string",
                    "description": "Title for the DPP document",
                    "default": "Daily Practice Problem Set"
                },
                "compile": {
                    "type": "boolean",
                    "description": "Whether to compile DPP to PDF",
                    "default": False
                }
            },
            "required": ["count"]
        },
        function=create_dpp_tool
    )


def extract_subitems_tool(
    tex: Optional[str] = None,
    content: Optional[str] = None,
    output: Optional[str] = None
) -> dict[str, Any]:
    """Extract individual subitems from multi-part LaTeX questions.
    
    Splits patterns like \\item (a), \\item (b), \\item (c) into separate items.
    
    Args:
        tex: Path to TeX file containing subitems
        content: Direct LaTeX content string (alternative to tex)
        output: Output directory path for saving individual subitem files
        
    Returns:
        Dictionary containing:
            - subitems: List of extracted subitem contents
            - count: Number of subitems extracted
            - output_paths: List of output file paths (if output specified)
    """
    from vbagent.latex.extractor import extract_subitems
    
    # Validate input
    if not tex and not content:
        raise ValueError("Either 'tex' or 'content' must be provided")
    
    # Get LaTeX content
    if tex:
        tex_path = Path(tex)
        if not tex_path.exists():
            raise FileNotFoundError(f"TeX file not found: {tex}")
        latex_content = tex_path.read_text()
    else:
        latex_content = content
    
    # Extract subitems
    subitems = extract_subitems(latex_content)
    
    # Save to files if output specified
    output_paths = []
    if output and len(subitems) > 1:
        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine base name
        if tex:
            base_name = Path(tex).stem
        else:
            base_name = "subitem"
        
        for i, subitem in enumerate(subitems, 1):
            # Create filename with letter suffix (a, b, c, ...)
            letter = chr(ord('a') + i - 1) if i <= 26 else str(i)
            output_path = output_dir / f"{base_name}_{letter}.tex"
            output_path.write_text(f"\\item {subitem}")
            output_paths.append(str(output_path))
    
    return {
        "subitems": subitems,
        "count": len(subitems),
        "output_paths": output_paths if output_paths else None
    }


def parse_latex_project_tool(
    main_tex: str,
    max_depth: int = 10
) -> dict[str, Any]:
    """Parse multi-file LaTeX project with recursive \\input{} resolution.
    
    Follows \\input{} and \\include{} references recursively, resolving
    relative paths and detecting circular references.
    
    Args:
        main_tex: Path to the main .tex file
        max_depth: Maximum recursion depth (default: 10)
        
    Returns:
        Dictionary containing:
            - files: Dictionary mapping file paths to their content
            - file_count: Number of files in the project
            - main_file: Path to the main file
            - referenced_files: List of all referenced file paths
    """
    from vbagent.latex.extractor import parse_latex_project, CircularReferenceError
    
    # Validate input
    main_path = Path(main_tex)
    if not main_path.exists():
        raise FileNotFoundError(f"Main TeX file not found: {main_tex}")
    
    # Parse project
    try:
        files = parse_latex_project(main_path, max_depth=max_depth)
    except CircularReferenceError as e:
        return {
            "error": "circular_reference",
            "message": str(e),
            "cycle_path": e.cycle_path
        }
    
    # Get list of referenced files (excluding main file)
    main_file_str = str(main_path.resolve())
    referenced_files = [f for f in files.keys() if f != main_file_str]
    
    return {
        "files": files,
        "file_count": len(files),
        "main_file": main_file_str,
        "referenced_files": referenced_files
    }


def extract_from_directory_tool(
    directory: str,
    subdirectory: Optional[str] = None,
    recursive: bool = True,
    pattern: str = "*.tex"
) -> dict[str, Any]:
    """Extract LaTeX files from a directory with optional filtering.
    
    Args:
        directory: Root directory to search
        subdirectory: Optional subdirectory filter (e.g., "scans", "variants")
        recursive: Whether to search subdirectories recursively (default: True)
        pattern: Glob pattern for matching files (default: "*.tex")
        
    Returns:
        Dictionary containing:
            - files: List of file paths found
            - count: Number of files found
            - directory: Directory that was searched
            - subdirectory: Subdirectory filter used (if any)
    """
    from vbagent.latex.extractor import extract_from_directory
    
    # Validate input
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    # Extract files
    files = extract_from_directory(
        dir_path,
        subdirectory=subdirectory,
        recursive=recursive,
        pattern=pattern
    )
    
    # Convert to strings
    file_paths = [str(f) for f in files]
    
    return {
        "files": file_paths,
        "count": len(file_paths),
        "directory": str(dir_path),
        "subdirectory": subdirectory
    }


def register_latex_extraction_tools(registry: "ToolRegistry") -> None:
    """Register LaTeX extraction tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    # Register extract_subitems tool
    registry.register(
        name="extract_subitems",
        description="Extract individual subitems from multi-part LaTeX questions. "
                   "Splits patterns like \\item (a), \\item (b), \\item (c) into separate items.",
        parameters={
            "type": "object",
            "properties": {
                "tex": {
                    "type": "string",
                    "description": "Path to TeX file containing subitems"
                },
                "content": {
                    "type": "string",
                    "description": "Direct LaTeX content string (alternative to tex)"
                },
                "output": {
                    "type": "string",
                    "description": "Output directory path for saving individual subitem files"
                }
            }
        },
        function=extract_subitems_tool
    )
    
    # Register parse_latex_project tool
    registry.register(
        name="parse_latex_project",
        description="Parse multi-file LaTeX project with recursive \\input{} resolution. "
                   "Follows \\input{} and \\include{} references, resolves relative paths, "
                   "and detects circular references.",
        parameters={
            "type": "object",
            "properties": {
                "main_tex": {
                    "type": "string",
                    "description": "Path to the main .tex file"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum recursion depth to prevent infinite loops",
                    "default": 10,
                    "minimum": 1
                }
            },
            "required": ["main_tex"]
        },
        function=parse_latex_project_tool
    )
    
    # Register extract_from_directory tool
    registry.register(
        name="extract_from_directory",
        description="Extract LaTeX files from a directory with optional filtering. "
                   "Can filter by subdirectory (e.g., 'scans', 'variants') and supports "
                   "recursive or non-recursive search.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Root directory to search"
                },
                "subdirectory": {
                    "type": "string",
                    "description": "Optional subdirectory filter (e.g., 'scans', 'variants')"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to search subdirectories recursively",
                    "default": True
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern for matching files",
                    "default": "*.tex"
                }
            },
            "required": ["directory"]
        },
        function=extract_from_directory_tool
    )



def export_files_tool(
    files: list[str],
    output: str,
    mode: str = "flat",
    template: Optional[str] = None,
    title: str = "LaTeX Document"
) -> dict[str, Any]:
    """Export LaTeX files in different formats.
    
    Supports three export modes:
    - flat: All files in a single directory
    - structured: Organized subdirectories by type
    - project: main.tex with \\input{} references
    
    Args:
        files: List of LaTeX file paths to export
        output: Output directory path
        mode: Export mode (flat, structured, or project)
        template: Custom LaTeX template file path (for project mode)
        title: Document title (for project mode)
        
    Returns:
        Dictionary containing:
            - output_dir: Directory where files were exported
            - file_count: Number of files exported
            - mode: Export mode used
            - main_tex: Path to main.tex file (for project mode)
    """
    from vbagent.export import Exporter, ExportMode
    
    # Validate mode
    valid_modes = ["flat", "structured", "project"]
    if mode not in valid_modes:
        raise ValueError(
            f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}"
        )
    
    # Convert file paths
    file_paths = [Path(f) for f in files]
    output_dir = Path(output)
    
    # Validate all files exist
    for file_path in file_paths:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
    
    # Parse mode
    export_mode = ExportMode(mode.lower())
    
    # Read custom template if provided
    template_content = None
    if template:
        template_path = Path(template)
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template}")
        template_content = template_path.read_text()
    
    # Create exporter and export
    exporter = Exporter()
    result = exporter.export(
        files=file_paths,
        output_dir=output_dir,
        mode=export_mode,
        template=template_content,
        title=title
    )
    
    return result.to_dict()


def export_directory_tool(
    directory: str,
    output: str,
    mode: str = "flat",
    pattern: str = "*.tex",
    recursive: bool = True,
    template: Optional[str] = None,
    title: str = "LaTeX Document"
) -> dict[str, Any]:
    """Export all LaTeX files from a directory.
    
    Args:
        directory: Directory containing LaTeX files
        output: Output directory path
        mode: Export mode (flat, structured, or project)
        pattern: File pattern to match (default: *.tex)
        recursive: Whether to search subdirectories recursively
        template: Custom LaTeX template file path (for project mode)
        title: Document title (for project mode)
        
    Returns:
        Dictionary containing:
            - output_dir: Directory where files were exported
            - file_count: Number of files exported
            - mode: Export mode used
            - main_tex: Path to main.tex file (for project mode)
            - source_directory: Directory that was exported
    """
    from vbagent.export import Exporter, ExportMode
    
    # Validate directory
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # Find matching files
    if recursive:
        file_paths = list(dir_path.rglob(pattern))
    else:
        file_paths = list(dir_path.glob(pattern))
    
    if not file_paths:
        raise ValueError(f"No files matching '{pattern}' found in {directory}")
    
    # Parse mode
    export_mode = ExportMode(mode.lower())
    
    # Read custom template if provided
    template_content = None
    if template:
        template_path = Path(template)
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template}")
        template_content = template_path.read_text()
    
    # Create exporter and export
    exporter = Exporter()
    output_dir = Path(output)
    
    result = exporter.export(
        files=file_paths,
        output_dir=output_dir,
        mode=export_mode,
        template=template_content,
        title=title
    )
    
    result_dict = result.to_dict()
    result_dict["source_directory"] = str(dir_path)
    
    return result_dict


def register_export_tools(registry: "ToolRegistry") -> None:
    """Register export tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    # Register export_files tool
    registry.register(
        name="export_files",
        description="Export LaTeX files in different formats. "
                   "Supports flat (single directory), structured (organized subdirs), "
                   "or project (main.tex with \\input{}) modes.",
        parameters={
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of LaTeX file paths to export",
                    "minItems": 1
                },
                "output": {
                    "type": "string",
                    "description": "Output directory path"
                },
                "mode": {
                    "type": "string",
                    "enum": ["flat", "structured", "project"],
                    "description": "Export mode. "
                                 "flat: all files in one directory; "
                                 "structured: organized subdirectories; "
                                 "project: main.tex with \\input{} references",
                    "default": "flat"
                },
                "template": {
                    "type": "string",
                    "description": "Custom LaTeX template file path (for project mode)"
                },
                "title": {
                    "type": "string",
                    "description": "Document title (for project mode)",
                    "default": "LaTeX Document"
                }
            },
            "required": ["files", "output"]
        },
        function=export_files_tool
    )
    
    # Register export_directory tool
    registry.register(
        name="export_directory",
        description="Export all LaTeX files from a directory. "
                   "Searches for files matching a pattern and exports them in the specified format.",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory containing LaTeX files"
                },
                "output": {
                    "type": "string",
                    "description": "Output directory path"
                },
                "mode": {
                    "type": "string",
                    "enum": ["flat", "structured", "project"],
                    "description": "Export mode",
                    "default": "flat"
                },
                "pattern": {
                    "type": "string",
                    "description": "File pattern to match (e.g., '*.tex', 'dpp_*.tex')",
                    "default": "*.tex"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to search subdirectories recursively",
                    "default": True
                },
                "template": {
                    "type": "string",
                    "description": "Custom LaTeX template file path (for project mode)"
                },
                "title": {
                    "type": "string",
                    "description": "Document title (for project mode)",
                    "default": "LaTeX Document"
                }
            },
            "required": ["directory", "output"]
        },
        function=export_directory_tool
    )


def register_metadata_tools(registry: "ToolRegistry") -> None:
    """Register metadata system tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    from vbagent.metadata.store import MetadataStore
    from pathlib import Path
    
    # Create a default metadata store instance
    # In production, this should be configurable
    default_db_path = Path.home() / ".vbagent" / "metadata.db"
    default_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def index_question_bank_tool(directory: str, recursive: bool = True) -> dict:
        """Index a directory of LaTeX questions with metadata.
        
        Args:
            directory: Path to question bank directory
            recursive: Whether to scan subdirectories recursively
            
        Returns:
            Dictionary with indexing results
        """
        store = MetadataStore(default_db_path)
        try:
            count = store.index_directory(Path(directory), recursive=recursive)
            return {
                "success": True,
                "indexed_count": count,
                "directory": directory,
                "database": str(default_db_path)
            }
        finally:
            store.close()
    
    def query_questions_tool(
        topic: str = None,
        difficulty: str = None,
        chapter: str = None,
        tags: list = None,
        limit: int = 100
    ) -> dict:
        """Query questions by metadata filters.
        
        Args:
            topic: Filter by topic
            difficulty: Filter by difficulty (easy, medium, hard)
            chapter: Filter by chapter
            tags: Filter by tags (list of strings)
            limit: Maximum number of results
            
        Returns:
            Dictionary with query results
        """
        store = MetadataStore(default_db_path)
        try:
            results = store.query(
                topic=topic,
                difficulty=difficulty,
                chapter=chapter,
                tags=tags,
                limit=limit
            )
            return {
                "success": True,
                "count": len(results),
                "questions": [q.to_dict() for q in results]
            }
        finally:
            store.close()
    
    def get_metadata_statistics_tool() -> dict:
        """Get aggregate statistics about the question bank.
        
        Returns:
            Dictionary with statistics
        """
        store = MetadataStore(default_db_path)
        try:
            stats = store.get_statistics()
            return {
                "success": True,
                "statistics": stats
            }
        finally:
            store.close()
    
    # Register tools
    registry.register(
        name="index_question_bank",
        description="Index a directory of LaTeX questions with metadata. "
                   "Scans all .tex files and extracts metadata (chapter, topic, difficulty, etc.).",
        parameters={
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Path to question bank directory"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to scan subdirectories recursively",
                    "default": True
                }
            },
            "required": ["directory"]
        },
        function=index_question_bank_tool
    )
    
    registry.register(
        name="query_questions",
        description="Query questions by metadata filters. "
                   "Supports filtering by topic, difficulty, chapter, and tags.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Filter by topic"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Filter by difficulty level"
                },
                "chapter": {
                    "type": "string",
                    "description": "Filter by chapter"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags (questions must have all specified tags)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 100,
                    "minimum": 1
                }
            }
        },
        function=query_questions_tool
    )
    
    registry.register(
        name="get_metadata_statistics",
        description="Get aggregate statistics about the question bank. "
                   "Returns counts by chapter, difficulty, topic, and overall statistics.",
        parameters={
            "type": "object",
            "properties": {}
        },
        function=get_metadata_statistics_tool
    )


def register_dpp_tools(registry: "ToolRegistry") -> None:
    """Register DPP (Daily Practice Problem) builder tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    from vbagent.metadata.store import MetadataStore
    from vbagent.dpp.builder import DPPBuilder
    from pathlib import Path
    
    # Create default metadata store
    default_db_path = Path.home() / ".vbagent" / "metadata.db"
    default_db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def create_dpp_tool(
        count: int,
        strategy: str = "balanced",
        topic: str = None,
        difficulty: str = None,
        chapter: str = None,
        tags: list = None,
        output: str = None,
        title: str = "Daily Practice Problem Set",
        compile_pdf: bool = False
    ) -> dict:
        """Create a Daily Practice Problem set.
        
        Args:
            count: Number of questions to include
            strategy: Selection strategy (balanced, topic_coverage, random)
            topic: Filter by topic
            difficulty: Filter by difficulty
            chapter: Filter by chapter
            tags: Filter by tags
            output: Output directory path
            title: DPP title
            compile_pdf: Whether to compile to PDF
            
        Returns:
            Dictionary with DPP creation results
        """
        store = MetadataStore(default_db_path)
        try:
            builder = DPPBuilder(store)
            
            # Build filters
            filters = {}
            if topic:
                filters["topic"] = topic
            if difficulty:
                filters["difficulty"] = difficulty
            if chapter:
                filters["chapter"] = chapter
            if tags:
                filters["tags"] = tags
            
            # Set output path
            output_path = Path(output) if output else Path.cwd() / "dpp_output"
            
            # Create DPP
            result = builder.create_dpp(
                count=count,
                strategy=strategy,
                filters=filters if filters else None,
                output_path=output_path,
                title=title
            )
            
            response = {
                "success": True,
                "main_tex": str(result.main_tex_path),
                "question_count": len(result.questions),
                "strategy_used": result.strategy_used,
                "questions": [q.to_dict() for q in result.questions]
            }
            
            # Compile if requested
            if compile_pdf:
                success, message = result.compile(output_dir=output_path)
                response["compiled"] = success
                response["compile_message"] = message
            
            return response
            
        finally:
            store.close()
    
    # Register tool
    registry.register(
        name="create_dpp",
        description="Create a Daily Practice Problem (DPP) set from the question bank. "
                   "Selects questions using the specified strategy and generates a LaTeX document.",
        parameters={
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of questions to include in the DPP",
                    "minimum": 1
                },
                "strategy": {
                    "type": "string",
                    "enum": ["balanced", "topic_coverage", "random"],
                    "description": "Selection strategy. "
                                 "balanced: balance difficulty distribution (40% easy, 40% medium, 20% hard); "
                                 "topic_coverage: maximize topic diversity; "
                                 "random: random selection",
                    "default": "balanced"
                },
                "topic": {
                    "type": "string",
                    "description": "Filter questions by topic"
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Filter questions by difficulty"
                },
                "chapter": {
                    "type": "string",
                    "description": "Filter questions by chapter"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter questions by tags"
                },
                "output": {
                    "type": "string",
                    "description": "Output directory path (default: ./dpp_output)"
                },
                "title": {
                    "type": "string",
                    "description": "DPP title",
                    "default": "Daily Practice Problem Set"
                },
                "compile_pdf": {
                    "type": "boolean",
                    "description": "Whether to compile the DPP to PDF",
                    "default": False
                }
            },
            "required": ["count"]
        },
        function=create_dpp_tool
    )



def generate_problem_tool(
    idea: str,
    topic: str,
    concepts: Optional[list[str]] = None,
    question_type: str = "passage",
    num_questions: int = 2,
    difficulty: str = "medium",
    with_diagram: bool = True,
    output_dir: str = "agentic/generated",
    run_pipeline: bool = True
) -> dict[str, Any]:
    """Generate a complete problem from an idea or concept description.
    
    Uses Agent 5 (Idea Generator) to create a problem, then optionally runs
    the full pipeline (TikZ generation, classification, difficulty assessment).
    
    Args:
        idea: Description of the problem idea (e.g., "double block friction system")
        topic: Topic for the problem (e.g., "Mechanics", "Thermodynamics")
        concepts: List of specific concepts to cover (optional)
        question_type: Type of question (mcq_sc, mcq_mc, passage, subjective, etc.)
        num_questions: Number of questions (for passage type)
        difficulty: Target difficulty level (easy, medium, hard)
        with_diagram: Whether to include diagrams
        output_dir: Directory to save generated files
        run_pipeline: Whether to run full pipeline (classification, TikZ, difficulty)
        
    Returns:
        Dictionary containing:
            - problem_latex: Generated problem LaTeX
            - solution_latex: Generated solution LaTeX
            - idea_latex: Core concepts and ideas
            - diagram_description: Description of diagram if generated
            - saved_to: Path where problem was saved
            - metadata: Classification and difficulty metadata (if run_pipeline=True)
    """
    from vbagent.agents.classification.idea_generator import generate_from_idea
    from vbagent.cli.core.process import process_generated_problem
    from pathlib import Path
    
    # Prepare concepts list
    if concepts is None:
        concepts = []
    
    # Prepare ideas list from the main idea
    ideas = [idea]
    
    # Generate problem using Agent 5
    generated = generate_from_idea(
        ideas=ideas,
        concepts=concepts,
        topic=topic,
        difficulty=difficulty,
        question_type=question_type
    )
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find next available problem number
    existing = list(output_path.glob("problem_*.tex"))
    next_num = len(existing) + 1
    problem_file = output_path / f"problem_{next_num}.tex"
    
    # Save basic problem
    problem_file.write_text(generated.problem_latex)
    
    result = {
        "problem_latex": generated.problem_latex,
        "solution_latex": generated.solution_latex,
        "idea_latex": generated.idea_latex,
        "diagram_description": generated.diagram_description,
        "saved_to": str(problem_file),
        "generation_metadata": generated.generation_metadata
    }
    
    # Run full pipeline if requested
    if run_pipeline:
        pipeline_result = process_generated_problem(
            generated=generated,
            problem_num=next_num,
            output_base_dir=Path(output_dir).parent if output_dir != "agentic/generated" else Path("agentic")
        )
        result["metadata"] = pipeline_result
        result["saved_to"] = pipeline_result.get("problem_path", str(problem_file))
    
    return result


def register_generation_tools(registry: "ToolRegistry") -> None:
    """Register problem generation tools with the registry.
    
    Args:
        registry: ToolRegistry instance to register tools with
    """
    registry.register(
        name="generate_problem",
        description="Generate a complete physics/chemistry problem from an idea or concept description. "
                   "Creates problem statement, solution, and optionally diagrams with full metadata.",
        parameters={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "Description of the problem idea (e.g., 'double block friction system', "
                                 "'projectile motion with air resistance')"
                },
                "topic": {
                    "type": "string",
                    "description": "Topic for the problem (e.g., 'Mechanics', 'Thermodynamics', 'Kinematics')"
                },
                "concepts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of specific concepts to cover (e.g., ['friction', 'normal force', 'energy conservation'])"
                },
                "question_type": {
                    "type": "string",
                    "enum": ["mcq_sc", "mcq_mc", "subjective", "passage", "assertion_reason", "match"],
                    "description": "Type of question to generate",
                    "default": "passage"
                },
                "num_questions": {
                    "type": "integer",
                    "description": "Number of questions (relevant for passage type)",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 2
                },
                "difficulty": {
                    "type": "string",
                    "enum": ["easy", "medium", "hard"],
                    "description": "Target difficulty level",
                    "default": "medium"
                },
                "with_diagram": {
                    "type": "boolean",
                    "description": "Whether to include diagrams in the problem",
                    "default": True
                },
                "output_dir": {
                    "type": "string",
                    "description": "Directory to save generated files",
                    "default": "agentic/generated"
                },
                "run_pipeline": {
                    "type": "boolean",
                    "description": "Whether to run full pipeline (TikZ generation, classification, difficulty assessment)",
                    "default": True
                }
            },
            "required": ["idea", "topic"]
        },
        function=generate_problem_tool
    )
