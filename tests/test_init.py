import importlib
import io
import sqlite3
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from mytool import cache

init_commands = importlib.import_module("mytool.commands.init")


class InitializationTests(unittest.TestCase):
    def setUp(self):
        temporary_home = TemporaryDirectory(prefix="mytool-test-")
        self.addCleanup(temporary_home.cleanup)
        self.home = Path(temporary_home.name)
        self.env_path = self.home / ".config" / "mytool" / ".env"
        self.db_path = self.home / ".local" / "share" / "mytool" / "trans.db"
        contexts = ExitStack()
        self.addCleanup(contexts.close)
        contexts.enter_context(patch.object(Path, "home", return_value=self.home))
        contexts.enter_context(patch.object(cache, "DB_PATH", self.db_path))
        contexts.enter_context(redirect_stdout(io.StringIO()))

    def prepare_existing_state(self):
        init_commands.init()
        self.env_path.write_text(
            "DEEPSEEK_API_KEY=test-placeholder\n"
            "BASE_URL=https://example.invalid\n",
            encoding="utf-8",
        )
        cache.save("demo --help", "hello", "你好")

    def test_init_preserves_existing_config_and_translations(self):
        self.prepare_existing_state()
        original_config = self.env_path.read_bytes()

        init_commands.init()

        self.assertEqual(self.env_path.read_bytes(), original_config)
        self.assertEqual(cache.lookup("demo --help", "hello"), "你好")

    def test_reinit_preserves_existing_config(self):
        self.prepare_existing_state()
        original_config = self.env_path.read_bytes()
        original_mode = self.env_path.stat().st_mode & 0o777

        init_commands.reinit()

        self.assertEqual(self.env_path.read_bytes(), original_config)
        self.assertEqual(self.env_path.stat().st_mode & 0o777, original_mode)

    def test_reinit_clears_only_translations_and_cache_remains_usable(self):
        self.prepare_existing_state()
        with sqlite3.connect(self.db_path) as db:
            db.execute("CREATE TABLE other_data (value TEXT)")
            db.execute("INSERT INTO other_data VALUES ('keep')")

        init_commands.reinit()

        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM translations").fetchone()[0], 0
            )
            self.assertEqual(
                db.execute("SELECT value FROM other_data").fetchone()[0], "keep"
            )
        cache.save("new --help", "new text", "新译文")
        self.assertEqual(cache.lookup("new --help", "new text"), "新译文")

    def test_reinit_on_fresh_home_is_repeatable(self):
        init_commands.reinit()
        init_commands.reinit()

        self.assertTrue(self.db_path.is_file())
        self.assertEqual(self.env_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            self.env_path.read_text(encoding="utf-8"),
            "DEEPSEEK_API_KEY=\nBASE_URL=https://api.deepseek.com\n",
        )
        with sqlite3.connect(self.db_path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM translations").fetchone()[0], 0
            )


if __name__ == "__main__":
    unittest.main()
