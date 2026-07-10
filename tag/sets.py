import ast
import maya.cmds as cmds

def add_to_set(object):

    set_list = ast.literal_eval(cmds.getAttr(f"{object}.SETS_TAG"))

    for set_type in set_list:

        if not cmds.objExists(set_type):
            cmds.sets(name=set_type)
        cmds.sets(object, addElement=set_type)

