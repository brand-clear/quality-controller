

import os
import sys
import getpass
import logging
from datetime import datetime
from PyQt4 import QtGui
import gatekeeper.gatekeeper as gk
import pyqtauto.setters as setters
from pyqtauto.widgets import OrphanMessageBox
from defaults import Icon, Path, user_data
from supervisor import SupervisorController


def user_level(username):
	"""Return the user level for a given username.

	Parameters
	----------
	username : str

	Returns
	-------
	{'Inspector', 'Supervisor', None}
		Registered user level for `username` as defined in 'users.xlsx'.
	
	"""
	try:
		users = user_data()
		user = users[users['Username'] == username]

		if user['Level'].tolist()[0] == 'Inspector':
			return 'Inspector'

		elif user['Level'].tolist()[0] == 'Supervisor':
			return 'Supervisor'
	
	except IndexError:
		# Not a registered user
		return None


class Main(QtGui.QMainWindow):
	"""The Main Class represents the entry point to the quality_controller
	application.

	Parameters
	----------
	user : str
	level : {'Supervisor', 'Inspector'}

	Attributes
	----------
	user : str
	level : {'Supervisor', 'Inspector'}
	statusbar : QStatusBar
	interfaces : dict
	gk : GateKeeper

	"""
	def __init__(self, user, level):
		self.user = user
		self.level = level
		self.gk = gk.GateKeeper(self.user, Path.LOCKFILE)
		super(Main, self).__init__()
		setters.set_uniform_margins(self, 10)
		self.setWindowTitle('Quality Controller')
		self.statusbar = QtGui.QStatusBar()
		self.setStatusBar(self.statusbar)
		# ----------------------------
		# TODO
		# Complete inspector interface
		# ----------------------------
		self.interfaces = {
			'Supervisor': self.supervisor_interface,
			'Inspector': None
		}
		self.set_interface()

	def closeEvent(self, event):
		"""Ensure that existing lock is released upon window close."""
		if self.gk.lock_is_acquired:
			self.gk.unlock()

	def set_interface(self):
		"""Set user interface according to registered user level."""
		self.interfaces[self.level]()
		
	def supervisor_interface(self):
		"""Launch interface for supervisor users."""
		self.window = SupervisorController()
		self.setCentralWidget(self.window.view)
		if self.gk.lock():
			# ------------------------------
			# TODO
			# Setup analytics functionality.
			# ------------------------------
			self.window.view.analytics_btn.setEnabled(False)
			self.statusbar.showMessage(
			'Logged in as %s with full access.' % self.user, 
			4000
			)
		else:
			# Set read-only access.
			self.window.view.disable()
			self.statusbar.showMessage(
			'Logged in as %s with read-only access.' % self.user, 
			4000
			)
		self.show()


if __name__ == '__main__':

	logging.basicConfig(
		filename=os.path.join(Path.LOG, 'access.log'), 
		level=logging.INFO
	)

	# Create application
	app = QtGui.QApplication(sys.argv)
	icon = QtGui.QIcon(QtGui.QPixmap(Icon.SULZER))
	app.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
	app.setWindowIcon(icon)

	# Get user data
	username = getpass.getuser()
	level = user_level(username)


	if level == None:
		# Unregistered user
		logging.warning('Attempted login by %s on %s at %s' % (
			getpass.getuser(), 
			datetime.now().strftime('%m/%d/%Y'),
			datetime.now().strftime('%H:%M:%S')
			)
		)

		OrphanMessageBox(
			'UserError',
			['You do not have permission to access this program.'],
			'critical'
		).exec_()

	else:
		logging.info('%s logged in on %s at %s' % (
			getpass.getuser(), 
			datetime.now().strftime('%m/%d/%Y'),
			datetime.now().strftime('%H:%M:%S')
			)
		)
		# Open application
		qc = Main(username, level)
		sys.exit(app.exec_())