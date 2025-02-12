import json

class queue():
    def __init__(self):
        self.busy = True # This should initalize to False when I'm done testing it
        self.q = self.load_queue()

    def load_queue(self):
        queue_file = open("flask_app/task_queue.json", "r")
        task_queue = json.load(queue_file)
        queue_file.close()
        return task_queue
    
    def save_queue(self):
        queue_file = open("flask_app/task_queue.json", "w")
        json.dump(self.q, queue_file)
        queue_file.close()
    
    def add(self, item):
        new_key = str(len(self.q))
        self.q[new_key] = item
        self.save_queue()
        return new_key
    
    def remove(self, key):
        removed = self.q.pop(key, None)
        return removed
    