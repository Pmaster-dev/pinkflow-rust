# pinkflow-pipeline

[![Release](https://github.com/Pmaster-dev/pinkflow-pipeline/actions/workflows/release.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-pipeline/actions/workflows/release.yml)
[![Version Check](https://github.com/Pmaster-dev/pinkflow-pipeline/actions/workflows/version-check.yml/badge.svg)](https://github.com/Pmaster-dev/pinkflow-pipeline/actions/workflows/version-check.yml)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](./version.txt)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/Pmaster-dev/pinkflow-pipeline)](https://github.com/Pmaster-dev/pinkflow-pipeline/issues)
[![GitHub stars](https://img.shields.io/github/stars/Pmaster-dev/pinkflow-pipeline)](https://github.com/Pmaster-dev/pinkflow-pipeline/stargazers)
[![GitHub license](https://img.shields.io/github/license/Pmaster-dev/pinkflow-pipeline)](https://github.com/Pmaster-dev/pinkflow-pipeline/blob/main/LICENSE)

A comprehensive distributed agentic system for vision to idea, idea to validation, validated to justified, justified report to proposal, approved proposal to dev to preview to hot-loaded building, and community curation DAO with accessibility features showcase.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Versioning](#versioning)
- [CI/CD Integration](#cicd-integration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## Overview

pinkflow-pipeline is an intelligent system that orchestrates multiple AI agents to help validate ideas, build projects, and manage community curation. The platform emphasizes accessibility, particularly for ASL (American Sign Language) support, and integrates with various services for real-time collaboration and knowledge management.

## Features

- 🤖 **Multi-Agent Orchestration** - Coordinates multiple AI agents for complex workflows
- ✅ **Idea Validation** - Automated validation of ideas with AI-powered scoring
- 🏗️ **Project Building** - Transform validated ideas into structured projects
- ♿ **Accessibility First** - Built-in ASL support and accessibility features
- 🔄 **Real-time Collaboration** - PinkSync integration for live updates and alerts
- 📊 **Knowledge Management** - RAG memory and Elasticsearch integration
- 🏛️ **Community DAO** - Decentralized curation and governance features

## Project Structure

See [filesystem](./filesystem) for the complete directory structure and organization.

## Versioning

This project uses [Semantic Versioning](https://semver.org/) for version management.

### Current Version

The current version is tracked in [`version.txt`](./version.txt).

### Version Format

Versions follow the `MAJOR.MINOR.PATCH` format:
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in a backward-compatible manner
- **PATCH**: Backward-compatible bug fixes

### Managing Versions

We provide a `version_manager.py` script to automate version updates:

#### Get Current Version
```bash
python version_manager.py --get-version
```

#### Bump Version
```bash
# Bump patch version (0.1.0 -> 0.1.1)
python version_manager.py --bump patch --message "Bug fixes and improvements"

# Bump minor version (0.1.0 -> 0.2.0)
python version_manager.py --bump minor --message "Added new features"

# Bump major version (0.1.0 -> 1.0.0)
python version_manager.py --bump major --message "Breaking changes"
```

#### Create Git Tag
```bash
python version_manager.py --create-tag --message "Release v0.1.0"
```

### Release Workflow

1. **Make your changes** and commit them to your branch
2. **Update the version** using the version manager:
   ```bash
   python version_manager.py --bump [major|minor|patch] --message "Description of changes"
   ```
3. **Review the changes** in `version.txt` and `CHANGELOG.md`
4. **Commit the version update**:
   ```bash
   git add version.txt CHANGELOG.md
   git commit -m "Bump version to X.Y.Z"
   ```
5. **Create a Git tag**:
   ```bash
   python version_manager.py --create-tag --message "Release vX.Y.Z"
   ```
6. **Push changes and tags**:
   ```bash
   git push
   git push origin --tags
   ```

### Changelog

All notable changes are documented in [CHANGELOG.md](./CHANGELOG.md) following the [Keep a Changelog](https://keepachangelog.com/) format.

## CI/CD Integration

### Automated Version Tagging

For CI/CD pipelines, you can automate version tagging:

```yaml
# Example GitHub Actions workflow
name: Release
on:
  push:
    branches: [main]
    
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Get version
        id: version
        run: echo "VERSION=$(cat version.txt)" >> $GITHUB_OUTPUT
      - name: Create Release
        uses: actions/create-release@v1
        with:
          tag_name: v${{ steps.version.outputs.VERSION }}
          release_name: Release v${{ steps.version.outputs.VERSION }}
```

## Development

### Prerequisites

- Python 3.8+
- Git

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/Pmaster-dev/pinkflow-pipeline.git
   cd pinkflow-pipeline
   ```

2. Check the current version:
   ```bash
   python version_manager.py --get-version
   ```

## Contributing

When contributing to this project:

1. Create a feature branch from `main`
2. Make your changes
3. Update the changelog if applicable
4. Submit a pull request
5. The maintainers will handle version bumping for releases

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- **Repository**: [github.com/Pmaster-dev/pinkflow-pipeline](https://github.com/Pmaster-dev/pinkflow-pipeline)
- **Issues**: [Report a bug or request a feature](https://github.com/Pmaster-dev/pinkflow-pipeline/issues)

---

<p align="center">
  Made with ❤️ by the pinkflow-pipeline Team
</p>
