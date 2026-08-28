from __future__ import annotations

import colorsys
import json

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core import clamp_color


RGB = tuple[float, float, float]
HSV = tuple[float, float, float]


COLOR_FOLDER = Path(__file__).resolve().parent
PALETTE_FOLDER = COLOR_FOLDER / "palettes"
RIG_PALETTE_FOLDER = COLOR_FOLDER / "rig_palettes"


@dataclass
class PaletteColor:
    rgb: RGB
    name: str | None = None

    # Rig-specific options.
    rig_type: str | None = None
    draw_on_top: bool = False
    thickness: float = -1.0

    def __post_init__(self) -> None:
        self.rgb = clamp_color(self.rgb)

    @property
    def hsv(self) -> HSV:
        return colorsys.rgb_to_hsv(*self.rgb)

    @property
    def hue(self) -> float:
        return self.hsv[0]

    @property
    def hex_value(self) -> str:
        r, g, b = self.rgb

        return "#{:02X}{:02X}{:02X}".format(
            round(r * 255),
            round(g * 255),
            round(b * 255),
        )

    @classmethod
    def from_hsv(
        cls,
        hsv: HSV,
        name: str | None = None,
        **kwargs,
    ) -> PaletteColor:
        return cls(
            rgb=colorsys.hsv_to_rgb(*hsv),
            name=name,
            **kwargs,
        )

    @classmethod
    def from_hex(
        cls,
        hex_value: str,
        name: str | None = None,
        **kwargs,
    ) -> PaletteColor:
        value = hex_value.lstrip("#")

        if len(value) != 6:
            raise ValueError(
                f"Expected 6-character hex value. Got: {hex_value}"
            )

        rgb = (
            int(value[0:2], 16) / 255.0,
            int(value[2:4], 16) / 255.0,
            int(value[4:6], 16) / 255.0,
        )

        return cls(
            rgb=rgb,
            name=name,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "rgb": list(self.rgb),
            "hsv": list(self.hsv),
            "hex": self.hex_value,
            "rig_type": self.rig_type,
            "draw_on_top": self.draw_on_top,
            "thickness": self.thickness,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PaletteColor:
        return cls(
            name=data.get("name"),
            rgb=tuple(data["rgb"]),
            rig_type=data.get("rig_type"),
            draw_on_top=data.get("draw_on_top", False),
            thickness=data.get("thickness", -1.0),
        )


@dataclass
class Palette:
    name: str
    colors: list[PaletteColor] = field(default_factory=list)
    is_rig_palette: bool = False

    @property
    def color_count(self) -> int:
        return len(self.colors)

    @property
    def folder(self) -> Path:
        if self.is_rig_palette:
            return RIG_PALETTE_FOLDER

        return PALETTE_FOLDER

    def add_color(
        self,
        color: PaletteColor,
    ) -> None:
        self.colors.append(color)

    def get_color(
        self,
        identifier: str | int,
    ) -> PaletteColor:
        if isinstance(identifier, int):
            return self.colors[identifier]

        for color in self.colors:
            if color.name == identifier:
                return color

            if self.is_rig_palette and color.rig_type == identifier:
                return color

        raise KeyError(
            f'Color "{identifier}" does not exist '
            f'in palette "{self.name}".'
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "is_rig_palette": self.is_rig_palette,
            "color_count": self.color_count,
            "colors": [
                color.to_dict()
                for color in self.colors
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> Palette:
        return cls(
            name=data["name"],
            is_rig_palette=data.get(
                "is_rig_palette",
                False,
            ),
            colors=[
                PaletteColor.from_dict(color)
                for color in data.get("colors", [])
            ],
        )


def save_palette(
    palette: Palette,
    filename: str | None = None,
) -> Path:
    palette.folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = filename or palette.name

    filename = (
        filename
        .strip()
        .lower()
        .replace(" ", "_")
    )

    if not filename.endswith(".json"):
        filename += ".json"

    path = palette.folder / filename

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            palette.to_dict(),
            file,
            indent=4,
        )

    return path


def load_palette(
    filename: str,
    rig_palette: bool = False,
) -> Palette:
    folder = (
        RIG_PALETTE_FOLDER
        if rig_palette
        else PALETTE_FOLDER
    )

    if not filename.endswith(".json"):
        filename += ".json"

    path = folder / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Palette does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return Palette.from_dict(data)