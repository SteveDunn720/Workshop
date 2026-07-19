import maya.cmds as cmds

from Workshop.color.rig_color_setup import rig_color_channels, initialize_rig_color_type


def apply_color_tag(object):
    tag = cmds.getAttr(f'{object}.CONTROL_COLOR_TAG')

    channels = initialize_rig_color_type(tag)

    cmds.setAttr(object + ".overrideEnabled", 1)
    cmds.setAttr(object + ".overrideRGBColors", 1)
    #cmds.setAttr(object + ".overrideColorRGB", None)
    cmds.connectAttr(
            f"{channels.color}",
            f"{object}.overrideColorRGB",
        )
    
    if object == 'color_options_ctrl':
        return
    
    cmds.addAttr(object, longName=f'{tag}_Display_Options', proxy=channels.des)
    cmds.addAttr(object, longName='Color', proxy=channels.color)
    #cmds.addAttr(object, longName=f'{tag}_Thickness', proxy=channels.thickness)
    cmds.addAttr(object, longName=f'{tag}_Draw_On_Top', proxy=channels.draw_on_top)
