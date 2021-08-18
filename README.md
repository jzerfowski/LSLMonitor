# LSLMonitor
Small application to update and show available LabStreamingLayer ([LSL](https://labstreaminglayer.readthedocs.io/))
streams on the network. Updates every seconds (`resolve_time`) and shows all relevant information in a window.

## Requirements
- [pylsl](https://github.com/labstreaminglayer/liblsl-Python)
- [PySimpleGUI](https://pysimplegui.readthedocs.io/en/latest/)
- [xmltodict](https://github.com/martinblech/xmltodict)

## Standalone build
A standalone executable can be found in [dist/LSLMonitor.exe](/dist/LSLMonitor.exe). It is generated from a virtual environment (see [requirements.txt](requirements.txt)) by executing
```shell
pyinstaller LSLMonitor.spec
```
