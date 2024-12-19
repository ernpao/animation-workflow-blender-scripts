import json
from typing import Optional

import bpy
from database.database import DatabaseQueue
from functions_distribute import *
from functions_scene import *


class Task:
    name: str
    __data: any

    def __init__(self, name: str) -> None:
        # self.__data = json.loads(json_str)
        # self.name = self.__data["name"]
        self.name = name
        self.__data = json.loads(f'{{"name": "{name}"}}')
        pass

    def get_value(self, key: str):
        return self.__data[key]

    def set_value(self, key: str, value):
        self.__data[key] = value

    def json(self):
        return json.dumps(self.__data)


class TaskQueue(DatabaseQueue):
    def __init__(self) -> None:
        super().__init__(
            table_name="task_queue",
            primary_key_name="tq_id",
            value_column_name="tq_data",
        )

    def enqueue_task(self, task: Task) -> bool:
        # json_str = f'{{"name": "{task_name}"}}'
        json_str = task.json()
        # print(json_str)
        self.enqueue(json_str)
        return True

    def enqueue_task_name(self, task_name: str) -> bool:
        task = Task(task_name)
        return self.enqueue_task(task)

    def dequeue_task(self) -> Optional[Task]:
        last_entry = self.dequeue()
        if last_entry is not None:
            print(f"Last entry: {last_entry}")
            json_obj = json.loads(last_entry)
            task = Task(json_obj["name"])

            for key in json_obj:
                value = json_obj[key]
                task.set_value(key, value)

            return task
        else:
            return None

    def has_tasks(self) -> bool:
        return not self.is_empty()


class CF_Task_Dequeue(bpy.types.Operator):
    bl_idname = "custom_functions.task_dequeue"
    bl_label = "Custom Function: Task Dequeue"
    bl_description = "Dequeue the most recent task in the database."
    # size: bpy.props.IntProperty()

    def __process_align_task(self, task: Task):
        relative_to = task.get_value("relative_to")
        mode = task.get_value("mode")
        axis = task.get_value("axis")

        bpy.ops.object.align(
            align_mode=mode,
            align_axis={axis},
            relative_to=relative_to,
        )

    def __process_distribute_task(self, task: Task):
        axis = task.get_value("axis")

        if axis == "X":
            distribute_selected_objects_along_x()

        if axis == "Y":
            distribute_selected_objects_along_y()

        if axis == "Z":
            distribute_selected_objects_along_z()

    def execute(self, context):
        queue = TaskQueue()

        if queue.has_tasks():
            task = queue.dequeue_task()
            print(f"Task Dequeued: {task.name}")

            if task.name == "align":
                self.__process_align_task(task)

            if task.name == "distribute":
                self.__process_distribute_task(task)

        else:
            print("No tasks enqueued.")

        return {"FINISHED"}


if __name__ == "__main__":
    task_queue = TaskQueue()
    task_queue.clear()

    task = Task("Test")
    task.set_value("Test_Value", 9999)

    task_queue.enqueue_task(task)
    task = task_queue.dequeue_task()
    print(f"Task name is: {task.name}")
