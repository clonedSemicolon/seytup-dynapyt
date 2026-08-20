#!/usr/bin/env python3
"""Resolve and instrument one or more DynaPyt targets for the composite action."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from typing import Iterable


class TargetError(RuntimeError):
    """Raised when an action target cannot be resolved or instrumented."""


def parse_target_specs(
    targets: str, directory: str = "", package: str = ""
) -> list[tuple[str, str]]:
    """Parse explicit targets or fall back to the legacy single-target inputs."""
    if targets.strip():
        raw_specs = targets.splitlines()
    elif directory.strip():
        raw_specs = [f"directory:{directory}"]
    elif package.strip():
        raw_specs = [f"package:{package}"]
    else:
        raise TargetError("Setup mode needs targets, directory, or package.")

    parsed: list[tuple[str, str]] = []
    for raw_spec in raw_specs:
        spec = raw_spec.strip()
        if not spec or spec.startswith("#"):
            continue

        kind, separator, value = spec.partition(":")
        kind = kind.strip()
        value = value.strip()
        if not separator or kind not in {"directory", "package", "file"}:
            raise TargetError(
                f"Invalid target '{spec}'. Expected directory:<path>, "
                "package:<import-name>, or file:<path>."
            )
        if not value:
            raise TargetError(f"Target '{spec}' has an empty value.")
        parsed.append((kind, value))

    if not parsed:
        raise TargetError("No valid DynaPyt targets were supplied.")
    return parsed


def resolve_package(name: str) -> list[tuple[str, Path]]:
    """Resolve a Python import name to all instrumentable source locations."""
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise TargetError(f"Python package is not importable: {name}")

    locations = list(spec.submodule_search_locations or [])
    if locations:
        return [("directory", Path(location)) for location in locations]

    if spec.origin and spec.origin.endswith(".py"):
        return [("file", Path(spec.origin))]

    raise TargetError(
        f"Python target '{name}' has no instrumentable .py source: {spec.origin}"
    )


def resolve_targets(
    specs: Iterable[tuple[str, str]]
) -> list[tuple[str, Path, str]]:
    """Resolve directory/file paths and expand package targets."""
    resolved: list[tuple[str, Path, str]] = []
    for kind, value in specs:
        if kind == "package":
            package_targets = resolve_package(value)
            print(f"[dynapyt] Resolved package '{value}':")
            for resolved_kind, path in package_targets:
                print(f"[dynapyt]   {resolved_kind}:{path}")
                resolved.append((resolved_kind, path, f"package:{value}"))
        else:
            resolved.append((kind, Path(value), f"{kind}:{value}"))
    return resolved


def backup_paths(kind: str, target: Path) -> set[Path]:
    if kind == "directory":
        return set(target.rglob("*.py.orig"))
    return {Path(f"{target}.orig")} if Path(f"{target}.orig").is_file() else set()


def instrument_target(kind: str, target: Path, analysis: str) -> int:
    """Instrument one resolved path and return its newly created backup count."""
    if kind == "directory":
        if not target.is_dir():
            raise TargetError(f"Directory target does not exist: {target}")
        command = [
            sys.executable,
            "-m",
            "dynapyt.run_instrumentation",
            "--directory",
            str(target),
            "--analysis",
            analysis,
        ]
    elif kind == "file":
        if not target.is_file():
            raise TargetError(f"File target does not exist: {target}")
        if target.suffix != ".py":
            raise TargetError(f"File targets must end in .py: {target}")
        command = [
            sys.executable,
            "-m",
            "dynapyt.instrument.instrument",
            "--files",
            str(target),
            "--analysis",
            analysis,
        ]
    else:
        raise TargetError(f"Unsupported resolved target type: {kind}")

    before = backup_paths(kind, target)
    subprocess.run(command, check=True)
    after = backup_paths(kind, target)
    count = len(after - before)
    print(f"[dynapyt] Instrumented {count} file(s) for {kind} target: {target}")
    return count


def main() -> int:
    analysis = os.environ.get("DYNAPYT_ANALYSIS_INPUT", "").strip()
    if not analysis:
        raise TargetError("The analysis input must not be empty.")

    specs = parse_target_specs(
        os.environ.get("DYNAPYT_TARGETS_INPUT", ""),
        os.environ.get("DYNAPYT_DIRECTORY_INPUT", ""),
        os.environ.get("DYNAPYT_PACKAGE_INPUT", ""),
    )
    resolved = resolve_targets(specs)
    total = sum(
        instrument_target(kind, path, analysis) for kind, path, _source in resolved
    )

    print(
        f"[dynapyt] Instrumented {total} new Python file(s) across "
        f"{len(resolved)} resolved target(s)."
    )
    fail_on_empty = os.environ.get(
        "DYNAPYT_FAIL_ON_EMPTY_INPUT", "true"
    ).lower() in {"1", "true", "yes"}
    if total == 0:
        message = (
            "No files were instrumented; the selected workflow steps cannot "
            "produce DynaPyt traces."
        )
        if fail_on_empty:
            raise TargetError(message)
        print(f"::warning::{message}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TargetError, subprocess.CalledProcessError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1)
