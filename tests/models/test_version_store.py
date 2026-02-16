"""Property tests for Version Store.

Tests for VersionStore persistence, version history retrieval,
statistics accumulation, and serialization round-trip.
"""

import tempfile
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from vbagent.models.version_store import (
    VersionStore,
    SuggestionStatus,
    StoredSuggestion,
)
from vbagent.models.review import Suggestion, ReviewIssueType
from vbagent.models.diff import generate_unified_diff, apply_diff_to_content


# =============================================================================
# Strategies for generating test data
# =============================================================================

VALID_ISSUE_TYPES = list(ReviewIssueType)
VALID_STATUSES = list(SuggestionStatus)

issue_type_strategy = st.sampled_from(VALID_ISSUE_TYPES)
status_strategy = st.sampled_from(VALID_STATUSES)
confidence_strategy = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)

# Safe text for content
safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Zs"),
        blacklist_characters="\r\x00",
    ),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip())

# Problem IDs and file paths
problem_id_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip())

file_path_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./",
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() and not x.startswith("/"))


@st.composite
def suggestion_strategy(draw):
    """Generate valid Suggestion instances for testing."""
    original = draw(safe_text)
    suggested = draw(safe_text)
    file_path = draw(file_path_strategy)
    
    diff = generate_unified_diff(original, suggested, file_path)
    
    return Suggestion(
        issue_type=draw(issue_type_strategy),
        file_path=file_path,
        description=draw(safe_text),
        reasoning=draw(safe_text),
        confidence=draw(confidence_strategy),
        original_content=original,
        suggested_content=suggested,
        diff=diff,
    )


# =============================================================================
# Property 6: Rejected Suggestion Storage
# =============================================================================

@given(
    suggestion=suggestion_strategy(),
    problem_id=problem_id_strategy,
)
@settings(max_examples=100)
def test_property_rejected_suggestion_storage(suggestion: Suggestion, problem_id: str):
    """
    **Feature: qa-review-agent, Property 6: Rejected Suggestion Storage**
    **Validates: Requirements 4.3**
    
    Property: For any suggestion that is rejected, the Version Store SHALL contain
    a record with matching problem_id, file_path, and diff content that can be
    retrieved.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Reject the suggestion (store it with REJECTED status)
        suggestion_id = store.save_suggestion(
            suggestion, problem_id, SuggestionStatus.REJECTED
        )
        
        # Property: The suggestion should be retrievable by ID
        stored = store.get_suggestion(suggestion_id)
        assert stored is not None, "Rejected suggestion should be retrievable by ID"
        
        # Property: Retrieved record should have matching problem_id
        assert stored.problem_id == problem_id, (
            f"Problem ID mismatch: expected {problem_id}, got {stored.problem_id}"
        )
        
        # Property: Retrieved record should have matching file_path
        assert stored.file_path == suggestion.file_path, (
            f"File path mismatch: expected {suggestion.file_path}, got {stored.file_path}"
        )
        
        # Property: Retrieved record should have matching diff content
        assert stored.diff == suggestion.diff, (
            f"Diff content mismatch:\nExpected: {suggestion.diff}\nGot: {stored.diff}"
        )
        
        # Property: Status should be REJECTED
        assert stored.status == SuggestionStatus.REJECTED, (
            f"Status should be REJECTED, got {stored.status}"
        )
        
        # Property: Should also be retrievable via version history query
        versions = store.get_versions(problem_id=problem_id)
        assert len(versions) >= 1, "Should find at least one version for problem_id"
        
        matching = [v for v in versions if v.id == suggestion_id]
        assert len(matching) == 1, "Should find exactly one matching version"
        assert matching[0].diff == suggestion.diff, "Version history diff should match"
        
        store.close()


# =============================================================================
# Property 7: Version Store Persistence
# =============================================================================

@given(
    suggestions=st.lists(suggestion_strategy(), min_size=1, max_size=5),
    problem_id=problem_id_strategy,
)
@settings(max_examples=100, deadline=1000)
def test_property_version_store_persistence(suggestions: list, problem_id: str):
    """
    **Feature: qa-review-agent, Property 7: Version Store Persistence**
    **Validates: Requirements 5.1, 5.2, 5.5**
    
    Property: For any sequence of suggestions stored for the same problem-file
    combination, each stored suggestion SHALL have a unique, monotonically
    increasing version number, and all required fields SHALL be persisted.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        saved_ids = []
        for suggestion in suggestions:
            suggestion_id = store.save_suggestion(
                suggestion, problem_id, SuggestionStatus.REJECTED
            )
            saved_ids.append(suggestion_id)
        
        # Retrieve all versions for this problem
        versions = store.get_versions(problem_id=problem_id)
        
        # Property: All suggestions should be persisted
        assert len(versions) == len(suggestions), (
            f"Expected {len(suggestions)} versions, got {len(versions)}"
        )
        
        # Group by file_path to check version numbers
        by_file: dict[str, list[StoredSuggestion]] = {}
        for v in versions:
            by_file.setdefault(v.file_path, []).append(v)
        
        for file_path, file_versions in by_file.items():
            # Sort by version number
            sorted_versions = sorted(file_versions, key=lambda x: x.version)
            
            # Property: Version numbers should be unique and monotonically increasing
            version_numbers = [v.version for v in sorted_versions]
            assert len(version_numbers) == len(set(version_numbers)), (
                f"Version numbers not unique: {version_numbers}"
            )
            for i in range(1, len(version_numbers)):
                assert version_numbers[i] > version_numbers[i-1], (
                    f"Version numbers not monotonically increasing: {version_numbers}"
                )
        
        # Property: All required fields should be persisted
        for stored in versions:
            assert stored.problem_id == problem_id
            assert stored.file_path  # non-empty
            assert stored.diff is not None
            assert stored.reasoning  # non-empty
            assert stored.created_at is not None
            assert stored.version >= 1
        
        store.close()



