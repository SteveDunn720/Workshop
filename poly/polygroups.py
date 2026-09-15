from dataclasses import dataclass, field

from Workshop.poly.convert import (
    to_border_edges,
    to_internal_edges,
    to_uvs,
    uv_shell_to_edges,
    uv_shell_to_faces,
    uv_shell_to_verts,
)
from Workshop.poly.uvs import faces_to_uv_shell, faces_to_uvs, fit_uvs_to_udim, get_uv_shell, get_uv_shell_count, get_uv_shell_from_id, get_uv_shell_id, get_uv_shells, get_uvs_in_udim, move_uv_shell_to_udim, sew_uv_edges
from Workshop.poly.meshes import get_mesh_shells, is_mesh
from Workshop.poly.uv_sets import copy_uv_set, create_uv_set
from Workshop.poly.uv_sets import (
    create_uv_set,
    validate_uv_set,
)
from Workshop.poly.face import get_face_indices, get_selected_faces
from Workshop.color.maya import set_faces_color
from Workshop.color.maya import set_color_display as set_mesh_color_display
from Workshop.color.core import random_color


@dataclass
class PolyGroup:
    name: str
    index: int
    mesh: str
    uv_set: str
    color: tuple[float, float, float]

    def apply_color(self) -> None:
        """Apply this polygroup's color to its current faces."""

        faces = self.get_faces()

        set_faces_color(
            mesh=self.mesh,
            faces=get_face_indices(faces),
            color=self.color,
        )

    @property
    def udim(self) -> int:
        """Get the UDIM assigned to this polygroup."""

        return get_udim_from_index(
            index=self.index,
        )

    def get_uvs(self) -> list[str]:
        """Get the current UVs belonging to this polygroup."""

        return get_uvs_in_udim(
            mesh=self.mesh,
            udim=self.udim,
            uv_set=self.uv_set,
        )

    def get_faces(self) -> list[str]:
        """Get the current faces belonging to this polygroup."""

        return uv_shell_to_faces(
            self.get_uvs()
        )

    def get_edges(self) -> list[str]:
        """Get the current edges belonging to this polygroup."""

        return uv_shell_to_edges(
            self.get_uvs()
        )

    def get_verts(self) -> list[str]:
        """Get the current vertices belonging to this polygroup."""

        return uv_shell_to_verts(
            self.get_uvs()
        )

    def get_border_edges(self) -> list[str]:
        """Get the current border edges belonging to this polygroup."""

        return to_border_edges(
            self.get_faces()
        )


@dataclass
class PolyGroupSubLayer:
    name: str
    mesh: str
    uv_set: str

    polygroups: list[PolyGroup] = field(
        default_factory=list
    )


@dataclass
class PolyGroupLayer:
    name: str
    mesh: str
    uv_set: str

    polygroups: list[PolyGroup] = field(
        default_factory=list
    )

    sublayers: list[PolyGroupSubLayer] = field(
        default_factory=list
    )

    def set_color_display(
        self,
        enabled: bool,
    ) -> None:
        """Toggle polygroup color display."""

        set_mesh_color_display(
            mesh=self.mesh,
            enabled=enabled,
        )

def initialize_polygroup_layer(
    mesh: str,
    name: str | None = None,
    uv_set: str | None = None,
) -> PolyGroupLayer:
    """
    Initialize a polygroup layer.

    If no UV set is supplied, a new polygroup UV set is created and
    the entire mesh is registered as the default polygroup.

    If an existing UV set is supplied, the layer is connected to it
    without automatically generating polygroups.

    Args:
        mesh: Mesh the layer belongs to.
        name: Optional layer name.
        uv_set: Optional existing UV set.

    Returns:
        Initialized PolyGroupLayer.
    """

    if not is_mesh(mesh):
        raise RuntimeError(
            f"Object is not a polygon mesh: '{mesh}'."
        )

    if name is None:
        name = "polygroup_layer"

    create_default = uv_set is None

    if uv_set is None:
        uv_set = f"{name}_UV"

        create_uv_set(
            mesh=mesh,
            uv_set=uv_set,
            initialize=True,
        )

    else:
        validate_uv_set(
            mesh=mesh,
            uv_set=uv_set,
        )

    layer = PolyGroupLayer(
        name=name,
        mesh=mesh,
        uv_set=uv_set,
    )

    if create_default:
        initialize_default_polygroup(
            layer=layer,
        )

    return layer


