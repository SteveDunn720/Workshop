import ast
import maya.cmds as cmds

def lock_channels(object):
    tag = cmds.getAttr(f'{object}.LOCK_TAG')
    channels = ast.literal_eval(tag)

    for channel in channels:
        cmds.setAttr(f'{object}.{channel}', lock=True, keyable=False, channelBox=True)

def hide_channels(object):
    tag = cmds.getAttr(f'{object}.HIDE_TAG')
    channels = ast.literal_eval(tag)

    for channel in channels:
        cmds.setAttr(f'{object}.{channel}', channelBox=False, keyable=False)

def not_keyable_channels(object):
    tag = cmds.getAttr(f'{object}.HIDE_TAG')
    channels = ast.literal_eval(tag)

    for channel in channels:
        cmds.setAttr(f'{object}.{channel}', keyable=False)

def object_visibility(object):
    tag = cmds.getAttr(f'{object}.OBJECT_VISIBILITY_TAG')
    if tag == 'ALWAYS':
        cmds.setAttr(f'{object}.visibility', 0) #type:ignore
    elif tag == 'COMPONENT':
        pass
    else:
        try:
            cmds.connectAttr(tag, f'{object}.visibilty')
        except RuntimeError as e:
            print(f'failed to connect object:{object} visibilty to {tag} : error {e}')