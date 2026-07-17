# Third-Party Notices

Omni Verte itself is licensed under the Elastic License 2.0 (see `LICENSE`).
It bundles, or depends on at runtime, the third-party components listed below.
Each remains under its own license; those licenses are reproduced or linked
here as required. This file is informational — the authoritative license for
each component is the one shipped with that component.

## Bundled / runtime dependencies

| Component | Purpose | License |
| --- | --- | --- |
| [PySide6](https://www.qt.io/qt-for-python) (Qt for Python) | GUI toolkit | LGPL-3.0 |
| [PySideSix-Frameless-Window](https://pypi.org/project/PySideSix-Frameless-Window/) | Frameless/themed window chrome | LGPL-3.0 |
| [PySide6-Fluent-Widgets](https://pypi.org/project/PySide6-Fluent-Widgets/) | Fluent-style widgets | **GPL-3.0** (dual-licensed; commercial license available) |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Local speech-to-text | MIT |
| [openai](https://github.com/openai/openai-python) | OpenAI / Groq API client | Apache-2.0 |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) | Audio capture | MIT |
| [numpy](https://numpy.org/) | Numerics | BSD-3-Clause |
| [scipy](https://scipy.org/) | Signal processing | BSD-3-Clause |
| [rapidfuzz](https://github.com/maxbachmann/RapidFuzz) | Fuzzy matching (glossary layer C) | MIT |
| [keyboard](https://github.com/boppreh/keyboard) | Global keyboard hooks | MIT |
| [mouse](https://github.com/boppreh/mouse) | Mouse hooks | MIT |
| [pyperclip](https://github.com/asweigart/pyperclip) | Clipboard access | BSD-3-Clause |
| [pystray](https://github.com/moses-palmer/pystray) | System-tray icon | LGPL-3.0 |
| [Pillow](https://python-pillow.org/) | Image handling (tray icon) | HPND (MIT-CMU) |
| [keyring](https://github.com/jaraco/keyring) | Credential Manager access | MIT |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `.env` parsing | BSD-3-Clause |
| [PyJWT](https://github.com/jpadilla/pyjwt) | License-token (JWT) decode | MIT |
| [cryptography](https://github.com/pyca/cryptography) | Ed25519 verification backend | Apache-2.0 OR BSD-3-Clause |
| [PyTorch](https://pytorch.org/) (optional) | CUDA acceleration (not bundled) | BSD-3-Clause |

## License obligations

- **LGPL-3.0** (PySide6, PySideSix-Frameless-Window, pystray): the application
  links these dynamically (PyInstaller keeps them as separate modules), and they
  may be replaced with compatible versions. The full text of the
  [GNU LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.txt) and
  [GNU GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.txt) applies.
- **GPL-3.0** (PySide6-Fluent-Widgets): the free edition is GPL-3.0; a
  commercial license is offered by the author for proprietary use. See
  https://qfluentwidgets.com for terms.
- **MIT / BSD / Apache-2.0 / HPND** components: permissive — their copyright and
  permission notices are retained with the distributed package metadata.

Qt and the Qt logo are trademarks of The Qt Company Ltd. All other trademarks
are the property of their respective owners.
