import json
import os

import bpy
import bpy.utils.previews
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper
from functions_distribute import *
from functions_scene import *
from libs.cyberpunk_2077_utils.main.attribute_import import manage_garment_support
from libs.cyberpunk_2077_utils.main.setup import MaterialBuilder
from libs.io_scene_gltf2.blender.imp.gltf2_blender_gltf import BlenderGlTF
from libs.io_scene_gltf2.io.imp.gltf2_io_gltf import glTFImporter
from libs.python_helper_functions.functions_log import *

WOLVENKIT_GARMENTS_LOCATION = "F:\\WolvenKit\\WolvenKit_Projects\\Cyberpunk_2077_Garments\\source\\raw\\base\\characters\\garment"
BLENDER_FILES_LOCATION = (
    "F:\\WolvenKit\\WolvenKit_Projects\\Cyberpunk_2077_Garments\\blender"
)

BLENDER_TEMPLATE_FILE = f"{BLENDER_FILES_LOCATION}\\template.blend"


class __AssetImporter:
    image_format = "png"
    exclude_unused_mats = True
    with_materials = True
    update_gi = True
    import_garmentsupport = True
    appearances = "ALL"

    def import_file(self, filepath: str, mesh_name):
        gltf_importer = glTFImporter(
            filepath,
            {
                "files": None,
                "loglevel": 0,
                "import_pack_images": True,
                "merge_vertices": False,
                "import_shading": "NORMALS",
                "bone_heuristic": "TEMPERANCE",
                "guess_original_bind_pose": False,
                "import_user_extensions": "",
            },
        )
        gltf_importer.read()
        gltf_importer.checks()

        # kwekmaster: modified to reflect user choice
        # print(filepath + " Loaded; With materials: " + str(self.with_materials))

        existingMeshes = bpy.data.meshes.keys()

        existingMaterials = bpy.data.materials.keys()

        BlenderGlTF.create(gltf_importer)

        imported = bpy.context.selected_objects  # the new stuff should be selected
        collection = bpy.data.collections.new(mesh_name)
        bpy.context.scene.collection.children.link(collection)

        for o in imported:
            for parent in o.users_collection:
                parent.objects.unlink(o)
            collection.objects.link(o)
            # print('o.name - ',o.name)
            if "Armature" in o.name:
                # o.hide_set(True)
                # o.d
                bpy.data.objects.remove(o, do_unlink=True)  # remove the armature
                pass

        for name in bpy.data.materials.keys():
            if name not in existingMaterials:
                bpy.data.materials.remove(
                    bpy.data.materials[name],
                    do_unlink=True,
                    do_id_user=True,
                    do_ui_user=True,
                )

        if self.import_garmentsupport:
            manage_garment_support(existingMeshes, gltf_importer)

        BasePath = filepath.replace(".glb", "")
        # Kwek: Gate this-
        # -do the block iff corresponding Material.json exist
        # Kwek: was tempted to do a try-catch, but that is just La-Z
        # Kwek: Added another gate for materials
        if self.with_materials and os.path.exists(BasePath + ".Material.json"):
            file = open(BasePath + ".Material.json", mode="r")
            obj = json.loads(file.read())
            BasePath = str(obj["MaterialRepo"]) + "\\"

            json_apps = obj["Appearances"]
            # fix the app names as for some reason they have their index added on the end.
            appkeys = [k for k in json_apps.keys()]
            for i, k in enumerate(appkeys):
                json_apps[k[: -1 * len(str(i))]] = json_apps.pop(k)

            validmats = {}
            # appearances = ({'name':'short_hair'},{'name':'02_ca_limestone'},{'name':'ml_plastic_doll'},{'name':'03_ca_senna'})
            # if appearances defined populate valid mats with the mats for them, otherwise populate with everything used.

            # if len(appearances) > 0 and "ALL" not in appearances:
            #     for key in json_apps.keys():
            #         if key in appearances:
            #             for m in json_apps[key]:
            #                 validmats[m] = True

            # there isnt always a default, so if none were listed, or ALL was used, or an invalid one add everything.
            if len(validmats) == 0:
                for key in json_apps.keys():
                    for m in json_apps[key]:
                        validmats[m] = True

            for mat in validmats.keys():
                for m in obj["Materials"]:
                    if m["Name"] == mat:
                        if "BaseMaterial" in m.keys():
                            if "GlobalNormal" in m["Data"].keys():
                                GlobalNormal = m["Data"]["GlobalNormal"]
                            else:
                                GlobalNormal = "None"
                            if "MultilayerMask" in m["Data"].keys():
                                MultilayerMask = m["Data"]["MultilayerMask"]
                            else:
                                MultilayerMask = "None"
                            if "DiffuseMap" in m["Data"].keys():
                                DiffuseMap = m["Data"]["DiffuseMap"]
                            else:
                                DiffuseMap = "None"

                            validmats[mat] = {
                                "Name": m["Name"],
                                "BaseMaterial": m["BaseMaterial"],
                                "GlobalNormal": GlobalNormal,
                                "MultilayerMask": MultilayerMask,
                                "DiffuseMap": DiffuseMap,
                            }
                        else:
                            print(m.keys())

            MatImportList = [k for k in validmats.keys()]

            Builder = MaterialBuilder(obj, BasePath, str(self.image_format))

            counter = 0
            bpy_mats = bpy.data.materials
            for name in bpy.data.meshes.keys():
                if name not in existingMeshes:
                    bpy.data.meshes[name].materials.clear()
                    if (
                        gltf_importer.data.meshes[counter].extras is not None
                    ):  # Kwek: I also found that other material hiccups will cause the Collection to fail
                        for matname in gltf_importer.data.meshes[counter].extras[
                            "materialNames"
                        ]:
                            if matname in validmats.keys():
                                # print('matname: ',matname, validmats[matname])
                                m = validmats[matname]
                                if (
                                    matname in bpy_mats.keys()
                                    and matname[:5] != "Atlas"
                                    and "BaseMaterial" in bpy_mats[matname].keys()
                                    and bpy_mats[matname]["BaseMaterial"]
                                    == m["BaseMaterial"]
                                    and bpy_mats[matname]["GlobalNormal"]
                                    == m["GlobalNormal"]
                                    and bpy_mats[matname]["MultilayerMask"]
                                    == m["MultilayerMask"]
                                ):
                                    bpy.data.meshes[name].materials.append(
                                        bpy_mats[matname]
                                    )
                                elif (
                                    matname in bpy_mats.keys()
                                    and matname[:5] == "Atlas"
                                    and bpy_mats[matname]["BaseMaterial"]
                                    == m["BaseMaterial"]
                                    and bpy_mats[matname]["DiffuseMap"]
                                    == m["DiffuseMap"]
                                ):
                                    bpy.data.meshes[name].materials.append(
                                        bpy_mats[matname]
                                    )
                                else:
                                    if matname in validmats.keys():
                                        index = 0
                                        for rawmat in obj["Materials"]:
                                            if rawmat["Name"] == matname:
                                                try:
                                                    bpymat = Builder.create(index)
                                                    if bpymat:
                                                        bpymat["BaseMaterial"] = (
                                                            validmats[matname][
                                                                "BaseMaterial"
                                                            ]
                                                        )
                                                        bpymat["GlobalNormal"] = (
                                                            validmats[matname][
                                                                "GlobalNormal"
                                                            ]
                                                        )
                                                        bpymat["MultilayerMask"] = (
                                                            validmats[matname][
                                                                "MultilayerMask"
                                                            ]
                                                        )
                                                        bpymat["DiffuseMap"] = (
                                                            validmats[matname][
                                                                "DiffuseMap"
                                                            ]
                                                        )
                                                        bpy.data.meshes[
                                                            name
                                                        ].materials.append(bpymat)
                                                except FileNotFoundError as fnfe:
                                                    # Kwek -- finally, even if the Builder couldn't find the materials, keep calm and carry on
                                                    # print(str(fnfe))
                                                    pass
                                            index = index + 1
                            else:
                                # print(matname, validmats.keys())
                                pass

                    counter = counter + 1

            if not self.exclude_unused_mats:
                index = 0
                for rawmat in obj["Materials"]:
                    if rawmat["Name"] not in bpy.data.materials.keys() and (
                        (rawmat["Name"] in MatImportList) or len(MatImportList) < 1
                    ):
                        Builder.create(index)
                    index = index + 1

        # Join objects in the collection
        # bpy.ops.object.select_all(action="DESELECT")
        deselect_all()

        with_active = False
        for o in collection.all_objects:
            o.select_set(True)
            if not with_active:
                bpy.context.view_layer.objects.active = o
                with_active = True

        bpy.ops.object.join()
        # bpy.ops.object.select_all(action="DESELECT")
        deselect_all()

        for o in collection.all_objects:
            o.name = mesh_name

        # Move to scene collection and remove the dummy collection
        scene_collection = bpy.context.scene.collection
        for o in collection.all_objects:
            scene_collection.objects.link(o)
            collection.objects.unlink(o)

        bpy.data.collections.remove(collection, do_unlink=True)

        # Update the viewport
        # bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        pass


