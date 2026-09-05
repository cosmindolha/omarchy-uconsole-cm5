#!/usr/bin/python3
"""CM5 uConsole: GPIO10 headphone detect, GPIO11 speaker amplifier enable."""
import re
import subprocess
import time

def pin(*args):
    return subprocess.check_output(['pinctrl',*args],text=True).strip()

def update():
    state=re.search(r'\|\s*(hi|lo)\b',pin('get','10'))
    if not state: raise RuntimeError('Cannot read GPIO10 headphone-detect state')
    pin('set','11','op','dh' if state[1]=='lo' else 'dl')

if __name__=='__main__':
    import sys
    pin('set','10','ip','pn')
    update()
    if '--once' not in sys.argv:
        while True:
            time.sleep(1)
            update()
