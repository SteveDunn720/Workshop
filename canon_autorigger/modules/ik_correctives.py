from attr import dataclass

from Workshop.control.core import Control
from Workshop.transform.constraint import constraint
from Workshop.control import create_control
from Workshop.joint import create_joint
from Workshop.guide.core import GuideInfo
from Workshop.maya_api.node import DistanceBetweenNode, MultiplyDivideNode
from Workshop.transform.utils import create_transform, create_locator

from .module_initialize import module_prep, module_space
from .ik import create_IK_single_chain

import maya.cmds as cmds


@dataclass
class module_info:
    control:Control
    joint:str

class Ik_correctives:
    def __init__(
        self,
        part: str = "pec",
        side: str = "M",
        parent: str = "components",
        control_parent: str | None = None,
        control_size: float = 1.0,
        guides: list[GuideInfo] = [],
        joint_parent:str = 'skel',
        end_ik_space:list = [],
        root_ik_space:list = [],
        control_color:str = 'MISC',
        control_shape:str = 'circle',
        divisions:int = 1,
        mid_control:bool = False,

    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str | None = control_parent
        self.control_size: float = control_size
        self.guides: list = guides
        self.joint_parent = joint_parent
        self.root_ik_space = root_ik_space
        self.end_ik_space = end_ik_space
        self.control_color = control_color
        self.control_shape = control_shape
        self.primary_axis = "Y"
        self.divisions = divisions
        self.mid_control = mid_control

    # -------------------
    # Build steps
    # -------------------

    def ik_correctives_build(self):

        #modeule prep work
        prep = module_prep(part=self.part, parent=self.parent, side=self.side, fkik=False, gut=True)
        self.main_grp = prep.main_grp
        self.control_grp = prep.control_grp
        self.guts = prep.guts

        ik_joints = []
        bind_joints = []



        for guide in self.guides:
            if guide == self.guides[0]:
                self.ik_end_grp = create_transform(name=f'{guide.descriptor}_grp', parent=self.guts, transform=guide.name)
                self.ik_end_loc = create_transform(name=f'{guide.descriptor}_driver', parent=self.ik_end_grp, transform=guide.name)
                constraint(drivers=self.end_ik_space, driven=self.ik_end_grp, constraint_type='parent', parent=self.guts)
                
            else:
                root_ik = create_joint(name=f'ik_{guide.descriptor}', transform=guide.name, connect=False, bind_set=False, ue_set=False, parent=self.guts)
                end_ik = create_joint(name=f'ik_{guide.descriptor}_end', transform=self.guides[0].name, connect=False, bind_set=False, ue_set=False, parent=root_ik)
                cmds.setAttr(f'{end_ik}.jointOrient', 0, 0, 0)
                ik = create_IK_single_chain(name=guide.descriptor, start_joint=root_ik, end_joint=end_ik,)
                cmds.parent(ik.handle, self.guts)

                ik_dist = DistanceBetweenNode(name=guide.descriptor)
                ik_dist.input_matrix1.connect_from(f'{root_ik}.worldMatrix[0]')
                ik_dist.input_matrix2.connect_from(f'{self.ik_end_loc}.worldMatrix[0]')

                ik_dist.distance.connect_to(f'{end_ik}.translate{self.primary_axis}')

                constraint(drivers=[self.ik_end_loc], driven=ik.handle, constraint_type='parent', parent=self.guts)
                constraint(drivers=self.root_ik_space, driven=root_ik, constraint_type='parent', parent=self.guts)

                ik_joints.append(root_ik)

                mult = 1 / (self.divisions + 1)


                for i in range(self.divisions):
                    if i % 3 == 0:
                        mult_node = MultiplyDivideNode(
                            name=f'ik_{guide.descriptor}_{i + 1:02d}'
                        )

                    channel_index = i % 3

                    if channel_index == 0:
                        channel = "X"
                    elif channel_index == 1:
                        channel = "Y"
                    else:
                        channel = "Z"

                    joint = create_joint(
                        name=f'ik_{guide.descriptor}_{i + 1:02d}',
                        transform=guide.name,
                        connect=False,
                        bind_set=False,
                        ue_set=False,
                        parent=root_ik,
                    )
                    ik_joints.append(joint)

                    cmds.connectAttr(f'{end_ik}.translate{self.primary_axis}',f'{mult_node}.input1{channel}') #type:ignore
                    cmds.setAttr(f'{mult_node}.input2{channel}', mult * (i+1)) #type:ignore
                    cmds.connectAttr(f'{mult_node}.output{channel}',f'{joint}.translate{self.primary_axis}') #type:ignore

        for ik in ik_joints:

            jnt_name = ik.removeprefix("ik_").removesuffix("_jnt")
            joint = create_joint(
                name=jnt_name,
                transform=ik,
                connect=False,
                parent=self.joint_parent,
            )
            bind_joints.append(joint)
            constraint(drivers=[ik], driven=joint, constraint_type='parent', parent=self.guts)







            # for adding an mid control, we need to take the input of hte middle joints, sub them in for an add node that takes in the local control primary axis // and the end joints's y axis, to decide where the joints need to be  


                    



                



























        #controls
        """self.ik_correctives_ctrl = create_control(
            name=f'{self.part}_{self.side}',
            parent=self.control_grp,
            transform=self.guides[0].name,
            size=self.control_size,
            control_shape=self.control_shape,
            direction="y",
            color_type=self.control_color

        )"""

        #module_space(control=self.ik_correctives_ctrl, space_list=self.control_space)

        #joints

        #self.ik_correctives_joint = create_joint(name=f'def_{self.part}_{self.side}', transform=self.ik_correctives_ctrl.ctrl, connect=True, parent=self.joint_parent)

        #constraint(drivers=[self.ik_correctives_ctrl.ctrl], driven=self.ik_correctives_joint, constraint_type='parent', parent=self.guts)

        #ik_correctives_info = module_info(control =self.ik_correctives_ctrl, joint=self.ik_correctives_joint)
        #return ik_correctives_info