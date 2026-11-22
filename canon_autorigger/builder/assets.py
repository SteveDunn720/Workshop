"""Pure filesystem utilities for Workshop rig assets; no Maya/Qt dependency."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from Workshop import config

_VALID_NAME = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')


@dataclass(frozen=True)
class ValidationResult:
    directory: Path
    exists: bool
    missing: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.exists and not self.missing


def validate_name(name: str) -> str:
    name = name.strip()
    if not _VALID_NAME.fullmatch(name):
        raise ValueError('Names must start with a letter and contain only letters, digits, _ or -.')
    return name


def asset_dir(category: str, name: str) -> Path:
    return config.category_root(category) / validate_name(name)


def list_assets(category: str) -> list[str]:
    root = config.category_root(category)
    if not root.is_dir():
        return []
    return sorted((p.name for p in root.iterdir() if p.is_dir() and _VALID_NAME.fullmatch(p.name)), key=str.casefold)


def scene_file(folder: Path, name: str, suffix: str) -> Path | None:
    """Recognize Maya ASCII/binary and RJG-style capitalization."""
    for path in folder.iterdir() if folder.is_dir() else ():
        if path.is_file() and path.suffix.lower() in config.MAYA_FILE_EXTENSIONS:
            if path.stem.casefold() == f'{name}_{suffix}'.casefold():
                return path
    return None


def missing_items(folder: Path, name: str) -> tuple[str, ...]:
    missing = []
    for suffix in ('guides', 'model'):
        if scene_file(folder, name, suffix) is None:
            missing.append(f'{name}_{suffix}.ma/.mb')
    if not (folder / 'skin_data').is_dir():
        missing.append('skin_data/')
    return tuple(missing)


def validate_asset(category: str, name: str) -> ValidationResult:
    folder = asset_dir(category, name)
    return ValidationResult(folder, folder.is_dir(), missing_items(folder, name))


def _blank_ma() -> str:
    # Minimal, valid Maya ASCII scene; no scene modifications required.
    return ('//Maya ASCII scene\n'
            'requires maya "2023";\n'
            'currentUnit -l centimeter -a degree -t film;\n'
            'fileInfo "application" "Workshop";\n')


def initialize_asset(category: str, name: str, source: str | None = None) -> ValidationResult:
    """Create only missing entries. Copy from a source asset or create empty scenes.

    Existing target files and skin data are NEVER overwritten. Only copies a
    source's skin_data directory when the target lacks it.
    """
    name = validate_name(name)
    target = asset_dir(category, name)
    source_folder = asset_dir(category, source) if source else None
    if source_folder is not None:
        if source_folder == target:
            raise ValueError('An asset cannot use itself as its source.')
        if not source_folder.is_dir():
            raise FileNotFoundError(f'Source asset not found: {source_folder}')
    target.mkdir(parents=True, exist_ok=True)
    for suffix in ('guides', 'model'):
        if scene_file(target, name, suffix) is not None:
            continue
        src = scene_file(source_folder, source, suffix) if source_folder else None
        if src is not None:
            dst = target / f'{name}_{suffix}{src.suffix.lower()}'
            shutil.copy2(src, dst)
        else:
            dst = target / f'{name}_{suffix}.ma'
            with dst.open('x', encoding='utf-8') as stream:
                stream.write(_blank_ma())
    skin = target / 'skin_data'
    if not skin.exists():
        src_skin = source_folder / 'skin_data' if source_folder else None
        if src_skin is not None and src_skin.is_dir():
            shutil.copytree(src_skin, skin)
        else:
            skin.mkdir()
    return validate_asset(category, name)
