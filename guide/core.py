from __future__ import annotations

from dataclasses import dataclass, field
import maya.cmds as cmds
from maya.api.OpenMaya import MMatrix

from Workshop.joint import create_joint
from Workshop.transform.matrix import set_local_matrix
from Workshop.transform.utils import create_transform, match_location, match_transform
from Workshop.transform.curve import create_line_curve, style_curve, curve_cvs

@dataclass
class GuideInfo:
    name: str
    pos: tuple[float, float, float]
    rot: tuple[float, float, float]
    guide_type: str
    extra_channels: list[str] = field(default_factory=list)
    descriptor: str = ""
    guide_parent:str = ""
    component:str = ""
    side:str = ""


@dataclass
class SplineGuideInfo:
    curve:GuideInfo
    lower:GuideInfo
    lower_tan:GuideInfo
    upper:GuideInfo
    upper_tan:GuideInfo

@dataclass
class ChainGuideInfo:
    guides:list[GuideInfo]


def mirror_guide(guide: GuideInfo) -> GuideInfo | None:
    if guide.guide_type == 'joint':

        temp_parent = create_transform(name='temp_grp')
        parent = cmds.listRelatives(guide.name, parent=True)

        new_guide = create_guide_from_position(
            pos=guide.pos,
            guide_name=guide.descriptor.replace('_L', '_R'),
            parent=temp_parent,
            component_type='joint',
        )

        cmds.setAttr(f'{new_guide.name}.rotate', *guide.rot)
        cmds.setAttr(f'{temp_parent}.scaleX', -1)

        cmds.parent(new_guide.name, parent[0])

        cmds.delete(temp_parent)

        return new_guide

    print(f'mirror not built for {guide.guide_type}')
    return None


def align_guides(
    guide_01: GuideInfo,
    guide_02: GuideInfo,
    primary_axis: str = "X",
    flip: bool = False,
) -> GuideInfo:

    axis = primary_axis.upper()

    axis_vectors = {
        "X": (1, 0, 0),
        "Y": (0, 1, 0),
        "Z": (0, 0, 1),
    }

    if axis not in axis_vectors:
        raise ValueError(
            f"Invalid primary_axis: {primary_axis}. Expected X, Y, or Z."
        )

    aim_vector = axis_vectors[axis]

    if flip:
        aim_vector = tuple(-value for value in aim_vector)

    # Pick an up axis that is not the primary axis
    up_vectors = {
        "X": (0, 1, 0),
        "Y": (0, 0, 1),
        "Z": (0, 1, 0),
    }

    up_vector = up_vectors[axis]

    aim = cmds.aimConstraint(
        guide_02.name,
        guide_01.name,
        aimVector=aim_vector,
        upVector=up_vector,
        worldUpType="vector",
        worldUpVector=up_vector,
        maintainOffset=False,
    )

    cmds.delete(aim)

    rotation = cmds.xform(
        guide_01.name,
        query=True,
        rotation=True,
        worldSpace=True,
    )

    guide_01.rot = (
        rotation[0],
        rotation[1],
        rotation[2],
    )

    return guide_01


def create_guide_from_position(pos, guide_name, parent, component_type:str | None = None)->GuideInfo:
    guide = create_joint(name=f'{guide_name}_guide', connect=False, parent=parent, suffix=False)

    if isinstance(pos, str):
        if not cmds.objExists(pos):
            print(f'{pos} does not exist')
            return None
        match_location(transform=guide, target_transform=pos)
    elif isinstance(pos, (list, tuple)):
        cmds.xform(guide, query=False, worldSpace=True, translation=pos)
    elif isinstance(pos, MMatrix):
        set_local_matrix(transform=guide, matrix=pos, use_joint_orient=False, )
    else:
        print(f'{pos} is incompatible')
        return None
    return_pos = cmds.xform(guide, query=True, translation=True, worldSpace=True)
    return_rot = cmds.xform(guide, query=True, rotation=True, worldSpace=True)
    
    info = GuideInfo(name=guide, pos=return_pos, rot=return_rot, guide_type='joint', extra_channels=[], descriptor=guide_name) #type:ignore
    add_guide_metadata(
        guide=guide,
        descriptor=guide_name,
        guide_type="joint",
        guide_parent=parent,
        component=component_type
    )
    return info


