import threading
import time
import pylsl
import PySimpleGUI as sg

import xml.etree.ElementTree as ET

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

winsize = (600, 600)

lsl_format_dict = {
1: 'cf_float32',
2: 'cf_double64',
3: 'cf_string',
4: 'cf_int32',
5: 'cf_int16',
6: 'cf_int8',
7: 'cf_int64',
0: 'cf_undefined'}

class ContinuousResolverThreaded:
    def __init__(self, resolve_time=1, callback_changed=None, forget_after=5):
        # Don't make the update period too short as this seems to lead to
        self.resolver = pylsl.ContinuousResolver(prop=None, value=None, pred=None, forget_after=forget_after)

        self.available_streams = dict()
        self.callback_changed = callback_changed
        self.resolve_time = resolve_time
        self.running = False

        self.thread = None

    def update_loop(self):
        while self.running:
            self.update()

    def update(self):
        # results = self.resolver.results()  # returns StreamInfo objects
        results = pylsl.resolve_streams(self.resolve_time)

        new = dict()
        for result in results:
            if result.name() not in self.available_streams:
                new_watcher = StreamWatcher(result)
                new[new_watcher.name()] = new_watcher

        deleted = dict()
        for name, watcher in self.available_streams.items():
            if name not in [r.name() for r in results]:
                deleted[name] = watcher

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
        logger.info(f"Starting Thread, looking for threads with resolve_time={self.resolve_time}s")
        self.running = True
        self.thread = threading.Thread(target=self.update_loop)
        self.thread.start()

    def stop(self):
        logger.info(f"Stopping Thread")
        self.running = False
        self.thread.join()


class StreamWatcher:
    def __init__(self, info):
        self.inlet = pylsl.StreamInlet(info)
        self.info = self.inlet.info()

    def name(self):
        # Mirror the common info interface
        return self.info.name()

    def __str__(self):
        return self.info.__str__()

class StreamText:
    def __init__(self, info=None):
        self._info = info
        self.text = sg.Text("EmptyNanana", visible=False, size=winsize)

    @property
    def info(self):
        return self._info

    def update_row(self):
        if self.info is not None:
            info = self.info
            name_line = f"{info.name()} {'('+info.source_id()+')' if len(info.source_id())>0 else ''} @{info.hostname()}"
            type_line = f"{info.type()} @{info.nominal_srate():.2f} Hz"
            channels_line = f"{info.channel_count()} channel{'s' if info.channel_count()>1 else ''} of format {lsl_format_dict[info.channel_format()]}"
            misc_line = f""
            xml_lines = f"{info.as_xml()}"
            t = '\n'.join([name_line, type_line, channels_line])
            desc = ET.fromstring(info.as_xml()).find('desc')
            desc_xml = ET.tostring(desc, encoding='unicode')
            if len(desc_xml)>10:
                tooltip_text = ET.tostring(desc, encoding='unicode')
                self.text.set_tooltip(tooltip_text)

                t += '\n'+desc_xml
            # t = f"{name_line}\n{type_line}\n{host_line}\n{channels_line}\n{xml_lines}"
            visible = True
        else:
            # tooltip_text = "No Tooltip Text"
            self.text.set_tooltip('')
            t = "Empty"
            visible = False

        t_xsize, t_ysize = max([len(l) for l in t.splitlines()]), len(t.splitlines())
        self.text.set_size(size=(t_xsize, t_ysize))
        self.text.update(t, visible=visible)

    @info.setter
    def info(self, info):
        print(f"setting info {info}")
        self._info = info
        self.update_row()

    def row(self):
        return [self.text]

checkbox_auto_update = sg.Checkbox("Auto update", default=True, enable_events=True, key='toggle_auto_update')
button_update = sg.Button("Update now", enable_events=True, key='button_update_now')

num_stream_elements = 10
stream_texts = [StreamText(info=None) for i in range(num_stream_elements)]
streams_column = sg.Column([stream_text.row() for stream_text in stream_texts], scrollable=True, vertical_scroll_only=True, expand_x=True, expand_y=True)


def update_stream_rows(results, new, deleted):
    num_available_streams = len(continuous_resolver.available_streams.values())
    for i, stream_text in enumerate(stream_texts):
        if i < num_available_streams:
            stream_watcher = list(continuous_resolver.available_streams.values())[i]
            stream_text.info = stream_watcher.info
        else:
            stream_text.info = None

# Define the window's contents
layout = [[streams_column],
          [checkbox_auto_update, button_update]]

# Create the window
sg.theme('DarkAmber')   # Add a touch of color
window = sg.Window('LSL Monitor', layout, size=winsize)
window.read(timeout=500)

continuous_resolver = ContinuousResolverThreaded(forget_after=1, callback_changed=update_stream_rows)
if checkbox_auto_update.get:
    continuous_resolver.start()

# Display and interact with the Window using an Event Loop
while True:
    event, values = window.read(timeout=100)
    # See if user wants to quit or window was closed
    # print(event)
    if event == checkbox_auto_update.Key:
        auto_update = checkbox_auto_update.get()
        if auto_update:
            continuous_resolver.start()
        else:
            continuous_resolver.stop()
    elif event == button_update.Key:
        continuous_resolver.update()
    elif event == sg.WINDOW_CLOSED or event == 'Quit':
        break
    # streams_column.layout(stream_rows)
    streams_column.contents_changed()
    # Output a message to the window
    # window['-OUTPUT-'].update('Hello ' + values['-INPUT-'] + "! Thanks for trying PySimpleGUI")

# Finish up by removing from the screen
window.close()