from turtle import position

from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, align_guides, create_guide_from_position, mirror_guide
from Workshop.maya_api.node import DecomposeMatrixNode, NearestPointOnCurveNode

from .module_initialize import module_prep, module_space


@dataclass
class module_info:
    control:Control
    joint:str

class Mouth:
    def __init__(
        self,
        guides: dict[str, GuideInfo],
        part: str = "mouth",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        joint_parent:str = 'skel',
        control_space:list = [],

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: dict[str, GuideInfo] = guides
        self.joint_parent = joint_parent
        self.control_space = control_space


        self.main_M_color = 'Middle'
        self.sub_M_color = 'SubMiddle'
    
        self.main_L_color = 'Left'
        self.sub_L_color = 'SubLeft'
    
        self.main_R_color = 'Right'
        self.sub_R_color = 'SubRight'

    # -------------------
    # Build steps
    # -------------------




    def get_curve_percent(self, guide:GuideInfo, curve:str)->float:
        near = NearestPointOnCurveNode(name=f'{self.part}_NPOC')
        dec = DecomposeMatrixNode(name=f'{self.part}_DCM')

        dec.input_matrix.connect_from(f'{guide.name}.worldMatrix[0]')
        near.in_position.connect_from(dec.output_translate)
        near.input_curve.connect_from(f'{curve}.worldSpace[0]')
        num = near.result.parameter.get()

        cmds.delete(dec.name, near.name)
        return num

    def mouth_build(self):

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        self.main_controls = {}



        center_pos = cmds.pointOnCurve(
                    self.guides['L_mouth'].name,
                    parameter=0,
                    position=True,
                    turnOnPercentage=True,
                )

        center_guide = create_guide_from_position(guide_name='mouth_center_M', pos=center_pos, parent='guides')
        

        for side in ['L', 'R']:

            mid_pos = cmds.pointOnCurve(
                        self.guides[f'{side}_mouth'].name,
                        parameter=.5,
                        position=True,
                        turnOnPercentage=True,
                    )
    
            mid_guide = create_guide_from_position(guide_name=f'mouth_mid_{side}', pos=mid_pos, parent='guides')
                
            corner_pos = cmds.pointOnCurve(
                        self.guides[f'{side}_mouth'].name,
                        parameter=1,
                        position=True,
                        turnOnPercentage=True,
                    )
    
            corner_guide = create_guide_from_position(guide_name=f'mouth_corner_{side}', pos=corner_pos, parent='guides')


            if side == 'L':

                mid_percent = self.get_curve_percent(curve=self.guides[f'{side}_path'].name, guide=mid_guide)
                
                corner_percent = self.get_curve_percent(curve=self.guides[f'{side}_path'].name, guide=corner_guide)
            
                lipcenter_pos = cmds.pointOnCurve(
                                                    self.guides[f'{side}_path'].name,
                                                    parameter=0,
                                                    position=True,
                                                    turnOnPercentage=True,
                                                )
                                
                lipcenter_guide = create_guide_from_position(guide_name='lip_center_M', pos=lipcenter_pos, parent='guides')


                lipmid_pos = cmds.pointOnCurve(
                    self.guides[f'{side}_path'].name,
                    parameter=mid_percent,
                    position=True,
                    turnOnPercentage=True,
                )
                                
                lipmid_guide = create_guide_from_position(guide_name=f'lip_mid_{side}', pos=lipmid_pos, parent='guides')

                lipcorner_pos = cmds.pointOnCurve(
                    self.guides[f'{side}_path'].name,
                    parameter=corner_percent,
                    position=True,
                    turnOnPercentage=True,
                )
                                
                lipcorner_guide = create_guide_from_position(guide_name=f'lip_corner_{side}', pos=lipcorner_pos, parent='guides')

                align_guides(guide_01=lipcorner_guide, guide_02=lipmid_guide, flip=True)
                align_guides(guide_01=lipmid_guide, guide_02=lipcorner_guide)
            else:

                lipcorner_guide = mirror_guide(guide=lipcorner_guide)
                lipmid_guide = mirror_guide(guide=lipmid_guide)

            for vertical in ['upper', 'lower']:
                v_mod = 1 if vertical == 'upper' else -1
                if side == 'L':

                    lip_center = self.mouth_ctrl = create_control(
                                name=f'{vertical}_lip_M',
                                parent=self.control_grp,
                                transform=lipcenter_guide.name,
                                size=self.control_size/100,
                                control_shape='triangle',
                                direction="y",
                                color_type=self.main_M_color,
                                shape_position_offset=(0,self.control_size/70*v_mod,self.control_size/80),
                                shape_rotation_offset=(90*v_mod,0,0)
                            )

                    self.main_controls[f'{vertical}_M_center'] = lip_center

                lip_mid = self.mouth_ctrl = create_control(
                        name=f'{vertical}_lip_mid_{side}',
                        parent=self.control_grp,
                        transform=lipmid_guide.name,
                        size=self.control_size/100,
                        control_shape='triangle',
                        direction="y",
                        color_type=self.main_L_color if side == 'L' else self.main_R_color,
                        shape_position_offset=(0,self.control_size/70*v_mod,self.control_size/80),
                        shape_rotation_offset=(90*v_mod,0,0)
                    )

                


                lip_corner = self.mouth_ctrl = create_control(
                    name=f'{vertical}_lip_corner_{side}',
                    parent=self.control_grp,
                    transform=lipcorner_guide.name,
                    size=self.control_size/100,
                    control_shape='triangle',
                    direction="y",
                    color_type=self.main_L_color if side == 'L' else self.main_R_color,
                    shape_position_offset=(0,self.control_size/70*v_mod,self.control_size/80),
                    shape_rotation_offset=(90*v_mod,0,0)
                )

                self.main_controls[f'{vertical}_{side}_mid'] = lip_mid
                self.main_controls[f'{vertical}_{side}_corner'] = lip_corner


                    






















        """#controls
        self.mouth_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color
        )

        module_space(control=self.mouth_ctrl, space_list=self.control_space)

        #joints

        self.mouth_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.mouth_ctrl.ctrl, connect=True, parent=self.joint_parent)

        constraint(drivers=[self.mouth_ctrl.ctrl], driven=self.mouth_joint, constraint_type='parent', parent=self.guts)

        mouth_info = module_info(control =self.mouth_ctrl, joint=self.mouth_joint)
        return mouth_info"""