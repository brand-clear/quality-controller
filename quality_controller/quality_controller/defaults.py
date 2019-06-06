

import sys
from os.path import join as osjoin
from os.path import split as ossplit
from os.path import dirname
import pandas as pd


# Local directory structure
# -------------------------
# Quality Control/
#   |---quality_controller/
#       |---data/
#       |---docs/
#       |---macros/
#       |---log/
#       |---quality_controller/
#           |---app.py
#           |---build/
#           |---dist/
#               |---quality_controller/
#                   |---quality_controller.exe
#       |---tests/


def user_data():
    """
    Returns
    -------
    DataFrame
        User data from 'users.xlsx'.
        Columns include: 'Username', 'Name', 'Level', 'Email'.
        'Level' options include: 'Supervisor', 'Inspector'.
    
    """
    return pd.read_excel(osjoin(Path.DATA, 'users.xlsx'))


class Path:
    """Path constants"""

    # In either case, get the top-level quality_controller directory
    if ossplit(sys.executable)[1] == 'python.exe':
        # Dev mode
        ROOT = dirname(dirname(__file__))
    else:
        # Exe mode
        ROOT = dirname(dirname(dirname(dirname(sys.executable))))

    # Local
    DATA = osjoin(ROOT, 'data')
    IMAGES = osjoin(DATA, 'images')
    LOG = osjoin(ROOT, 'log')
    LOCKFILE = osjoin(DATA, 'supervisor.qc')
    SUBMITTED_REPORTS = osjoin(DATA, 'submitted reports')
    REJECTED_REPORTS = osjoin(DATA, 'rejected reports')
    # External 
    PROJECTS_FOLDER = 'L:\\Division2\\PROJECTS FOLDER'
    

class Icon:
    """Icon image constants"""

    ROOT = Path.IMAGES
    APPROVE = osjoin(ROOT, 'approve.png')
    REJECT = osjoin(ROOT, 'reject.png')
    INSPECTOR = osjoin(ROOT, 'inspector.png')
    OPEN = osjoin(ROOT, 'open.png')
    REFRESH = osjoin(ROOT, 'refresh.png')
    ANALYTICS = osjoin(ROOT, 'analytics.png')
    SULZER = osjoin(ROOT, 'sulzer.png')
    SUPERVISOR = osjoin(ROOT, 'supervisor.png')
