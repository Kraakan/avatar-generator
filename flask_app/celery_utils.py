from celery import current_app as current_celery_app


def make_celery(app):
    celery = current_celery_app
    celery.config_from_object(app.config, namespace="CELERY")

    return celery

def init_celery(app, celery):
    """Add flask app context to celery.Task"""
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask