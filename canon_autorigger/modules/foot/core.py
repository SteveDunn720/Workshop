
from dataclasses import dataclass
from weakref import proxy
import maya.cmds as cmds

from Workshop.control import create_control
from Workshop.transform.utils import get_position, match_transform, convert_to_matrix
from Workshop.joint import create_joint
from Workshop.maya_api.node import ConditionNode, DistanceBetweenNode, MultiplyDivideNode, ReverseNode
from Workshop.guide.core import GuideInfo
from Workshop.transform.constraint import constraint
from attribute_utils import add_proxy, connect_attributes, set_attribute

from ..ik import auto_pv_space, create_IK_single_chain
from ..module_shared import fkik_switch, module_prep, module_space

from.utils import build_compressible_ik_length
from .roll import Roll

@dataclass
class module_info:
    ik_controls:list
    fk_control:list
    swtich_joints:list
    fk_joints:list
    ik_joints:list
    bind_joints:list

@dataclass
class foot_guides:
    true_heel:GuideInfo
    true_foot:GuideInfo
    true_groundfoot:GuideInfo
    true_toe:GuideInfo
    true_inbank:GuideInfo
    true_outbank:GuideInfo
    true_ball:GuideInfo
    og_foot_pos:list[GuideInfo]
    aim_angle:float
    neg:str
    pos:str

