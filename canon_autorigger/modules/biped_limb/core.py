from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import create_control
from Workshop.joint import create_joint
from Workshop.transform.utils import create_transform
from Workshop.control.core import Control
from Workshop.transform.constraint import constraint


from ..display_line import create_connection_curve
from ..ik import create_IK_rotate_plane, create_IK_single_chain, IK_data
from ..module_shared import module_prep, module_space, fkik_switch
from ..twist import create_swing_driver, create_twist
from ..correctives.ik_bone import IK_Bone

from .stretch import build_stretchy_ik


from Workshop.canon_autorigger.module_schema import (
    ModuleSetting,
    ModuleRelationship,
    ModuleGuideArray,
)


@dataclass
class moudle_info:
    fk_root:Control
    ik_root:Control
    fk_ik_switch:str
    end_ik_hook:list
    ik_controls:list
    fk_controls:list
    ik_len:list
    ik_stretch_attr:str
    ik_joints:list
    fk_joints:list
    switch_joints:list
    bind_joints:list
    controls:list
    ik_main_handle: IK_data
    ik_singlechain: IK_data | None
    ik_len_joints:list
    fk_hook:str
    upper_sub_joints:list
    lower_sub_joints:list
    auto_pv_driven:str | None



class Biped_Limb:

    MODULE_NAME = "biped_limb"
    DISPLAY_NAME = "Biped Limb"

    GUIDES = (
        ModuleGuideArray(
            name="limb",
            default_count=3,
            minimum_count=3,
            spacing=(0.0, -5.0, 0.0),
            guide_type="joint",
            parented=True,
        ),
    )

    SETTINGS = (
        ModuleSetting(
            name="rig_size",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="ik_end_control",
            setting_type="bool",
            default=False,
        ),
        ModuleSetting(
            name="ikfk_blend",
            setting_type="float",
            default=1.0,
        ),
        ModuleSetting(
            name="ik_length",
            setting_type="bool",
            default=False,
        ),
        ModuleSetting(
            name="split",
            setting_type="string",
            default="single_twist",
        ),
        ModuleSetting(
            name="fk_shape_twist",
            setting_type="float",
            default=0.0,
        ),
        ModuleSetting(
            name="fk_ctrl_shapes",
            setting_type="control_shape",
            default="fk",
        ),
        ModuleSetting(
            name="ik_ctrl_shapes",
            setting_type="control_shape",
            default="box",
        ),
        ModuleSetting(
            name="pv_ctrl_shapes",
            setting_type="control_shape",
            default="sphere",
        ),
        ModuleSetting(
            name="bendy_control_shape",
            setting_type="control_shape",
            default="round_square",
        ),
        ModuleSetting(
            name="twist_count",
            setting_type="int",
            default=4,
        ),
        ModuleSetting(
            name="auto_pv_space",
            setting_type="bool",
            default=False,
        ),
        ModuleSetting(
            name="twist_joints",
            setting_type="bool",
            default=True,
        ),

        ModuleSetting(
            name="ik_bone",
            setting_type="bool",
            default=False,
        ),

        ModuleSetting(
            name="ik_bone_offset",
            setting_type="float",
            default=0.1,
        ),
    )

    RELATIONSHIPS = (
        ModuleRelationship(
            name="joint_parent",
            relationship_type="joint",
            default="auto",
        ),
        ModuleRelationship(
            name="fk_control_space",
            relationship_type="control_space",
            default="auto",
        ),
        ModuleRelationship(
            name="ik_root_control_space",
            relationship_type="control_space",
            default="auto",
        ),
        ModuleRelationship(
            name="ik_pv_control_space",
            relationship_type="control_space",
            default="auto",
        ),
        ModuleRelationship(
            name="ik_end_control_space",
            relationship_type="control_space",
            default="auto",
        ),
    )
    def __init__(
        self,
        guides: list,
        part: str = "leg",
        side: str = "L",
        parent: str = "rig",
        joint_parent:str = None,
        rig_size: float = 1.0,
        fk_control_space:list = [],
        ik_root_control_space:list = [],
        ik_pv_control_space:list = [],
        ik_end_control_space:list = [],
        ik_end_control:bool = False,
        ikfk_blend:float = 1,
        ik_length:bool = False,
        split:str | None = 'single_twist',
        fk_shape_twist = 0,
        fk_ctrl_shapes:str = 'fk',
        ik_ctrl_shapes:str = 'box',
        pv_ctrl_shapes:str = 'sphere',
        bendy_control_shape:str = 'round_square',
        twist_count:int = 4, 
        auto_pv_space:bool = False,
        twist_joints: bool = True,
        ik_bone: bool = False,
        ik_bone_offset: float = 1/50,


    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.rig_size: float = rig_size
        self.guides: list = guides
        self.ik_end_control = ik_end_control
        self.fk_control_space = fk_control_space
        self.ik_root_control_space = ik_root_control_space
        self.ik_pv_control_space = ik_pv_control_space
        self.ik_end_control_space = ik_end_control_space
        self.main_control_color = 'Left' if self.side == 'L' else 'Right'
        self.ikfk_blend = ikfk_blend
        self.ik_length = ik_length
        self.joint_parent = joint_parent
        self.split = split
        self.fk_shape_twist = fk_shape_twist
        self.fk_ctrl_shapes = fk_ctrl_shapes
        self.ik_ctrl_shapes = ik_ctrl_shapes
        self.pv_ctrl_shapes = pv_ctrl_shapes
        self.bendy_control_shape = bendy_control_shape
        self.twist_count = twist_count
        self.auto_pv_space = auto_pv_space
        self.twist_joints = twist_joints
        self.ik_bone = ik_bone
        self.ik_bone_offset = ik_bone_offset


    @staticmethod
    def preview(
        part: str,
        side: str,
        guides: list[str],
        settings: dict,
    ) -> dict:
        """
        Predict the controls and joints created by Biped_Limb.

        Does not create Maya nodes.
        """

        if len(guides) != 3:
            raise ValueError(
                f"Biped_Limb '{part}_{side}' requires exactly "
                f"3 guides, received {len(guides)}."
            )

        def descriptor(guide: str) -> str:
            name = guide.split("|")[-1]

            if name.endswith("_guide"):
                return name[:-6]

            return name

        descriptors = [
            descriptor(guide)
            for guide in guides
        ]

        root, middle, end = descriptors

        ik_end_control = settings.get(
            "ik_end_control",
            False,
        )

        ik_length = settings.get(
            "ik_length",
            False,
        )

        # --------------------------------------------------
        # FK CONTROLS
        # --------------------------------------------------

        fk_controls = [
            f"FK_{root}_ctrl",
            f"FK_{middle}_ctrl",
        ]

        if ik_end_control:
            fk_controls.append(
                f"FK_{end}_ctrl"
            )

        # --------------------------------------------------
        # IK CONTROLS
        # --------------------------------------------------

        ik_controls = [
            f"IK_{root}_ctrl",
            f"{part}_IK_PV_{side}_ctrl",
        ]

        if ik_end_control:
            ik_end = f"IK_{end}_ctrl"
        else:
            ik_end = f"IK_{part}_end_{side}_ctrl"

        ik_controls.append(ik_end)

        # --------------------------------------------------
        # BIND JOINTS
        # --------------------------------------------------

        bind_joints = [
            f"def_{root}_jnt",
            f"def_{middle}_jnt",
        ]

        if ik_end_control:
            bind_joints.append(
                f"def_{end}_jnt"
            )

        # --------------------------------------------------
        # OTHER JOINTS
        # --------------------------------------------------

        switch_joints = [
            f"switch_{root}_jnt",
            f"switch_{middle}_jnt",
        ]

        if ik_end_control:
            switch_joints.append(
                f"switch_{end}_jnt"
            )
        else:
            switch_joints.append(
                f"switch_{end}_solver_jnt"
            )

        ik_joints = [
            f"IK_{root}_jnt",
            f"IK_{middle}_jnt",
        ]

        if ik_end_control:
            ik_joints.append(
                f"IK_{end}_jnt"
            )
        else:
            ik_joints.append(
                f"IK_{end}_hook_jnt"
            )

        fk_joints = [
            f"FK_{root}_jnt",
            f"FK_{middle}_jnt",
        ]

        if ik_end_control:
            fk_joints.append(
                f"FK_{end}_jnt"
            )
        else:
            fk_joints.append(
                f"FK_{end}_solver_jnt"
            )

        if ik_length:
            ik_joints.extend([
                f"IK_len_{root}_jnt",
                f"IK_len_{end}_jnt",
            ])

        # --------------------------------------------------
        # OUTPUT
        # --------------------------------------------------

        controls = fk_controls + ik_controls

        joints = bind_joints

        return {
            "controls": controls,
            "joints": joints,

            "output_control": fk_controls[0],
            "output_joint": bind_joints[-1],

            "fk_controls": fk_controls,
            "ik_controls": ik_controls,

            "bind_joints": bind_joints,
            "switch_joints": switch_joints,
            "fk_joints": fk_joints,
            "ik_joints": ik_joints,

            "fk_root": fk_controls[0],
            "ik_root": ik_controls[0],
            "ik_pv": ik_controls[1],
            "ik_end": ik_end,
        }

    def build(self):

        #module prep

        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=True, bendy=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts
        self.ik_control_grp = prep.ik_grp
        self.fk_control_grp = prep.fk_grp
        self.bend_control_grp = prep.bendy_grp

        self.controls = []
        self.bind_joints = []


        self.switch_joints = []
        jnt_par = self.guts

        #switch_joints
        for i,jnt in enumerate(self.guides):
            if not self.ik_end_control and i == len(self.guides) - 1:
                switch_jnt = create_joint(name=f'switch_{jnt.descriptor}_solver', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            else:
                switch_jnt = create_joint(name=f'switch_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.switch_joints.append(switch_jnt)
            jnt_par = switch_jnt

        #fk_build

        self.fk_controls = []
        self.fk_joints = []

        jnt_par = self.guts
        ctrl_par = self.fk_control_grp
        for i,jnt in enumerate(self.guides):
            if not self.ik_end_control and i == len(self.guides) - 1:
                fk_jnt = create_joint(name=f'FK_{jnt.descriptor}_solver', transform=jnt.name, parent=jnt_par, bind_set= False, ue_set=False,)
                self.fk_joints.append(fk_jnt)
                continue
            ctrl = create_control(
                name=f'FK_{jnt.descriptor}',
                parent=ctrl_par,
                transform=jnt.name,
                size=self.rig_size/6,
                control_shape=self.fk_ctrl_shapes,
                direction="y",
                color_type=self.main_control_color,
                shape_rotation_offset=(0,self.fk_shape_twist,0)
            )

            fk_jnt = create_joint(name=f'FK_{jnt.descriptor}', transform=ctrl.ctrl, parent=jnt_par, bind_set= False, ue_set=False, connect=False)
            constraint(drivers=[ctrl.ctrl], driven=fk_jnt, parent=self.guts,)

            self.fk_joints.append(fk_jnt)
            self.fk_controls.append(ctrl)
            self.controls.append(ctrl)
            jnt_par = fk_jnt
            ctrl_par = ctrl.ctrl
        fk_hook = self.fk_joints[-1]
            
            

        self.ik_joints = []
        self.ik_controls = []
        module_space(space_list=self.fk_control_space, control=self.fk_controls[0])
        jnt_par = self.guts


        
        #IK_build 

        for i,jnt in enumerate(self.guides):
            jnt_name = jnt.descriptor
            if not self.ik_end_control and i == len(self.guides) - 1:
                jnt_name = f'{jnt.descriptor}_hook'
            ik_jnt = create_joint(name=f'IK_{jnt_name}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
            self.ik_joints.append(ik_jnt)
            jnt_par = ik_jnt

        self.ik_handle = create_IK_rotate_plane(name=f'{self.part}_{self.side}', start_joint=self.ik_joints[0], mid_joint=self.ik_joints[1], end_joint=self.ik_joints[2], auto_pv=True, pole_vector_guide='', mirror_pv=True if self.side == 'R' else False)
        cmds.parent(self.ik_handle.handle, self.ik_handle.pole_vector, self.guts)
        self.ik_root_ctrl = create_control(
                name=f'IK_{self.guides[0].descriptor}',
                parent=self.ik_control_grp,
                transform=self.ik_handle.start_joint,
                size=self.rig_size/8,
                control_shape=self.ik_ctrl_shapes,
                direction="y",
                color_type=self.main_control_color
            )
        module_space(space_list=self.ik_root_control_space, control=self.ik_root_ctrl)
        self.controls.append(self.ik_root_ctrl)
        self.ik_controls.append(self.ik_root_ctrl)
        constraint(drivers=[self.ik_root_ctrl.ctrl], driven=self.ik_handle.start_joint, parent=self.guts, constraint_type="parent")
        self.ik_pv_ctrl = create_control(
                name=f'{self.part}_IK_PV_{self.side}',
                parent=self.ik_control_grp,
                transform=self.ik_handle.pole_vector,
                size=self.rig_size/10,
                control_shape=self.pv_ctrl_shapes,
                direction="y",
                color_type=self.main_control_color,
            )

        if self.auto_pv_space:
            pv_driven = create_transform(name=f'{self.part}_IK_PV_{self.side}_auto_driven', transform=self.guides[2].name, parent=self.guts)
            """for axis in ["X", "Y", "Z"]:
                cmds.setAttr(f'{pv_driven}.rotate{axis}', 0)
                cmds.setAttr(f'{pv_driven}.scale{axis}', 1)"""
            pv_space = [pv_driven, *self.ik_pv_control_space]
        else:
            pv_driven = None
            pv_space =self.ik_pv_control_space

        module_space(space_list=pv_space, control=self.ik_pv_ctrl)
        self.controls.append(self.ik_pv_ctrl)
        self.ik_controls.append(self.ik_pv_ctrl)
        constraint(drivers=[self.ik_pv_ctrl.ctrl], driven=self.ik_handle.pole_vector, parent=self.guts, constraint_type="parent")

        if self.ik_end_control:
            self.ik_end_ctrl = create_control(
                name=f'IK_{self.guides[2].descriptor}',
                parent=self.ik_control_grp,
                transform=self.guides[2].name,
                size=self.rig_size/8,
                control_shape=self.ik_ctrl_shapes,
                direction="y",
                color_type=self.main_control_color
            )
            constraint(drivers=[self.ik_end_ctrl.ctrl], driven=self.ik_handle.handle, parent=self.guts, constraint_type="parent")
            cmds.orientConstraint(self.ik_end_ctrl.ctrl, self.ik_joints[2], maintainOffset=True) #REPLACE
            module_space(space_list=self.ik_end_control_space, control=self.ik_end_ctrl)
            self.controls.append(self.ik_end_ctrl)
            self.ik_controls.append(self.ik_end_ctrl)
            self.ik_hook = None
        else:
            self.ik_end_ctrl = create_control(
                name=f'IK_{self.part}_end_{self.side}',
                parent=self.ik_control_grp,
                transform=self.guides[2].name,
                size=self.rig_size/8,
                control_shape=self.ik_ctrl_shapes,
                direction="y",
                color_type=self.main_control_color
            )
            constraint(drivers=[self.ik_end_ctrl.ctrl], driven=self.ik_handle.handle, parent=self.guts, constraint_type="parent")
            cmds.orientConstraint(self.ik_end_ctrl.ctrl, self.ik_joints[2], maintainOffset=True) #REPLACE
            self.controls.append(self.ik_end_ctrl)
            self.ik_controls.append(self.ik_end_ctrl)
            cmds.hide(self.ik_end_ctrl.ctrl)
            self.ik_hook = self.ik_end_ctrl.ctrl


        #self.fkik_switch(controls=self.controls)
        self.FK_IK_Switch = fkik_switch(controls=self.controls, node_attr=self.main_grp, descriptor=self.part, fk_grp=self.fk_control_grp, ik_grp=self.ik_control_grp, fk_joints=self.fk_joints, ik_joints=self.ik_joints, switch_joints=self.switch_joints )
        cmds.setAttr(self.FK_IK_Switch, self.ikfk_blend)


        if self.ik_length:
            self.ik_len_joints = []
            jnt_par = self.guts
            for i,jnt in enumerate(self.guides):
                if i == 1:
                    pass
                else:
                    jnt_name = jnt.descriptor
                    ik_jnt = create_joint(name=f'IK_len_{jnt_name}', transform=jnt.name, parent=jnt_par, connect=False, bind_set= False, ue_set=False,)
                    self.ik_len_joints.append(ik_jnt)
                    jnt_par = ik_jnt
            self.ik_len_chain = create_IK_single_chain(name=f'{self.part}_len_{self.side}', start_joint=self.ik_len_joints[0], end_joint=self.ik_len_joints[1],)
            cmds.parent(self.ik_len_chain.handle, self.guts)
            cmds.pointConstraint(self.ik_joints[0], self.ik_len_joints[0])
            ik_len = [self.ik_len_chain, self.ik_len_joints[0], self.ik_len_joints[1]]
        else:
            ik_len = []

        #stretch
        
        if not self.ik_end_control:
            end_pos = create_transform(name=f'{self.guides[2].descriptor}_len_pos', transform=self.guides[2].name, parent=self.guts)
        else:
            end_pos = self.ik_end_ctrl.ctrl

        build_stretchy_ik(
            name=f'{self.guides[0].descriptor}',
            root_reference=self.ik_root_ctrl.ctrl,
            ik_control=end_pos,
            upper_joint=self.ik_joints[0],
            lower_joint=self.ik_joints[1],
            end_joint=self.ik_joints[2],
            stretch_attr= "stretch",
            drive_length_joint=self.ik_length,
            len_joint=ik_len[2] if self.ik_length else '')

        jnt_par = self.joint_parent

        #bind chain
        for i,jnt in enumerate(self.guides):
            bind_jnt = create_joint(name=f'def_{jnt.descriptor}', transform=jnt.name, parent=jnt_par, connect=False)   
            self.bind_joints.append(bind_jnt)
            jnt_par = bind_jnt
            #constraint(drivers=[self.switch_joints[i]], driven=bind_jnt, parent=self.guts, constraint_type="parent")

        # --------------------------------------------------
        # Twist joints
        # --------------------------------------------------

        self.twists = []

        if self.twist_joints:

            for i in range(len(self.bind_joints) - 1):

                twist = create_twist(
                    start_driver=self.switch_joints[i],
                    end_driver=self.switch_joints[i + 1],

                    start_joint=self.bind_joints[i],
                    end_joint=self.bind_joints[i + 1],

                    twist_count=self.twist_count,
                    primary_axis="Y",

                    cst_parent=self.guts,

                    mid_control=True,
                    control_parent=self.bend_control_grp,
                    rig_size=self.rig_size / 10,
                    control_shape=self.bendy_control_shape,
                )

                self.twists.append(twist)

        else:

            # Without twist joints, we still need to
            # constrain the bind joints to the switch chain.

            for switch_joint, bind_joint in zip(
                self.switch_joints,
                self.bind_joints,
                strict=True,
            ):

                constraint(
                    drivers=[switch_joint],
                    driven=bind_joint,
                    constraint_type="parent",
                    maintain_offset=True,
                    parent=self.guts,
                )


        # --------------------------------------------------
        # IK Bone Correctives
        # --------------------------------------------------

        self.ik_bones = []

        if self.ik_bone:

            # Lower half of the limb
            root_driver = self.switch_joints[1]
            end_driver = self.switch_joints[2]

            # Shared offset magnitude
            offset = self.rig_size * self.ik_bone_offset

            # Build positive and negative X bone correctives
            for direction, sign in [
                ("positive", 1),
                ("negative", -1),
            ]:

                bone = IK_Bone(
                    part=f"{self.part}_lower_{direction}",
                    side=self.side,

                    root_driver=root_driver,
                    end_driver=end_driver,

                    primary_axis="X",
                    offset=offset * sign,

                    parent=self.main_grp,
                    control_parent=self.bend_control_grp,
                    joint_parent=self.bind_joints[1],

                    rig_size=self.rig_size / 30,
                    control_shape=self.bendy_control_shape,
                    control_color=self.main_control_color,

                    stretch_default=1.0,
                )

                bone_info = bone.build()

                self.ik_bones.append(bone_info)

                # Include corrective controls in module controls.
                self.controls.append(bone_info.control)



        if not self.ik_end_control:
            cmds.delete(self.bind_joints[-1])
            self.bind_joints.pop()

        pv_line = create_connection_curve(
            start=self.switch_joints[1],
            end=self.ik_pv_ctrl.ctrl,
            parent=self.ik_control_grp,
            name=f"{self.part}_{self.side}_pv_line",
        )

        mid = len(self.twists) // 2

        upper_twist_data = self.twists[:mid]
        lower_twist_data = self.twists[mid:]

        self.upper_twists = [
            joint
            for twist in upper_twist_data
            for joint in twist.twist_joints
        ]

        self.lower_twists = [
            joint
            for twist in lower_twist_data
            for joint in twist.twist_joints
        ]




        self.info = moudle_info(
                fk_root = self.fk_controls[0],
                ik_root = self.ik_controls[0],
                fk_ik_switch = self.FK_IK_Switch,
                end_ik_hook = [self.ik_hook, self.ik_joints[-1], end_pos],
                ik_controls = self.ik_controls,
                fk_controls = self.fk_controls,
                ik_len=ik_len,
                ik_stretch_attr = f'{end_pos}.stretch',
                fk_joints=self.fk_joints,
                ik_joints=self.ik_joints,
                switch_joints=self.switch_joints,
                bind_joints=self.bind_joints,
                controls = self.controls,
                ik_main_handle=self.ik_handle,
                ik_singlechain=self.ik_len_chain if self.ik_length else None,
                ik_len_joints = self.ik_len_joints if self.ik_length else [],
                fk_hook = fk_hook,
                upper_sub_joints=self.upper_twists,
                lower_sub_joints=self.lower_twists,
                auto_pv_driven = pv_driven,
                )
        
        return self.info
