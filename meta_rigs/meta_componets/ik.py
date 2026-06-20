from attr import dataclass
import maya.cmds as cmds
from Workshop.transform.utils import match_location


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
    
    cmds.poleVectorConstraint(pv_loc, ik_handle)#type:ignore                                              
    
    handle = IK_data(start_joint=start_joint, end_joint=end_joint, handle=ik_handle, effector=effector, spline_curve='', type='rotate_plane', pole_vector=pv_loc)       
    
    return handle                                                   

    

        




def generate_autoPV(joints:list=['start', 'mid', 'end'], name:str='pv_name') ->str:
    return 'your mom'




    

