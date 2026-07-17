# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Windows installer (`OmniVerte-Setup-<version>.exe`) built with Inno Setup:
  per-user install, Start Menu/desktop shortcuts, optional autostart.
- `scripts/build.ps1` to build the executable and installer locally end-to-end.
- `release` GitHub Actions workflow: builds and publishes the installer plus a
  portable zip to GitHub Releases on every `v*` tag.

### Changed
- PyInstaller build switched from onefile to onedir for fast startup (no per-run
  self-extraction) and clean installer layout.
- The bundled executable now ships the `VERSION` file, so the About page shows
  the real version instead of "unknown".

## [0.1.7]

- Baseline before installer/release tooling. See git history for earlier changes.
