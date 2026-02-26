import asyncio
import unittest

from omnimind_agents.safe_backend import SafeBackend


class MockBackend:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, command: str):
        self.calls.append(command)
        return {"stdout": "ok", "stderr": "", "exitCode": 0}

    async def read_file(self, path: str):
        return path


class SafeBackendTests(unittest.IsolatedAsyncioTestCase):
    async def test_blocks_rm_commands(self):
        inner = MockBackend()
        safe = SafeBackend(inner)
        result = await safe.execute("rm -rf /home")
        self.assertEqual(inner.calls, [])
        self.assertNotEqual(result["exitCode"], 0)
        self.assertIn("BLOCKED", result["stderr"])

    async def test_blocks_sudo_commands(self):
        inner = MockBackend()
        safe = SafeBackend(inner)
        result = await safe.execute("sudo apt install evil")
        self.assertEqual(inner.calls, [])
        self.assertIn("BLOCKED", result["stderr"])

    async def test_allows_safe_commands(self):
        inner = MockBackend()
        safe = SafeBackend(inner)
        await safe.execute("git status")
        self.assertEqual(inner.calls, ["git status"])

    async def test_proxies_non_execute_methods(self):
        inner = MockBackend()
        safe = SafeBackend(inner)
        value = await safe.read_file("/path")
        self.assertEqual(value, "/path")


if __name__ == "__main__":
    unittest.main()
