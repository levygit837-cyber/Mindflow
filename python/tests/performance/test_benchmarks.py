"""Performance benchmarks for filesystem and cache operations.

Measures performance of file operations, search tools, and cache operations.
Compares v1 vs v2 performance where applicable.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from mindflow_backend.agents.tools.caching.result_cache import ResultCache
from mindflow_backend.agents.tools.filesystem.file_operations_v2 import (
    FileReadToolV2,
    FileWriteToolV2,
    FileEditToolV2,
)
from mindflow_backend.agents.tools.filesystem.search_tools_v2 import (
    GlobToolV2,
    GrepToolV2,
)


class TestFileOperationsBenchmarks:
    """Benchmark file read/write/edit operations."""

    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file with content."""
        file_path = tmp_path / "test.txt"
        content = "Line {}\n" * 1000  # 1000 lines
        file_path.write_text(content.format(*range(1000)))
        return file_path

    @pytest.fixture
    def large_file(self, tmp_path):
        """Create large test file (10MB)."""
        file_path = tmp_path / "large.txt"
        content = "x" * (10 * 1024 * 1024)  # 10MB
        file_path.write_text(content)
        return file_path

    @pytest.mark.benchmark
    def test_read_small_file_performance(self, test_file, benchmark):
        """Benchmark reading small file (1000 lines)."""
        tool = FileReadToolV2()

        def read_file():
            return asyncio.run(tool.execute(
                file_path=str(test_file),
                include_line_numbers=True
            ))

        result = benchmark(read_file)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_read_large_file_performance(self, large_file, benchmark):
        """Benchmark reading large file (10MB)."""
        tool = FileReadToolV2()

        def read_file():
            return asyncio.run(tool.execute(
                file_path=str(large_file),
                include_line_numbers=False
            ))

        result = benchmark(read_file)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_write_file_performance(self, tmp_path, benchmark):
        """Benchmark writing file."""
        tool = FileWriteToolV2()
        content = "x" * 10000  # 10KB

        def write_file():
            file_path = tmp_path / f"write_{time.time()}.txt"
            return asyncio.run(tool.execute(
                file_path=str(file_path),
                content=content,
                atomic=True
            ))

        result = benchmark(write_file)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_edit_file_performance(self, test_file, benchmark):
        """Benchmark editing file."""
        tool = FileEditToolV2()

        def edit_file():
            return asyncio.run(tool.execute(
                file_path=str(test_file),
                old_string="Line 500",
                new_string="Modified Line 500",
                replace_all=False
            ))

        result = benchmark(edit_file)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_edit_file_replace_all_performance(self, test_file, benchmark):
        """Benchmark editing file with replace_all."""
        tool = FileEditToolV2()

        def edit_file():
            return asyncio.run(tool.execute(
                file_path=str(test_file),
                old_string="Line",
                new_string="Modified",
                replace_all=True
            ))

        result = benchmark(edit_file)
        assert result["success"] is True


class TestSearchBenchmarks:
    """Benchmark glob and grep search operations."""

    @pytest.fixture
    def test_directory(self, tmp_path):
        """Create test directory with many files."""
        # Create 100 Python files
        for i in range(100):
            file_path = tmp_path / f"file_{i}.py"
            content = f"def function_{i}():\n    return {i}\n"
            file_path.write_text(content)

        # Create 50 text files
        for i in range(50):
            file_path = tmp_path / f"file_{i}.txt"
            file_path.write_text(f"Content {i}\n")

        return tmp_path

    @pytest.mark.benchmark
    def test_glob_simple_pattern_performance(self, test_directory, benchmark):
        """Benchmark glob with simple pattern."""
        tool = GlobToolV2()

        def glob_search():
            return asyncio.run(tool.execute(
                pattern="*.py",
                path=str(test_directory)
            ))

        result = benchmark(glob_search)
        assert result["success"] is True
        assert len(result["matches"]) == 100

    @pytest.mark.benchmark
    def test_glob_recursive_pattern_performance(self, test_directory, benchmark):
        """Benchmark glob with recursive pattern."""
        tool = GlobToolV2()

        def glob_search():
            return asyncio.run(tool.execute(
                pattern="**/*.py",
                path=str(test_directory)
            ))

        result = benchmark(glob_search)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_grep_simple_pattern_performance(self, test_directory, benchmark):
        """Benchmark grep with simple pattern."""
        tool = GrepToolV2()

        def grep_search():
            return asyncio.run(tool.execute(
                pattern="function_",
                path=str(test_directory),
                output_mode="content"
            ))

        result = benchmark(grep_search)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_grep_regex_pattern_performance(self, test_directory, benchmark):
        """Benchmark grep with regex pattern."""
        tool = GrepToolV2()

        def grep_search():
            return asyncio.run(tool.execute(
                pattern=r"function_\d+",
                path=str(test_directory),
                output_mode="content"
            ))

        result = benchmark(grep_search)
        assert result["success"] is True

    @pytest.mark.benchmark
    def test_grep_with_context_performance(self, test_directory, benchmark):
        """Benchmark grep with context lines."""
        tool = GrepToolV2()

        def grep_search():
            return asyncio.run(tool.execute(
                pattern="function_",
                path=str(test_directory),
                output_mode="content",
                context_before=2,
                context_after=2
            ))

        result = benchmark(grep_search)
        assert result["success"] is True


