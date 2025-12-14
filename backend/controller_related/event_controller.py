class EventHandler:
    """
    Pure internal event dispatcher.
    Does NOT touch Socket.IO — only forwards events to registered callbacks.
    app.py registers listeners for events that need to be sent to frontend.
    """

    def __init__(self):
        self.listeners = {}

    def on(self, event_name: str, callback):
        """Register a callback for an event"""
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(callback)

    def dispatch_event(self, event_name: str, data: dict = {}):
        """
        Dispatch an event internally.
        """
        if event_name in self.listeners:
            for callback in self.listeners[event_name]:
                callback(data)