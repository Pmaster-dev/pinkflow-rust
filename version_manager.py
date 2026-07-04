#!/usr/bin/env python3
"""
Version management script for pinkflow-rust.

This script automates version updates and changelog management.
It supports semantic versioning (MAJOR.MINOR.PATCH) and integrates with Git tags.

Usage:
    python3 version_manager.py --bump [major|minor|patch] --message "Release message"
    python3 version_manager.py --get-version
    python3 version_manager.py --create-tag
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class VersionManager:
    """Manages version updates and changelog entries."""

    def __init__(self, repo_root=None):
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).parent
        self.version_file = self.repo_root / "version.txt"
        self.changelog_file = self.repo_root / "CHANGELOG.md"
        self.cargo_file = self.repo_root / "Cargo.toml"

    def get_current_version(self):
        if not self.version_file.exists():
            return "0.0.0"
        return self.version_file.read_text(encoding="utf-8").strip()

    def parse_version(self, version_str):
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        return tuple(map(int, match.groups()))

    def bump_version(self, bump_type):
        major, minor, patch = self.parse_version(self.get_current_version())

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(
                f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'"
            )

        return f"{major}.{minor}.{patch}"

    def update_version_file(self, new_version):
        self.version_file.write_text(f"{new_version}\n", encoding="utf-8")
        print(f"Updated version.txt to {new_version}")

    def update_cargo_version(self, new_version):
        if not self.cargo_file.exists():
            print("Warning: Cargo.toml not found. Skipping Cargo manifest update.")
            return

        content = self.cargo_file.read_text(encoding="utf-8")
        section_match = re.search(r"\[package\](.*?)(?=\n\[|\Z)", content, re.DOTALL)
        if not section_match:
            raise ValueError("Could not find [package] section in Cargo.toml")

        package_body = section_match.group(1)
        updated_body, replacements = re.subn(
            r'version\s*=\s*"[^"]+"',
            f'version = "{new_version}"',
            package_body,
            count=1,
        )

        if replacements == 0:
            raise ValueError("Could not find package version entry in Cargo.toml")

        updated_content = (
            content[: section_match.start(1)] + updated_body + content[section_match.end(1) :]
        )
        self.cargo_file.write_text(updated_content, encoding="utf-8")
        print(f"Updated Cargo.toml to {new_version}")

    def update_changelog(self, version, message):
        if not self.changelog_file.exists():
            print("Warning: CHANGELOG.md not found. Skipping changelog update.")
            return

        content = self.changelog_file.read_text(encoding="utf-8")
        today = datetime.now().strftime("%Y-%m-%d")
        new_entry = f"\n## [{version}] - {today}\n\n{message}\n"

        unreleased_pattern = r"(## \[Unreleased\].*?)(\n## \[|$)"

        def replace_func(match):
            return match.group(1) + new_entry + match.group(2)

        updated_content, replacements = re.subn(
            unreleased_pattern,
            replace_func,
            content,
            count=1,
            flags=re.DOTALL,
        )

        if replacements == 0:
            updated_content = content.rstrip() + new_entry

        self.changelog_file.write_text(updated_content, encoding="utf-8")
        print(f"Updated CHANGELOG.md with version {version}")

    def create_git_tag(self, version, message=""):
        tag_name = f"v{version}"
        tag_message = message or f"Release version {version}"

        try:
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                check=True,
                cwd=self.repo_root,
            )
            print(f"Created Git tag: {tag_name}")
            print("Note: Push the tag with: git push origin --tags")
        except subprocess.CalledProcessError as exc:
            print(f"Error creating Git tag: {exc}")
            sys.exit(1)
        except FileNotFoundError:
            print("Git not found. Skipping tag creation.")


def main():
    parser = argparse.ArgumentParser(
        description="Manage versions and changelog for pinkflow-rust"
    )
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Bump version (major, minor, or patch)",
    )
    parser.add_argument("--message", help="Release message for changelog")
    parser.add_argument(
        "--get-version", action="store_true", help="Display the current version"
    )
    parser.add_argument(
        "--create-tag", action="store_true", help="Create a Git tag for the current version"
    )

    args = parser.parse_args()
    manager = VersionManager()

    if args.get_version:
        print(manager.get_current_version())
        return

    if args.create_tag:
        manager.create_git_tag(manager.get_current_version(), args.message or "")
        return

    if args.bump:
        if not args.message:
            print("Error: --message is required when bumping version")
            sys.exit(1)

        previous_version = manager.get_current_version()
        new_version = manager.bump_version(args.bump)
        manager.update_version_file(new_version)
        manager.update_cargo_version(new_version)
        manager.update_changelog(new_version, args.message)

        print(f"\nVersion bumped from {previous_version} to {new_version}")
        print("Next steps:")
        print("  1. Review the changes in version.txt, Cargo.toml, and CHANGELOG.md")
        print(
            "  2. Commit the changes: git add version.txt Cargo.toml CHANGELOG.md && git commit -m 'Bump version to {}'".format(
                new_version
            )
        )
        print(
            f"  3. Create a tag: python3 version_manager.py --create-tag --message 'Release {new_version}'"
        )
        print("  4. Push changes and tags: git push && git push origin --tags")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
