from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform, get_distance_between, get_flat_y_aim_rotation
from Workshop.transform.mesh_info import get_position_from_vertex
from Workshop.guide.core import create_guide_from_position, guide_info


@dataclass
class foot_guides:
    true_heel:guide_info
    true_foot:guide_info
    true_groundfoot:guide_info
    true_toe:guide_info
    true_inbank:guide_info
    true_outbank:guide_info
    true_ball:guide_info
    og_foot_pos:list[guide_info]
    aim_angle:str



def generate_foot_guides(parent:str, side='l'):
    mh_left_verts = ['body_lod0_mesh.vtx[24485]', 'body_lod0_mesh.vtx[20091]', 'body_lod0_mesh.vtx[19180]', 'body_lod0_mesh.vtx[19178]']
    mh_right_verts = ['body_lod0_mesh.vtx[28288]', 'body_lod0_mesh.vtx[12493]', 'body_lod0_mesh.vtx[11582]', 'body_lod0_mesh.vtx[11580]']
    if not cmds.objExists('foot_guides'):
        foot_parent = create_transform(name='foot_guides', parent=parent)
    else:
        foot_parent = 'foot_guides'

    guide_names = ['heel', 'toe_tip', 'outer', 'inner']

    #side = 'l'
    side_list = []
    true_guides = []
    vert_list = mh_left_verts if side == 'l' else mh_right_verts
    side_parent = create_transform(name=f'{side}_foot_guides', parent=foot_parent)
    for i, vert in enumerate(vert_list):
        pos = get_position_from_vertex(vert=vert)
        true_pos = (pos[0], 0, pos[2])
        guide = create_guide_from_position(pos=true_pos, guide_name=f'{side}_{guide_names[i]}_temp', parent=side_parent)
        side_list.append(guide)
    ball_pos = cmds.xform(f'ball_{side}', query=True, worldSpace=True, translation=True)
    true_ball_pos = (ball_pos[0], 0, ball_pos[2]) #type:ignore
    ball_guide = create_guide_from_position(pos=true_ball_pos, guide_name=f'{side}_ball_roll_pos_temp', parent=side_parent)
    foot_pos = cmds.xform(f'foot_{side}', query=True, worldSpace=True, translation=True)
    true_foot_pos = (foot_pos[0], 0, foot_pos[2]) #type:ignore
    foot_guide = create_guide_from_position(pos=true_foot_pos, guide_name=f'{side}_foot_roll_pos_temp', parent=side_parent)
    side_list.append(ball_guide)
    side_list.append(foot_guide)


    aim = get_flat_y_aim_rotation(source=side_list[0].name, target=side_list[1].name)


    true_ball_guide = create_guide_from_position(pos=(0,0,0), guide_name=f'{side}_ball_guide', parent=side_parent)
    toe_tip_dist = get_distance_between(obj_a=side_list[1].name, obj_b=ball_guide.name)
    true_toetip_guide = create_guide_from_position(pos=(0,0,toe_tip_dist), guide_name=f'{side}_toetip_guide', parent=side_parent)
    heel_dist = get_distance_between(obj_a=side_list[0].name, obj_b=ball_guide.name)
    true_toetip_guide = create_guide_from_position(pos=(0,0,-toe_tip_dist), guide_name=f'{side}_heel_guide', parent=side_parent)
    bank_dist = get_distance_between(obj_a=side_list[2].name, obj_b=side_list[3].name)
    if side == 'r':
        side_01 = 'inner'
        side_02 = 'outer'
    else:
        side_01 = 'outer'
        side_02 = 'inner'
    bank_01 = create_guide_from_position(pos=(bank_dist/2,0,0), guide_name=f'{side}_{side_01}_guide', parent=side_parent)
    bank_02 = create_guide_from_position(pos=(bank_dist/2,0,0), guide_name=f'{side}_{side_02}_guide', parent=side_parent)
    foot_dist = get_distance_between(obj_a=foot_guide.name, obj_b=ball_guide.name)
    true_footground_guide = create_guide_from_position(pos=(bank_dist/2,0,0), guide_name=f'{side}_footground_guide', parent=side_parent)
    true_foot_guide = create_guide_from_position(pos=(bank_dist/2, foot_pos[0], 0), guide_name=f'{side}_foot_guide', parent=side_parent)














