"""
Installs dependencies for the Game Engine

If running this file produces an error, try:
    1. running IDLE as an administrator
    2. opening this file in IDLE
    3. run this file

Alternative for Windows:
    1. Open Command Prompt as Administrator
    2. Change directory to setup.py folder (in command prompt)
        cd /d "full/path/to/folder"
    3. Run one of the following
        a. setup.py
        b. py setup.py
        c. python setup.py

"""

__version__ = "1.1.0"

import sys
import subprocess


def execute(cmd):
    process = subprocess.run(cmd,
                             capture_output=True,
                             # check=True,
                             universal_newlines=True)

    if process.stdout:
        print(process.stdout)
    
    if process.returncode != 0:
        print("Something went wrong. Consult the notes above.")
        print(process.stderr)

    process.check_returncode()


if __name__ == '__main__':
    execute([sys.executable, "-m", "pip", "install", "pymunk"])
