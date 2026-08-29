from attr import dataclass

import maya.cmds as cmds

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo, create_guide_from_position
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
        control_color:str = 'MISC',
        control_shape:str = 'circle'

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: dict[str, GuideInfo] = guides
        self.joint_parent = joint_parent
        self.control_space = control_space
        self.control_color = control_color
        self.control_shape = control_shape

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
                            

            for vertical in ['upper', 'lower']:
                pass






















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