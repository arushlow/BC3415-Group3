from gunicorn.app.base import BaseApplication

from wsgi import app


def run_server():
    class WSGIApplication(BaseApplication):
        def __init__(self, app, options=None):
            self.application = app
            self.options = options or {}
            super().__init__()
            
        def load_config(self):
            for key, value in self.options.items():
                if key in self.cfg.settings and value is not None:
                    self.cfg.set(key, value)
                    
        def load(self):
            return self.application
    
    options = {
        'bind': '127.0.0.1:8000',
        'workers': 1,
        'worker_class': 'gevent',
        'timeout': 120,
        'keepalive': 5,
        'max_requests': 1000,
        'max_requests_jitter': 200,
        'preload_app': True,
    }
    
    WSGIApplication(app, options).run()


if __name__ == "__main__":
    run_server()
