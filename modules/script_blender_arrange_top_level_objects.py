from functions_distribute import *
from functions_scene import *
from libs.python_helper_functions.functions_log import *

clear()
tlo = select_top_level_objects()
print(f"Top Level Objects Count: {len(tlo)}")

distribute_selected_meshes(set_object_centers=False, spacing_factor=1)


# select_top_level_empty_objects()
# distribute_selected_objects()

import bpy
