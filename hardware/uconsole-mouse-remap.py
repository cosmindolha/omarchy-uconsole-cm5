#!/usr/bin/python3
"""Keep uConsole motion/buttons, map its trackball middle click to left click."""
import os
from evdev import InputDevice,UInput,ecodes

device=InputDevice(os.environ.get('DEVICE_PATH','/dev/input/uconsole-mouse'))
if device.name!='ClockworkPI uConsole Mouse': raise SystemExit('Unexpected mouse device')
virtual=UInput.from_device(device,name='ClockworkPI uConsole Mouse Remapped')
try:
    device.grab()
    for event in device.read_loop():
        if event.type==ecodes.EV_SYN: virtual.syn()
        else:
            code=ecodes.BTN_LEFT if event.type==ecodes.EV_KEY and event.code==ecodes.BTN_MIDDLE else event.code
            virtual.write(event.type,code,event.value)
finally:
    device.close()
    virtual.close()
