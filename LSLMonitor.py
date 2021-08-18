import logging
import threading
import webbrowser

import PySimpleGUI as sg
import xmltodict

import pylsl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

info_url = r"https://github.com/jzerfowski/LSLMonitor"

winsize = (600, 600)
num_stream_elements = 50  # This is the maximum number of streams that can be shown, due to limitations of PySimpleGUI
resolve_time = 1


class ContinuousResolverThreaded:
    """
    Continuously try to resolve streams on the network. Unfortunately ContinuousResolver from pylsl seemed
    to lose the streams every now and then so we replicate the behaviour by just searching for some time
    """

    def __init__(self, resolve_time, callback_changed=None):
        self.available_streams = dict()
        self.callback_changed = callback_changed
        self.resolve_time = resolve_time
        self.running = False

        self.thread = None

    def update_loop(self):
        while self.running:
            self.update()

    def update(self):
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
        logger.info(f"Starting Thread, looking for streams with resolve_time={self.resolve_time}s")
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
        # Mirror the common info interface so we can compare against info.name() from resolved StreamInfo instances
        return self.info.name()

    def __str__(self):
        return self.info.__str__()


class StreamText:
    def __init__(self, index, info=None):
        self._info = info
        self.text = sg.Text("", visible=False, size=winsize, key=f"-TXT_STREAMTEXT{index}")

    def update_row(self):
        """
        Automatically update stream information derived from self.info
        :return:
        """
        if self.info is not None:
            info = xmltodict.parse(self.info.as_xml())['info']

            name_line = f"{info['name']} {'(' + info['source_id'] + ')' if len(info['source_id']) > 0 else ''} {info['hostname']}{'@' + info['v4address'] if info['v4address'] is not None else ''}:{info['v4data_port']}/{info['v4service_port']}"
            type_line = f"{info['type']} @{float(info['nominal_srate']):.2f} Hz"
            channels_line = f"{info['channel_count']} channel{'s' if int(info['channel_count']) > 1 else ''} ({info['channel_format']})"
            more_info_line = f"Created at {float(info['created_at']):.3f}, Version {float(info['version']):.1f}"
            # Construct a complex string to show all information that are contained in the stream's description
            t_desc = ""
            if 'desc' in info and info['desc'] is not None:
                desc_dict = info['desc']
                t_desc = ""
                if 'channels' in desc_dict:
                    t_channels = ""
                    t_channels = "\tChannels:\n"
                    for channel in desc_dict['channels']['channel']:
                        t_channels += '\t\t'
                        t_channels += ', '.join(f"{key}: {value}" for key, value in channel.items())
                        t_channels += '\n'
                    t_desc += t_channels

                t_desc += "\tOther info:\n"
                for key, value in desc_dict.items():
                    if key != 'channels':
                        t_desc += f"\t\t{key}: {value}\n"

            t = '\n'.join([name_line, type_line, channels_line, more_info_line, t_desc])
            t += '\n'
            visible = True
        else:
            t = "Empty"
            visible = False

        t_xsize, t_ysize = max([len(l) for l in t.splitlines()]), len(t.splitlines())
        self.text.set_size(size=(t_xsize, t_ysize))
        self.text.update(t, visible=visible)

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, info):
        print(f"setting info {info}")
        self._info = info
        self.update_row()

    def row(self):
        return [self.text]


# Definition of important GUI Elements
checkbox_auto_update = sg.Checkbox("Auto update", default=True, enable_events=True, key='-CHK_UPDATE_NOW-')
button_update = sg.Button("Update now", enable_events=True, key='-BTN_UPDATE_NOW-')
text_count_streams_available = sg.Text("No streams found", key='-TXT_COUNT_STREAMS-')
text_more_info = sg.Text("More information", key='-TXT_MORE_INFO-', enable_events=True, justification='right',
                         tooltip="Opens in Browser")

# Define the GUI elements that show stream information
stream_texts = [StreamText(i, info=None) for i in range(num_stream_elements)]
streams_column = sg.Column([stream_text.row() for stream_text in stream_texts], scrollable=True, expand_x=True,
                           expand_y=True)

# Define the window's contents
layout = [[streams_column],
          [checkbox_auto_update, button_update, text_count_streams_available, text_more_info]]

# Create the window
sg.theme('DarkAmber')  # Add a touch of color
window_icon_base64 = b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAD7AAAA+wFieMcIAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAdxJREFUWIXt1r9rFEEUB/DP6UnEpAkmUfBHIwhiYSEIgoVFCgsb7W0sg9qI+AdoJyKIFioWWghax0KEVIKF4i8EQYMgBiFiPD1QRCOxmE242+xedufIbuMXhoU3733fd2fezBtqRgMHcBVDFeduYwJeYqGm8aKJjYminfiyav/bjRG8xUizw/gNrYoELOVdU1HCXNQuoJljH8cHvMuZ34RDGMMsXuNZB+cRPBS2dUXMCBU52mF7glM5/kfxHZO4hvv4gcvJ/FDCt6dHztHEZyZvBfLQwHWcSb6LGMa+klwoXwMDSbLZlL2FBzECyq7AL9zDLdwRtuqpUAMLMQJiTsExYQu24xxeCZfK/qoEzOMGDmMrdmA6sa26gAGsS9ne47buU1QYvWpgG/ambG2hBi7gMT5iN07jbsp3V4r/J95kJcq6B6bwNWNsxiXhr+eTuE84L6wODObETnXwL90DeQKKYC02lIxZJqCfXvBXWNa+UHsz+i+giTlsweca8s81cBA3hSZTFHm+ZZ50LRwv4d+F35a/cP/EEMXWQFZcFFdM0KBwCWVxra9CwNkecyfLkjUK+EwIhTosXKG93nrwXDhZbTwSekdfWOwVMWN6JfIiT7KLOBEhHK5ExlWHfztEkAY+nHB8AAAAAElFTkSuQmCC'
window = sg.Window('LSL Monitor', layout, size=winsize, icon=window_icon_base64)
window.read(timeout=100)  # Read window to initialize all GUi elements


# Callback method for continuous_resolver
def update_stream_rows(results, new, deleted):
    num_available_streams = len(continuous_resolver.available_streams.values())

    text_count_streams_available.update(
        f"{num_available_streams if num_available_streams else 'No'} streams found")

    for i, stream_text in enumerate(stream_texts):
        if i < num_available_streams:
            stream_watcher = list(continuous_resolver.available_streams.values())[i]
            stream_text.info = stream_watcher.info
        else:
            stream_text.info = None


continuous_resolver = ContinuousResolverThreaded(resolve_time=resolve_time, callback_changed=update_stream_rows)
if checkbox_auto_update.get:
    continuous_resolver.start()

# Display and interact with the Window using an Event Loop
while True:
    event, values = window.read(timeout=100)

    # Check what the event is
    if event == checkbox_auto_update.Key:
        auto_update = checkbox_auto_update.get()
        if auto_update:
            continuous_resolver.start()
        else:
            continuous_resolver.stop()
    elif event == text_more_info.Key:
        webbrowser.open(info_url)
    elif event == button_update.Key:
        continuous_resolver.update()
    elif event == sg.WINDOW_CLOSED or event == 'Quit':
        break

    streams_column.contents_changed()

# Finish up by removing from the screen
window.close()
continuous_resolver.stop()
