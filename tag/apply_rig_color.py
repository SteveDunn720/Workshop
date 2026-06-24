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

    #cmds.connectAttr(f'{channels.r}', f'{object}.drawOverride.overrideColorRGB.overrideColorR' )
    #cmds.connectAttr(f'{channels.g}', f'{object}.drawOverride.overrideColorRGB.overrideColorG' )
    #cmds.connectAttr(f'{channels.b}', f'{object}.drawOverride.overrideColorRGB.overrideColorB' )
