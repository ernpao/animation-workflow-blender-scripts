import os
import pathlib

import bpy


def document_save(filepath: str):
    bpy.ops.wm.save_as_mainfile(filepath=filepath)


def document_open(filepath: str, register_to_timer: bool = False):
    if register_to_timer:

        def open_file():
            bpy.ops.wm.open_mainfile(filepath=filepath)

        bpy.app.timers.register(open_file)

    else:
        bpy.ops.wm.open_mainfile(filepath=filepath)