def __import_wolvenkit_garment_models_into_scene(
    path: str = WOLVENKIT_GARMENTS_LOCATION,
    import_limit: int = None,
    category: str = None,
):
    importer = __AssetImporter()
    imported_count = 0
    for root, dirs, files in os.walk(path):
        if (import_limit is not None) and (imported_count >= import_limit):
            return

        path_depth = root.split(os.sep)

        print((len(path_depth) - 1) * "---", os.path.basename(root))

        textures_folder_found = False

        for dir in dirs:
            if dir == "textures":
                textures_folder_found = True

        for file in files:  # files in directory
            filepath = root + os.sep + file

            if textures_folder_found:
                depth_marker = len(path_depth) * "---"
                # print(depth_marker, file)
                if file.endswith(".glb"):
                    print(depth_marker, "Importing " + file + "...")
                    # import file
                    glb_filepath = filepath
                    glb_mesh_name = file.replace(".glb", "")

                    if (
                        (category is not None)
                        and (glb_filepath.find(os.sep + category + os.sep) != -1)
                        and (not object_with_name_exists_in_scene(glb_mesh_name))
                    ):
                        importer.import_file(glb_filepath, glb_mesh_name)
                        imported_count += 1

                    else:
                        pass


def __import_test():
    importer = __AssetImporter()
    importer.import_file(
        "F:\\WolvenKit\\WolvenKit_Projects\\Cyberpunk_2077_Garments\\source\\raw\\base\\characters\\garment\\citizen_badlands\\feet\\s1_054_boot__farmer\\s1_054_ma_boot__farmer.glb",
        "s1_054_ma_boot__farmer",
    )


