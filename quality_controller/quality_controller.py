import os
import sys
import getpass
import logging
from datetime import datetime
from PyQt4 import QtGui
import gatekeeper.gatekeeper as gk
import pyqtauto.setters as setters
from pyqtauto.widgets import OrphanMessageBox
from config import Path, Icon, user_data
from reviewer import ReviewerInterface


def user_level(username):
	"""Return a username's user level {'Inspector', 'Supervisor', None}.

	Parameters
	----------
	username : str
	
	"""
	try:
		users = user_data()
		user = users[users['Username'] == username]
		return user['Level'].tolist()[0]
	except IndexError:
		# Not a registered user
		return None


class Main(QtGui.QMainWindow):
	"""
	Application entry point.

	Parameters
	----------
	user : str
	level : {'Supervisor', 'Inspector'}

	Attributes
	----------
	user
	level
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
		self.reviewer_interface()

	def closeEvent(self, event):
		"""Ensure that existing lock is released upon window close."""
		if self.gk.lock_is_acquired:
			self.gk.unlock()
		
	def reviewer_interface(self):
		"""Launch reviewer interface."""
		self.window = ReviewerInterface()
		self.setCentralWidget(self.window.view)
		if self.gk.lock():
			# -----------------------------
			# TODO
			# Setup analytics functionality
			# -----------------------------
			self.window.view.analytics_btn.setEnabled(False)
			self.statusbar.showMessage(
				'Logged in as %s with full access.' % self.user, 
				4000)
		else:
			# Set read-only access
			self.window.view.disable()
			self.statusbar.showMessage(
				'Logged in as %s with read-only access.' % self.user, 
				4000)
		self.show()


if __name__ == '__main__':
	logging.basicConfig(filename=os.path.join(Path.LOG, 'access.log'), 
		level=logging.INFO)

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
			datetime.now().strftime('%H:%M:%S')))

		OrphanMessageBox('UserError', 
			['You do not have permission to access this program.'], 
			'critical').exec_()
	else:
		logging.info('%s logged in on %s at %s' % (
			getpass.getuser(), 
			datetime.now().strftime('%m/%d/%Y'),
			datetime.now().strftime('%H:%M:%S')))
		# Open application
		qc = Main(username, level)
		sys.exit(app.exec_())