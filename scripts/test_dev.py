"""Safe stdlib tests: mock Docker; never delete real data or use external APIs."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("dev", Path(__file__).with_name("dev.py"))
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class InfrastructureSafety(unittest.TestCase):
    def test_names_reject_sql_and_path_injection(self):
        for value in ("../trip", "trip;DROP DATABASE x", "postgres-app", "x" * 41):
            with self.assertRaises(ValueError):
                dev.identifier(value)
        self.assertEqual(dev.identifier("test_trip"), "test_trip")

    def test_private_config_is_exclusive(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "secret"
            dev.write_private(path, "original")
            with self.assertRaises(FileExistsError):
                dev.write_private(path, "replacement")
            self.assertEqual(path.read_text(), "original")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_backup_failure_prevents_shutdown(self):
        with patch.object(dev, "status"), patch("builtins.input", return_value="STOP ALL"), \
             patch.object(dev, "backup_all", side_effect=RuntimeError("backup failed")), \
             patch.object(dev, "run") as command:
            with self.assertRaises(RuntimeError):
                dev.stop_all()
            command.assert_not_called()

    def test_cancel_never_backs_up_or_stops(self):
        with patch.object(dev, "status"), patch("builtins.input", return_value="no"), \
             patch.object(dev, "backup_all") as backup, patch.object(dev, "run") as command:
            with self.assertRaises(RuntimeError):
                dev.stop_all()
            backup.assert_not_called()
            command.assert_not_called()

    def test_new_database_refuses_existing_config(self):
        with TemporaryDirectory() as directory, patch.object(dev, "CONFIG", Path(directory)):
            (Path(directory) / "db-trip.json").write_text("{}")
            with patch.object(dev, "psql") as sql:
                with self.assertRaises(RuntimeError):
                    dev.new_database("trip")
                sql.assert_not_called()

    def test_image_lock_is_not_silently_replaced(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "lock"
            path.write_text("existing")
            with patch.object(dev, "LOCK", path), patch.object(dev, "docker_ready"), patch.object(dev, "run") as command:
                with self.assertRaises(RuntimeError):
                    dev.pin_images()
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
