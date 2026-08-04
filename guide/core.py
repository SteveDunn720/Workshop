from __future__ import annotations

from dataclasses import dataclass, field
import maya.cmds as cmds
from maya.api.OpenMaya import MMatrix

from Workshop.joint import create_joint
from Workshop.transform.matrix import set_local_matrix
from Workshop.transform.utils import match_location, match_transform
from Workshop.transform.curve import create_line_curve, style_curve, curve_cvs

@dataclass
class GuideInfo:
    name: str
    pos: tuple[float, float, float]
    rot: tuple[float, float, float]
    guide_type: str
    extra_channels: list[str] = field(default_factory=list)
    descriptor: str = ""

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





def create_guide_from_position(pos, guide_name, parent)->GuideInfo:
    guide = create_joint(name=f'{guide_name}_guide', connect=False, parent=parent, suffix=False)

    if isinstance(pos, str):
        if not cmds.objExists(pos):
            print(f'{pos} does not exist')
            return None
        match_location(transform=guide, target_transform=pos)
    elif isinstance(pos, tuple):
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
    )
    return info


def read_guide(guide: str) -> GuideInfo:
    """Create GuideInfo from an existing Maya guide."""

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

    if node_type == "joint":
        guide_type = "joint"
    elif node_type == "transform":
        shapes = cmds.listRelatives(guide, shapes=True) or []

        if shapes and cmds.nodeType(shapes[0]) == "nurbsCurve":
            guide_type = "curve"
        else:
            guide_type = "transform"
    else:
        guide_type = node_type

    descriptor = guide

    if cmds.attributeQuery("guideDescriptor", node=guide, exists=True):
        descriptor = cmds.getAttr(f"{guide}.guideDescriptor")

    extra_channels = []

    if cmds.attributeQuery("guideExtraChannels", node=guide, exists=True):
        channel_string = cmds.getAttr(f"{guide}.guideExtraChannels") or ""
        extra_channels = [
            channel
            for channel in channel_string.split(",")
            if channel
        ]

    return GuideInfo(
        name=guide,
        pos=tuple(pos),
        rot=tuple(rot),
        guide_type=guide_type,
        extra_channels=extra_channels,
        descriptor=descriptor,
    )

def add_guide_metadata(
    guide: str,
    descriptor: str,
    guide_type: str,
    extra_channels: list[str] | None = None,
) -> None:
    """Store guide identification data directly on a Maya node."""

    extra_channels = extra_channels or []

    attributes = {
        "guideDescriptor": descriptor,
        "guideType": guide_type,
        "guideExtraChannels": ",".join(extra_channels),
    }

    for attr_name, value in attributes.items():
        if not cmds.attributeQuery(attr_name, node=guide, exists=True):
            cmds.addAttr(
                guide,
                longName=attr_name,
                dataType="string",
            )

        cmds.setAttr(
            f"{guide}.{attr_name}",
            value,
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