def initialize_default_polygroup(
    layer: PolyGroupLayer,
    name: str = "default",
) -> PolyGroup:
    """Initialize the entire mesh as the default polygroup."""

    shell_count = get_uv_shell_count(
        mesh=layer.mesh,
        uv_set=layer.uv_set,
    )

    if shell_count != 1:
        raise RuntimeError(
            f"Expected one UV shell when initializing default "
            f"polygroup, found {shell_count}."
        )

    polygroup = initialize_polygroup(
        layer=layer,
        name=name,
    )

    uvs = get_uv_shell_from_id(
        mesh=layer.mesh,
        shell_id=0,
        uv_set=layer.uv_set,
    )

    fit_uvs_to_udim(
        uvs=uvs,
        udim=polygroup.udim,
        uv_set=layer.uv_set,
    )

    return polygroup


def initialize_polygroup_sublayer(
    layer: PolyGroupLayer,
    name: str,
) -> PolyGroupSubLayer:
    """
    Initialize a sublayer underneath a polygroup layer.

    Sublayers share the UV set belonging to their parent layer.

    Args:
        layer: Parent polygroup layer.
        name: Name of the new sublayer.

    Returns:
        Initialized PolyGroupSubLayer.
    """

    sublayer = PolyGroupSubLayer(
        name=name,
        mesh=layer.mesh,
        uv_set=layer.uv_set,
    )

    layer.sublayers.append(
        sublayer
    )

    return sublayer


def initialize_polygroup(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    name: str | None = None,
    color: tuple[float, float, float] | None = None,
) -> PolyGroup:
    """Initialize a polygroup."""

    index = get_next_polygroup_index(
        layer=layer,
    )

    if name is None:
        name = generate_polygroup_name(
            layer=layer,
            index=index,
        )

    if polygroup_name_exists(
        layer=layer,
        name=name,
    ):
        raise RuntimeError(
            f"Polygroup '{name}' already exists "
            f"in '{layer.name}'."
        )

    if color is None:
        color = random_color()

    polygroup = PolyGroup(
        name=name,
        index=index,
        mesh=layer.mesh,
        uv_set=layer.uv_set,
        color=color,
    )

    layer.polygroups.append(
        polygroup
    )

    return polygroup


def polygroup_name_exists(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    name: str,
) -> bool:
    """Check whether a polygroup name already exists in a layer."""

    return any(
        polygroup.name == name
        for polygroup in layer.polygroups
        
    )


def get_next_polygroup_index(
    layer: PolyGroupLayer | PolyGroupSubLayer,
) -> int:
    """Get the next available polygroup index."""

    if not layer.polygroups:
        return 0

    return max(
        polygroup.index
        for polygroup in layer.polygroups
    ) + 1


def generate_polygroup_name(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    index: int | None = None,
) -> str:
    """Generate a default polygroup name."""

    if index is None:
        index = get_next_polygroup_index(
            layer=layer,
        )

    return f"polygroup_{index:02d}"



def generate_polygroups_from_uv_shells(
    mesh: str,
    source_uv_set: str,
    name: str = "polygroup_layer",
) -> PolyGroupLayer:
    """Create a polygroup layer from an existing UV set."""

    if not is_mesh(mesh):
        raise RuntimeError(
            f"Object is not a polygon mesh: '{mesh}'."
        )

    validate_uv_set(
        mesh=mesh,
        uv_set=source_uv_set,
    )

    polygroup_uv_set = f"{name}_UV"

    copy_uv_set(
        mesh=mesh,
        source_uv_set=source_uv_set,
        target_uv_set=polygroup_uv_set,
    )

    layer = PolyGroupLayer(
        name=name,
        mesh=mesh,
        uv_set=polygroup_uv_set,
    )

    # IMPORTANT:
    # Capture every shell before modifying any UVs.
    shells = get_uv_shells(
        mesh=mesh,
        uv_set=polygroup_uv_set,
    )

    for shell_uvs in shells:
        polygroup = initialize_polygroup(
            layer=layer,
        )

        fit_uvs_to_udim(
            uvs=shell_uvs,
            udim=polygroup.udim,
            uv_set=polygroup_uv_set,
        )

        polygroup.apply_color()

    return layer


