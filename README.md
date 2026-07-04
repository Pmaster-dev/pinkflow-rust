# pinkflow-rust

[![Rust CI](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/ci.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/ci.yml)
[![Release](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/release.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/release.yml)
[![Version Check](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/version-check.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/version-check.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./version.txt)

`pinkflow-rust` is now a minimal Rust project scaffold for the Pinkflow runtime. This repository keeps a small Python helper for release/version management and preserves the existing static design artifacts while establishing a real Rust codebase.

## Current Repository Scope

- Rust binary crate in `/home/runner/work/pinkflow-rust/pinkflow-rust/src`
- Versioning files: `/home/runner/work/pinkflow-rust/pinkflow-rust/version.txt`, `/home/runner/work/pinkflow-rust/pinkflow-rust/CHANGELOG.md`, `/home/runner/work/pinkflow-rust/pinkflow-rust/version_manager.py`
- GitHub Actions workflows for CI, release tagging, and version validation
- Static design/prototype assets in `/home/runner/work/pinkflow-rust/pinkflow-rust/index.html` and `/home/runner/work/pinkflow-rust/pinkflow-rust/magicians.html`

## Getting Started

### Prerequisites

- Rust toolchain with `cargo`
- Python 3.8+

### Build

```bash
cargo build
```

### Test

```bash
cargo test
python3 -m unittest discover -s tests
```

### Run

```bash
cargo run
cargo run -- version
cargo run -- help
```

## Version Management

The canonical repository version is stored in `/home/runner/work/pinkflow-rust/pinkflow-rust/version.txt`.

Use the helper script to bump versions and keep the Rust manifest in sync:

```bash
python3 version_manager.py --get-version
python3 version_manager.py --bump patch --message "Describe the release"
python3 version_manager.py --create-tag --message "Release v0.1.1"
```

When bumping a version, the script updates:

- `/home/runner/work/pinkflow-rust/pinkflow-rust/version.txt`
- `/home/runner/work/pinkflow-rust/pinkflow-rust/Cargo.toml`
- `/home/runner/work/pinkflow-rust/pinkflow-rust/CHANGELOG.md`

## Repository Layout

See `/home/runner/work/pinkflow-rust/pinkflow-rust/filesystem` for the current tracked structure.

## Contributing

1. Create a branch from `main`
2. Make your changes
3. Run the Rust and Python test commands above
4. Update the changelog when preparing a release
5. Open a pull request
