import bpy
from functions_document import *
from functions_scene import *
from libs.python_helper_functions.functions_log import *


def __export(
    o: bpy.types.Object,
    subdirectory: str = "",
    export_method: str = ".fbx",
    scale: float = 1.0,
):

    export_directory = f"{bpy.path.abspath('//')}\\{subdirectory}"

    # Create subdirectory if it does not exist
    if not os.path.exists(export_directory):
        os.makedirs(export_directory)

    # deselect_all()
    # o.select_set(True)
    export_name = f"{export_directory}\\{o.name}"

    if export_method == ".fbx":
        export_file_path = f"{export_name}.fbx"
        print(f"Exporting FBX: {export_file_path}")

        bpy.ops.export_scene.fbx(
            filepath=export_file_path,
            use_selection=True,
            global_scale=scale,
        )
        return

    if export_method == ".obj":
        export_file_path = f"{export_name}.obj"
        print(f"Exporting OBJ: {export_file_path}")

        bpy.ops.wm.obj_export(
            filepath=export_file_path,
            export_selected_objects=True,
            global_scale=scale,
        )
        return


def export_obj(
    o: bpy.types.Object,
    subdirectory: str = "OBJ",
    scale: float = 1.0,
):
    __export(
        o,
        subdirectory=subdirectory,
        export_method=".obj",
        scale=scale,
    )


def export_fbx(
    o: bpy.types.Object,
    subdirectory: str = "FBX",
    scale: float = 100.0,
):
    __export(
        o,
        subdirectory=subdirectory,
        export_method=".fbx",
        scale=scale,
    )


def export_top_level_objects_as_obj():
    o_list = get_top_level_objects()
    export_count = 1
    for o in o_list:
        print(f"Exporting {export_count} of {len(o_list)}: {o.name}")
        select_object_and_children(o)
        export_obj(o)
        export_count += 1
        pass

    print_okgreen("Done!")


export_top_level_objects_as_obj()
document_open_location()
