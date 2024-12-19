import bpy
from functions_scene import *
from libs.python_helper_functions.functions_log import *


def rename_object(o: bpy.types.Object, name: str):
    print(f"Renaming '{o.name}' to '{name}'")
    o.name = name


def rename_object_to_lower(o: bpy.types.Object):
    print("Changing object name to lower case:")
    new_name = o.name.lower()
    rename_object(o, new_name)


def rename_object_replace(o: bpy.types.Object, str_old: str, str_new: str):
    print(f"Replacing '{str_old}' in '{o.name}' to '{str_new}'...")
    new_name = o.name.replace(str_old, str_new)
    rename_object(o, new_name)


def rename_objects_replace(objects: list[bpy.types.Object], str_old: str, str_new: str):
    for o in objects:
        rename_object_replace(o, str_old, str_new)
    return


def rename_objects_to_lower(objects: list[bpy.types.Object]):
    for o in objects:
        rename_object_to_lower(o)


def rename_data_to_object_name(o: bpy.types.Object):
    if o.data and o.data.users == 1:
        o.data.name = o.name


def rename_data_to_object_names(objects: list[bpy.types.Object]):
    for o in objects:
        rename_data_to_object_name(o)
    return


clear()
objects = get_selected_meshes()
rename_objects_to_lower(objects)
rename_objects_replace(objects, "part", "hard_surfaces_2")
rename_objects_replace(objects, " ", "_")
rename_data_to_object_names(objects)
print_done()