def read_guide(guide: str) -> GuideInfo:
    #Create GuideInfo from an existing Maya guide

    attrs = ['descriptor_TAG', 'guidetype_TAG', 'guideparent_TAG', 'component_TAG']
    


    if not cmds.objExists(guide):
        raise ValueError(f"Guide does not exist: {guide}")

    pos = cmds.xform(
        guide,
        query=True,
        worldSpace=True,
        translation=True,
    )

    rot = cmds.xform(
        guide,
        query=True,
        worldSpace=True,
        rotation=True,
    )

    node_type = cmds.nodeType(guide)

    if cmds.attributeQuery(attrs[1], node=guide, exists=True):
        guide_type = cmds.getAttr(f'{guide}.{attrs[1]}')
    else:
        if node_type == "joint":
            guide_type = "joint"
        elif node_type == "transform":
            shapes = cmds.listRelatives(guide, shapes=True) or []

            if shapes and cmds.nodeType(shapes[0]) == "nurbsCurve":
                guide_type = "curve"
            else:
                guide_type = "transform"
        else:
            guide_type = node_type[0]
        cmds.addAttr(
            guide,
            longName=attrs[1],
            dataType="string",
        )

        cmds.setAttr(
            f"{guide}.{attrs[1]}",
            guide_type,
            type="string",
        )
    
    descriptor = guide.removesuffix("_guide")
    extra_channels = []

    if cmds.attributeQuery("guideExtraChannels", node=guide, exists=True):
        channel_string = cmds.getAttr(f"{guide}.guideExtraChannels") or ""
        extra_channels = [
            channel
            for channel in channel_string.split(",")
            if channel
        ]

    if cmds.attributeQuery(attrs[2], node=guide, exists=True):
        parent = cmds.getAttr(f'{guide}.{attrs[2]}')
    else:
        parent = cmds.listRelatives(guide, parent=True)[0]
        cmds.addAttr(
            guide,
            longName=attrs[2],
            dataType="string",
        )

        cmds.setAttr(
            f"{guide}.{attrs[2]}",
            parent,
            type="string",
        )

    if cmds.attributeQuery(attrs[3], node=guide, exists=True):
        comp = cmds.getAttr(f'{guide}.{attrs[3]}')
    else:
        comp = None
        cmds.addAttr(
            guide,
            longName=attrs[3],
            dataType="string",
        )
        

    if "_L_" in guide:
        side = "L"
    elif "_R_" in guide:
        side = "R"
    elif "_M_" in guide:
        side = "M"
    else:
        side = None
    

    return GuideInfo(
        name=guide,
        pos=tuple(pos), #type:ignore
        rot=tuple(rot), #type:ignore
        guide_type=guide_type, #type:ignore
        extra_channels=extra_channels,
        descriptor=descriptor,
        guide_parent = parent, 
        component=comp, #type:ignore
        side=side #type:ignore
    )

def add_guide_metadata(
    guide: str,
    descriptor: str,
    guide_type: str,
    guide_parent: str, 
    component: str | None

) -> None:
    """Store guide identification data directly on a Maya node."""

    attrs = ['descriptor_TAG', 'guidetype_TAG', 'guideparent_TAG', 'component_TAG']
    values = [descriptor, guide_type, guide_parent, component]

    for i, attr, in enumerate(attrs):
        if values[i]:
            cmds.addAttr(
                guide,
                longName=attr,
                dataType="string",
            )

            cmds.setAttr(
                f"{guide}.{attr}",
                values[i],
                type="string",
            )


def create_spline_guide(parent:str, lower_name:str='lower', upper_name:str='upper', curve_name:str='spline', side:str='M', position:list=[]):
    if position:
        upper_pos = position[0]
        lower_pos = position[1]
    else:
        upper_pos = (0,5,0)
        lower_pos = (0,0,0)

    upper = create_guide_from_position(pos=upper_pos, guide_name=f"{upper_name}_{side}", parent=parent)
    lower = create_guide_from_position(pos=lower_pos, guide_name=f"{lower_name}_{side}", parent=parent)

    curve = create_line_curve(name=f'{curve_name}_{side}_guide', start_position=lower_pos, end_position=upper_pos)
    style_curve(curve=curve, line_width=5, draw_on_top=True, template=True)
    cmds.displaySmoothness(
        curve,
        pointsWire=16,
        pointsShaded=4,
        polygonObject=3,
    )
    cmds.parent(curve, parent)

    curve_guide = GuideInfo(name=f'{curve_name}_{side}_guide', pos=(0,0,0), rot=(0,0,0), guide_type='curve', extra_channels=[], descriptor=f"{upper_name}_{side}")

    clusters, pos = curve_cvs(curve=curve, clusters=True)

    upper_tan = create_guide_from_position(pos=tuple(pos[2]), guide_name=f'{upper_name}_tan_{side}', parent=upper.name)
    lower_tan = create_guide_from_position(pos=tuple(pos[1]), guide_name=f'{lower_name}_tan_{side}', parent=lower.name)

    guides = [lower, lower_tan, upper_tan, upper]

    for i,cluster in enumerate(clusters): 
        #match_transform(transform=cluster, target_transform=guides[i].name)
        cmds.parent(cluster, guides[i].name)
        tform = cmds.listRelatives(parent=True)[0]
        if tform == guides[i].name:
            cmds.setAttr(f'{cluster}.visibility', False)
            cmds.setAttr(f"{cluster}.hiddenInOutliner", True)
        else:
            tform = cmds.rename(tform, f"{guides[i].name}_offset")
            cmds.setAttr(f'{tform}.visibility', False)
            cmds.setAttr(f"{tform}.hiddenInOutliner", True)

    info = spline_GuideInfo(curve=curve_guide, upper=upper, upper_tan=upper_tan, lower=lower, lower_tan=lower_tan)
    return info






def chain_guides(names:list, side:str='M', position:list=[], parent:str=''):
    guide_list=[]
    for i,g in enumerate(names):
        guide = create_guide_from_position(pos=position[i], guide_name=f"{g}_{side}", parent=parent)
        guide_list.append(guide)
    info = chain_GuideInfo(guides=guide_list)
    return info

