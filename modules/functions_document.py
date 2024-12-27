import os
import pathlib

import bpy

from modules.libs.python_helper_functions.functions_file import *


def document_save(filepath: str):
    bpy.ops.wm.save_as_mainfile(filepath=filepath)


def document_open(filepath: str, register_to_timer: bool = False):
    if register_to_timer:

        def open_file():
            bpy.ops.wm.open_mainfile(filepath=filepath)

        bpy.app.timers.register(open_file)

    else:
        bpy.ops.wm.open_mainfile(filepath=filepath)


def get_blend_files_in_directory(directory: str):
    return file_get_directory_items_by_extension(directory, ".blend")


def for_each_blend_file_in_directory(directory: str, callback):
    files = get_blend_files_in_directory(directory)
    for f in files:
        callback(f)


def document_open_location():
    if bpy.data.filepath:
        file_open_location(bpy.data.filepath)
