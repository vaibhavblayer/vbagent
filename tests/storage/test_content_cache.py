"""Concurrency regression tests for the shared content cache index."""

from concurrent.futures import ThreadPoolExecutor

from vbagent.storage.content_cache import ContentCache


def test_parallel_cache_writes_preserve_all_index_entries(tmp_path):
    values = [f"cached value {index}" for index in range(12)]

    def write_value(value):
        cache = ContentCache(str(tmp_path))
        return cache.put(value, "tex", problem_id=value)

    with ThreadPoolExecutor(max_workers=6) as executor:
        entries = list(executor.map(write_value, values))

    fresh_cache = ContentCache(str(tmp_path))
    assert fresh_cache.get_stats()["total_entries"] == len(values)
    for value, (content_hash, _) in zip(values, entries):
        assert fresh_cache.has(content_hash)
        assert fresh_cache.get(content_hash, problem_id=value) == value