# =============================================================================
# Property 8: Version History Retrieval
# =============================================================================

@given(
    suggestions=st.lists(suggestion_strategy(), min_size=1, max_size=5),
    problem_id=problem_id_strategy,
)
@settings(max_examples=100)
def test_property_version_history_retrieval(suggestions: list, problem_id: str):
    """
    **Feature: qa-review-agent, Property 8: Version History Retrieval**
    **Validates: Requirements 5.3**
    
    Property: For any problem_id with N stored suggestions, querying version
    history for that problem_id SHALL return exactly N suggestions.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Save all suggestions
        for suggestion in suggestions:
            store.save_suggestion(suggestion, problem_id, SuggestionStatus.REJECTED)
        
        # Retrieve versions
        versions = store.get_versions(problem_id=problem_id)
        
        # Property: Should return exactly N suggestions
        assert len(versions) == len(suggestions), (
            f"Expected {len(suggestions)} versions, got {len(versions)}"
        )
        
        # Property: All returned suggestions should have the correct problem_id
        for v in versions:
            assert v.problem_id == problem_id
        
        store.close()


# =============================================================================
# Property 9: Stored Diff Application
# =============================================================================

@given(suggestion=suggestion_strategy(), problem_id=problem_id_strategy)
@settings(max_examples=100, deadline=1000)
def test_property_stored_diff_application(suggestion: Suggestion, problem_id: str):
    """
    **Feature: qa-review-agent, Property 9: Stored Diff Application**
    **Validates: Requirements 5.4**
    
    Property: For any suggestion stored in the Version Store, retrieving it by ID
    and applying its diff to content with the original content SHALL produce the
    expected modified content.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Save suggestion
        suggestion_id = store.save_suggestion(
            suggestion, problem_id, SuggestionStatus.REJECTED
        )
        
        # Retrieve by ID
        stored = store.get_suggestion(suggestion_id)
        assert stored is not None, "Stored suggestion should be retrievable"
        
        # Apply stored diff to original content
        result = apply_diff_to_content(stored.original_content, stored.diff)
        
        # Property: Applying diff should produce expected modified content
        assert result is not None, "Diff application should succeed"
        assert result.strip() == stored.suggested_content.strip(), (
            f"Applied content mismatch:\n"
            f"Expected: {repr(stored.suggested_content)}\n"
            f"Got: {repr(result)}"
        )
        
        store.close()



# =============================================================================
# Property 10: Version Data Serialization Round-Trip
# =============================================================================

