from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import uuid
from urllib.parse import urlparse

TASKS_FILE = "tasks.json"


class Task:
    def __init__(self, title, priority, isDone=False, id=None):
        self.title = title
        self.priority = priority
        self.isDone = isDone
        self.id = id if id else str(uuid.uuid4())

    def to_dict(self):
        return {
            "title": self.title,
            "priority": self.priority,
            "isDone": self.isDone,
            "id": self.id
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["title"], data["priority"], data["isDone"], data["id"])


class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, "r") as f:
                    data = json.load(f)
                    self.tasks = {task["id"]: Task.from_dict(
                        task) for task in data}
            except json.JSONDecodeError:
                self.tasks = {}
                print("Error upload file")

    def save_tasks(self):
        with open(TASKS_FILE, "w") as f:
            json.dump([task.to_dict()
                      for task in self.tasks.values()], f, indent=4)

    def create_task(self, title, priority):
        new_task = Task(title=title, priority=priority)
        self.tasks[new_task.id] = new_task
        self.save_tasks()
        return new_task

    def get_all_tasks(self):
        return [task.to_dict() for task in self.tasks.values()]

    def complete_task(self, task_id):
        if task_id in self.tasks:
            self.tasks[task_id].isDone = True
            self.save_tasks()
            return True
        return False


class TaskHandler(BaseHTTPRequestHandler):
    task_manager = TaskManager()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == "/tasks":
            tasks = TaskHandler.task_manager.get_all_tasks()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(tasks).encode())
        else:
            self.send_error(404)

    def do_POST(self):
        parsed_url = urlparse(self.path)

        if parsed_url.path == "/tasks":
            content_len = int(self.headers.get('Content-Length', 0))
            if content_len == 0:
                self.send_error(400, "Body Not Found")
                return

            content = self.rfile.read(content_len).decode("utf-8")
            try:
                data = json.loads(content)
                title = data.get("title")
                priority = data.get("priority")
                if not title or not priority:
                    self.send_error(400, "Missing required argument")
                    return

                new_task = TaskHandler.task_manager.create_task(
                    title, priority)
                self.send_response(201)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(new_task.to_dict()).encode())

            except json.JSONDecodeError:
                self.send_error(400, "Error JSON")

        elif parsed_url.path.startswith("/tasks/") and parsed_url.path.endswith("/complete"):
            path_parts = parsed_url.path.split("/")
            if len(path_parts) == 4 and path_parts[2]:
                task_id = path_parts[2]
                print(task_id)
                if TaskHandler.task_manager.complete_task(task_id):
                    self.send_response(200)
                    self.end_headers()
                else:
                    self.send_error(404, 'task Not Found')
            else:
                self.send_error(400, "ID Not Found")

        else:
            self.send_error(404)


def run(handler_class=BaseHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


if __name__ == '__main__':
    run(handler_class=TaskHandler)
