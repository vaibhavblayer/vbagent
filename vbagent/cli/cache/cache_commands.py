"""CLI commands for cache management.

Provides commands to inspect, clean, and manage the metadata and content cache.
"""

import click
from rich.table import Table

from ..common import _get_console, _get_panel


@click.group()
def cache():
    """Manage pipeline cache and metadata.
    
    \b
    Commands:
        status  - Show cache statistics
        clean   - Clean up old or unused cache entries
        clear   - Clear entire cache
        list    - List all cached problems
    """
    pass


@cache.command()
def status():
    """Show cache statistics and metadata summary.
    
    \b
    Examples:
        vbagent cache status
    """
    from vbagent.storage import MetadataManager, ContentCache
    
    console = _get_console()
    
    # Initialize managers
    metadata_mgr = MetadataManager()
    content_cache = ContentCache()
    
    # Get statistics
    metadata_stats = metadata_mgr.get_stats()
    cache_stats = content_cache.get_stats()
    
    # Display metadata stats
    console.print(_get_panel(
        f"Total Problems: {metadata_stats['total']}\n"
        f"Completed: {metadata_stats['completed']}\n"
        f"Failed: {metadata_stats['failed']}\n\n"
        f"By Subject:\n" + "\n".join(f"  {k}: {v}" for k, v in metadata_stats['by_subject'].items()) + "\n\n"
        f"By Type:\n" + "\n".join(f"  {k}: {v}" for k, v in metadata_stats['by_type'].items()),
        title="Metadata Statistics",
        border_style="cyan"
    ))
    
    # Display cache stats
    console.print(_get_panel(
        f"Total Entries: {cache_stats['total_entries']}\n"
        f"Total Size: {cache_stats['total_size_mb']} MB\n\n"
        f"By Type:\n" + "\n".join(f"  {k}: {v}" for k, v in cache_stats['by_type'].items()) + "\n\n"
        f"Last Cleanup: {cache_stats['last_cleanup'] or 'Never'}",
        title="Content Cache Statistics",
        border_style="green"
    ))


@cache.command()
@click.option(
    "--subject",
    type=str,
    help="List problems for specific subject (physics, chemistry, mathematics)"
)
@click.option(
    "--type",
    "question_type",
    type=str,
    help="List problems for specific type (mcq_sc, subjective, etc.)"
)
def list(subject: str = None, question_type: str = None):
    """List all cached problems with metadata.
    
    \b
    Examples:
        vbagent cache list
        vbagent cache list --subject chemistry
        vbagent cache list --type subjective
    """
    from vbagent.storage import MetadataManager
    
    console = _get_console()
    metadata_mgr = MetadataManager()
    
    # Get problem IDs
    if subject:
        problem_ids = metadata_mgr.list_by_subject(subject)
    elif question_type:
        problem_ids = metadata_mgr.list_by_type(question_type)
    else:
        problem_ids = metadata_mgr.list_all()
    
    if not problem_ids:
        console.print("[yellow]No problems found.[/yellow]")
        return
    
    # Create table
    table = Table(title=f"Cached Problems ({len(problem_ids)})")
    table.add_column("Problem ID", style="cyan")
    table.add_column("Subject", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Stages", justify="right")
    table.add_column("Duration", justify="right")
    
    for problem_id in sorted(problem_ids):
        metadata = metadata_mgr.load(problem_id)
        if not metadata:
            continue
        
        subject_str = metadata.classification.subject if metadata.classification else "?"
        type_str = metadata.classification.question_type if metadata.classification else "?"
        stages_str = f"{metadata.stages_completed}/{metadata.stages_completed + metadata.stages_failed + metadata.stages_skipped}"
        
        duration_str = "?"
        if metadata.total_duration_ms:
            duration_s = metadata.total_duration_ms / 1000
            duration_str = f"{duration_s:.1f}s"
        
        table.add_row(problem_id, subject_str, type_str, stages_str, duration_str)
    
    console.print(table)


@cache.command()
@click.option(
    "--days",
    type=int,
    default=30,
    help="Remove cache entries not accessed in N days (default: 30)"
)
@click.option(
    "--unused",
    is_flag=True,
    help="Remove cache entries not referenced by any problem"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be deleted without actually deleting"
)
def clean(days: int, unused: bool, dry_run: bool):
    """Clean up old or unused cache entries.
    
    \b
    Examples:
        vbagent cache clean --days 30
        vbagent cache clean --unused
        vbagent cache clean --days 7 --dry-run
    """
    from vbagent.storage import MetadataManager, ContentCache
    
    console = _get_console()
    
    metadata_mgr = MetadataManager()
    content_cache = ContentCache()
    
    if dry_run:
        console.print("[yellow]DRY RUN - No files will be deleted[/yellow]\n")
    
    if unused:
        # Get valid problem IDs
        valid_ids = metadata_mgr.list_all()
        
        # Count entries before
        before = content_cache.get_stats()['total_entries']
        
        if not dry_run:
            content_cache.cleanup_unused(valid_ids)
        
        after = content_cache.get_stats()['total_entries']
        removed = before - after
        
        console.print(f"[green]✓[/green] Removed {removed} unused cache entries")
    
    if days:
        # Count entries before
        before = content_cache.get_stats()['total_entries']
        
        if not dry_run:
            content_cache.cleanup_old(days)
        
        after = content_cache.get_stats()['total_entries']
        removed = before - after
        
        console.print(f"[green]✓[/green] Removed {removed} cache entries older than {days} days")
    
    # Show final stats
    stats = content_cache.get_stats()
    console.print(f"\nCache size: {stats['total_size_mb']} MB ({stats['total_entries']} entries)")


@cache.command()
@click.option(
    "--problem",
    type=str,
    help="Clear cache for specific problem only"
)
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def clear(problem: str = None):
    """Clear entire cache or specific problem.
    
    \b
    Examples:
        vbagent cache clear
        vbagent cache clear --problem problem_1
    """
    from vbagent.cache import PipelineCache
    
    console = _get_console()
    
    cache = PipelineCache()
    cache.clear(problem)
    
    if problem:
        console.print(f"[green]✓[/green] Cleared cache for {problem}")
    else:
        console.print("[green]✓[/green] Cleared entire cache")
