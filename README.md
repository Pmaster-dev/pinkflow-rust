# pinkflow-rust

[![Rust CI](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/ci.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/ci.yml)
[![Release](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/release.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/release.yml)
[![Version Check](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/version-check.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-rust/actions/workflows/version-check.yml)
[![Version](https://img.shields.io/github/v/release/Pmaster-dev/pinkflow-rust?display_name=tag&sort=semver)](https://github.com/Pmaster-dev/pinkflow-rust/releases)

`pinkflow-rust` is now a minimal Rust project scaffold for the Pinkflow runtime. This repository keeps a small Python helper for release/version management and preserves the existing static design artifacts while establishing a real Rust codebase.

## Current Repository Scope

- Rust binary crate in `src/`
- Versioning files: `version.txt`, `CHANGELOG.md`, `version_manager.py`
- GitHub Actions workflows for CI, release tagging, and version validation
- Static design/prototype assets in `index.html` and `magicians.html`

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

The canonical repository version is stored in `version.txt`.

Use the helper script to bump versions and keep the Rust manifest in sync:

```bash
python3 version_manager.py --get-version
python3 version_manager.py --bump patch --message "Describe the release"
python3 version_manager.py --create-tag --message "Release v0.1.1"
```

When bumping a version, the script updates:

- `version.txt`
- `Cargo.toml`
- `CHANGELOG.md`

## Repository Layout

See `filesystem` for the current tracked structure.

## Contributing

1. Create a branch from `main`
2. Make your changes
3. Run the Rust and Python test commands above
4. Update the changelog when preparing a release
5. Open a pull request
