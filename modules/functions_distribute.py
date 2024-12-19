import math

import bpy
from functions_scene import *


def __nearest_square(limit):
    answer = 0
    while (answer + 1) ** 2 < limit:
        answer += 1
    return (answer + 1) ** 2


def __distribute_objects(
    objects: list[bpy.types.Object],
    spacing_factor: float = 1.5,
    set_object_centers=True,
):
    object_count = objects.__len__()

    nearest_square = __nearest_square(object_count)
    row_count = math.sqrt(nearest_square)

    max_width = 0
    max_length = 0

    for obj in objects:
        if obj.dimensions.x > max_width:
            max_width = obj.dimensions.x

        if obj.dimensions.y > max_length:
            max_length = obj.dimensions.y

        if len(obj.children) > 0:
            for child in obj.children:
                if child.dimensions.x > max_width:
                    # print("max_width")
                    max_width = child.dimensions.x
                    # print(max_width)

                if child.dimensions.y > max_length:
                    # print("max_length")
                    max_length = child.dimensions.y
                    # print(max_length)

    # print(max_width)
    # print(max_length)

    spacing = max(max_length, max_width) * spacing_factor

    x = 0
    y = 0
    row_index = 0
    col_index = 0

    # deselect all of the objects
    bpy.ops.object.select_all(action="DESELECT")

    for obj in objects:
        x = row_index * spacing
        y = col_index * spacing
        row_index += 1

        obj.select_set(True)
        if set_object_centers:
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

        # Set Location
        # print(f"Moving {mesh.name} to X:{x} Y:{y}")
        obj.location.x = x
        obj.location.y = y
        obj.location.z = 0

        # Set Rotation
        # mesh.rotation_euler.z = math.radians(0)
        # mesh.rotation_euler.y = math.radians(180)

        if row_index == row_count:
            row_index = 0
            col_index += 1
    pass


def distribute_selected_meshes(
    set_object_centers=True,
    spacing_factor: float = 1.5,
):
    # print("Distributing selected objects...")
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    mesh_count = meshes.__len__()

    if mesh_count < 2:
        print("Less than 2 meshes are currently selected. Terminating the script.")
        return

    __distribute_objects(
        meshes,
        set_object_centers=set_object_centers,
        spacing_factor=spacing_factor,
    )
    print("Done!")
    return


def distribute_scene_meshes(
    set_object_centers=True,
    spacing_factor: float = 1.5,
):
    object_count = count_objects_in_scene()
    print(f"Objects to distribute: {object_count}")
    for o in bpy.context.scene.collection.all_objects:
        o.select_set(True)
    distribute_selected_meshes(
        set_object_centers=set_object_centers,
        spacing_factor=spacing_factor,
    )


def distribute_objects(
    objects: list[bpy.types.Object],
    spacing_factor: float = 1.5,
    set_object_centers=True,
):
    __distribute_objects(
        objects,
        spacing_factor=spacing_factor,
        set_object_centers=set_object_centers,
    )


def distribute_selected_objects(set_object_centers=True, spacing_factor: float = 1.5):
    __distribute_objects(
        bpy.context.selected_objects,
        set_object_centers=set_object_centers,
        spacing_factor=spacing_factor,
    )


def distribute_selected_objects_alphabetically(
    set_object_centers=True,
    spacing_factor: float = 1.5,
):
    o = [obj for obj in bpy.context.selected_objects]

    def get_name(o: bpy.types.Object):
        return o.name

    o.sort(key=get_name)
    distribute_objects(
        objects=o,
        set_object_centers=set_object_centers,
        spacing_factor=spacing_factor,
    )


def __sort_list_of_objects_by_position_on_axis(
    axis: int,
    objects: list[bpy.types.Object],
):
    def get_x(o: bpy.types.Object):
        return o.location.x

    def get_y(o: bpy.types.Object):
        return o.location.y

    def get_z(o: bpy.types.Object):
        return o.location.z

    if axis == 1:
        objects.sort(key=get_y)
    elif axis == 2:
        objects.sort(key=get_z)
    else:
        objects.sort(key=get_x)


def __get_min_max_location_of_objects(
    axis: int,
    objects: list[bpy.types.Object],
) -> tuple[float, float]:
    objects_copy = objects.copy()
    __sort_list_of_objects_by_position_on_axis(axis, objects_copy)
    first, last = __get_first_and_last_in_array(objects_copy)

    min = first.location.x
    max = last.location.x

    print(f"min: {min}")
    print(f"max: {max}")

    if axis == 1:
        min = first.location.y
        max = last.location.y
    elif axis == 2:
        min = first.location.z
        max = last.location.z

    return min, max


def __get_total_distance_across_objects(
    axis: int,
    objects: list[bpy.types.Object],
) -> float:
    min, max = __get_min_max_location_of_objects(axis, objects)
    return max - min


def __get_half_total_distance_across_objects(
    axis: int,
    objects: list[bpy.types.Object],
) -> float:
    return __get_total_distance_across_objects(axis, objects) / 2


def __get_average_space_between_objects(
    axis: int,
    objects: list[bpy.types.Object],
) -> float:
    d = __get_total_distance_across_objects(axis, objects)
    return d / (len(objects) - 1)


def __get_first_and_last_in_array(
    objects: list[bpy.types.Object],
) -> tuple[bpy.types.Object, bpy.types.Object]:
    first = objects[0]
    last = objects[len(objects) - 1]
    return first, last


