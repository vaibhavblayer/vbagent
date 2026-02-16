"""Tests for formatting utilities."""

import pytest
from vbagent.utils.formatting import format_result_table, format_diff, format_stats


class TestFormatResultTable:
    """Tests for format_result_table function."""
    
    def test_format_dict_result(self):
        """Test formatting a dictionary result."""
        result = {
            "name": "test",
            "value": 42,
            "active": True,
            "score": 0.95
        }
        
        table = format_result_table(result, "Test Result")
        
        assert table.title == "Test Result"
        assert len(table.columns) == 2
        assert table.columns[0].header == "Field"
        assert table.columns[1].header == "Value"
    
    def test_format_object_result(self):
        """Test formatting an object with __dict__."""
        class TestResult:
            def __init__(self):
                self.question_type = "MCQ"
                self.difficulty = "medium"
                self.has_diagram = True
        
        result = TestResult()
        table = format_result_table(result, "Classification")
        
        assert table.title == "Classification"
        assert len(table.columns) == 2
    
    def test_format_none_values(self):
        """Test formatting None values."""
        result = {"field": None}
        table = format_result_table(result, "Test")
        
        # Should handle None gracefully
        assert table is not None
    
    def test_format_list_values(self):
        """Test formatting list values."""
        result = {"tags": ["physics", "mechanics", "kinematics"]}
        table = format_result_table(result, "Test")
        
        assert table is not None
    
    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = {"tags": []}
        table = format_result_table(result, "Test")
        
        assert table is not None
    
    def test_format_nested_dict(self):
        """Test formatting nested dictionary."""
        result = {"metadata": {"author": "test", "version": "1.0"}}
        table = format_result_table(result, "Test")
        
        assert table is not None
    
    def test_format_boolean_values(self):
        """Test formatting boolean values."""
        result = {"active": True, "disabled": False}
        table = format_result_table(result, "Test")
        
        assert table is not None
    
    def test_format_float_values(self):
        """Test formatting float values."""
        result = {"score": 0.95, "confidence": 0.8765}
        table = format_result_table(result, "Test")
        
        assert table is not None


class TestFormatDiff:
    """Tests for format_diff function."""
    
    def test_format_simple_diff(self):
        """Test formatting a simple diff."""
        old = "Hello world"
        new = "Hello Python world"
        
        diff = format_diff(old, new, "test.txt")
        
        assert diff is not None
        assert isinstance(diff, str)
        # Should contain diff markers
        assert any(marker in diff for marker in ['+', '-', '@@'])
    
    def test_format_multiline_diff(self):
        """Test formatting multiline diff."""
        old = "Line 1\nLine 2\nLine 3"
        new = "Line 1\nModified Line 2\nLine 3"
        
        diff = format_diff(old, new, "test.txt")
        
        assert diff is not None
        assert "Modified" in diff or "+" in diff
    
    def test_format_diff_no_filename(self):
        """Test formatting diff without filename."""
        old = "Hello"
        new = "Hi"
        
        diff = format_diff(old, new)
        
        assert diff is not None
        # Should use default filename
        assert "file" in diff
    
    def test_format_identical_content(self):
        """Test formatting diff with identical content."""
        content = "Same content"
        
        diff = format_diff(content, content, "test.txt")
        
        # Should return empty or minimal diff
        assert isinstance(diff, str)
    
    def test_format_empty_to_content(self):
        """Test formatting diff from empty to content."""
        old = ""
        new = "New content"
        
        diff = format_diff(old, new, "test.txt")
        
        assert diff is not None
        assert "+" in diff or "New content" in diff
    
    def test_format_content_to_empty(self):
        """Test formatting diff from content to empty."""
        old = "Old content"
        new = ""
        
        diff = format_diff(old, new, "test.txt")
        
        assert diff is not None
        assert "-" in diff or "Old content" in diff
    
    def test_format_diff_with_special_chars(self):
        """Test formatting diff with special characters."""
        old = "Line with $pecial ch@rs"
        new = "Line with $pecial ch@rs modified"
        
        diff = format_diff(old, new, "test.txt")
        
        assert diff is not None


class TestFormatStats:
    """Tests for format_stats function."""
    
    def test_format_basic_stats(self):
        """Test formatting basic statistics."""
        stats = {
            "total": 100,
            "success": 95,
            "failed": 5
        }
        
        table = format_stats(stats, "Test Statistics")
        
        assert table.title == "Test Statistics"
        assert len(table.columns) == 2
        assert table.columns[0].header == "Metric"
        assert table.columns[1].header == "Value"
    
    def test_format_stats_with_floats(self):
        """Test formatting statistics with float values."""
        stats = {
            "average": 85.5,
            "success_rate": 0.95,
            "error_rate": 0.05
        }
        
        table = format_stats(stats)
        
        assert table is not None
        # Default title should be "Statistics"
        assert table.title == "Statistics"
    
    def test_format_stats_with_percentages(self):
        """Test formatting statistics with percentage values."""
        stats = {
            "completion": 0.75,
            "accuracy": 0.95
        }
        
        table = format_stats(stats)
        
        assert table is not None
    
    def test_format_stats_with_large_numbers(self):
        """Test formatting statistics with large numbers."""
        stats = {
            "total_processed": 1000000,
            "total_errors": 5000
        }
        
        table = format_stats(stats)
        
        assert table is not None
    
    def test_format_empty_stats(self):
        """Test formatting empty statistics."""
        stats = {}
        
        table = format_stats(stats)
        
        assert table is not None
        assert table.title == "Statistics"
    
    def test_format_stats_with_nested_dict(self):
        """Test formatting statistics with nested dictionary."""
        stats = {
            "by_type": {"MCQ": 50, "Subjective": 30},
            "total": 80
        }
        
        table = format_stats(stats)
        
        assert table is not None
    
    def test_format_stats_with_list(self):
        """Test formatting statistics with list values."""
        stats = {
            "errors": ["error1", "error2", "error3"],
            "total": 3
        }
        
        table = format_stats(stats)
        
        assert table is not None
    
    def test_format_stats_no_title(self):
        """Test formatting statistics without custom title."""
        stats = {"count": 10}
        
        table = format_stats(stats)
        
        assert table.title == "Statistics"
    
    def test_format_stats_with_string_values(self):
        """Test formatting statistics with string values."""
        stats = {
            "status": "completed",
            "mode": "batch"
        }
        
        table = format_stats(stats)
        
        assert table is not None


class TestFormatIntegration:
    """Integration tests for formatting utilities."""
    
    def test_all_formatters_return_valid_objects(self):
        """Test that all formatters return valid Rich objects."""
        # Test result table
        result = {"field": "value"}
        result_table = format_result_table(result, "Test")
        assert result_table is not None
        
        # Test diff
        diff = format_diff("old", "new", "test.txt")
        assert diff is not None
        assert isinstance(diff, str)
        
        # Test stats
        stats = {"count": 10}
        stats_table = format_stats(stats)
        assert stats_table is not None
    
    def test_formatters_handle_edge_cases(self):
        """Test that formatters handle edge cases gracefully."""
        # Empty inputs
        empty_result = {}
        assert format_result_table(empty_result, "Empty") is not None
        
        empty_diff = format_diff("", "", "empty.txt")
        assert isinstance(empty_diff, str)
        
        empty_stats = {}
        assert format_stats(empty_stats) is not None