def __get_garment_directories() -> list[str]:
    directories = []

    for root, dirs, files in os.walk(WOLVENKIT_GARMENTS_LOCATION):
        for directory in dirs:
            location = f"{root}\\{directory}"

            is_top_level_directory = True

            if WOLVENKIT_GARMENTS_LOCATION != root:
                is_top_level_directory = False

            if os.path.isdir(location) and is_top_level_directory:
                directories.append(directory)
                # print(location)

    # print(f"Directories found: {directories.__len__()}")

    return directories


def __import_all_wolvenkit_garments():
    garment_classes = __get_garment_directories()
    garment_categories = [
        "arms",
        "feet",
        "hands",
        "head",
        "item",
        "legs",
        "torso",
    ]

    for garment_class in garment_classes:
        ignore_list = ["citizen_casualxx"]
        if garment_class not in ignore_list:
            for garment_category in garment_categories:
                garments_path = f"{WOLVENKIT_GARMENTS_LOCATION}\\{garment_class}"
                save_location = f"{BLENDER_FILES_LOCATION}\\{garment_category}"

                from pathlib import Path

                Path(save_location).mkdir(parents=True, exist_ok=True)

                save_filepath = f"{save_location}\\{garment_class}.blend"

                if not os.path.exists(save_filepath):
                    clear()
                    print(
                        f"Import process: Importing '{garment_category}' garments in {garments_path}..."
                    )
                    remove_scene_objects()
                    # directories = get_clothing_directories()
                    __import_wolvenkit_garment_models_into_scene(
                        path=garments_path, category=garment_category
                    )
                    distribute_scene_meshes()
                    document_save(save_filepath)
                    clear()
                else:
                    print(
                        f"Import process: Garments of type '{garment_class}\{garment_category}' already imported: {save_filepath}"
                    )

    print("All garments have been imported!")


def __open_template_file():
    document_open(BLENDER_TEMPLATE_FILE)


