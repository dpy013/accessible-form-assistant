# Repository instructions

## Project overview

- This repository contains a Windows desktop application for accessibility issue collection and report export.
- The app entry point is `src.main:main`.
- The codebase is organized under `src\`, with core logic in `src\core\` and UI code in `src\ui\`.

## Tech stack and packaging

- Use Python 3.12 for development and automation changes.
- Keep dependency definitions aligned between `pyproject.toml` and `requirements.txt` when adding, removing, or updating runtime packages.
- The project is packaged with PyInstaller using `accessible-form-assist.spec`.

## Expected change style

- Prefer small, targeted changes that preserve the current desktop workflow and file-based project structure.
- Reuse existing parsing, importing, exporting, and project management helpers in `src\core\` before adding new abstractions.
- Keep Windows paths and PowerShell-friendly commands in documentation and automation unless a change is explicitly cross-platform.

## Validation

- Run `python -m compileall src` after Python code changes.
- If a change affects packaging or CI, also check the existing GitHub Actions workflow in `.github\workflows\build-binary.yml`.

## GitHub workflow expectations

- Treat `main` as protected; update it through pull requests instead of direct pushes.
- Dependabot is configured to manage both Python dependencies and GitHub Actions updates.
