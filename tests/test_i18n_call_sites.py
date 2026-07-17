# file: tests/test_i18n_call_sites.py

"""Static checks over every `t()` call site in the app source.

The catalog tests (`test_i18n_catalog.py`) look outward from the catalog: does
every locale cover every key? These look the other way — does every key the code
*asks for* actually exist, and does every lookup happen somewhere it can see the
current locale? A typo'd key is not an exception, it renders as a raw dotted
string in the UI, so nothing catches it at runtime until a user reports it.

Parsed with `ast`, not imported and not grepped: importing would need Qt and a
config dir, and a regex cannot tell a `t(...)` in a function body from one in a
class body — which is the exact distinction the freeze rule turns on.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from i18n._en import STRINGS as EN

REPO = Path(__file__).resolve().parent.parent

# The app's own packages. Excludes tests/, env/, dist/, build/ and the i18n
# package itself (whose `t` is the definition, not a call site).
SOURCE_DIRS = ("ui", "services", "tray_preparing", "licensing")

SOURCE_FILES = sorted(
    p
    for d in SOURCE_DIRS
    for p in (REPO / d).rglob("*.py")
    if "__pycache__" not in p.parts
) + [REPO / "OmniVerte.py"]

_FILE_IDS = [str(p.relative_to(REPO)).replace("\\", "/") for p in SOURCE_FILES]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _t_calls(tree: ast.Module) -> list[ast.Call]:
    """Every `t(...)` call in a module."""
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "t"
    ]


def _literal_key(call: ast.Call) -> str | None:
    """The key of a `t("literal")` call, or None if it's computed.

    Computed keys are real and intentional — the tray builds
    `t(f"tray.device.{backend}")` — so they are skipped rather than failed. The
    catalog's own "no keys English lacks" test is what covers their targets.
    """
    if not call.args:
        return None
    first = call.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def test_source_files_were_found():
    """Guard on the guard: a moved directory or a bad glob would make every
    test below pass vacuously."""
    assert len(SOURCE_FILES) > 15


@pytest.mark.parametrize("path", SOURCE_FILES, ids=_FILE_IDS)
def test_every_literal_t_key_exists(path):
    """A key the code asks for but the catalog lacks renders as the raw dotted
    string in the UI — no exception, no log a user would see. This is the only
    thing standing between a typo and a shipped `general.hotkye.custom`."""
    missing = sorted(
        {
            key
            for call in _t_calls(_parse(path))
            if (key := _literal_key(call)) is not None and key not in EN
        }
    )
    assert not missing, f"{path.name} calls t() with keys absent from _en.py: {missing}"


def _import_time_t_lines(tree: ast.Module) -> list[int]:
    """Line numbers of `t()` calls that run when the module is imported.

    "Deferred" means the call sits in a body that runs later — a def or a lambda.
    Everything else at module scope runs on import. Three subtleties this has to
    get right, each of which a simpler check gets wrong:

    * A **default argument** is evaluated where the `def` is written, not when
      the function is called, so `def f(tip=t("x"))` at module scope IS an
      import-time call. (This is why base.py's factories take a None sentinel.)
    * A **lambda body** is deferred even at module scope: `CB = lambda: t("x")`
      is fine — the lookup happens when the callback fires.
    * A **class body** runs in its enclosing context's timing, so it inherits
      `deferred` rather than forcing it either way: a class at module scope
      freezes, a class defined inside a function does not.
    """
    lines: set[int] = set()

    def visit(node: ast.AST, deferred: bool) -> None:
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "t"
            and not deferred
        ):
            lines.add(node.lineno)

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in [*node.args.defaults, *node.args.kw_defaults, *node.decorator_list]:
                if d is not None:
                    visit(d, deferred)
            for stmt in node.body:
                visit(stmt, True)
            return
        if isinstance(node, ast.Lambda):
            for d in [*node.args.defaults, *node.args.kw_defaults]:
                if d is not None:
                    visit(d, deferred)
            visit(node.body, True)
            return

        for child in ast.iter_child_nodes(node):
            visit(child, deferred)

    visit(tree, False)
    return sorted(lines)


@pytest.mark.parametrize("path", SOURCE_FILES, ids=_FILE_IDS)
def test_no_t_call_at_import_time(path):
    """THE freeze rule, enforced.

    A module-level `TITLE = t("x")` or a class attribute `PAGE_TITLE = t("x")`
    resolves once, under whatever locale happened to be active when the module
    was first imported — and then survives every rebuild, every retranslate and
    every language switch. It is the one bug in this feature that looks like it
    works right up until someone changes language, and it is close to invisible
    in review, because the call site looks identical to a correct one.
    """
    offenders = _import_time_t_lines(_parse(path))
    assert not offenders, (
        f"{path.name} resolves t() at import time, freezing it in the boot "
        f"locale (lines {offenders}). Hold a catalog KEY at module/class scope "
        f"and call t() inside the function that builds the widget."
    )