def __create_list_of_objects_to_append(garment_category: str):
    # garment_category = "feet"
    text_file_data = []
    text_file_filepath = (
        f"{BLENDER_FILES_LOCATION}\\{garment_category}\\{garment_category}.txt"
    )

    for (
        root,
        dirs,
        files,
    ) in os.walk(f"{BLENDER_FILES_LOCATION}\\{garment_category}"):
        for filename in files:
            source_filepath = f"{root}\\{filename}"
            dest_blend_filepath = f"{root}\\{garment_category}.blend"

            if (
                filename.endswith(".blend")
                and not (source_filepath == dest_blend_filepath)
                and not (BLENDER_FILES_LOCATION == root)
            ):
                clear()

                # Collect object names from source file
                document_open(source_filepath)
                object_names = get_all_object_names()
                print(f"Objects to import: {object_names.__len__()}")
                print(object_names)

                # Create or open destination file
                if os.path.exists(dest_blend_filepath):
                    document_open(dest_blend_filepath)
                    print(f"Opening existing destination file: {dest_blend_filepath}")
                else:
                    print(f"Creating new destination file: {dest_blend_filepath}")
                    __open_template_file()
                    document_save(dest_blend_filepath)

                # Append objects from source to dest
                print(
                    f"Appending objects from {source_filepath} to {dest_blend_filepath}"
                )

                source_directory = f"{source_filepath}\\Object"

                for object_name in object_names:
                    #     if not object_with_name_exists_in_scene(object_name):
                    #         print(f"Appending '{object_name}'...")
                    #         bpy.ops.wm.append(
                    #             filepath=source_filepath,
                    #             directory=source_directory,
                    #             filename=object_name,
                    #         )
                    text_file_data.append(
                        f"{source_filepath}|{source_directory}|{object_name}"
                    )
                    pass

                # document_save(dest_blend_filepath)

                # print(
                #     f"Done appending objects from {source_filepath} to {dest_blend_filepath}"
                # )

    with open(text_file_filepath, "w") as f:
        for line in text_file_data:
            f.write("%s\n" % line)
    f.close()
    print(f"Done creating list of objects to append: {text_file_filepath}")


def __delete_empty_blend_files():
    files_removed = 0
    for (
        root,
        dirs,
        files,
    ) in os.walk(BLENDER_FILES_LOCATION):
        for filename in files:
            if (
                filename.endswith(".blend")
                and not ("delete" in root)
                and not (BLENDER_FILES_LOCATION == root)
            ):
                clear()

                filepath = f"{root}\\{filename}"
                bpy.ops.wm.open_mainfile(filepath=filepath)

                objects_found = count_objects_in_scene()

                print(f"File {filename} has {objects_found} objects in the scene.")

                if objects_found == 0:
                    save_location = f"{root}\\delete"

                    from pathlib import Path

                    Path(save_location).mkdir(parents=True, exist_ok=True)

                    new_filepath = f"{save_location}\\{filename}"
                    document_save(new_filepath)

                    os.remove(filepath)
                    files_removed += 1

                    print(f"File {filepath} has been moved to {new_filepath}")
        pass
    pass


# ----------- SCRIPT EXECUTION ----------- #

if __name__ == "__main__":

    clear()
    garment_category = "head"
    # garment_category = "feet"

    def create_list():
        __create_list_of_objects_to_append(garment_category)

    def process_list():
        text_file_filepath = (
            f"{BLENDER_FILES_LOCATION}\\{garment_category}\\{garment_category}.txt"
        )

        destination_filepath = (
            f"{BLENDER_FILES_LOCATION}\\{garment_category}\\{garment_category}.blend"
        )

        appended = 0
        f = open(text_file_filepath, "r")
        for line in f.readlines():
            split_string = line.split("|")
            source_filepath = split_string[0]
            source_directory = split_string[1]
            source_object_name = split_string[2]
            # clear()

            # if appended < 1:
            if True:
                print("---Appending object---")
                print(
                    f"""
                    File Path: {source_filepath}
                    Directory: {source_directory}
                    Object Name: {source_object_name}
                """
                )

                bpy.ops.wm.append(
                    filepath=source_filepath,
                    directory=source_directory,
                    filename=source_object_name,
                    # check_existing=True,
                )

                appended += 1

        print("Done processing list!")

    # bpy.app.timers.register(create_list)
    # bpy.app.timers.register(process_list)
