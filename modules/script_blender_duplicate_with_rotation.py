import math

import bpy
from functions_distribute import *
from functions_scene import *
from libs.python_helper_functions.functions_log import *

# This makes rotated copies of all meshes in a scene. Mainly Use for creating pre-rotated walls, doors, etc. for asset libraries.


def __duplicate_with_rotation(o: bpy.types.Object, rotation: int, x_displacement):
    original_name = o.name
    duplicate = duplicate_object(o)
    duplicate.rotation_euler.z = math.radians(rotation)
    duplicate.name = f"{original_name}_{rotation}"
    duplicate.location.x += x_displacement


if __name__ == "__main__":
    clear()

    names = get_all_mesh_names()

    for name in names:
        mesh = get_object_by_name(name)
        spacing = mesh.dimensions.x * 2

    if "Floor" not in mesh.name:
        __duplicate_with_rotation(mesh, 90, spacing)
        __duplicate_with_rotation(mesh, 180, spacing * 2)
        __duplicate_with_rotation(mesh, 270, spacing * 3)

    distribute_scene_meshes()
