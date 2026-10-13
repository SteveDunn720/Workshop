from dataclasses import dataclass


@dataclass
class GuidePlacement:
    """
    Describes how a guide position should be solved from mesh data.
    """

    name: str
    region: str

    method: str = "center"

    offset: tuple[float, float, float] = (
        0.0,
        0.0,
        0.0,
    )

@dataclass
class SplinePlacement:
    name: str
    side: str = "M"

    lower_name: str = "lower"
    upper_name: str = "upper"

    lower_region: str = ""
    upper_region: str = ""