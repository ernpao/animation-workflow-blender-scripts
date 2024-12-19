import os
import pathlib

import bpy


# with bpy.types.Object as Object:
def set_active_object(o: bpy.types.Object):
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def for_each_scene_object(callback):
    scene_collection = bpy.context.scene.collection
    for o in scene_collection.all_objects:
        callback(o)
    return


def for_each_selected_object(callback):
    os = bpy.context.selected_objects
    for o in os:
        callback(o)
    return


def object_with_name_exists_in_scene(name: str) -> bool:
    scene_collection = bpy.context.scene.collection
    for o in scene_collection.all_objects:
        if o.name == name:
            return True
    return False


def count_objects_in_scene() -> int:
    return bpy.context.scene.collection.objects.__len__()


def remove_object(object):
    bpy.data.objects.remove(object, do_unlink=True)
    return


def deselect_all():
    def deselect(o):
        o.select_set(False)

    for_each_scene_object(deselect)


def remove_collection(
    collection: bpy.types.Collection,
    retain_collection_objects: bool = False,
):
    if retain_collection_objects:
        scene_collection = bpy.context.scene.collection
        for o in collection.all_objects:
            scene_collection.objects.link(o)
            collection.objects.unlink(o)
    else:
        for o in collection.all_objects:
            collection.objects.unlink(o)
            remove_object(o)

    bpy.data.collections.remove(collection, do_unlink=True)


def remove_scene_objects():
    object_list = []

    def __add_to_list(o):
        object_list.append(o)

    for_each_scene_object(__add_to_list)

    for o in object_list:
        remove_object(o)

    pass


def document_save(filepath: str):
    bpy.ops.wm.save_as_mainfile(filepath=filepath)


def document_open(filepath: str, register_to_timer: bool = False):
    if register_to_timer:

        def open_file():
            bpy.ops.wm.open_mainfile(filepath=filepath)

        bpy.app.timers.register(open_file)

    else:
        bpy.ops.wm.open_mainfile(filepath=filepath)


def get_all_object_names() -> list[str]:
    object_names = []

    def add_name(o):
        object_names.append(o.name)

    for_each_scene_object(add_name)
    return object_names


def get_object_by_name(name: str) -> bpy.types.Object | None:
    scene_collection = bpy.context.scene.collection
    for o in scene_collection.all_objects:
        if o.name == name:
            return o


def get_all_mesh_names() -> list[str]:
    mesh_names = []

    def add_name(o: bpy.types.Object):
        if o.type == "MESH":
            mesh_names.append(o.name)

    for_each_scene_object(add_name)
    return mesh_names


def duplicate_object(o: bpy.types.Object) -> bpy.types.Object | None:
    if o:
        deselect_all()
        o.select_set(True)
        bpy.ops.object.duplicate(linked=False, mode="TRANSLATION")

        # new duplicate object will be selected after the operation
        selected = get_selected_meshes()
        if selected.__len__() > 0:
            return selected[0]


def get_selected_meshes() -> list[bpy.types.Object]:
    return [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]


def get_parent_objects_in_selection() -> list[bpy.types.Object]:
    return [
        obj
        for obj in bpy.context.selected_objects
        if (obj.type == "MESH" and obj.parent == None)
    ]


def select_top_level_objects() -> list[bpy.types.Object]:
    # select empties in the scene
    bpy.ops.object.select_by_type(extend=False)
    objects = bpy.context.selected_objects

    top_level_objects = []
    # remove elements with children from selection
    for obj in objects:
        if len(obj.children) > 0 or obj.parent is None:
            obj.select_set(True)
            top_level_objects.append(obj)
        else:
            obj.select_set(False)

    return top_level_objects


def select_objects(objects: list[bpy.types.Object]):
    for o in objects:
        o.select_set(True)


def get_top_level_objects() -> list[bpy.types.Object]:
    result = select_top_level_objects()
    deselect_all()
    return result


def select_top_level_empty_objects() -> list[bpy.types.Object]:
    # select empties in the scene
    bpy.ops.object.select_by_type(extend=False, type="EMPTY")
    empties = bpy.context.selected_objects

    parent_empties = []
    # remove elements with children from selection
    for obj in empties:
        if len(obj.children) > 0:
            obj.select_set(True)
            parent_empties.append(obj)

    return parent_empties


def count_parent_empties():
    parent_empties = select_top_level_empty_objects()
    return len(parent_empties)


def file_exists(path: str) -> bool:
    return pathlib.Path(path).exists()


def origin_to_cursor():
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")


def get_all_children(o: bpy.types.Object) -> list[bpy.types.Object]:
    children = []

    for child in o.children:
        if child not in children:
            children.append(child)

        for subchild in get_all_children(child):
            children.append(subchild)

    return children


def select_object_and_children(o: bpy.types.Object):
    deselect_all()
    children = get_all_children(o)
    select_objects(children)
    set_active_object(o)
