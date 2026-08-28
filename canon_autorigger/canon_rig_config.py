from attr import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform, get_distance_between, get_flat_y_aim_rotation
from Workshop.transform.mesh_info import get_position_from_vertex
from Workshop.guide.core import create_guide_from_position, GuideInfo, read_guide, SplineGuideInfo
from Workshop.tag.core import sets_tag
from .modules.foot import foot_guides


@dataclass
class cannon_guide_config:
    root:GuideInfo
    spine:SplineGuideInfo
    hip:GuideInfo
    chest:GuideInfo
    neck:SplineGuideInfo
    head:GuideInfo
    leg:dict[str, list[GuideInfo]]
    arm:dict[str, list[GuideInfo]]
    clav:dict[str, list[GuideInfo]]
    fingers:dict[str, list[GuideInfo]]
    foot:dict[str, list[GuideInfo]]
    metacarpal:dict[str, list[GuideInfo]]

    pec_correctives:dict[str,list[GuideInfo]] | None
    trap_correctives:dict[str,list[GuideInfo]] | None
    necktrap_correctives:dict[str,list[GuideInfo]] | None

    full_joint_correctives:bool

    face:list[GuideInfo]
    jaw:list[GuideInfo]



def read_guides()->cannon_guide_config:
    #read root
    root = read_guide('root_M_guide')
    # Spine
    chest = read_guide('chest_root_M_guide')
    cog = read_guide('cog_M_guide')
    chest_curve = read_guide('chest_M_guide')
    chest_tan = read_guide('chest_tan_M_guide')
    hip_curve = read_guide('hip_M_guide')
    hip_tan = read_guide('hip_tan_M_guide')
    spine_curve = read_guide('spine_curve_M_guide')
    spine = SplineGuideInfo(curve=spine_curve, lower=hip_curve, lower_tan=hip_tan, upper=chest_curve, upper_tan=chest_tan)
    # neck
    neck_upper = read_guide('upper_neck_M_guide')
    neck_upper_tan = read_guide('upper_neck_tan_M_guide')
    neck_lower = read_guide('lower_neck_M_guide')
    neck_lower_tan = read_guide('lower_neck_tan_M_guide')
    neck_curve = read_guide('neck_M_guide')
    neck = SplineGuideInfo(curve=neck_curve, lower=neck_lower, lower_tan=neck_lower_tan, upper=neck_upper, upper_tan=neck_upper_tan)
    # head
    head = read_guide('head_root_M_guide')
    # mirrored body guides
    fingers = {}
    leg = {}
    foot = {}
    arm = {}
    clav = {}
    metacarpal = {}
    pec_cor = {}
    trap_cor = {}
    necktrap_cor = {}
    for side in ['L', 'R']:
        leg[side] = [read_guide(f'upperleg_{side}_guide'), read_guide(f'knee_{side}_guide'), read_guide(f'foot_{side}_guide')]
        arm[side] = [read_guide(f'shoulder_{side}_guide'), read_guide(f'elbow_{side}_guide'), read_guide(f'hand_{side}_guide')]
        foot[side] = [read_guide(f'foot_{side}_guide'), read_guide(f'toe_ball_{side}_guide'), read_guide(f'toe_ee_{side}_guide')]
        clav[side] = read_guide(f'clav_{side}_guide')
        metacarpal[side] = [read_guide(f'finger_index_{side}_00_guide'), read_guide(f'finger_middle_{side}_00_guide'), read_guide(f'finger_ring_{side}_00_guide'), read_guide(f'finger_pinky_{side}_00_guide'),]

        #fingers = finger_Index_L_01_guide
        for fing in ['thumb', 'index', 'middle', 'ring', 'pinky' ]:
            joint_list = []
            for i in [ '01', '02', '03', '04']:
                guide = read_guide(f'finger_{fing}_{side}_{i}_guide')
                joint_list.append(guide)
            fingers[f'{fing}_{side}'] = joint_list

        pec_cor[side] = [read_guide(f'pec_insert_{side}_guide'), read_guide(f'pec_01_{side}_guide'), read_guide(f'pec_02_{side}_guide')]
        trap_cor[side] = [read_guide(f'trap_insert_{side}_guide'), read_guide(f'trap_01_{side}_guide'), read_guide(f'trap_02_{side}_guide')]
        necktrap_cor[side] = [read_guide(f'necktrap_insert_{side}_guide'), read_guide(f'necktrap_01_{side}_guide')]

    #face_guides

    face = [read_guide('upper_head_M_guide'), read_guide('lower_head_M_guide')]
    jaw = [read_guide('jaw_M_guide'), read_guide('jaw_ee_M_guide'), read_guide('larynx_M_guide')]




    #tag geo
    sets_tag('geo', ['bind_joints_set'])

    all_guides = cannon_guide_config(
        root=root, 
        hip=cog, 
        chest=chest, 
        spine=spine, 
        neck=neck, 
        head=head, 
        leg=leg, 
        arm=arm, 
        fingers=fingers, 
        foot=foot, 
        clav=clav, 
        metacarpal=metacarpal, 
        pec_correctives=pec_cor, 
        trap_correctives=trap_cor,
        necktrap_correctives=necktrap_cor,
        full_joint_correctives=True,
        face=face,
        jaw=jaw,
    )
    return all_guides
    




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














