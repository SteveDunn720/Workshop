import maya.cmds as cmds

from Workshop.meta_rigs.meta_componets.root import Root
from Workshop.transform import create_transform


def build():

    rig_root_grp = create_transform(name="components", parent='rig')




    bbox = cmds.exactWorldBoundingBox("body_lod0_mesh")

    size_x = bbox[3] - bbox[0]
    size_z = bbox[5] - bbox[2]

    average = (size_x + size_z) / 3


    root_rig = Root(control_size=average)
    root_rig.root_build()