def create_polygroup_from_selection(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    name: str | None = None,
    color: tuple[float, float, float] | None = None,
) -> PolyGroup:
    """Create a polygroup from the currently selected faces."""

    faces = get_selected_faces()

    if not faces:
        raise RuntimeError(
            "No polygon faces selected."
        )

    faces_to_uv_shell(
        faces=faces,
        uv_set=layer.uv_set,
        create_uv_set_if_missing=False,
        sew_interior=True,
    )

    uvs = faces_to_uvs(
        faces,
        uv_set=layer.uv_set,
    )

    if not uvs:
        raise RuntimeError(
            "Could not find UVs for selected faces."
        )

    shell_uvs = get_uv_shell(
        uv=uvs[0],
        uv_set=layer.uv_set,
    )

    polygroup = initialize_polygroup(
        layer=layer,
        name=name,
        color=color,
    )

    fit_uvs_to_udim(
    uvs=shell_uvs,
    udim=polygroup.udim,
    uv_set=layer.uv_set,
)

    polygroup.apply_color()

    return polygroup


def generate_polygroups_from_mesh_shells(
    layer: PolyGroupLayer | PolyGroupSubLayer,
) -> list[PolyGroup]:
    """
    Generate polygroups from disconnected polygon regions.
    """

    mesh_shells = get_mesh_shells(
        mesh=layer.mesh,
    )

    polygroups = []

    for faces in mesh_shells:

        faces_to_uv_shell(
            faces=faces,
            uv_set=layer.uv_set,
            create_uv_set_if_missing=False,
            sew_interior=True,
        )

        uvs = faces_to_uvs(
            faces,
            uv_set=layer.uv_set,
        )

        if not uvs:
            continue

        shell_id = get_uv_shell_id(
            uv=uvs[0],
            uv_set=layer.uv_set,
        )

        polygroup = initialize_polygroup(
            layer=layer,
            shell_id=shell_id,
        )

        polygroups.append(
            polygroup
        )

    return polygroups


def get_udim_from_index(
    index: int,
) -> int:
    """
    Get a UDIM number from a polygroup index.

    Args:
        index: Polygroup index.

    Returns:
        Corresponding UDIM number.
    """

    if index < 0:
        raise ValueError(
            "Polygroup index cannot be negative."
        )

    return 1001 + index


def combine_polygroups(
    target: PolyGroup,
    source: PolyGroup,
) -> PolyGroup:
    """Combine one polygroup into another."""

    if target.mesh != source.mesh:
        raise RuntimeError(
            "Cannot combine polygroups from different meshes."
        )

    if target.uv_set != source.uv_set:
        raise RuntimeError(
            "Cannot combine polygroups from different UV sets."
        )

    combined_faces = (
        target.get_faces()
        + source.get_faces()
    )

    interior_edges = to_internal_edges(
        combined_faces
    )

    sew_uv_edges(
        edges=interior_edges,
        uv_set=target.uv_set,
    )

    combined_uvs = faces_to_uvs(
        faces=combined_faces,
        uv_set=target.uv_set,
    )

    fit_uvs_to_udim(
        uvs=combined_uvs,
        udim=target.udim,
        uv_set=target.uv_set,
    )

    target.apply_color()

    return target


def remove_polygroup(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    polygroup: PolyGroup,
) -> None:
    """Remove a polygroup from a layer."""

    if polygroup not in layer.polygroups:
        raise RuntimeError(
            f"Polygroup '{polygroup.name}' does not belong "
            f"to layer '{layer.name}'."
        )

    layer.polygroups.remove(
        polygroup
    )

def merge_polygroups(
    layer: PolyGroupLayer | PolyGroupSubLayer,
    target: PolyGroup,
    source: PolyGroup,
) -> PolyGroup:
    """Merge a source polygroup into a target polygroup."""

    combine_polygroups(
        target=target,
        source=source,
    )

    remove_polygroup(
        layer=layer,
        polygroup=source,
    )

    return target