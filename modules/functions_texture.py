import numbers

import bpy
from functions_distribute import *
from functions_log import *
from functions_scene import *


def add_new_material_to_object(
    o: bpy.types.Object,
    material_name: str,
):
    new_material = bpy.data.materials.new(name=material_name)
    o.data.materials.append(new_material)


def remove_all_materials_from_object(o: bpy.types.Object):
    if (
        hasattr(o, "data")
        and hasattr(o.data, "materials")
        and len(o.data.materials) > 0
    ):
        o.data.materials.clear()


def add_material_with_same_name_as_object(o: bpy.types.Object, prefix="", suffix=""):
    # o = bpy.context.active_object
    if (
        hasattr(o, "data")
        and hasattr(o.data, "materials")
        and len(o.data.materials) < 1
    ):
        mat_name = o.name

        if isinstance(mat_name, numbers.Number):
            # Prepend underscore for numeric names (for import to CC4/iC8)
            mat_name = f"_{mat_name}"

        add_new_material_to_object(o, material_name=f"{prefix}{mat_name}{suffix}")


objects = get_selected_meshes()

for o in objects:
    remove_all_materials_from_object(o)
    add_material_with_same_name_as_object(o)
    # add_material_with_same_name_as_object(o, prefix="jacket_")
print_done()
