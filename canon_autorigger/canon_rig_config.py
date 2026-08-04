from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform, get_distance_between, get_flat_y_aim_rotation
from Workshop.transform.mesh_info import get_position_from_vertex
from Workshop.guide.core import create_guide_from_position, guide_info
from .modules.foot import foot_guides



def generate_foot_guides(parent:str, side='L'):
    if not cmds.objExists('foot_guides_temp'):
        foot_parent = create_transform(name='foot_guides_temp', parent=parent)
    else:
        foot_parent = 'foot_guides_temp'

    #side = 'l'
    side_parent = create_transform(name=f'{side}_foot_guides', parent=foot_parent)

    side_list = [f'heel_{side}_guide', f'toetip_ground_{side}_guide', f'bankout_{side}_guide', f'bankin_{side}_guide', f'toeball_ground_{side}_guide', f'footroll_root_{side}_guide']

    foot_pos = cmds.xform(f'foot_{side}_guide', query=True, worldSpace=True, translation=True)


    aim = get_flat_y_aim_rotation(source=side_list[0], target=side_list[1])

    true_ball_guide = create_guide_from_position(pos=(0,0,0), guide_name=f'{side}_ball_guide', parent=side_parent)
    toe_tip_dist = get_distance_between(obj_a=side_list[1], obj_b=f'toeball_ground_{side}_guide')
    true_toetip_guide = create_guide_from_position(pos=(0,0,toe_tip_dist), guide_name=f'{side}_toetip_guide', parent=side_parent)
    heel_dist = get_distance_between(obj_a=side_list[0], obj_b=f'toeball_ground_{side}_guide')
    true_heel_guide = create_guide_from_position(pos=(0,0,-heel_dist), guide_name=f'{side}_heel_guide', parent=side_parent)
    bank_dist = get_distance_between(obj_a=side_list[2], obj_b=side_list[3])
    if side == 'R':
        side_01 = 'inner'
        side_02 = 'outer'
        mod = -1
    else:
        side_01 = 'outer'
        side_02 = 'inner'
        mod = 1
    bank_01_guide = create_guide_from_position(pos=((bank_dist/2) * mod,0,0), guide_name=f'{side}_{side_01}_guide', parent=side_parent)
    bank_02_guide = create_guide_from_position(pos=((-bank_dist/2) * mod,0,0), guide_name=f'{side}_{side_02}_guide', parent=side_parent)
    foot_dist = get_distance_between(obj_a=f'footroll_root_{side}_guide', obj_b=f'toeball_ground_{side}_guide')
    true_footground_guide = create_guide_from_position(pos=(0,0,-foot_dist), guide_name=f'{side}_footground_guide', parent=side_parent)
    true_foot_guide = create_guide_from_position(pos=(0, foot_pos[0] * mod, -foot_dist), guide_name=f'{side}_foot_guide', parent=side_parent)

    guides_info = foot_guides(true_heel=true_heel_guide,
                                true_foot=true_foot_guide,
                                true_groundfoot=true_footground_guide,
                                true_toe=true_toetip_guide,
                                true_inbank=bank_01_guide if side == 'l' else bank_02_guide,
                                true_outbank=bank_02_guide if side == 'l' else bank_01_guide,
                                true_ball=true_ball_guide,
                                og_foot_pos=side_list,
                                aim_angle=aim,
                                neg='outer' if side == 'r' else 'inner',
                                pos='inner' if side == 'r' else 'outer',)
    return guides_info