class TestCacheBenchmarks:
    """Benchmark cache operations."""

    @pytest.fixture
    def cache(self):
        """Create cache instance."""
        return ResultCache(max_size=10000, max_memory_mb=100)

    @pytest.mark.benchmark
    def test_cache_set_performance(self, cache, benchmark):
        """Benchmark cache set operation."""
        def cache_set():
            for i in range(100):
                cache.set(f"key_{i}", {"data": f"value_{i}"})

        benchmark(cache_set)

    @pytest.mark.benchmark
    def test_cache_get_hit_performance(self, cache, benchmark):
        """Benchmark cache get (hit) operation."""
        # Populate cache
        for i in range(100):
            cache.set(f"key_{i}", {"data": f"value_{i}"})

        def cache_get():
            for i in range(100):
                cache.get(f"key_{i}")

        benchmark(cache_get)

    @pytest.mark.benchmark
    def test_cache_get_miss_performance(self, cache, benchmark):
        """Benchmark cache get (miss) operation."""
        def cache_get():
            for i in range(100):
                cache.get(f"nonexistent_key_{i}")

        benchmark(cache_get)

    @pytest.mark.benchmark
    def test_cache_eviction_performance(self, benchmark):
        """Benchmark cache LRU eviction."""
        cache = ResultCache(max_size=100)  # Small cache

        def cache_with_eviction():
            # Add 200 items to trigger eviction
            for i in range(200):
                cache.set(f"key_{i}", {"data": f"value_{i}"})

        benchmark(cache_with_eviction)

    @pytest.mark.benchmark
    def test_cache_cleanup_performance(self, benchmark):
        """Benchmark cache cleanup of expired entries."""
        cache = ResultCache(default_ttl=0.001)  # 1ms TTL

        # Populate cache
        for i in range(1000):
            cache.set(f"key_{i}", {"data": f"value_{i}"})

        time.sleep(0.01)  # Wait for expiration

        def cache_cleanup():
            cache.cleanup_expired()

        benchmark(cache_cleanup)


class TestMemoryUsage:
    """Test memory usage of operations."""

    @pytest.mark.benchmark
    def test_read_file_memory_usage(self, tmp_path):
        """Test memory usage when reading large file."""
        # Create 100MB file
        large_file = tmp_path / "large.txt"
        content = "x" * (100 * 1024 * 1024)
        large_file.write_text(content)

        tool = FileReadToolV2()

        import tracemalloc
        tracemalloc.start()

        result = asyncio.run(tool.execute(
            file_path=str(large_file),
            include_line_numbers=False
        ))

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        assert result["success"] is True
        # Peak memory should be reasonable (< 200MB for 100MB file)
        assert peak < 200 * 1024 * 1024

    @pytest.mark.benchmark
    def test_cache_memory_usage(self):
        """Test cache memory usage."""
        cache = ResultCache(max_size=10000, max_memory_mb=10)

        import tracemalloc
        tracemalloc.start()

        # Add 1000 entries
        for i in range(1000):
            cache.set(f"key_{i}", {"data": "x" * 1000})  # 1KB each

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = cache.get_stats()

        # Memory usage should be tracked correctly
        assert stats["total_size_bytes"] > 0
        assert stats["memory_usage_percent"] > 0


class TestConcurrency:
    """Test concurrent operation performance."""

    @pytest.mark.benchmark
    def test_concurrent_file_reads(self, tmp_path, benchmark):
        """Benchmark concurrent file reads."""
        # Create 10 test files
        files = []
        for i in range(10):
            file_path = tmp_path / f"file_{i}.txt"
            file_path.write_text(f"Content {i}\n" * 100)
            files.append(file_path)

        tool = FileReadToolV2()

        async def concurrent_reads():
            tasks = [
                tool.execute(file_path=str(f), include_line_numbers=True)
                for f in files
            ]
            return await asyncio.gather(*tasks)

        def run_concurrent():
            return asyncio.run(concurrent_reads())

        results = benchmark(run_concurrent)
        assert len(results) == 10
        assert all(r["success"] for r in results)

    @pytest.mark.benchmark
    def test_concurrent_cache_operations(self, benchmark):
        """Benchmark concurrent cache operations."""
        cache = ResultCache()

        async def concurrent_cache_ops():
            # Mix of set and get operations
            tasks = []
            for i in range(100):
                if i % 2 == 0:
                    tasks.append(asyncio.to_thread(cache.set, f"key_{i}", f"value_{i}"))
                else:
                    tasks.append(asyncio.to_thread(cache.get, f"key_{i-1}"))
            return await asyncio.gather(*tasks)

        def run_concurrent():
            return asyncio.run(concurrent_cache_ops())

        benchmark(run_concurrent)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "benchmark"])
