from __future__ import annotations

import maya.api.OpenMaya as om
from maya import cmds

from .core import GuideInfo, create_guide_from_position


class GuideCurve:
    """
    Utility class for reading and rebuilding guide curves.

    Example:
        guide_object = GuideCurve(
            curve="spine_guide_crv",
            resample_amount=5,
            output_names=["hip", "spineA", "spineB"],
            ignore_handles=True,
            align_normals=True,
        )

        print(guide_object.locator_list[0].name)
        print(guide_object.locator_list[0].pos)
        print(guide_object.locator_list[0].rot)
        print(guide_object.locator_list[0].matrix)

        print(guide_object.curve)
        print(guide_object.group)
        print(guide_object.count)
    """

    def __init__(
        self,
        curve: str,
        resample_amount: int = -1,
        output_names: list[str] | None = None,
        ignore_handles: bool = True,
        align_normals: bool = False,
        mirror: bool = False,
        primary_axis: str | None = None,
    ):

        self.input_curve = curve
        self.resample_amount = resample_amount
        self.output_names = output_names or []
        self.ignore_handles = ignore_handles
        self.align_normals = align_normals
        self.mirror = mirror
        self.primary_axis = primary_axis

        self.locator_list: list[GuideInfo] = []

        self.curve: str = ""
        self.group: str = ""
        self.count: int = 0

        self.build()

    # =========================================================
    # BUILD
    # =========================================================

    def refresh_locator_data(self) -> None:
        """
        Update stored locator positions, rotations,
        and world matrices after mirroring.
        """

        for locator in self.locator_list:
            locator.pos = tuple(
                cmds.xform(
                    locator.name,
                    query=True,
                    worldSpace=True,
                    translation=True,
                )  # type:ignore
            )

            locator.rot = tuple(
                cmds.xform(
                    locator.name,
                    query=True,
                    worldSpace=True,
                    rotation=True,
                )  # type:ignore
            )

            matrix = cmds.xform(
                locator.name,
                query=True,
                worldSpace=True,
                matrix=True,
            )

            if not isinstance(matrix, (list, tuple)):
                raise TypeError(f"Expected matrix, got {type(matrix).__name__}")

            locator.matrix = [float(value) for value in matrix]

    def mirror_curve_for_build(self) -> None:
        """
        Reflect the duplicated curve across world X = 0
        before creating guides.
        """

        mirror_grp = cmds.group(
            empty=True,
            name=f"{self.input_curve}_tempMirror_grp",
        )

        cmds.parent(
            self.curve,
            mirror_grp,
        )

        cmds.setAttr(
            f"{mirror_grp}.scaleX",
            -1,  # type:ignore
        )

        cmds.parent(
            self.curve,
            world=True,
        )

        cmds.delete(mirror_grp)

    def mirror_guide_group(self) -> None:
        """
        Mirror the completed guide group back across X.

        The negative scale is retained on the group so
        its children inherit the reflected transform.
        """

        cmds.setAttr(
            f"{self.group}.scaleX",
            -1,  # type:ignore
        )

    def enforce_curve_direction(self) -> bool:
        """
        Ensure the curve starts closest to the world X center
        and progresses outward.

        Works for both positive and negative X.

        Returns:
            bool: True if the curve was reversed.
        """

        cvs = cmds.ls(
            f"{self.curve}.cv[*]",
            flatten=True,
        )

        if len(cvs) < 2:
            return False

        start_pos = cmds.pointPosition(
            cvs[0],
            world=True,
        )

        end_pos = cmds.pointPosition(
            cvs[-1],
            world=True,
        )

        start_distance = abs(start_pos[0])
        end_distance = abs(end_pos[0])

        if start_distance > end_distance:
            cmds.reverseCurve(
                self.curve,
                constructionHistory=False,
                replaceOriginal=True,
            )

            return True

        return False

    def ensure_primary_axis(self) -> None:
        """Optionally orient the duplicated curve along a signed world axis."""
        if self.primary_axis is None:
            return

        axis = self.primary_axis.upper().strip()
        axis_indices = {
            "+X": (0, 1),
            "-X": (0, -1),
            "+Y": (1, 1),
            "-Y": (1, -1),
            "+Z": (2, 1),
            "-Z": (2, -1),
        }
        if axis not in axis_indices:
            raise ValueError(
                f"Invalid primary_axis: {self.primary_axis}. "
                "Expected +X, -X, +Y, -Y, +Z, or -Z."
            )

        cvs = cmds.ls(f"{self.curve}.cv[*]", flatten=True) or []
        if len(cvs) < 2:
            return

        axis_index, desired_sign = axis_indices[axis]
        start = cmds.pointPosition(cvs[0], world=True)
        end = cmds.pointPosition(cvs[-1], world=True)
        delta = end[axis_index] - start[axis_index]
        if abs(delta) < 1e-6:
            return

        if (1 if delta > 0 else -1) != desired_sign:
            cmds.reverseCurve(
                self.curve,
                constructionHistory=False,
                replaceOriginal=True,
            )

    def build(self) -> None:

        self.duplicate_and_resample_curve()

        if self.mirror:
            self.mirror_curve_for_build()

        if self.primary_axis is None:
            self.enforce_curve_direction()
        else:
            self.ensure_primary_axis()

        self.create_group()
        self.create_locators()

        if self.mirror:
            self.mirror_guide_group()
            self.refresh_locator_data()

        self.count = len(self.locator_list)

    # =========================================================
    # CURVE SETUP
    # =========================================================

    def duplicate_and_resample_curve(self) -> None:

        self.curve = cmds.duplicate(
            self.input_curve,
            name=f"{self.input_curve}_guideCurve",
        )[0]

        if self.resample_amount != -1:
            cmds.rebuildCurve(
                self.curve,
                constructionHistory=False,
                replaceOriginal=True,
                rebuildType=0,
                endKnots=1,
                keepRange=0,
                keepControlPoints=False,
                keepEndPoints=True,
                keepTangents=False,
                spans=self.resample_amount - 1,
                degree=3,
                tolerance=0.01,
            )

    def create_group(self) -> None:

        self.group = cmds.group(
            empty=True,
            name=f"{self.input_curve}_guide_grp",
        )

        cmds.parent(self.curve, self.group)

    # =========================================================
    # LOCATORS
    # =========================================================

    def create_locators(self) -> None:

        cvs = cmds.ls(f"{self.curve}.cv[*]", flatten=True)

        if self.ignore_handles and len(cvs) > 4:
            cvs = cvs[1:-1]

        padding = len(str(len(cvs)))

        for i, cv in enumerate(cvs):
            pos: list[float] = cmds.pointPosition(cv, world=True)

            # -------------------------------------------------
            # Name
            # -------------------------------------------------

            if i < len(self.output_names):
                loc_name = self.output_names[i]
            else:
                loc_name = f"{self.input_curve}_cv_{str(i + 1).zfill(padding)}"

            guide = create_guide_from_position(
                pos=pos,
                guide_name=loc_name,
                parent=self.group,
            )

            # Align the actual Workshop guide before caching its data.
            if self.align_normals:
                rot = self._calculate_rotation_from_cvs(cvs, i)
                cmds.xform(
                    guide.name,
                    worldSpace=True,
                    rotation=rot,
                )

            self.locator_list.append(guide)

    # =========================================================
    # NORMAL / ROTATION
    # =========================================================

    def _calculate_rotation_from_cvs(
        self,
        cvs: list[str],
        index: int,
    ) -> tuple[float, float, float]:

        current_pos = om.MVector(cmds.pointPosition(cvs[index], world=True))

        # -----------------------------------------------------
        # Edge Cases
        # -----------------------------------------------------

        if index == 0:
            next_pos = om.MVector(cmds.pointPosition(cvs[index + 1], world=True))

            tangent = (next_pos - current_pos).normalize()

        elif index == len(cvs) - 1:
            prev_pos = om.MVector(cmds.pointPosition(cvs[index - 1], world=True))

            tangent = (current_pos - prev_pos).normalize()

        else:
            prev_pos = om.MVector(cmds.pointPosition(cvs[index - 1], world=True))

            next_pos = om.MVector(cmds.pointPosition(cvs[index + 1], world=True))

            tangent = (next_pos - prev_pos).normalize()

        # -----------------------------------------------------
        # Build Rotation Matrix
        # -----------------------------------------------------

        up_vector = om.MVector(0, 1, 0)

        # Prevent parallel vector issue
        if abs(tangent * up_vector) > 0.999:
            up_vector = om.MVector(1, 0, 0)

        side = (tangent ^ up_vector).normalize()
        up = (side ^ tangent).normalize()

        matrix = om.MMatrix(
            [
                side.x,
                side.y,
                side.z,
                0.0,
                up.x,
                up.y,
                up.z,
                0.0,
                tangent.x,
                tangent.y,
                tangent.z,
                0.0,
                current_pos.x,
                current_pos.y,
                current_pos.z,
                1.0,
            ]
        )

        transform_matrix = om.MTransformationMatrix(matrix)

        euler = transform_matrix.rotation()

        rot = (
            om.MAngle(euler.x).asDegrees(),
            om.MAngle(euler.y).asDegrees(),
            om.MAngle(euler.z).asDegrees(),
        )

        return rot