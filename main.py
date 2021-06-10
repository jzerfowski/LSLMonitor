import threading
import time
import pylsl
import PySimpleGUI as sg

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


sg.theme('DarkAmber')   # Add a touch of color

class ContinuousResolverThreaded(pylsl.ContinuousResolver):
    def __init__(self, update_period=0.1, callback_changed=None, prop=None, value=None, pred=None, forget_after=5.0):
        self.available_streams = dict()
        self.callback_changed = callback_changed
        self.update_period = update_period
        self.running = False

        super().__init__(prop=prop, value=value, pred=pred, forget_after=forget_after)
        self.thread = threading.Thread(target=self.update_loop)
        self.start()

    def update_loop(self):

        while self.running:
            self.update()
            time.sleep(self.update_period)

    def update(self):
        results = self.results()  # returns StreamInfo objects

        new = dict()
        for result in results:
            if result.name() not in self.available_streams:
                new_watcher = StreamWatcher(result)
                new[new_watcher.name()] = new_watcher

        deleted = dict()
        for name, watcher in self.available_streams.items():
            if name not in [r.name() for r in results]:
                deleted[name] = watcher

        # new = [StreamWatcher(result) for result in results if result.name() not in [s.name() for s in self.available_streams]]
        # deleted = [s for s in self.available_streams if s.name() not in [r.name() for r in results]]

        if len(new) > 0:
            logger.info(f"New streams found: {new}")
        if len(deleted) > 0:
            logger.info(f"Streams deleted: {deleted}")

        [self.available_streams.pop(name) for name in deleted.keys()]
        self.available_streams.update(new)

        if len(new) + len(deleted) > 0:
            if self.callback_changed is not None:
                self.callback_changed(results, new, deleted)

    def start(self):
        self.running = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

class StreamWatcher:
    def __init__(self, info):
        self.info = info

    def text(self):
        t = f"""
        Name: {self.name()}\n
        Info: {self.info.to_xml()}\n        
        """

    def layout(self):
        return [sg.Text(self.text)]

    def name(self):
        # Mirror the common info interface
        return self.info.name()

    def __str__(self):
        return self.info.__str__()


continuous_resolver = ContinuousResolverThreaded(forget_after=1)


# Define the window's contents
layout = [[sg.Text("What's your name?\nNewline\tTest")],
          [sg.Input(key='-INPUT-')],
          [sg.Text(size=(40,1), key='-OUTPUT-')],
          [sg.Button('Ok'), sg.Button('Quit')],
          [sg.Checkbox("Auto update", default=True)]]

# Create the window
window = sg.Window('LSL Monitor', layout)

# Display and interact with the Window using an Event Loop
while True:
    event, values = window.read()
    # See if user wants to quit or window was closed
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break
    layout = [w.layout for w in continuous_resolver.available_streams.values()]
    window.layout(layout)
    # Output a message to the window
    # window['-OUTPUT-'].update('Hello ' + values['-INPUT-'] + "! Thanks for trying PySimpleGUI")

# Finish up by removing from the screen
window.close()