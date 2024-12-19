import math
import shutil

import bpy
from functions_distribute import *
from functions_export import *
from functions_scene import *

KITBASH_BLENDER_FILES_PATH = "F:\\Projects - Animation\\KitBash3D Blender Files"
KITBASH_DOWNLOADS_PATH = "F:\\Projects - Animation\\KitBash3D Downloads"  # This is where the texture files are located


# Distrubutes all top-level empty objects
def __arrange_models():
    select_top_level_empty_objects()
    distribute_selected_objects()
    print(count_parent_empties())


# For use on KitBash3D Blender files. This script uses (copies) the textures found in KITBASH_DOWNLOADS_PATH into KITBASH_BLENDER_FILES_PATH in a folder structure that is recognized by Character Creator 4.
# 1.) Isolate the meshes of the model whose textures you wish to export (hotkey: "/").
# 2.) Select all meshes
# 3.) Set the values to use for root_name and kit_name variables.
# 3.) Run the script.
def __export_textures_with_cc4_folder_structure(root_name: str, kitbash_kit_name: str):
    export_success = False

    # textures_export_location = f"{KITBASH_BLENDER_FILES_PATH}\\{kitbash_kit_name}\\FBX"
    # textures_export_location = f"C:\\Users\\Ernest\\Desktop\\{kitbash_kit_name}\\FBX"
    textures_export_location = (
        f"C:\\{kitbash_kit_name}\\FBX"  # For filename too long errors
    )

    print(f"Exporting to: {textures_export_location}")

    root_folder_name = f"{root_name}__root"
    meshes = get_selected_meshes()
    print(root_folder_name)

    node_folder_name = None

    if len(meshes) == 1:
        node_folder_name = f"{root_name}__node"
        print(node_folder_name)

    for o in meshes:
        material_slots = o.material_slots

        if len(meshes) > 1:
            node_folder_name = f"{o.name}__node"
            print(node_folder_name)

        mesh_folder_name = f"{o.name}__mesh"
        print(f"\t{mesh_folder_name}")

        for material_slot in material_slots:
            file_path_diffuse = None
            file_path_metallic = None
            file_path_normal = None
            file_path_roughness = None
            file_path_emissive = None
            file_path_opacity = None

            mat_folder_name = f"{material_slot.name}__material"
            print(f"\t\t{mat_folder_name}")

            textures = [
                x
                for x in material_slot.material.node_tree.nodes
                if x.type == "TEX_IMAGE"
            ]

            for texture in textures:
                texture_file_name: str = texture.image.name
                texture_path: str = texture.image.filepath.replace(
                    "//..\..\KitBash3D Downloads\\",
                    f"{KITBASH_DOWNLOADS_PATH}\\",
                )
                # print(f"\t\t\t\t{texture_path}")

                texture_file_found = file_exists(texture_path)
                # print(texture_file_found)
                # print(f"\t\t\t{texture_file_name}")

                if texture_file_found:
                    export = False
                    export_file_name = None

                    if "_basecolor." in texture_file_name:
                        file_path_diffuse = texture_file_name.replace(
                            "_basecolor", "__Diffuse"
                        )
                        export = True
                        export_file_name = file_path_diffuse
                        # print(f"\t\t\t\tDiffuse: {file_path_diffuse}")

                    elif "_normal." in texture_file_name:
                        texture_file_name = texture_file_name.replace(
                            "_normal", "__Normal"
                        )
                        export = True
                        file_path_normal = texture_file_name
                        export_file_name = file_path_normal
                        # print(f"\t\t\t\tNormal: {file_path_normal}")

                    elif "_metallic." in texture_file_name:
                        file_path_metallic = texture_file_name.replace(
                            "_metallic", "__Metallic"
                        )
                        export = True
                        export_file_name = file_path_metallic
                        # print(f"\t\t\t\tMetallic: {file_path_metallic}")

                    elif "_roughness." in texture_file_name:
                        file_path_roughness = texture_file_name.replace(
                            "_roughness", "__Roughness"
                        )
                        export = True
                        export_file_name = file_path_roughness
                        # print(f"\t\t\t\tRoughness: {file_path_roughness}")

                    elif "_emissive." in texture_file_name:
                        file_path_emissive = texture_file_name.replace(
                            "_emissive", "__Glow"
                        )
                        export = True
                        export_file_name = file_path_emissive
                        # print(f"\t\t\t\tEmissive: {file_path_emissive}")

                    elif "_opacity." in texture_file_name:
                        file_path_opacity = texture_file_name.replace(
                            "_opacity", "__Opacity"
                        )
                        export = True
                        export_file_name = file_path_opacity
                        # print(f"\t\t\t\tOpacity: {file_path_opacity}")

                    if export and export_file_name is not None:
                        src_file_path = texture_path
                        dst_location = f"{textures_export_location}\\{root_folder_name}\\{node_folder_name}\\{mesh_folder_name}\\{mat_folder_name}"
                        pathlib.Path(dst_location).mkdir(parents=True, exist_ok=True)

                        if pathlib.Path(dst_location).exists():
                            dst_file_path = f"\\\\?\\{dst_location}\\{export_file_name}"
                            print(f"Textures: {textures_export_location}")
                            try:
                                shutil.copyfile(src_file_path, dst_file_path)
                                export_success = True
                            except:
                                print("ERROR")
                                pass

    print("Done!")
    # if export_success:
    #     # Open export location
    #     os.startfile(os.path.realpath(textures_export_location))


# Old function for exporting only the textures
def __export_textures():

    root_name = "XXXXXXXXXX"
    root_name = "Hi Tech Streets"

    # kit_name = "Atom Punk"
    # kit_name = "Cyber Streets"
    # kit_name = "Cyber District"
    # kit_name = "Cyber Punk"
    # kit_name = "Enchanted"
    # kit_name = "Every City Emergency"
    # kit_name = "Future Warfare"
    kit_name = "Hi Tech Streets"
    # kit_name = "Lunar Base"
    # kit_name = "Mission To Minerva"
    # kit_name = "Oasis"
    # kit_name = "Restaurants"
    # kit_name = "Secret Lab"
    # kit_name = "Store Interiors Neighborhood Shops"
    # kit_name = "Treasure Island"

    __export_textures_with_cc4_folder_structure(root_name, kit_name)


def __export_models():
    top_level_objects = select_top_level_empty_objects()
    deselect_all()
    for o in top_level_objects:
        deselect_all()
        print(o.name)
        o.select_set(True)

        children = get_all_children(o)
        for child in children:
            child.select_set(True)
            print(f"    {child.name}")

        export_fbx(o, scale=1.0)

        # kit_name = "Atom Punk"
        # kit_name = "Cyber Streets"
        # kit_name = "Cyber District"
        # kit_name = "Cyber Punk"
        # kit_name = "Enchanted"
        # kit_name = "Every City Emergency"
        # kit_name = "Future Warfare"
        # kit_name = "Hi Tech Streets"
        # kit_name = "Lunar Base"
        # kit_name = "Mission To Minerva"
        # kit_name = "Oasis"
        # kit_name = "Restaurants"
        # kit_name = "Secret Lab"
        # kit_name = "Steampunk"
        # kit_name = "Store Interiors Neighborhood Shops"
        # kit_name = "Treasure Island"

        # __export_textures_with_cc4_folder_structure(o.name, kit_name)

    # os.startfile(os.path.realpath(f"{bpy.path.abspath('//')}\\FBX"))


# if __name__ == "__main__":
# __arrange_models()
# __export_textures()  # Legacy
__export_models()