class Foot:
    def __init__(
        self,
        leg_info,
        feet_guides:foot_guides,
        part: str = "foot",
        side: str = "L",
        parent: str = "components",
        control_parent: str | None = None,
        rig_size: float = 1.0,
        guides: list = [],
        piv_guides: list = [],
        fk_control_space:list = [],
        ik_control_space:list = [],
        ik_hook:list=[],
        fkik_switch_attr:str = '',
        joint_parent:str = 'foot_joint',
        fk_start_size:float = 6.0,
        fk_shape:str = "fk",
        fk_twist:tuple = (0,90,0),
        ik_foot_size:float = 1/4,
        ik_foot_shape:str = "foot",
        ik_toe_shape:str = "ik_toes",
        ik_toe_size:float = 1/8,
        ik_foot_twist:tuple = (0,0,0),
        piv_shape:str = 'sphere',

        

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.rig_size: float = rig_size
        self.guides: list = guides
        self.fk_control_space = fk_control_space
        self.ik_control_space = ik_control_space
        self.main_control_color = 'Left' if self.side == 'L' else 'Right' 
        self.ik_hook = ik_hook
        self.feet_guides = feet_guides
        self.fkik_switch_attr = fkik_switch_attr
        self.leg_info = leg_info
        self.joint_parent = joint_parent
        self.fk_start_size = fk_start_size
        self.fk_shape = fk_shape
        self.fk_twist = fk_twist
        self.ik_foot_size = ik_foot_size
        self.ik_foot_shape = ik_foot_shape
        self.ik_toe_shape = ik_toe_shape
        self.ik_toe_size = ik_toe_size
        self.ik_foot_twist = ik_foot_twist
        self.piv_guides = piv_guides
        self.piv_shape = piv_shape

    # -------------------
    # Build steps
    # -------------------


    def get_ground_distance(self, object)->float:
        pos = get_position(object)

        return pos[1]
        

    def _build_limited_roll_copy(self, roll_info):
        """Mirror the evaluated roll pivots under the length-limited leg output.

        The *source* roll tree stays parented under the animator's foot controls.
        Only the mirrored hierarchy moves with the length-limited leg joint.
        We connect LOCAL transform channels, so the roll/bank pivots retain
        their original relationships instead of copying world matrices.
        """
        if not self.leg_info.ik_len:
            raise ValueError("Foot roll length copy requires leg IK length joints.")

        def long_path(node):
            matches = cmds.ls(node, long=True) or []
            if len(matches) != 1:
                raise RuntimeError(f"Roll transform is missing or ambiguous: {node}")
            return matches[0]

        root = long_path(roll_info.roll_grp)
        up = long_path(roll_info.up_driver)
        down = long_path(roll_info.down_driver)

        def path_from_root(leaf):
            path = []
            current = leaf
            while current != root:
                path.append(current)
                parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
                if not parents:
                    raise RuntimeError(f"{leaf} is not beneath {root}")
                current = parents[0]
            return list(reversed(path))

        # The source roll is planted under the animator foot control.
        # Follow its root, not IK_len: otherwise the pivot lift is doubled.
        offset = cmds.createNode(
            "transform", name=f"foot_{self.side}_limited_roll_offset",
            parent=self.guts,
        )
        cmds.xform(
            offset, worldSpace=True,
            matrix=cmds.xform(self.guides[0].name, query=True,
                              worldSpace=True, matrix=True),
        )
        cmds.parentConstraint(root, offset, maintainOffset=True)

        # A separate layer applies ONLY the displacement caused by the
        # capped leg length.  Before the cap it remains at (0, 0, 0).
        correction = cmds.createNode(
            "transform", name=f"foot_{self.side}_roll_reach_correction",
            parent=offset,
        )

        # Recreate the union of the paths leading to ankle and ball/toe.
        # This includes bank and twist pivots, the roll center and the
        # complete back/front chains, without duplicating animator controls.
        # Include every pivot from roll.py, not just the paths to the
        # ankle and toe. This retains the complete banking/twist structure.
        pivot_sources = [long_path(p) for p in roll_info.pivot_transforms]
        pivot_sources += [up, down]
        originals = [root]
        for leaf in pivot_sources:
            for source in path_from_root(leaf):
                if source not in originals:
                    originals.append(source)
        # Source pivots are listed in build order, not necessarily DAG order
        # (roll_center gets reparented underneath bank_twist_offset).
        originals.sort(key=lambda item: item.count("|"))

        mirrored = {}
        for source in originals:
            if source == root:
                parent = correction
            else:
                src_parent = cmds.listRelatives(
                    source, parent=True, fullPath=True,
                )[0]
                parent = mirrored[src_parent]

            short_name = source.rsplit("|", 1)[-1].replace(":", "_")
            copy = cmds.createNode(
                "transform",
                name=f"{short_name}_limited_{self.side}",
                parent=parent,
            )
            mirrored[source] = copy

            cmds.setAttr(
                f"{copy}.rotateOrder",
                cmds.getAttr(f"{source}.rotateOrder"),
            )
            # Match rest local pivots, then mirror every animated component.
            # The root is special: its position is held relative to the
            # length offset, not driven by the unrestricted foot control.
            if source == root:
                cmds.xform(
                    copy, worldSpace=True,
                    matrix=cmds.xform(source, query=True,
                                      worldSpace=True, matrix=True),
                )
                continue

            for attr in ("rotatePivot", "rotatePivotTranslate",
                         "scalePivot", "scalePivotTranslate", "rotateAxis"):
                value = cmds.getAttr(f"{source}.{attr}")[0]
                cmds.setAttr(f"{copy}.{attr}", *value, type="double3")

            for base, axes in (("translate", "XYZ"),
                               ("rotate", "XYZ"),
                               ("scale", "XYZ"),
                               ("shear", "XYZ")):
                # Maya's shear channels are XY/XZ/YZ, not shearX/Y/Z.
                if base == "shear":
                    suffixes = ("XY", "XZ", "YZ")
                else:
                    suffixes = axes
                for axis in suffixes:
                    cmds.connectAttr(
                        f"{source}.{base}{axis}",
                        f"{copy}.{base}{axis}",
                        force=True,
                    )

        # --------------------------------------------------
        # Reach-only offset (the tested double-lift correction).
        # --------------------------------------------------
        # Measure the ankle against the hip.  This is the *unrestricted*
        # source roll, never the limited copy, avoiding evaluation cycles.
        limb_root = self.leg_info.ik_joints[0]
        limb_short = limb_root.rsplit("|", 1)[-1]
        if not limb_short.startswith("IK_") or not limb_short.endswith("_jnt"):
            raise RuntimeError(f"Unexpected IK root name: {limb_root}")
        prefix = limb_short[len("IK_"):-len("_jnt")]
        distance_node = f"{prefix}_stretch_distance"
        length_sum = f"{prefix}_limb_length_sum.output1D"
        if not cmds.objExists(distance_node):
            raise RuntimeError(f"Missing stretch distance: {distance_node}")
        if not cmds.objExists(length_sum):
            raise RuntimeError(f"Missing limb length output: {length_sum}")
        hip_matrix = cmds.connectionInfo(
            f"{distance_node}.inMatrix1", sourceFromDestination=True,
        )
        if not hip_matrix:
            raise RuntimeError("Missing hip matrix driving stretch distance")
        ankle_source = cmds.connectionInfo(
            f"{distance_node}.inMatrix2", sourceFromDestination=True,
        )
        # The limb stretch module measures its own end_pos transform.
        # That is a valid endpoint even if end_ik_hook has a different
        # structure in a particular Biped_Limb revision.  The Foot.build()
        # method connects the *actual* endpoint to the source roll ankle.
        if not ankle_source or not ankle_source.endswith(".worldMatrix[0]"):
            raise RuntimeError(
                "Stretch distance needs a transform worldMatrix endpoint. "
                f"Found {ankle_source!r}"
            )

        hip_dm = cmds.createNode(
            "decomposeMatrix", name=f"{prefix}_reach_hip_dm",
        )
        ankle_dm = cmds.createNode(
            "decomposeMatrix", name=f"{prefix}_reach_ankle_dm",
        )
        cmds.connectAttr(hip_matrix, f"{hip_dm}.inputMatrix")
        cmds.connectAttr(f"{up}.worldMatrix[0]", f"{ankle_dm}.inputMatrix")

        direction = cmds.createNode(
            "plusMinusAverage", name=f"{prefix}_reach_direction",
        )
        cmds.setAttr(f"{direction}.operation", 2)
        cmds.connectAttr(
            f"{ankle_dm}.outputTranslate", f"{direction}.input3D[0]",
        )
        cmds.connectAttr(
            f"{hip_dm}.outputTranslate", f"{direction}.input3D[1]",
        )

        safe_distance = cmds.createNode(
            "condition", name=f"{prefix}_reach_safe_distance",
        )
        cmds.setAttr(f"{safe_distance}.operation", 2)  # greater than
        cmds.connectAttr(f"{distance_node}.distance",
                         f"{safe_distance}.firstTerm")
        cmds.setAttr(f"{safe_distance}.secondTerm", 0.001)
        cmds.connectAttr(f"{distance_node}.distance",
                         f"{safe_distance}.colorIfTrueR")
        cmds.setAttr(f"{safe_distance}.colorIfFalseR", 0.001)

        unit = cmds.createNode(
            "multiplyDivide", name=f"{prefix}_reach_unit_vector",
        )
        cmds.setAttr(f"{unit}.operation", 2)  # divide
        for axis in "XYZ":
            cmds.connectAttr(
                f"{direction}.output3D{axis.lower()}",
                f"{unit}.input1{axis}",
            )
            cmds.connectAttr(
                f"{safe_distance}.outColorR", f"{unit}.input2{axis}",
            )

        excess = cmds.createNode(
            "plusMinusAverage", name=f"{prefix}_reach_excess",
        )
        cmds.setAttr(f"{excess}.operation", 2)
        cmds.connectAttr(length_sum, f"{excess}.input1D[0]")
        cmds.connectAttr(
            f"{distance_node}.distance", f"{excess}.input1D[1]",
        )

        gate = cmds.createNode(
            "condition", name=f"{prefix}_reach_excess_gate",
        )
        cmds.setAttr(f"{gate}.operation", 2)  # distance > allowed length
        cmds.connectAttr(
            f"{distance_node}.distance", f"{gate}.firstTerm",
        )
        cmds.connectAttr(length_sum, f"{gate}.secondTerm")
        cmds.connectAttr(
            f"{excess}.output1D", f"{gate}.colorIfTrueR",
        )
        cmds.setAttr(f"{gate}.colorIfFalseR", 0)

        displacement = cmds.createNode(
            "multiplyDivide", name=f"{prefix}_reach_world_delta",
        )
        for axis in "XYZ":
            cmds.connectAttr(
                f"{unit}.output{axis}", f"{displacement}.input1{axis}",
            )
            cmds.connectAttr(
                f"{gate}.outColorR", f"{displacement}.input2{axis}",
            )

        to_local = cmds.createNode(
            "vectorProduct", name=f"{prefix}_reach_local_delta",
        )
        cmds.setAttr(f"{to_local}.operation", 3)  # vector * matrix
        cmds.setAttr(f"{to_local}.normalizeOutput", False)
        cmds.connectAttr(
            f"{displacement}.output", f"{to_local}.input1",
        )
        cmds.connectAttr(
            f"{offset}.worldInverseMatrix[0]", f"{to_local}.matrix",
        )
        cmds.connectAttr(f"{to_local}.output", f"{correction}.translate")

        # Intermediary joints give the downstream IK/toe setup a distinct
        # driven layer. They never feed the unrestricted roll hierarchy.
        foot_driver = cmds.createNode(
            "joint", name=f"IK_roll_limited_foot_{self.side}_jnt",
            parent=offset,
        )
        ball_driver = cmds.createNode(
            "joint", name=f"IK_roll_limited_ball_{self.side}_jnt",
            parent=offset,
        )
        for joint, source in ((foot_driver, up), (ball_driver, down)):
            cmds.xform(
                joint, worldSpace=True,
                matrix=cmds.xform(source, query=True,
                                  worldSpace=True, matrix=True),
            )
            cmds.parentConstraint(
                mirrored[source], joint, maintainOffset=False,
            )
            cmds.setAttr(f"{joint}.visibility", 0)

        self.limited_roll_offset = offset
        self.limited_roll_pivots = mirrored
        self.limited_roll_joints = [foot_driver, ball_driver]
        return foot_driver, ball_driver

    def build(self):
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp

        ground_offset = self.get_ground_distance(object=self.guides[0].name)
        self.controls = []


        self.switch_joints = []

        jnt_par = self.guts
        #switch_joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'switch_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt
        
        #Fk_build
        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.guides):
            ctrl = create_control(
                name=f'FK_{jnt.descriptor}',
                parent=ctrl_par,
                transform=jnt.name,
                size=self.rig_size * 1/(self.fk_start_size * (i + 1)),
                control_shape=self.fk_shape,
                direction="y",
                color_type=self.main_control_color,
                shape_rotation_offset=self.fk_twist
            )

            fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False,)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl.ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl

        constraint(drivers=[self.fk_controls[0].ctrl], driven=self.leg_info.fk_hook)
            
            

        self.ik_joints = []
        self.ik_controls = []
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        jnt_par = self.guts
        

        #IK_build 
        for i,jnt in enumerate(self.guides):
            ik_jnt = create_joint(name=f'IK_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt
        
        ctrl_par = self.ik_control_grp

        self.ik_foot = create_control(
                name=f'IK_{self.guides[0].descriptor}_main',
                parent=ctrl_par,
                transform=self.guides[0].name,
                size=self.rig_size * self.ik_foot_size,
                control_shape=self.ik_foot_shape,
                direction="y",
                color_type=self.main_control_color,
                shape_position_offset=(0, -ground_offset, self.rig_size/10),
                shape_rotation_offset=self.ik_foot_twist
            )
        for axis in ['X', 'Y', 'Z']:
            set_attribute(f'{self.ik_foot.top}.rotate{axis}', 0)
        if self.side == 'R':
            set_attribute(f'{self.ik_foot.top}.rotateY', 180)
        self.front_piv = create_control(
                name=f'IK_{self.piv_guides[0].descriptor}_piv',
                parent=self.ik_foot.ctrl,
                transform=self.piv_guides[0].name,
                size=self.rig_size * self.ik_foot_size / 20,
                control_shape=self.piv_shape,
                direction="y",
                color_type=self.main_control_color, 
            )
        self.back_piv = create_control(
                name=f'IK_{self.piv_guides[1].descriptor}_piv',
                parent=self.front_piv.ctrl,
                transform=self.piv_guides[1].name,
                size=self.rig_size * self.ik_foot_size / 20,
                control_shape=self.piv_shape,
                direction="y",
                color_type=self.main_control_color, 
            )

        module_space(space_list=self.ik_control_space, control=self.ik_foot)
        self.ik_controls.append(self.ik_foot)
        self.controls.append(self.ik_foot)
        self.ik_toes = create_control(
                name=f'IK_{self.guides[1].descriptor}',
                parent=ctrl_par,
                transform=f'{self.guides[1].name}',
                size=self.rig_size * self.ik_toe_size,
                control_shape=self.ik_toe_shape,
                direction="y",
                color_type=self.main_control_color,
            )
        constraint(drivers=[self.ik_toes.ctrl], driven=self.ik_joints[1], constraint_type='parent', parent=self.guts)
        self.ik_controls.append(self.ik_toes)
        self.controls.append(self.ik_toes)


        self.FK_IK_Switch = fkik_switch(controls=self.controls, node_attr=self.main_grp, descriptor=self.part, fk_grp=self.fk_control_grp, ik_grp=self.ik_control_grp, fk_joints=self.fk_joints, ik_joints=self.ik_joints, switch_joints=self.switch_joints, connect_switch_attr=self.fkik_switch_attr )

        jnt_par = self.guts
        self.ik_roll_joints = []
        
        #IK_roll_build 
        for i,jnt in enumerate(self.guides):
            ik_jnt = create_joint(name=f'IK_roll_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.ik_roll_joints.append(ik_jnt)
            jnt_par = ik_jnt

        roll_ik = create_IK_single_chain(name=f'{self.part}_{self.side}_roll', start_joint=self.ik_roll_joints[0], end_joint=self.ik_roll_joints[1])
        cmds.parent(roll_ik.handle, self.guts)

        roll = Roll(part='roll', rig_size=self.rig_size, side=self.side, joints= [f'foot_{self.side}', f'ball_{self.side}'], guides=self.feet_guides, control_parent=self.back_piv.ctrl)
        roll_info = roll.build()

        match_transform(transform=roll_info.roll_grp, target_transform=self.feet_guides.og_foot_pos[-2]) #type:ignore
        cmds.parent(roll_info.roll_grp, self.back_piv.ctrl)
        add_proxy(source=self.leg_info.ik_stretch_attr, proxy_list=[self.ik_foot.ctrl], proxy_name='stretch')

        # --------------------------------------------------
        # Planted source roll vs. length-limited driven roll.
        # --------------------------------------------------
        # roll_grp is ALREADY parented beneath back_piv.ctrl above.
        # Do not constrain it to the IK length joint; it must remain
        # planted at the control pivot while the control moves past reach.

        # The stretch measuring end_pos must follow the UNLIMITED roll ankle
        # target, never the length-limited copy (that would create a cycle).
        # No height_difference translation is connected to end_pos.
        limb_root = self.leg_info.ik_joints[0]
        limb_short = limb_root.rsplit("|", 1)[-1]
        if not limb_short.startswith("IK_") or not limb_short.endswith("_jnt"):
            raise RuntimeError(f"Unexpected IK root name: {limb_root}")
        stretch_name = limb_short[len("IK_"):-len("_jnt")]
        endpoint_matrix = cmds.connectionInfo(
            f"{stretch_name}_stretch_distance.inMatrix2",
            sourceFromDestination=True,
        )
        if not endpoint_matrix or not endpoint_matrix.endswith(".worldMatrix[0]"):
            raise RuntimeError(
                f"Cannot resolve stretch endpoint: {endpoint_matrix!r}"
            )
        end_pos = endpoint_matrix.rsplit(".worldMatrix[0]", 1)[0]
        if not cmds.objExists(end_pos):
            raise RuntimeError(f"Stretch endpoint does not exist: {end_pos}")
        constraint(
            drivers=[roll_info.up_driver],
            driven=end_pos,
            constraint_type="parent",
            parent=self.guts,
        )

        # The separate IK length chain still follows the animator's
        # base foot pivot and provides the limited world-space motion.
        constraint(
            drivers=[self.back_piv.ctrl],
            driven=self.leg_info.ik_len[0].handle,
            constraint_type="parent",
            parent=self.guts,
        )
        constraint(
            drivers=[self.back_piv.ctrl],
            driven=self.leg_info.ik_len[2],
            constraint_type="orient",
            parent=self.guts,
        )

        # Mirror the complete pivot paths under an IK-length-driven offset.
        # Both downstream IK and toes read from the LIMITED copy.
        limited_ankle, limited_toe = self._build_limited_roll_copy(roll_info)

        constraint(drivers=[limited_toe], driven=roll_ik.handle,
                   constraint_type='parent', parent=self.guts)
        constraint(drivers=[limited_toe], driven=self.ik_roll_joints[1],
                   constraint_type='orient', parent=self.guts)
        constraint(drivers=[limited_ankle], driven=self.ik_hook[0],
                   constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_hook[1]], driven=self.ik_roll_joints[0],
                   constraint_type='parent', parent=self.guts)
        constraint(drivers=[self.ik_roll_joints[0]], driven=self.ik_joints[0],
                   constraint_type='parent', parent=self.guts)
        constraint(drivers=[limited_toe], driven=self.ik_toes.top,
                   constraint_type='parent', parent=self.guts)

        self.bind_joints = []

        jnt_par = self.joint_parent


        #bind joints
        for i,jnt in enumerate(self.guides):
            switch_jnt = create_joint(name=f'def_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False)
            self.bind_joints.append(switch_jnt)
            jnt_par = switch_jnt
            constraint(drivers=[self.switch_joints[i]], driven=switch_jnt, parent=self.guts, constraint_type="parent")


        if self.leg_info.auto_pv_driven:
            pv_auto = auto_pv_space(end_control=self.ik_foot, pv_control=self.leg_info.ik_controls[1], parent_space=self.ik_control_space[0], parent=self.guts, swing_range=((-90, 90),(-self.rig_size/10, self.rig_size/10)))
            cmds.parent(self.leg_info.auto_pv_driven, pv_auto.driver)


        feet_info = module_info(fk_control=self.fk_controls, ik_controls=self.ik_controls, swtich_joints=self.switch_joints, fk_joints=self.fk_joints, ik_joints=self.ik_joints, bind_joints=self.bind_joints,)
        return feet_info






