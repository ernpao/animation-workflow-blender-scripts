import bpy
from class_task_queue import CF_Task_Dequeue
from functions_distribute import *
from functions_orientation import *
from main_blender_server import *

# blender_version = getattr(bpy.app, "version")

bl_info = {
    "name": "Blender Plugin",
    "author": "Ernest Epistola",
    "version": (0, 0, 1),
    # "blender": (3, 5, 1),
    # "blender": (4, 0, 2),
    "location": "3D View > Properties > Object Alignment",
}

bl_info["blender"] = getattr(bpy.app, "version")


class Addon_Panel(bpy.types.Panel):
    bl_idname = "CF_PT_layout"
    bl_label = "Custom Function: Object Alignment"
    bl_category = "Object Alignment"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout

        # ----- ALIGN ----- #
        layout.label(text="Align Selected:")

        row = layout.row()
        row.operator("custom_functions.align_x", text="X")
        row.operator("custom_functions.align_y", text="Y")
        row.operator("custom_functions.align_z", text="Z")
        row = layout.row(align=True)

        row = layout.row()
        row.operator(
            "custom_functions.align_negative_sides_to_world_z",
            text="Negative Sides To World Z",
        )
        row = layout.row(align=True)

        row = layout.row()
        row.operator(
            "custom_functions.orient_to_ground",
            text="Orient To Ground",
        )
        row = layout.row(align=True)

        # ----- DISTRIBUTE ----- #
        layout.label(text="Distribute Selected:")

        row = layout.row()
        row.operator("custom_functions.distribute_x", text="X")
        row.operator("custom_functions.distribute_y", text="Y")
        row.operator("custom_functions.distribute_z", text="Z")
        row = layout.row(align=True)

        # ----- MOVE ----- #

        layout.label(text="Move Selected:")

        row = layout.row()
        row.operator(
            "custom_functions.align_centers_to_world_origin",
            text="To World Origin",
        )
        row.operator(
            "custom_functions.align_centers_to_world_xy",
            text="To World XY",
        )
        row.operator(
            "custom_functions.align_centers_to_active_xy",
            text="To Active XY",
        )
        row = layout.row(align=True)

        # ----- ROTATE ----- #

        layout.label(text="Rotate Selected By 90 Degrees:")

        layout.label(text="Along X Axis:")
        row = layout.row()
        row.operator(
            "custom_functions.rotate_x_90_ccw",
            # text="<",
            text="Rotate 90 Degrees CCW (X)",
            icon="TRIA_LEFT",
        )
        row.operator(
            "custom_functions.rotate_x_90_cw",
            # text=">",
            text="Rotate 90 Degrees CW (X)",
            icon="TRIA_RIGHT",
        )

        layout.label(text="Along Y Axis:")
        row = layout.row()
        row.operator(
            "custom_functions.rotate_y_90_ccw",
            # text="<",
            text="Rotate 90 Degrees CCW (Y)",
            icon="TRIA_LEFT",
        )
        row.operator(
            "custom_functions.rotate_y_90_cw",
            # text=">",
            text="Rotate 90 Degrees CW (Y)",
            icon="TRIA_RIGHT",
        )

        layout.label(text="Along Z Axis:")
        row = layout.row()
        row.operator(
            "custom_functions.rotate_z_90_ccw",
            # text="<",
            text="Rotate 90 Degrees CCW (Z)",
            icon="TRIA_LEFT",
        )
        row.operator(
            "custom_functions.rotate_z_90_cw",
            # text=">",
            text="Rotate 90 Degrees CW (Z)",
            icon="TRIA_RIGHT",
        )
        row = layout.row(align=True)


class CF_Align_X(bpy.types.Operator):
    bl_idname = "custom_functions.align_x"
    bl_label = "Custom Function: Align Selected Along X"
    bl_description = "Align selected objects along the X axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_selected_objects_along_x()
        return {"FINISHED"}


class CF_Align_Y(bpy.types.Operator):
    bl_idname = "custom_functions.align_y"
    bl_label = "Custom Function: Align Selected Along Y"
    bl_description = "Align selected objects along the Y axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_selected_objects_along_y()
        return {"FINISHED"}


class CF_Align_Z(bpy.types.Operator):
    bl_idname = "custom_functions.align_z"
    bl_label = "Custom Function: Align Selected Along Z"
    bl_description = "Align selected objects along the Z axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_selected_objects_along_z()
        return {"FINISHED"}


class CF_Align_Centers_To_World_Origin(bpy.types.Operator):
    bl_idname = "custom_functions.align_centers_to_world_origin"
    bl_label = "Custom Function: Move Selected To The World Origin"
    bl_description = "Align centers of selected objects to the world origin."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_centers_to_world_origin()
        return {"FINISHED"}


class CF_Align_Centers_To_World_XY(bpy.types.Operator):
    bl_idname = "custom_functions.align_centers_to_world_xy"
    bl_label = "Custom Function: Align Selected To World XY"
    bl_description = "Align centers of selected objects to the world XY."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_centers_to_world_xy()
        return {"FINISHED"}


