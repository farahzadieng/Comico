from pathlib import Path
import subprocess
import sys



ROOT=Path(__file__).parent


PROJECT=ROOT / "01-Panel-Detection"


MAIN=PROJECT / "main.py"



if __name__=="__main__":


    command=[

        sys.executable,

        str(MAIN),

        *sys.argv[1:]

    ]


    subprocess.run(command)