@given(suggestion=suggestion_strategy(), problem_id=problem_id_strategy)
@settings(max_examples=100)
def test_property_version_data_serialization_round_trip(
    suggestion: Suggestion, problem_id: str
):
    """
    **Feature: qa-review-agent, Property 10: Version Data Serialization Round-Trip**
    **Validates: Requirements 5.6**
    
    Property: For any StoredSuggestion, serializing to JSON (dict) and deserializing
    SHALL produce an equivalent StoredSuggestion with all fields preserved.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Save suggestion to get a StoredSuggestion
        suggestion_id = store.save_suggestion(
            suggestion, problem_id, SuggestionStatus.REJECTED
        )
        stored = store.get_suggestion(suggestion_id)
        assert stored is not None
        
        # Serialize to dict
        serialized = stored.to_dict()
        
        # Deserialize back
        deserialized = StoredSuggestion.from_dict(serialized)
        
        # Property: All fields should be preserved
        assert deserialized.id == stored.id
        assert deserialized.version == stored.version
        assert deserialized.problem_id == stored.problem_id
        assert deserialized.file_path == stored.file_path
        assert deserialized.issue_type == stored.issue_type
        assert deserialized.description == stored.description
        assert deserialized.reasoning == stored.reasoning
        assert deserialized.confidence == stored.confidence
        assert deserialized.original_content == stored.original_content
        assert deserialized.suggested_content == stored.suggested_content
        assert deserialized.diff == stored.diff
        assert deserialized.status == stored.status
        assert deserialized.session_id == stored.session_id
        # Compare timestamps (may have microsecond differences due to ISO format)
        assert abs((deserialized.created_at - stored.created_at).total_seconds()) < 1
        
        store.close()


# =============================================================================
# Property 11: Statistics Accumulation
# =============================================================================

@given(
    approved_count=st.integers(min_value=0, max_value=10),
    rejected_count=st.integers(min_value=0, max_value=10),
    skipped_count=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100, deadline=1000)
def test_property_statistics_accumulation(
    approved_count: int, rejected_count: int, skipped_count: int
):
    """
    **Feature: qa-review-agent, Property 11: Statistics Accumulation**
    **Validates: Requirements 7.1, 7.3**
    
    Property: For any sequence of review actions (approve, reject, skip), the
    cumulative statistics SHALL accurately reflect the total counts for each
    action type.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Create suggestions with different statuses
        base_suggestion = Suggestion(
            issue_type=ReviewIssueType.LATEX_SYNTAX,
            file_path="test.tex",
            description="Test",
            reasoning="Test",
            confidence=0.9,
            original_content="original",
            suggested_content="modified",
            diff="--- a/test.tex\n+++ b/test.tex\n",
        )
        
        # Save approved suggestions
        for i in range(approved_count):
            store.save_suggestion(
                base_suggestion, f"problem_approved_{i}", SuggestionStatus.APPROVED
            )
        
        # Save rejected suggestions
        for i in range(rejected_count):
            store.save_suggestion(
                base_suggestion, f"problem_rejected_{i}", SuggestionStatus.REJECTED
            )
        
        # Create session and track skipped
        session_id = store.create_session()
        store.update_session(
            session_id,
            problems_reviewed=approved_count + rejected_count + skipped_count,
            suggestions_made=approved_count + rejected_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            skipped_count=skipped_count,
            completed=True,
        )
        
        # Get stats
        stats = store.get_stats()
        
        # Property: Counts should match
        assert stats["approved_count"] == approved_count, (
            f"Approved count mismatch: expected {approved_count}, got {stats['approved_count']}"
        )
        assert stats["rejected_count"] == rejected_count, (
            f"Rejected count mismatch: expected {rejected_count}, got {stats['rejected_count']}"
        )
        assert stats["skipped_count"] == skipped_count, (
            f"Skipped count mismatch: expected {skipped_count}, got {stats['skipped_count']}"
        )
        
        # Property: Total suggestions should match approved + rejected
        assert stats["total_suggestions"] == approved_count + rejected_count
        
        store.close()



# =============================================================================
# Property 12: Date Range Filtering
# =============================================================================

@given(
    total_suggestions=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=50)
