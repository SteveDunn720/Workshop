import maya.cmds as cmds

from Workshop.transform.constraint import constraint
from Workshop.maya_api.node import ReverseNode


def fkik_switch(controls:list|None, node_attr:str, descriptor:str, fk_grp:str, ik_grp:str, fk_joints:list, ik_joints:list, switch_joints:list ):
    cmds.addAttr(node_attr, longName='FK_IK_Switch', attributeType='double', defaultValue=1, maxValue=1, minValue=0, keyable=True)
    FK_IK_Switch = f'{node_attr}.FK_IK_Switch'
    rev = ReverseNode(name=f"{descriptor}_FKIK_rev")
    rev.input.x.connect_from(FK_IK_Switch)
    rev.output.x.connect_to(f'{ik_grp}.visibility')
    cmds.connectAttr(FK_IK_Switch, f'{fk_grp}.visibility')
    for i,jnt in enumerate(switch_joints):
        parent_con = constraint(drivers=[fk_joints[i], ik_joints[i]], driven=jnt, constraint_type='parent', maintain_offset=True)

        parent_con.connections[0]
       
        cmds.connectAttr(FK_IK_Switch, f'{parent_con.connections[0]}')   #type:ignore
        cmds.connectAttr(rev.output.x, f'{parent_con.connections[1]}')   #type:ignore
    if controls:
        for control in controls:
            cmds.addAttr(control, longName='FKIK_Switch', proxy=FK_IK_Switch)

    return FK_IK_Switch