class CF_Align_Centers_To_Active_XY(bpy.types.Operator):
    bl_idname = "custom_functions.align_centers_to_active_xy"
    bl_label = "Custom Function: Align Selected To Active XY"
    bl_description = "Align centers of selected objects to the active object's XY."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_centers_to_active_xy()
        return {"FINISHED"}


class CF_Align_Negative_Sides_To_World_Z(bpy.types.Operator):
    bl_idname = "custom_functions.align_negative_sides_to_world_z"
    bl_label = "Custom Function: Align Selected Negative Sides To World Z"
    bl_description = "Align negative side of selected objects to the world Z axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        align_negative_sides_to_world_z()
        return {"FINISHED"}


class CF_Orient_To_Ground(bpy.types.Operator):
    bl_idname = "custom_functions.orient_to_ground"
    bl_label = "Custom Function: Orient To Ground"
    bl_description = "Align negative side of selected objects to the world Z axis and set object origin to footprint center."
    size: bpy.props.IntProperty()

    def execute(self, context):
        orient_selected_objects_to_ground()
        return {"FINISHED"}


class CF_Distribute_X(bpy.types.Operator):
    bl_idname = "custom_functions.distribute_x"
    bl_label = "Custom Function: Distribute Selected Along X"
    bl_description = "Distribute selected objects along the X axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        distribute_selected_objects_along_x()
        return {"FINISHED"}


class CF_Distribute_Y(bpy.types.Operator):
    bl_idname = "custom_functions.distribute_y"
    bl_label = "Custom Function: Distribute Selected Along Y"
    bl_description = "Distribute selected objects along the Y axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        distribute_selected_objects_along_y()
        return {"FINISHED"}


class CF_Distribute_Z(bpy.types.Operator):
    bl_idname = "custom_functions.distribute_z"
    bl_label = "Custom Function: Distribute Selected Along Z"
    bl_description = "Distribute selected objects along the Z axis."
    size: bpy.props.IntProperty()

    def execute(self, context):
        distribute_selected_objects_along_z()
        return {"FINISHED"}


# class CF_Server_Start(bpy.types.Operator):
#     bl_idname = "blender_server.start"
#     bl_label = "Custom Function: BLENDER_SERVER_START"
#     bl_description = "Start the automation server."
#     size: bpy.props.IntProperty()

#     def execute(self, context):
#         print("Test server")
#         start_server()
#         return {"FINISHED"}


class CF_Rotate_X_90_CCW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_x_90_ccw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Counter-Clockwise (X)"
    bl_description = (
        "Rotate selected objects counter-clockwise along the X axis by 90 degrees."
    )
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_ccw_x()
        return {"FINISHED"}


class CF_Rotate_X_90_CW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_x_90_cw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Clockwise (X)"
    bl_description = "Rotate selected objects clockwise along the X axis by 90 degrees."
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_cw_x()
        return {"FINISHED"}


class CF_Rotate_Y_90_CCW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_y_90_ccw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Counter-Clockwise (Y)"
    bl_description = (
        "Rotate selected objects counter-clockwise along the Y axis by 90 degrees."
    )
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_ccw_y()
        return {"FINISHED"}


class CF_Rotate_Y_90_CW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_y_90_cw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Clockwise (Y)"
    bl_description = "Rotate selected objects clockwise along the Y axis by 90 degrees."
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_cw_y()
        return {"FINISHED"}


class CF_Rotate_Z_90_CCW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_z_90_ccw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Counter-Clockwise (Z)"
    bl_description = (
        "Rotate selected objects counter-clockwise along the Z axis by 90 degrees."
    )
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_ccw_z()
        return {"FINISHED"}


class CF_Rotate_Z_90_CW(bpy.types.Operator):
    bl_idname = "custom_functions.rotate_z_90_cw"
    bl_label = "Custom Function: Rotate Selected 90 Degrees Clockwise (Z)"
    bl_description = "Rotate selected objects clockwise along the Z axis by 90 degrees."
    size: bpy.props.IntProperty()

    def execute(self, context):
        rotate_selected_90_degrees_cw_z()
        return {"FINISHED"}


class_list = [
    Addon_Panel,
    CF_Align_X,
    CF_Align_Y,
    CF_Align_Z,
    CF_Distribute_X,
    CF_Distribute_Y,
    CF_Distribute_Z,
    CF_Align_Centers_To_World_Origin,
    CF_Align_Centers_To_World_XY,
    CF_Align_Centers_To_Active_XY,
    CF_Align_Negative_Sides_To_World_Z,
    CF_Orient_To_Ground,
    CF_Rotate_X_90_CCW,
    CF_Rotate_X_90_CW,
    CF_Rotate_Y_90_CCW,
    CF_Rotate_Y_90_CW,
    CF_Rotate_Z_90_CCW,
    CF_Rotate_Z_90_CW,
    CF_Task_Dequeue,
    # CF_Server_Start,
]
registered_classes = []


def register():
    print("Registering classes...")
    for cls in class_list:
        bpy.utils.register_class(cls)
        registered_classes.append(cls)
    print("Classes registered!")


def unregister():
    for cls in registered_classes:
        bpy.utils.unregister_class(cls)
    del registered_classes[:]


if __name__ == "__main__":
    register()
