from attr import dataclass
import random
import maya.cmds as cmds

@dataclass
class rig_color_info:
    rig_type:str
    color:tuple
    draw_on_top:bool
    thickness:float

@dataclass
class rig_color_channels:
    r:str
    g:str
    b:str
    color:str
    draw_on_top:str
    thickness:str
    color_control:str

def initialize_rig_color_type(rig_type:str):
    color_control = 'color_options_ctrl'
    if cmds.attributeQuery(f'{rig_type}', node=color_control, exists=True):
        rig_colors = rig_color_channels(r=f'{color_control}.{rig_type}_Color_R', g=f'{color_control}.{rig_type}_Color_G', b=f'{color_control}.{rig_type}_Color_B', draw_on_top=f'{color_control}.{rig_type}_draw_on_top', thickness=f'{color_control}.{rig_type}_Thickness', color_control=color_control, color=f'{color_control}.{rig_type}_color')
        return rig_colors
    
    preset = False

    if preset:
        pass
    else:
        color_info = rig_color_info(rig_type=rig_type, color = (random.uniform(0, 1), random.uniform(0, 1), random.uniform(0, 1)), draw_on_top=False, thickness=-1)

    cmds.addAttr(color_control, longName=f'{rig_type}', attributeType="enum", enumName="_____:_____", keyable=False,) #type:ignore

    """cmds.addAttr(color_control, longName=f'{rig_type}_Color_R', attributeType='double', defaultValue=color_info.color[0], maxValue=1, minValue=0, keyable=True)
    cmds.addAttr(color_control, longName=f'{rig_type}_Color_G', attributeType='double', defaultValue=color_info.color[1], maxValue=1, minValue=0, keyable=True)
    cmds.addAttr(color_control, longName=f'{rig_type}_Color_B', attributeType='double', defaultValue=color_info.color[2], maxValue=1, minValue=0, keyable=True)"""

    cmds.addAttr(
        color_control,
        longName=f"{rig_type}_color",
        attributeType="double3",
        keyable=False,     )

    cmds.addAttr(
        color_control,
        longName=f"{rig_type}_colorR",
        attributeType="double",
        parent=f"{rig_type}_color",
        minValue=0, maxValue=1,
        defaultValue=color_info.color[0],
        keyable=False, 
    )

    cmds.addAttr(
        color_control,
        longName=f"{rig_type}_colorG",
        attributeType="double",
        parent=f"{rig_type}_color",
        minValue=0, maxValue=1,
        defaultValue=color_info.color[1],
        keyable=False,   )

    cmds.addAttr(
        color_control,
        longName=f"{rig_type}_colorB",
        attributeType="double",
        parent=f"{rig_type}_color",
        minValue=0, maxValue=1,
        defaultValue=color_info.color[2],
        keyable=False,
    )
    cmds.addAttr(color_control, longName=f'{rig_type}_draw_on_top', attributeType='bool', defaultValue=color_info.draw_on_top, keyable=False,)
    cmds.addAttr(color_control, longName=f'{rig_type}_Thickness', attributeType='double', defaultValue=color_info.thickness, minValue=-1, keyable=False)

    for attr in [f'{rig_type}_draw_on_top', f'{rig_type}_Thickness', f'{rig_type}', f"{rig_type}_color", f"{rig_type}_color.{rig_type}_colorR", f"{rig_type}_color.{rig_type}_colorG", f"{rig_type}_color.{rig_type}_colorB"]:
        cmds.setAttr(f'{color_control}.{attr}', keyable=False, channelBox=True)


    rig_colors = rig_color_channels(r=f'{color_control}.{rig_type}_Color_R', g=f'{color_control}.{rig_type}_Color_G', b=f'{color_control}.{rig_type}_Color_B', draw_on_top=f'{color_control}.{rig_type}_draw_on_top', thickness=f'{color_control}.{rig_type}_Thickness', color_control=color_control, color=f'{color_control}.{rig_type}_color')

    return rig_colors