def __distribute_objects_along_axis(
    axis: int,  # 0 is X, 1 is Y, 2 is Z
    objects: list[bpy.types.Object],
):
    obj_count = len(objects)
    if obj_count < 3:
        print(
            "Less than 3 objects are currently selected. Aborting distribute operation."
        )
        return

    __sort_list_of_objects_by_position_on_axis(axis, objects)

    initial, final = __get_min_max_location_of_objects(axis, objects)

    spacing = __get_average_space_between_objects(axis, objects)

    print(f"spacing: {spacing}")

    i = 0
    for o in objects:
        position = initial + (spacing * i)
        if axis == 0:
            o.location.x = position
        elif axis == 1:
            o.location.y = position
        else:
            o.location.z = position
        i += 1

    print("Distribute operation completed!")


def distribute_selected_objects_along_x():
    top_level_objects = get_parent_objects_in_selection()
    __distribute_objects_along_axis(0, top_level_objects)


def distribute_selected_objects_along_y():
    top_level_objects = get_parent_objects_in_selection()
    __distribute_objects_along_axis(1, top_level_objects)


def distribute_selected_objects_along_z():
    top_level_objects = get_parent_objects_in_selection()
    __distribute_objects_along_axis(2, top_level_objects)


def __align_objects_along_axis(
    axis: int,  # 0 is X, 1 is Y, 2 is Z
    objects: list[bpy.types.Object],
    anchor: bpy.types.Object = None,
):
    obj_count = len(objects)
    if obj_count < 3:
        print(
            "Less than 3 objects are currently selected. Aborting alignment operation."
        )
        return

    __sort_list_of_objects_by_position_on_axis(axis, objects)

    # center = __get_center_distance_across_objects(axis, objects)
    center = 0

    if anchor is not None:
        if axis == 0:
            center = anchor.location.x
        elif axis == 1:
            center = anchor.location.y
        else:
            center = anchor.location.z

    print(f"center: {center}")

    i = 0
    for o in objects:
        if axis == 0:
            o.location.x = center
        elif axis == 1:
            o.location.y = center
        else:
            o.location.z = center
        i += 1

    print("Alignment operation completed!")


def align_selected_objects_along_x():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(0, top_level_objects, anchor=bpy.context.active_object)


def align_selected_objects_along_scene_origin_x():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(0, top_level_objects)


def align_selected_objects_along_y():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(1, top_level_objects, anchor=bpy.context.active_object)


def align_selected_objects_along_scene_origin_y():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(1, top_level_objects)


def align_selected_objects_along_z():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(2, top_level_objects, anchor=bpy.context.active_object)


def align_selected_objects_along_scene_origin_z():
    top_level_objects = get_parent_objects_in_selection()
    __align_objects_along_axis(2, top_level_objects)


# Align Mode:
# OPT_1 = Negative Sides
# OPT_2 = Centers
# OPT_3 = Positive Sides
ALIGN_MODE_NEGATIVE_SIDES = "OPT_1"
ALIGN_MODE_CENTERS = "OPT_2"
ALIGN_MODE_POSITIVE_SIDES = "OPT_3"

# Relative To:
# OPT_1 = World Origin
# OPT_2 = 3D Cursor
# OPT_3 = Selection
# OPT_4 = Active
ALIGN_RELATIVE_TO_WORLD_ORIGIN = "OPT_1"
ALIGN_RELATIVE_TO_3D_CURSOR = "OPT_2"
ALIGN_RELATIVE_TO_SELECTION = "OPT_3"
ALIGN_RELATIVE_TO_ACTIVE = "OPT_4"


def align_negative_sides_to_world_z():
    bpy.ops.object.align(
        align_mode=ALIGN_MODE_NEGATIVE_SIDES,
        relative_to=ALIGN_RELATIVE_TO_WORLD_ORIGIN,
        align_axis={"Z"},
    )


def align_centers_to_world_xy():
    bpy.ops.object.align(
        align_mode=ALIGN_MODE_CENTERS,
        relative_to=ALIGN_RELATIVE_TO_WORLD_ORIGIN,
        align_axis={"X", "Y"},
    )


def align_centers_to_active_xy():
    bpy.ops.object.align(
        align_mode=ALIGN_MODE_CENTERS,
        relative_to=ALIGN_RELATIVE_TO_ACTIVE,
        align_axis={"X", "Y"},
    )


def align_centers_to_world_origin():
    bpy.ops.object.align(
        align_mode=ALIGN_MODE_CENTERS,
        relative_to=ALIGN_RELATIVE_TO_WORLD_ORIGIN,
        align_axis={"X", "Y", "Z"},
    )


#  bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')

#     Set the object’s origin, by either moving the data, or set to center of data, or use 3D cursor

#     Parameters:

#             type (enum in ['GEOMETRY_ORIGIN', 'ORIGIN_GEOMETRY', 'ORIGIN_CURSOR', 'ORIGIN_CENTER_OF_MASS', 'ORIGIN_CENTER_OF_VOLUME'], (optional)) –

#             Type

#                 GEOMETRY_ORIGIN Geometry to Origin – Move object geometry to object origin.

#                 ORIGIN_GEOMETRY Origin to Geometry – Calculate the center of geometry based on the current pivot point (median, otherwise bounding box).

#                 ORIGIN_CURSOR Origin to 3D Cursor – Move object origin to position of the 3D cursor.

#                 ORIGIN_CENTER_OF_MASS Origin to Center of Mass (Surface) – Calculate the center of mass from the surface area.

#                 ORIGIN_CENTER_OF_VOLUME Origin to Center of Mass (Volume) – Calculate the center of mass from the volume (must be manifold geometry with consistent normals).


# align_centers_to_world_origin()
# align_negative_sides_to_world_z()
