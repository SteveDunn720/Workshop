
from Workshop.meta_rigs import meta_componets

def build(meta_type:str='metahuman'):

    #verify and assign meta rig type, current plans for mixamo and metahuman, may add more later

    if meta_type == 'metahuman':
        rig_root = meta_componets.configure_metahuman_scene()
    else:
        print(f'meta_type:{meta_type} is incompatible with this build, only metahuman is curently compatable')
    
    body_rig_root:str = rig_root.body_rig #type:ignore
    rig_size:float = rig_root.scene_size #type:ignore

    root = meta_componets.Root(control_size=rig_size, parent=body_rig_root)
    root.root_build()
    """root = meta_componets.Root(control_size=rig_size, parent=body_rig_root)
    root.root_build()"""

    for side in ['l', 'r']:
        leg = meta_componets.Limb(part='leg', control_size=rig_size, parent=body_rig_root, side=side, joints= [f'thigh_{side}', f'calf_{side}', f'foot_{side}'],ik_end_control = True)
        leg.limb_build()
        arm = meta_componets.Limb(part='arm',control_size=rig_size, parent=body_rig_root, side=side, joints= [f'upperarm_{side}', f'lowerarm_{side}', f'hand_{side}'],ik_end_control = True)
        arm.limb_build()
