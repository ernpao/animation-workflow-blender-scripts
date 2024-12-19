import math

import bpy
from functions_distribute import *


def rotate_object_by_n_degrees(
    o: bpy.types.Object,
    x_degrees: float = 0,
    y_degrees: float = 0,
    z_degrees: float = 0,
):
    # o = bpy.context.active_object
    o.rotation_euler.x += math.radians(x_degrees)
    o.rotation_euler.y += math.radians(y_degrees)
    o.rotation_euler.z += math.radians(z_degrees)


# Set object's negative Z side to
# in and set the object's origin to the ground.
# - Changes object position
# - Changes object origin
def orient_object_to_ground(o: bpy.types.Object):

    # o = bpy.context.active_object
    deselect_all()
    o.select_set(True)

    # Origin to Center of Mass (Surface)
    bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")

    # save initial object location along x and y
    save_x = o.location.x
    save_y = o.location.y

    align_centers_to_world_xy()
    align_negative_sides_to_world_z()

    # Cursor to world origin
    bpy.ops.view3d.snap_cursor_to_center()

    # Origin to 3D Cursor
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

    # return object to previous posution
    o.location.x = save_x
    o.location.y = save_y


def orient_selected_object_to_ground():
    o = bpy.context.active_object
    orient_object_to_ground(o)


def orient_selected_objects_to_ground():
    for_each_selected_object(orient_object_to_ground)


def rotate_selected_by_n_degrees(
    x_degrees: float = 0,
    y_degrees: float = 0,
    z_degrees: float = 0,
):
    def callback(o: bpy.types.Object):
        rotate_object_by_n_degrees(
            o,
            x_degrees=x_degrees,
            y_degrees=y_degrees,
            z_degrees=z_degrees,
        )

    for_each_selected_object(callback)


def rotate_selected_90_degrees_ccw_x():
    rotate_selected_by_n_degrees(x_degrees=90)


def rotate_selected_90_degrees_cw_x():
    rotate_selected_by_n_degrees(x_degrees=-90)


def rotate_selected_90_degrees_ccw_y():
    rotate_selected_by_n_degrees(y_degrees=90)


def rotate_selected_90_degrees_cw_y():
    rotate_selected_by_n_degrees(y_degrees=-90)


def rotate_selected_90_degrees_ccw_z():
    rotate_selected_by_n_degrees(z_degrees=90)


def rotate_selected_90_degrees_cw_z():
    rotate_selected_by_n_degrees(z_degrees=-90)


if __name__ == "__main__":
    # iterate_through_scene_objects(orient_object_to_ground)
    # rotate_selected_90_degrees_cw_z()
    pass
