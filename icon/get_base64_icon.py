import base64

icon_filename = 'LSLMonitor_icon.png'

contents = open(icon_filename, 'rb').read()

encoded = base64.b64encode(contents)

print(str(encoded))