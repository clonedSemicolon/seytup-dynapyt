from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch


HELPER_PATH = Path(__file__).parents[1] / "scripts" / "instrument_targets.py"
SPEC = importlib.util.spec_from_file_location("instrument_targets", HELPER_PATH)
assert SPEC and SPEC.loader
instrument_targets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(instrument_targets)


class ParseTargetSpecsTests(unittest.TestCase):
    def test_parses_multiple_targets_and_comments(self) -> None:
        targets = r"""
        # Trace the installer and project
        package:pip
        directory:src
        file:C:\repo\setup.py
        """

        self.assertEqual(
            instrument_targets.parse_target_specs(targets),
            [
                ("package", "pip"),
                ("directory", "src"),
                ("file", r"C:\repo\setup.py"),
            ],
        )

    def test_legacy_directory_takes_precedence_over_package(self) -> None:
        self.assertEqual(
            instrument_targets.parse_target_specs("", "src", "installed_name"),
            [("directory", "src")],
        )

    def test_rejects_unknown_target_kind(self) -> None:
        with self.assertRaises(instrument_targets.TargetError):
            instrument_targets.parse_target_specs("repository:src")


class ResolvePackageTests(unittest.TestCase):
    def test_resolves_all_namespace_package_locations(self) -> None:
        fake_spec = SimpleNamespace(
            submodule_search_locations=["/first/pkg", "/second/pkg"],
            origin=None,
        )
        with patch.object(
            instrument_targets.importlib.util, "find_spec", return_value=fake_spec
        ):
            self.assertEqual(
                instrument_targets.resolve_package("sample"),
                [
                    ("directory", Path("/first/pkg")),
                    ("directory", Path("/second/pkg")),
                ],
            )

    def test_resolves_single_file_module(self) -> None:
        fake_spec = SimpleNamespace(
            submodule_search_locations=None, origin="/tmp/module.py"
        )
        with patch.object(
            instrument_targets.importlib.util, "find_spec", return_value=fake_spec
        ):
            self.assertEqual(
                instrument_targets.resolve_package("module"),
                [("file", Path("/tmp/module.py"))],
            )


class InstrumentTargetTests(unittest.TestCase):
    def test_counts_new_file_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "module.py"
            target.write_text("value = 1\n", encoding="utf-8")

            def create_backup(_command: list[str], check: bool) -> None:
                self.assertTrue(check)
                Path(f"{target}.orig").touch()

            with patch.object(
                instrument_targets.subprocess, "run", side_effect=create_backup
            ):
                count = instrument_targets.instrument_target(
                    "file", target, "example.Analysis"
                )

            self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
