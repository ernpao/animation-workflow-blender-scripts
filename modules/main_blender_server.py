from class_task_queue import *
from flask import Flask, json, request

# from flask_cors import CORS, cross_origin

api = Flask(__name__)
# cors = CORS(api)
# api.config["CORS_HEADERS"] = "Content-Type"
task_queue = TaskQueue()
task_queue.clear()

from functions_distribute import *


@api.route("/", methods=["GET"])
def get_index():
    return json.dumps(
        {
            "app": "Blender Automation Server",
            "success": True,
        }
    )


@api.route("/tasks", methods=["POST"])
# @cross_origin()
def post_blender():
    return process_post_request()


def process_post_request():
    json_ = request.get_json()
    print(json_)
    command = json_["command"].replace('"', "")
    print(command)

    task_queue.clear()
    task = Task(name=command)

    if command == "align":
        task.set_value(key="relative_to", value=json_["relative_to"])
        task.set_value(key="mode", value=json_["mode"])
        task.set_value(key="axis", value=json_["axis"])

    if command == "distribute":
        task.set_value(key="axis", value=json_["axis"])

    success = task_queue.enqueue_task(task)

    return json.dumps({"success": success})


def start_server():
    print("Starting automation server...")
    api.run(
        host="192.168.50.10",
        port=48912,
        debug=True,
    )


if __name__ == "__main__":
    start_server()
