from attr import dataclass
import maya.cmds as cmds
from Workshop.tag.lock_hide_key import hide_channels, lock_channels, not_keyable_channels, object_visibility
from Workshop.tag.apply_rig_color import apply_color_tag
from Workshop.tag.sets import add_to_set

@dataclass
class tag_info:
    tag_type:str
    tag_value:str


def add_tag(object:str, tag_type:str, tag_value:str):
    if cmds.attributeQuery(tag_type, node=object, exists=True):
        print(f"{object} already has tag {tag_type}, overwriting tag")
    else:
        cmds.addAttr(object, longName=tag_type, dataType='string')
    cmds.setAttr(f'{object}.{tag_type}', tag_value, type="string")

def remove_tag(object: str, tag_type: str):
    """
    Removes a custom string tag attribute from a node.
    Matches the style of add_tag().
    """

    if not cmds.objExists(object):
        print(f"{object} does not exist")
        return

    if cmds.attributeQuery(tag_type, node=object, exists=True):
        cmds.deleteAttr(f"{object}.{tag_type}")
        print(f"{object}: removed tag {tag_type}")
    else:
        print(f"{object}: no tag {tag_type} found to remove")



def lock_tag(
    object:str,
    translate:tuple = (True, True, True),
    rotate:tuple = (True, True, True),
    scale:tuple = (True, True, True),
    visibility:bool = True,
    extra_channels:list = [],
    hide_tag:bool = False,  
    ):

    channels_to_tag = []

    axes = ('X', 'Y', 'Z')

    for i, axis in enumerate(translate):
        if axis:
            channels_to_tag.append(f'translate{axes[i]}')
    for i, axis in enumerate(rotate):
        if axis:
            channels_to_tag.append(f'rotate{axes[i]}')
    for i, axis in enumerate(scale):
        if axis:
            channels_to_tag.append(f'scale{axes[i]}')
    if visibility:
        channels_to_tag.append('visibility')
    if extra_channels:
        for attr in extra_channels:
            channels_to_tag.append(attr)



    add_tag(object=object, tag_type='LOCK_TAG', tag_value=repr(channels_to_tag))
    if hide_tag:
        add_tag(object=object, tag_type='HIDE_TAG', tag_value=repr(channels_to_tag))


def hide_tag(
    object:str,
    translate:tuple = (True, True, True),
    rotate:tuple = (True, True, True),
    scale:tuple = (True, True, True),
    visibility:bool = True,
    extra_channels:list = [],
    lock_tag:bool = False,  
    ):

    channels_to_tag = []

    axes = ('X', 'Y', 'Z')

    for i, axis in enumerate(translate):
        if axis:
            channels_to_tag.append(f'translate{axes[i]}')
    for i, axis in enumerate(rotate):
        if axis:
            channels_to_tag.append(f'rotate{axes[i]}')
    for i, axis in enumerate(scale):
        if axis:
            channels_to_tag.append(f'scale{axes[i]}')
    if visibility:
        channels_to_tag.append('visibility')
    if extra_channels:
        for attr in extra_channels:
            channels_to_tag.append(attr)



    add_tag(object=object, tag_type='HIDE_TAG', tag_value=repr(channels_to_tag))
    if lock_tag:
        add_tag(object=object, tag_type='LOCK_TAG', tag_value=repr(channels_to_tag))

def not_keyable_tag(
    object:str,
    translate:tuple = (True, True, True),
    rotate:tuple = (True, True, True),
    scale:tuple = (True, True, True),
    visibility:bool = True,
    extra_channels:list = [], 
    ):

    channels_to_tag = []

    axes = ('X', 'Y', 'Z')

    for i, axis in enumerate(translate):
        if axis:
            channels_to_tag.append(f'translate{axes[i]}')
    for i, axis in enumerate(rotate):
        if axis:
            channels_to_tag.append(f'rotate{axes[i]}')
    for i, axis in enumerate(scale):
        if axis:
            channels_to_tag.append(f'scale{axes[i]}')
    if visibility:
        channels_to_tag.append('visibility')
    if extra_channels:
        for attr in extra_channels:
            channels_to_tag.append(attr)
    add_tag(object=object, tag_type='NOT_KEYABLE_TAG', tag_value=repr(channels_to_tag))


def control_color_tag(object:str, rig_color_type:str):
    add_tag(object=object, tag_type='CONTROL_COLOR_TAG', tag_value=rig_color_type)

def obj_vis_tag(object:str, visibility:str):
    """
    args:
    object: well ill let you take a guess
    visibility: 'ALWAYS': just hides the object '
                'RIG': connects it to the rig componet visibility channel
                '{control}.(channel)' if its not ALWAYS or RIG, it will attempt to connect
                    the vis to a control/channel, if not it will just pass 
    """
    add_tag(object=object, tag_type='OBJECT_VISIBILITY_TAG', tag_value=visibility)

def sets_tag(object:str, set:list[str]):
    """
    args:
    object: well ill let you take a guess
    set: will connect it to selection sets based on the set you give it
    """
    add_tag(object=object, tag_type='SETS_TAG', tag_value=repr(set))



def get_tags(object):
    tag_lib = ['LOCK_TAG', 'HIDE_TAG', 'NOT_KEYABLE_TAG', 'CONTROL_COLOR_TAG', 'OBJECT_VISIBILITY_TAG', 'SETS_TAG']

    for tag_type in tag_lib:
        if not cmds.attributeQuery(tag_type, node=object, exists=True):
            continue
        elif tag_type == 'LOCK_TAG':
            lock_channels(object=object)
        elif tag_type == 'HIDE_TAG':
            hide_channels(object=object)
        elif tag_type == 'NOT_KEYABLE_TAG':
            not_keyable_channels(object=object)
        elif tag_type == 'OBJECT_VISIBILITY_TAG':
            object_visibility(object=object)
        elif tag_type == 'CONTROL_COLOR_TAG':
            apply_color_tag(object=object)
        elif tag_type == 'SETS_TAG':
            add_to_set(object=object)







