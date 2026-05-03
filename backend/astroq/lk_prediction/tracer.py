import threading

class GraphTracer:
    _active_tracer = threading.local()

    def __init__(self):
        self.hits = []
        self._active_count = 0

    def __enter__(self):
        self._active_count += 1
        if not hasattr(self._active_tracer, 'stack'):
            self._active_tracer.stack = []
        self._active_tracer.stack.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._active_count -= 1
        self._active_tracer.stack.pop()

    def hit(self, node_id):
        if self._active_count > 0:
            self.hits.append(node_id)

    @classmethod
    def current(cls):
        stack = getattr(cls._active_tracer, 'stack', [])
        if stack:
            return stack[-1]
        return None

def trace_hit(node_id):
    tracer = GraphTracer.current()
    if tracer:
        tracer.hit(node_id)
