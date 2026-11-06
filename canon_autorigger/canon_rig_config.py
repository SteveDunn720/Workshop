from dataclasses import dataclass
import maya.cmds as cmds

from Workshop.transform.utils import create_transform, get_distance_between, get_flat_y_aim_rotation
from Workshop.transform.mesh_info import get_position_from_vertex
from Workshop.guide.core import create_guide_from_position, GuideInfo, read_guide, SplineGuideInfo
from Workshop.tag.core import sets_tag


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

    hip_correctives:dict[str,list[GuideInfo]] | None
    knee_correctives:dict[str,list[GuideInfo]] | None
    ankle_correctives:dict[str,list[GuideInfo]] | None
    elbow_correctives:dict[str,list[GuideInfo]] | None
    wrist_correctives:dict[str,list[GuideInfo]] | None
    chest_correctives:dict | None

    """pec_correctives:dict[str,list[GuideInfo]] | None
    trap_correctives:dict[str,list[GuideInfo]] | None
    necktrap_correctives:dict[str,list[GuideInfo]] | None"""

    full_joint_correctives:bool

    face:list[GuideInfo]
    jaw:list[GuideInfo]
    mouth:dict[str,GuideInfo]
    nose:dict[str,GuideInfo]
    teeth:list[GuideInfo]
    tongue:GuideInfo
    nl:list[GuideInfo]
    brow:list[GuideInfo]
    cheek:dict[str, list[GuideInfo]]
    ear:dict[str,GuideInfo]

    primary_geo:str



def read_guides(rig_name:str='Canon')->cannon_guide_config:
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

    mouth = {}
    nose = {}
    cheek = {}
    ear = {}
    hip_correctives = {}
    knee_correctives = {}
    ankle_correctives = {}
    elbow_correctives = {}
    wrist_correctives = {}
    chest_correctives = {}

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

        mouth[f'{side}_mouth'] = read_guide(f'lip_{side}_guide')
        mouth[f'{side}_path'] = read_guide(f'mouth_path_{side}_guide')
        nose[f'{side}_Nostril'] = read_guide(f'nose_Nostril_{side}_guide')
        nose[f'{side}_Outer'] = read_guide(f'nose_NostrilOuter_{side}_guide')
        nose[f'{side}_UpperCorner'] = read_guide(f'nose_UpperCorner_{side}_guide')
        cheek[f'{side}'] = [read_guide(f'cheek_puff_{side}_guide'), read_guide(f'cheek_bone_{side}_guide')]
        ear[f'{side}_root'] = read_guide(f'ear_root_{side}_guide')
        ear[f'{side}_lower'] = read_guide(f'ear_lower_{side}_guide')
        ear[f'{side}_upper'] = read_guide(f'ear_upper_{side}_guide')
        ear[f'{side}_outer'] = read_guide(f'ear_outer_{side}_guide')
        hip_correctives[side] = [read_guide(f'psoasup_{side}_guide'), read_guide(f'psoasdown_{side}_guide'), read_guide(f'glutelow_{side}_guide'), read_guide(f'glutemid_{side}_guide'), read_guide(f'gluteup_{side}_guide'), read_guide(f'trochanter_{side}_guide')]
        knee_correctives[side] = [read_guide(f'kneecap_{side}_guide'), read_guide(f'hamstring_{side}_guide'), read_guide(f'calf_{side}_guide'),]
        ankle_correctives[side] = [read_guide(f'tibialis_{side}_guide'), read_guide(f'achilles_{side}_guide'), read_guide(f'medialmalleolus_{side}_guide'), read_guide(f'lateralmalleolus_{side}_guide'),]
        elbow_correctives[side] = [read_guide(f'elbowin_{side}_guide'), read_guide(f'lowerbicep_{side}_guide'), read_guide(f'lowertricep_{side}_guide'), read_guide(f'pronator_{side}_guide')]
        wrist_correctives[side] = [read_guide(f'wristin_{side}_guide'), read_guide(f'wristout_{side}_guide'), read_guide(f'wristup_{side}_guide'), read_guide(f'wristdown_{side}_guide'), ]
        chest_correctives[side] = [pec_cor[side], trap_cor[side], necktrap_cor[side]]
    #face_guides

    face = [read_guide('upper_head_M_guide'), read_guide('lower_head_M_guide'), read_guide('mid_head_M_guide'), read_guide('top_head_M_guide'), read_guide('jaw_M_guide')]
    jaw = [read_guide('jaw_M_guide'), read_guide('jaw_ee_M_guide'), read_guide('larynx_M_guide')]
    nose['Nostril_Inner'] = read_guide('nose_Nostril_Inner_M_guide')
    nose['Tip'] = read_guide('nose_Tip_M_guide')
    nose['Bridge'] = read_guide('nose_Bridge_M_guide')
    nose['Root'] = read_guide('nose_Root_M_guide')
    teeth = [read_guide('teeth_upper_L_guide'),read_guide('teeth_upper_R_guide'), read_guide('teeth_lower_L_guide'), read_guide('teeth_lower_R_guide') ]
    tongue = read_guide('tongue_M_guide')
    nl = [read_guide('nl_L_guide'), read_guide('nl_R_guide')]
    brow = [read_guide('brow_L_guide'), read_guide('brow_R_guide')]



    #geo temp logic, need to decide later how this will work
    primary_mesh = f'{rig_name}_UBM_low'




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

        hip_correctives = hip_correctives,
        knee_correctives = knee_correctives,
        ankle_correctives = ankle_correctives,
        elbow_correctives = elbow_correctives,
        wrist_correctives = wrist_correctives,
        chest_correctives = chest_correctives,

        full_joint_correctives=True,

        face=face,
        jaw=jaw,
        mouth=mouth,
        nose=nose,
        teeth=teeth,
        tongue=tongue,
        nl=nl,
        brow=brow,
        cheek=cheek,
        ear=ear,

        primary_geo=primary_mesh,
    )
    return all_guides
    













