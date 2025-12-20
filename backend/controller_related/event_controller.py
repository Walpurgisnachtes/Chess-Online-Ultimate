class EventHandler:
    def __init__(self):
        self.listeners = {
            "capture": {}, 
            "bubble": {}
        }

    def on(self, event_name: str, callback, once: bool = False, capture: bool = False):
        """
        Register a callback.
        If capture=True, it fires during the first phase of dispatch.
        """
        phase = "capture" if capture else "bubble"
        
        if event_name not in self.listeners[phase]:
            self.listeners[phase][event_name] = []
        
        self.listeners[phase][event_name].append({
            "callback": callback,
            "once": once
        })

    def remove(self, event_name: str, callback=None, capture=None):
        """
        Remove listeners for `event_name`.

        Args:
            event_name: The event to clean up.
            callback: If provided, only this callback is removed.
            capture: 
                - True  -> inspect capture phase only
                - False -> inspect bubble phase only
                - None  -> inspect both phases (default)
        """
        phases = ["capture", "bubble"] if capture is None else \
                    ["capture"] if capture else ["bubble"]

        for phase in phases:
            if event_name not in self.listeners[phase]:
                continue

            if callback is None:
                # Remove entire event entry
                del self.listeners[phase][event_name]
                continue

            filtered = [
                listener for listener in self.listeners[phase][event_name]
                if listener["callback"] is not callback
            ]

            if filtered:
                self.listeners[phase][event_name] = filtered
            else:
                del self.listeners[phase][event_name]

    def dispatch_event(self, event_name: str, data: dict = {}):
        """
        1. Executes 'capture' listeners first.
        2. Executes 'bubble' listeners second.
        3. Cleans up 'once' listeners from both.
        """
        # Phase 1: Capture (Global/Interceptors)
        self._execute_phase("capture", event_name, data)
        
        # Phase 2: Bubble (Standard/Targeted)
        self._execute_phase("bubble", event_name, data)

    def _execute_phase(self, phase: str, event_name: str, data: dict):
        if event_name not in self.listeners[phase]:
            return

        remaining = []
        # Use a copy to avoid mutation errors
        for listener in self.listeners[phase][event_name]:
            listener["callback"](data)
            
            if not listener["once"]:
                remaining.append(listener)
        
        self.listeners[phase][event_name] = remaining