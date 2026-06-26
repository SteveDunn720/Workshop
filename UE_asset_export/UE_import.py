import unreal
import os

# --- CONFIGURATION ---
# The local path where your Maya exports are located
SOURCE_DIR = "C:/Users/sd547/Box/Sprint2026/Mistborn/test_repo/DoorA" 
# Where in the Content Browser you want them to go
GAME_PATH = "/Game/Assets/Doors/DoorA"

EXTENSIONS = (".fbx", ".obj")
 
def get_mesh_props_safely(pipeline):
    """
    Attempts to find the mesh properties sub-object regardless of UE5 version naming.
    """
    # Possible names used across UE 5.1, 5.2, 5.3, and 5.4+
    possible_names = ["common_meshes_properties", "common_mesh_properties"]
    
    for name in possible_names:
        try:
            props = pipeline.get_editor_property(name)
            if props:
                unreal.log(f"Success: Found mesh properties via '{name}'")
                return name, props
        except Exception:
            continue
            
    # If we get here, neither worked. Let's print all properties to help the user.
    unreal.log_error("Could not find mesh properties. Available properties on this pipeline are:")
    for prop_name in unreal.SystemLibrary.get_class_display_name(pipeline.get_class()):
        # Note: listing properties via Python is easier this way:
        pass
    
    # Alternative: Print directory of the object to see what's available
    unreal.log_warning(f"Available properties: {dir(pipeline)}")
    return None, None
 
def import_sub_assets_interchange(source_path, destination_path):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    static_mesh_lib = unreal.EditorStaticMeshLibrary()
    
    lod0_folder = os.path.join(source_path, "lod_0")
    if not os.path.exists(lod0_folder):
        unreal.log_error(f"Folder not found: {lod0_folder}")
        return
 
    lod0_files = [f for f in os.listdir(lod0_folder) if f.lower().endswith(EXTENSIONS)]
    created_meshes = {}
 
    for filename in lod0_files:
        full_path = os.path.abspath(os.path.join(lod0_folder, filename))
        asset_name = os.path.splitext(filename)[0].replace("_lod_0", "")
        
        task = unreal.AssetImportTask()
        task.filename = full_path
        task.destination_path = destination_path
        task.destination_name = asset_name
        task.automated = True
        task.save = True
        task.replace_existing = True
        
        # --- PIPELINE SETUP ---
        pipeline = unreal.InterchangeGenericMeshPipeline()
        prop_key, mesh_props = get_mesh_props_safely(pipeline)
        
        if mesh_props:
            # Apply the rotation (Maya Y-Up to UE Z-Up)
            mesh_props.set_editor_property("import_rotation", unreal.Rotator(90.0, 0.0, 0.0))
            # Put the modified props back into the pipeline
            pipeline.set_editor_property(prop_key, mesh_props)
            task.options = pipeline
        else:
            unreal.log_warning(f"Proceeding with default rotation for {asset_name} because properties were not found.")
 
        # Execute Import
        asset_tools.import_asset_tasks([task])
        
        # Load for LOD addition
        mesh_obj = unreal.EditorAssetLibrary.load_asset(f"{destination_path}/{asset_name}")
        if mesh_obj:
            created_meshes[asset_name] = mesh_obj
 
    # --- LOD IMPORT ---
    all_subdirs = [d for d in os.listdir(source_path) if os.path.isdir(os.path.join(source_path, d))]
    lod_folders = sorted([d for d in all_subdirs if d.startswith("lod_") and d != "lod_0"])
 
    for folder in lod_folders:
        try:
            lod_index = int(folder.split("_")[1])
        except: continue
        current_lod_dir = os.path.join(source_path, folder)
        for asset_name, mesh_obj in created_meshes.items():
            for ext in EXTENSIONS:
                lod_file = os.path.join(current_lod_dir, f"{asset_name}_lod_{lod_index}{ext}")
                if os.path.exists(lod_file):
                    static_mesh_lib.import_lod(mesh_obj, lod_index, lod_file)
 
    unreal.log("Automation Complete.")
 
# Execution
import_sub_assets_interchange(SOURCE_DIR, GAME_PATH)