import maya.cmds as cmds

from Workshop.transform.utils import create_transform, get_flat_y_aim_rotation
from Workshop.transform.mesh_info import get_position_from_vertex
from Workshop.guide.core import create_guide_from_position





def generate_foot_guides(parent:str):
    mh_left_verts = ['body_lod0_mesh.vtx[24485]', 'body_lod0_mesh.vtx[20091]', 'body_lod0_mesh.vtx[19180]', 'body_lod0_mesh.vtx[11580]']
    mh_right_verts = ['body_lod0_mesh.vtx[28288]', 'body_lod0_mesh.vtx[12493]', 'body_lod0_mesh.vtx[11582]', 'body_lod0_mesh.vtx[19178]']
    foot_parent = create_transform(name='foot_guides', parent=parent)

    guide_names = ['heel', 'toe_tip', 'outer', 'inner']

    side = 'l'
    side_list = []
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

    for temp in side_list