def test_property_date_range_filtering(total_suggestions: int):
    """
    **Feature: qa-review-agent, Property 12: Date Range Filtering**
    **Validates: Requirements 7.4**
    
    Property: For any set of stored suggestions with various timestamps and any
    date range query, the filtered results SHALL contain exactly those suggestions
    whose timestamps fall within the specified range.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        
        # Create suggestions (all will have current timestamp)
        base_suggestion = Suggestion(
            issue_type=ReviewIssueType.LATEX_SYNTAX,
            file_path="test.tex",
            description="Test",
            reasoning="Test",
            confidence=0.9,
            original_content="original",
            suggested_content="modified",
            diff="--- a/test.tex\n+++ b/test.tex\n",
        )
        
        for i in range(total_suggestions):
            store.save_suggestion(
                base_suggestion, f"problem_{i}", SuggestionStatus.REJECTED
            )
        
        # Query with large date range (should include all)
        stats_all = store.get_stats(days=365)
        assert stats_all["total_suggestions"] == total_suggestions, (
            f"Expected {total_suggestions} in 365-day range, got {stats_all['total_suggestions']}"
        )
        
        # Query with 7-day range (should include all recent)
        stats_week = store.get_stats(days=7)
        assert stats_week["total_suggestions"] == total_suggestions, (
            f"Expected {total_suggestions} in 7-day range, got {stats_week['total_suggestions']}"
        )
        
        # Query with no filter (should include all)
        stats_no_filter = store.get_stats()
        assert stats_no_filter["total_suggestions"] == total_suggestions
        
        store.close()


# =============================================================================
# Property 13: Checker Progress Tracking
# =============================================================================

@given(
    file_paths=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./", min_size=5, max_size=30)
        .filter(lambda x: x.strip() and not x.startswith("/")),
        min_size=1,
        max_size=5,
        unique=True,
    ),
    checker_type=st.sampled_from(["solution", "grammar", "clarity", "tikz"]),
)
@settings(max_examples=50)
def test_property_checker_progress_tracking(file_paths: list, checker_type: str):
    """
    **Feature: qa-review-agent, Property 13: Checker Progress Tracking**
    **Validates: Requirements for skipping already-checked files**
    
    Property: For any set of files marked as checked by a specific checker,
    querying checked files SHALL return exactly those files, and is_file_checked
    SHALL return True for checked files and False for unchecked files.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        output_dir = "/test/output"
        
        # Mark files as checked
        for i, file_path in enumerate(file_paths):
            passed = i % 2 == 0  # Alternate between passed and failed
            store.mark_file_checked(file_path, checker_type, output_dir, passed=passed)
        
        # Property: All marked files should be in checked set
        checked = store.get_checked_files(checker_type, output_dir)
        assert len(checked) == len(file_paths), (
            f"Expected {len(file_paths)} checked files, got {len(checked)}"
        )
        for fp in file_paths:
            assert fp in checked, f"File {fp} should be in checked set"
        
        # Property: is_file_checked should return True for checked files
        for fp in file_paths:
            assert store.is_file_checked(fp, checker_type, output_dir), (
                f"is_file_checked should return True for {fp}"
            )
        
        # Property: is_file_checked should return False for unchecked files
        unchecked_file = "/some/other/file.tex"
        assert not store.is_file_checked(unchecked_file, checker_type, output_dir), (
            "is_file_checked should return False for unchecked file"
        )
        
        # Property: Stats should reflect correct counts
        stats = store.get_checker_stats(checker_type, output_dir)
        assert stats["total"] == len(file_paths)
        
        store.close()


@given(
    file_paths=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./", min_size=5, max_size=30)
        .filter(lambda x: x.strip() and not x.startswith("/")),
        min_size=2,
        max_size=5,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_property_checker_progress_reset(file_paths: list):
    """
    **Feature: qa-review-agent, Property 14: Checker Progress Reset**
    **Validates: Requirements for --reset flag functionality**
    
    Property: After resetting checker progress, previously checked files
    SHALL no longer appear in the checked set.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        output_dir = "/test/output"
        checker_type = "clarity"
        
        # Mark all files as checked
        for fp in file_paths:
            store.mark_file_checked(fp, checker_type, output_dir, passed=True)
        
        # Verify all are checked
        checked = store.get_checked_files(checker_type, output_dir)
        assert len(checked) == len(file_paths)
        
        # Reset all progress
        reset_count = store.reset_checker_progress(checker_type, output_dir)
        assert reset_count == len(file_paths), (
            f"Expected to reset {len(file_paths)} files, got {reset_count}"
        )
        
        # Property: No files should be checked after reset
        checked_after = store.get_checked_files(checker_type, output_dir)
        assert len(checked_after) == 0, (
            f"Expected 0 checked files after reset, got {len(checked_after)}"
        )
        
        # Property: is_file_checked should return False for all files
        for fp in file_paths:
            assert not store.is_file_checked(fp, checker_type, output_dir), (
                f"is_file_checked should return False after reset for {fp}"
            )
        
        store.close()


@given(
    file_paths=st.lists(
        st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./", min_size=5, max_size=30)
        .filter(lambda x: x.strip() and not x.startswith("/")),
        min_size=3,
        max_size=5,
        unique=True,
    ),
)
@settings(max_examples=50)
def test_property_checker_progress_isolation(file_paths: list):
    """
    **Feature: qa-review-agent, Property 15: Checker Progress Isolation**
    **Validates: Different checkers track progress independently**
    
    Property: Files checked by one checker type SHALL NOT appear as checked
    for a different checker type.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        store = VersionStore(tmpdir)
        output_dir = "/test/output"
        
        # Mark files as checked by "clarity" checker
        for fp in file_paths:
            store.mark_file_checked(fp, "clarity", output_dir, passed=True)
        
        # Property: Files should be checked for "clarity"
        clarity_checked = store.get_checked_files("clarity", output_dir)
        assert len(clarity_checked) == len(file_paths)
        
        # Property: Files should NOT be checked for "grammar"
        grammar_checked = store.get_checked_files("grammar", output_dir)
        assert len(grammar_checked) == 0, (
            f"Expected 0 files checked for grammar, got {len(grammar_checked)}"
        )
        
        # Property: is_file_checked should be checker-specific
        for fp in file_paths:
            assert store.is_file_checked(fp, "clarity", output_dir)
            assert not store.is_file_checked(fp, "grammar", output_dir)
        
        store.close()
