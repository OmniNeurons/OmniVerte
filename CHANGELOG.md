# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.32] - 2026-09-25

### Added
- A header button between the license chip and the theme switch for adding a
  glossary term. Pro opens Settings on the Glossary term list, scrolled to the
  editor and ready to type. Without Pro the button explains that the shortcut
  and the larger glossary come with a license; the five Free terms stay
  available under Settings → Glossary.
- Google Gemini 3.5 Transcribe as a cloud transcription backend in the priority
  chain. Glossary terms go out as the API's own vocabulary list.

## [1.1.31] - 2026-08-26

### Added
- Rich text pasted into the main window (from a browser, Word, Slack, …) now
  keeps its formatting — bold, italic, headings, lists, tables, links —
  through Translate, Fix, and all rewrite styles. The result renders formatted
  in the Result card, and copying puts both plain text and HTML on the
  clipboard so rich targets paste the formatting while plain targets get clean
  text. Guarded round-trip: truncated or structurally diverged model replies
  are retried once, then degrade gracefully to the best available result.
- A "Clear styles" button on the Result card that appears only when the result
  actually carries formatting and flattens it to plain text.
- Max AI response length is now configurable (Settings → Languages → AI text
  processing; default 4000 tokens, up from the hard-coded 1500 that silently
  truncated long texts). Applies to every gpt-4o-mini transform, window
  buttons and hotkey actions alike.

### Fixed
- Pasting rich text whose adjacent spans carried different colours could hang
  the app in an infinite loop (a stream of "QTextCursor::setPosition: Position
  out of range" warnings). The colour-stripping sweep now collects its edits
  first and applies them after the walk, and no longer touches colourless
  fragments at all.

## [1.1.30] - 2026-08-25

### Added
- Cloud API failures the user must act on (quota exhausted, key rejected, rate
  limit, no network) now surface as a Windows tray toast naming the provider
  and the fix, in the UI language. One toast per recording session; messages
  are framed with warning marks so they can never be mistaken for dictated
  text.

### Fixed
- A failed final transcription (dead quota, revoked key, offline) no longer
  leaves the recording indicator stuck on "processing" — the app reports the
  error, resets, and the next hotkey press works again.
- When LLM post-processing fails and the raw transcript is pasted as a
  fallback, the user is now told why the text arrived uncorrected.

## [1.1.29] - 2026-08-03

### Fixed
- Pro settings pages now re-gate live when the license changes while the
  Settings window is open.

## [1.1.28] - 2026-08-02

### Added
- Every release now ships a second, stable-named installer asset
  `OmniVerte-Setup.exe` alongside the versioned one, so
  `releases/latest/download/OmniVerte-Setup.exe` is a permanent link that
  always resolves to the newest installer.

### Changed
- README download button points at the permanent installer link and starts
  the download in one click instead of opening the releases page.

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