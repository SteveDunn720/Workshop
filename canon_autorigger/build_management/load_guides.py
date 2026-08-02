from attr import dataclass
import maya.cmds as cmds

RIG_BUILD_DIRECTORY = r'C:\Users\sldun\Documents\maya\projects\rig_build'
CANNON_DIRECTORY = 'canon_rigs'



@dataclass
class import_info:
    all:list
    top:list



def load_guides(rig:str, rig_type:str = 'canon'):
    import_node_list = []

    if rig_type == 'canon':
        path_ = rf'{RIG_BUILD_DIRECTORY}\{CANNON_DIRECTORY}\{rig}\{rig}_guides.mb'
        print(path_)
        import_nodes = import_from_path(path_=path_)
        for node in import_nodes.top:
            short_name = node.rsplit("|", 1)[-1]
            
            if short_name not in ['guides', 'geo']:
                cmds.delete(short_name)
            else:
                import_node_list.append(short_name)
        clean_scene()
        return import_node_list
            
    else:
        print(f'rig_type:{rig_type} not supported')
        return



def clean_scene():
    pass

       

def import_from_path(path_):

    print(path_)

    new_nodes = cmds.file(
        path_,
        i=True,
        namespace=":",
        mergeNamespacesOnClash=True,
        returnNewNodes=True,
        preserveReferences=True,
        ignoreVersion=True,
        prompt=False,
    )

    top_level = [
        node
        for node in new_nodes
        if cmds.objectType(node, isType="transform")
        and not cmds.listRelatives(node, parent=True)
    ]

    return import_info(all=new_nodes, top=top_level)