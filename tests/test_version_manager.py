import tempfile
import textwrap
import unittest
from pathlib import Path

from version_manager import VersionManager


class VersionManagerTests(unittest.TestCase):
    def create_repo(self):
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)
        (root / "version.txt").write_text("0.1.0\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            textwrap.dedent(
                """\
                # Changelog

                ## [Unreleased]

                ### Added
                - Placeholder
                """
            ),
            encoding="utf-8",
        )
        (root / "Cargo.toml").write_text(
            textwrap.dedent(
                """\
                [package]
                name = "pinkflow-rust"
                version = "0.1.0"
                edition = "2024"

                [dependencies]
                """
            ),
            encoding="utf-8",
        )
        return temp_dir, VersionManager(root)

    def test_bump_patch_updates_cargo_and_version_files(self):
        temp_dir, manager = self.create_repo()
        self.addCleanup(temp_dir.cleanup)

        new_version = manager.bump_version("patch")
        manager.update_version_file(new_version)
        manager.update_cargo_version(new_version)

        self.assertEqual(manager.version_file.read_text(encoding="utf-8"), "0.1.1\n")
        self.assertIn('version = "0.1.1"', manager.cargo_file.read_text(encoding="utf-8"))

    def test_update_changelog_inserts_version_section(self):
        temp_dir, manager = self.create_repo()
        self.addCleanup(temp_dir.cleanup)

        manager.update_changelog("0.1.1", "Release notes")
        changelog = manager.changelog_file.read_text(encoding="utf-8")

        self.assertIn("## [0.1.1]", changelog)
        self.assertIn("Release notes", changelog)


if __name__ == "__main__":
    unittest.main()
