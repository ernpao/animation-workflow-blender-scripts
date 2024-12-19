from functions_log import *
from functions_scene import *


def smart_uv_unwrap_object(o: bpy.types.Object):
    bpy.ops.object.mode_set(mode="OBJECT")

    deselect_all()

    select_object_and_children(o)

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")


def smart_uv_unwrap_objects(objects: list[bpy.types.Object]):
    count = 1
    for o in objects:
        print(f"Unwrapping '{o.name}' {count} of {len(objects)}")
        smart_uv_unwrap_object(o)
        count += 1


def smart_uv_unwrap_top_level_objects():
    smart_uv_unwrap_objects(get_top_level_objects())
    print_okgreen("Done!")


def smart_uv_unwrap_selected_objects():
    smart_uv_unwrap_objects(get_parent_objects_in_selection())
    print_okgreen("Done!")


# smart_uv_unwrap_top_level_objects()
smart_uv_unwrap_selected_objects()
