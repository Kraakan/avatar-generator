import json
import subprocess

class task():
    def __init__(self, user:str, task_type:str, path:str, prompt:str, name:str, command = None, model_id=-1):
        self.user = user
        self.type = task_type
        self.path = path
        self.prompt = prompt
        self.name = name
        self.command = command
        self. model_id = model_id
        self.status = None
    
    def save(self):
        return_dict = {
            "user" : self.user,
            "type" : self.type,
            "path" : self.path,
            "prompt" : self.prompt,
            "name" : self.name,
            "command" : self.command,
            "status" : self.status,
            "model_id": self.model_id
        }
        return return_dict

class queue():
    def __init__(self):
        self.running = None
        self.q = self.load_queue()
        self.process = None

    def load_queue(self):
        queue_file = open("flask_app/task_queue.json", "r")
        task_queue = json.load(queue_file)
        queue_file.close()
        return task_queue
    
    def save_queue(self):
        queue_file = open("flask_app/task_queue.json", "w")
        json.dump(self.q, queue_file, indent=4)
        queue_file.close()
    
    def queue_task(self, user, task_type, path, prompt = "Placeholder Prompt", name="Placeholder Name", command = None, model_id=None):
        new_task = task(user, task_type, path, prompt, name, command, model_id)
        new_key = "0"
        for key in self.q.keys():
            new_key = str(int(key) + 1)
        self.q[new_key] = new_task.save()
        self.save_queue()
        if self.running != None:
            return new_key
        else: # TODO: Move this code to a method that can also run things from the queue
            self.running = new_key
            process = subprocess.Popen(new_task.command, stdout=subprocess.PIPE, universal_newlines=True) # TODO: Re-jigger image generateion to run as a subprocess
            self.track_process(process)
    
    def remove_task(self, key):
        removed = self.q.pop(key, None)
        self.save_queue()
        return removed
    
    def track_process(self, process):
        self.process = process
    
    def poll_process(self):
        if self.process == None:
            return 0
        result = self.process.poll()
        self.q[self.running]["status"] = result
        self.save_queue()
        return result
    
    def get_output(self):
        if self.process == None:
            return None
        result = self.process.communicate()
        return result
    
    def get_task_entry(self, task_key):
        if task_key not in self.q.keys():
            return None
        else:
            task_type = self.q[task_key]["type"]
            if  task_type == "model tuning":
                model_data = self.q[task_key]
                user = model_data["user"]
                new_model_dir = model_data["path"]
                prompt = model_data["prompt"]
                name = model_data["name"]
                return task_type, task_key, user, new_model_dir, prompt, name
            
            if  task_type == "image generation":
                image_data = self.q[task_key]
                user = image_data["user"]
                image_path = image_data["path"]
                prompt = image_data["prompt"]
                model_id = image_data["model_id"]
                return task_type, task_key, user, image_path, prompt, model_id

    

    
    def enter_image(self):
        new_image_entry = models.Generated_image(user_id = model.user_id, model_id = model.id, promt = prompt, filename = image_name)
        print(new_image_entry)
        db.session.add(new_image_entry)
        db.session.commit()