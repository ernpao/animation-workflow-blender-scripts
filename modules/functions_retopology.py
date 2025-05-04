# Script intended to be run within Blender

import time  # Optional: for timing execution

import bpy


def check_context():
    """Checks if the context is suitable for retopology (Object Mode, mesh selected)."""
    if bpy.context.mode != "OBJECT":
        print("Error: Please switch to OBJECT mode to run retopology.")
        return None  # Require manual switch for clarity

    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        print("Error: No object selected.")
        return None

    mesh_objects = [obj for obj in selected_objects if obj.type == "MESH"]
    if not mesh_objects:
        print("Error: No MESH object selected.")
        return None

    # Ensure the active object is one of the selected meshes
    active_obj = bpy.context.view_layer.objects.active
    if not active_obj or active_obj.type != "MESH" or active_obj not in mesh_objects:
        # If active object isn't a selected mesh, make the first selected mesh active
        bpy.context.view_layer.objects.active = mesh_objects[0]
        print(f"Set active object to: {mesh_objects[0].name}")

    return bpy.context.view_layer.objects.active


def retopologize_selected(
    target_face_count=10000, use_mesh_symmetry=True, preserve_sharp=False, seed=0
):
    """
    Retopologizes the active mesh object using Blender's QuadriFlow algorithm.
    Mimics some basic ZRemesher functionality by wrapping Blender's tool.
    Prints face counts before and after the operation.

    IMPORTANT: This function requires Blender's Python environment (bpy)
               and operates on the active mesh object in OBJECT mode.

    Args:
        target_face_count (int): Desired number of faces in the output mesh.
        use_mesh_symmetry (bool): Use mesh symmetry axes if available.
        preserve_sharp (bool): Try to preserve sharp edges (marked edges).
        seed (int): Random seed for the algorithm, changing it gives different results.

    Returns:
        set: {'FINISHED'} on success, {'CANCELLED'} on failure or context error.
    """
    print("--- Starting Retopology ---")

    # 1. --- Context Check ---
    target_obj = check_context()
    if target_obj is None:
        print("Retopology cancelled due to incorrect context.")
        return {"CANCELLED"}

    # --- Get Original Face Count ---
    try:
        original_face_count = len(target_obj.data.polygons)
        print(f"Target object: {target_obj.name}")
        print(f"Original face count: {original_face_count}")  # Print before count
    except AttributeError:
        print("Error: Could not access mesh data (polygons) on target object.")
        return {"CANCELLED"}
    except Exception as e:
        print(f"Error getting original face count: {e}")
        return {"CANCELLED"}

    print(
        f"Settings: Target Faces={target_face_count}, Symmetry={use_mesh_symmetry}, "
        f"PreserveSharp={preserve_sharp}, Seed={seed}"
    )

    start_time = time.time()
    original_name = (
        target_obj.name
    )  # Store name as QuadriFlow often replaces the object

    # 2. --- Execute QuadriFlow ---
    try:
        # Ensure the target object is active and selected (check_context should handle active)
        bpy.ops.object.select_all(action="DESELECT")
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = target_obj  # Redundant but safe

        # Call the QuadriFlow operator
        bpy.ops.object.quadriflow_remesh(
            target_faces=target_face_count,
            use_mesh_symmetry=use_mesh_symmetry,
            use_preserve_sharp=preserve_sharp,
            seed=seed,
        )

        end_time = time.time()
        print(
            f"Retopology finished for '{original_name}' in {end_time - start_time:.2f} seconds."
        )

        # 3. --- Post-Processing & Get New Face Count ---
        new_obj = bpy.context.object  # The operator usually leaves the new mesh active
        if new_obj and new_obj.type == "MESH" and new_obj.data:
            # Rename the resulting object for clarity
            new_obj.name = f"{original_name}_Retopo"
            # --- Get New Face Count ---
            new_face_count = len(new_obj.data.polygons)
            print(f"Resulting mesh named: {new_obj.name}")
            print(f"New face count: {new_face_count}")  # Print after count
        elif new_obj:
            print(
                f"Warning: Retopology operator ran, but the result object '{new_obj.name}' doesn't seem to be a valid mesh."
            )
        else:
            print(
                "Warning: Retopology operator ran, but could not identify the resulting object."
            )
            print(f"(Target face count was {target_face_count}, but result is unknown)")

        print("--- Retopology Complete ---")
        return {"FINISHED"}

    except RuntimeError as e:
        print(f"Error during QuadriFlow execution: {e}")
        print(
            "Common issues: Very low poly input, non-manifold geometry, or extreme target face counts."
        )
        print(
            f"(Original face count was {original_face_count})"
        )  # Add original count to error context
        print("--- Retopology Failed ---")
        return {"CANCELLED"}
    except Exception as e:
        if "keyword" in str(e) and "unrecognized" in str(e):
            print(f"An API error occurred: {e}")
            print(
                "This likely means your Blender version doesn't support one of the parameters used."
            )
            print(
                "Try removing more parameters like 'use_preserve_sharp' if the error persists,"
            )
            print("or consider updating Blender to a newer version (2.93+).")
        else:
            print(f"An unexpected error occurred: {e}")
        print(
            f"(Original face count was {original_face_count})"
        )  # Add original count to error context
        print("--- Retopology Failed ---")
        return {"CANCELLED"}
