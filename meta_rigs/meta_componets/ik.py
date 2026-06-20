from attr import dataclass
import maya.cmds as cmds
from Workshop.transform.utils import create_transform, match_location, get_distance_between, get_plane_normal, get_position, convert_to_matrix


@dataclass
class IK_data:
    start_joint:str
    end_joint:str
    handle:str
    effector:str
    spline_curve:str
    type:str
    pole_vector:str


def create_IK_rotate_plane(name:str, start_joint:str, end_joint:str, mid_joint:str, pole_vector_guide:str, auto_pv:bool=False)->IK_data:
    ik_handle, effector = cmds.ikHandle(                                                 #type:ignore
            name=name,
            startJoint=start_joint,
            endEffector=end_joint,
            solver="ikRPsolver"
        )

    if auto_pv:
        pv = generate_autoPV([start_joint, mid_joint, end_joint], f'{name}_PV')
    else:
        pv = pole_vector_guide

    pv_loc = cmds.spaceLocator(name=f'{name}_pv_loc')[0]
    match_location(pv_loc, pv) #type:ignore

    if auto_pv:
        cmds.delete(pv)
    
    cmds.poleVectorConstraint(pv_loc, ik_handle)#type:ignore                                              
    
    handle = IK_data(start_joint=start_joint, end_joint=end_joint, handle=ik_handle, effector=effector, spline_curve='', type='rotate_plane', pole_vector=pv_loc)       
    
    return handle                                                   

    

def generate_autoPV(joints: list, name: str = "pv_name") -> str:

    p0 = get_position(joints[0])
    p1 = get_position(joints[1])
    p2 = get_position(joints[2])

    limb_dir = (p2 - p0)
    limb_dir.normalize()

    normal = get_plane_normal(joints[0], joints[1], joints[2])
    normal.normalize()

    # stable PV direction (THIS is the fix)
    pv_dir = normal ^ limb_dir
    pv_dir.normalize()

    # distance scale
    first_dist = (p1 - p0).length()
    second_dist = (p2 - p1).length()
    avg_dist = (first_dist + second_dist) * -1

    mid_pos = p1

    pv_pos = mid_pos + (pv_dir * avg_dist)

    pv_matrix = convert_to_matrix(pos=(pv_pos.x, pv_pos.y, pv_pos.z))

    pv_object = create_transform(name=name, parent=None, transform=pv_matrix)

    return pv_object



    

