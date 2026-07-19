# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.27] - 2026-07-19

### Added
- Light audio enhance before transcription: high-pass filter and capped level
  boost so quieter / off-mic speech is more stable for ASR. Default is Light;
  Off sends raw capture (previous behaviour).
- Microphone input picker in Settings → Transcription. The list prefers Windows
  WASAPI and hides duplicate MME / DirectSound / WDM-KS entries and mapper
  aliases so each physical mic appears once.

### Fixed
- int16 mono conversion for sounddevice `(frames, 1)` buffers that could
  full-scale clip audio and make recognition unusable (including empty results
  with enhance Off).

## [1.1.26] - 2026-07-17

### Added
- Windows installer (`OmniVerte-Setup-<version>.exe`) via Inno Setup (per-user
  install, shortcuts, optional autostart).
- `scripts/build.ps1` for local executable + installer builds.
- GitHub Actions release workflow: build and publish the installer on `v*.*.*`
  tags.

### Changed
- PyInstaller layout switched from onefile to onedir (faster startup, cleaner
  install layout).
- Bundled `VERSION` file so the About page shows the real app version.

## [0.1.7]

- Baseline before installer/release tooling. See git history for earlier changes.