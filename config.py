"""Shared Workshop build directories and builder settings."""
from __future__ import annotations

from pathlib import Path

RIG_BUILD_DIRECTORY = r'C:\Users\sldun\Documents\maya\projects\rig_build'
CANNON_DIRECTORY = 'canon_rigs'
CANNON_PROP_DIRECTORY = 'canon_prop_rigs'

# Keys are UI labels; values are subfolders of RIG_BUILD_DIRECTORY.
ASSET_CATEGORIES = {
    'Characters': CANNON_DIRECTORY,
    'Props': CANNON_PROP_DIRECTORY,
    'Vehicles': 'vehicles',
}
DEFAULT_TEMPLATE = {'Characters': 'canon', 'Props': None, 'Vehicles': None}
PROFILE_DIRECTORY = '_profiles'
PROFILE_SIZE = 256
SNAPSHOT_SIZE = 512
MAYA_FILE_EXTENSIONS = ('.ma', '.mb')

SNAPSHOT_UTILS_MODULE = 'Workshop.snapshots.camera_core'


def category_root(category: str) -> Path:
    return Path(RIG_BUILD_DIRECTORY) / ASSET_CATEGORIES[category]


def profile_path(category: str, asset_name: str) -> Path:
    return Path(RIG_BUILD_DIRECTORY) / PROFILE_DIRECTORY / ASSET_CATEGORIES[category] / f'{asset_name}.png'
