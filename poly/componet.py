import maya.cmds as cmds

from Workshop.poly.convert import flatten_components



def get_component_object(
    component: str,
) -> str:
    """
    Get the object belonging to a component.

    Example:
        body_geo.f[10] -> body_geo
    """

    return component.split(".")[0]


def get_component_index(
    component: str,
) -> int:
    """
    Get the index from a single component.

    Example:
        body_geo.f[10] -> 10
    """

    return int(
        component.rsplit("[", 1)[1].rstrip("]")
    )



def get_component_indices(
    components: str | list[str],
) -> list[int]:
    components = flatten_components(components)

    return [
        get_component_index(component)
        for component in components
    ]