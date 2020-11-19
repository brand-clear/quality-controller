import sys
import os.path
import pandas as pd


class Path:
	"""Application paths."""

	# In either case, get the top-level quality_controller directory.
	if os.path.split(sys.executable)[1] == 'python.exe':
		# Dev mode
		ROOT = os.path.dirname(os.path.dirname(__file__))
	else:
		# Exe mode
		ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
			sys.executable))))

	# Local paths
	DATA = os.path.join(ROOT, 'data')
	IMAGES = os.path.join(DATA, 'images')
	LOG = os.path.join(ROOT, 'log')
	LOCKFILE = os.path.join(DATA, 'supervisor.qc')
	SUBMITTED_REPORTS = os.path.join(DATA, 'submitted reports')
	REJECTED_REPORTS = os.path.join(DATA, 'rejected reports')

	# External paths
	PROJECTS_FOLDER = 'L:\\Division2\\PROJECTS FOLDER'
	

class Icon:
	"""Application Icons."""
	ROOT = Path.IMAGES
	APPROVE = os.path.join(ROOT, 'approve.png')
	REJECT = os.path.join(ROOT, 'reject.png')
	INSPECTOR = os.path.join(ROOT, 'inspector.png')
	OPEN = os.path.join(ROOT, 'open.png')
	REFRESH = os.path.join(ROOT, 'refresh.png')
	ANALYTICS = os.path.join(ROOT, 'analytics.png')
	SULZER = os.path.join(ROOT, 'sulzer.png')
	SUPERVISOR = os.path.join(ROOT, 'supervisor.png')


def user_data():
	"""Returns a DataFrame containing user data.

	DataFrame columns include 'Username', 'Name', 'Level', and 'Email'.
	The 'Level' options include 'Supervisor' and 'Inspector.
	
	"""
	return pd.read_excel(os.path.join(Path.DATA, 'users.xlsx'))


def email_addresses(level):
	"""Returns a list of email addresses pertaining to a user level.

	Parameters
	----------
	level : {'Inspector', 'Supervisor'}

	"""
	users = user_data()
	return users[users['Level'] == level]['Email'].tolist()