import os
import sys
import csv
import shutil
import getpass
from datetime import datetime
from PyQt4 import QtGui
from sulzer.sos import Sos
from sulzer.extract import (Extract, JobNumberError, ProjectsFolderRootError, 
	DestinationError)
from pyqtauto.widgets import (ImageButton, Dialog, ComboBox, 
	ExceptionMessageBox, OrphanMessageBox, DialogButtonBox)
from pywinscript.msoffice import send_email
from config import Path, Icon, email_addresses


class ReviewerInterface(object):
	"""
	An interactive interface for reviewing, approving, or rejecting inspection
	reports.

	Attributes
	----------
	view : View

	"""
	def __init__(self):
		self.view = View()
		self.view.open_btn.clicked.connect(self.on_click_open)
		self.view.refresh_btn.clicked.connect(self.update_view)
		self.view.approve_btn.clicked.connect(self.on_click_approve)
		self.view.reject_btn.clicked.connect(self.on_click_reject)
		self.view.reports_lw.itemDoubleClicked.connect(self.on_click_open)
		self.update_view()

	def update_view(self):
		try:
			self.view.update(Logic.submitted_reports())
		except OSError as error:
			ExceptionMessageBox(error).exec_()

	def on_click_open(self):
		try:
			selection = self.view.selection
			# Open selection and corresponding print
			Sos.open_path(Logic.selection_path(selection))
			Sos.open_path(Extract.issued_print_pdf(selection))
			
		except IndexError:
			return  # No selection

		except (JobNumberError, ProjectsFolderRootError) as error:
			# This indicates that either a job number could not be extracted  
			# from or no projects folder has been created for the job number.
			ExceptionMessageBox(DrawingError(error)).exec_()

		except DestinationError as error:
			# Open corresponding drawing folder if drawing is not found.
			# Any errors that could be raised from the methods below would have
			# been raised already by the previous methods.
			ExceptionMessageBox(DrawingError(error, True)).exec_()
			job_num = Extract.job_number(selection)
			Sos.open_path(Extract.issued_prints_folder(job_num))

	def on_click_approve(self):
		try:
			# Validate selection
			selection = self.view.selection
			job_num = Extract.job_number(selection)
	
			# Specify work center
			dialog = WorkCenterDialog()
			if dialog.exec_():
				dept = dialog.selection
			else:
				return
			
			np_folder = Extract.qualified_part_folder(job_num, dept)
			
			# Perform os operations with validated paths
			shutil.move(Logic.selection_path(selection), os.path.join(np_folder, 
				selection))

			# Save approval to file
			Logic.save_to_file(Logic.filepath(), [selection, getpass.getuser(), 
				datetime.now()])

		except IndexError:
			pass  # No selection

		except (JobNumberError, ProjectsFolderRootError) as error:
			# This indicates that either a job number could not be extracted  
			# from 'selection' or no projects folder has been created for the
			# job number.
			ExceptionMessageBox(ReviewError(error)).exec_()

		except DestinationError as error:
			# NP folder was not found
			ExceptionMessageBox(ReviewError(error)).exec_()

		except IOError as error:
			# Existing approved PDF report open by another process or source
			# file not found.
			ExceptionMessageBox(ReviewError(error)).exec_()

		except WindowsError as error:
			# Approved PDF will be overridden if it exists, but the source file
			# is open by another process and cannot be deleted.
			# ***This only applies to certain file types. For example, errors 
			# are raised for PDF files, but not TXT files.***
			ExceptionMessageBox(ReviewError(error)).exec_()

		finally:
			self.update_view()

	def on_click_reject(self):
		try:
			# Validate selection
			selection = self.view.selection
			feedback = FeedbackDialog(selection)
			if feedback.exec_():

				# Perform os operations with validated paths
				shutil.move(Logic.selection_path(selection), os.path.join(
					Path.REJECTED_REPORTS, selection))

				# Save rejection to file
				Logic.save_to_file(Logic.filepath(False), feedback.feedback)

				# Notify inspector with email
				Logic.rejection_email(feedback.feedback)

		except IndexError:
			pass  # No selection

		except IOError as error:
			# Rejected PDF report open by another process or source
			# file not found.
			ExceptionMessageBox(ReviewError(error)).exec_()

		except WindowsError as error:
			# Rejected PDF will be overridden if it exists, but the source file
			# is open by another process and cannot be deleted.
			# ***This only applies to certain file types. For example, errors 
			# are raised for PDF files, but not TXT files.***
			ExceptionMessageBox(ReviewError(error)).exec_()

		finally:
			self.update_view()


class View(QtGui.QWidget):
	"""
	Represents an interface that allows priveleged users to view, approve, or 
	reject submitted inspection reports.

	Attributes
	----------
	open_btn = ImageButton
	approve_btn = ImageButton
	reject_btn = ImageButton
	refresh_btn = ImageButton
	analytics_btn = ImageButton
	reports_lw = QListWidget

	"""
	def __init__(self):
		super(View, self).__init__()
		self._layout = QtGui.QVBoxLayout(self)
		self._button_layout = QtGui.QHBoxLayout()
		self.open_btn = ImageButton(Icon.OPEN, self._button_layout, 
			tooltip='Open')
		self.approve_btn = ImageButton(Icon.APPROVE, self._button_layout,
			tooltip='Approve')
		self.reject_btn = ImageButton(Icon.REJECT, self._button_layout,
			tooltip='Reject')
		self.refresh_btn = ImageButton(Icon.REFRESH, self._button_layout,
			tooltip='Refresh')
		self.analytics_btn = ImageButton(Icon.ANALYTICS, self._button_layout,
			tooltip='Analytics')
		self._layout.addLayout(self._button_layout)
		self.reports_lw = QtGui.QListWidget()
		self._layout.addWidget(self.reports_lw)

	@property
	def selection(self):
		"""str: The selected item.

		Raises
		------
		IndexError
			No item was selected.

		"""
		return str(self.reports_lw.selectedItems()[0].text())

	def disable(self):
		"""Restrict widget use for read-only mode."""
		self.open_btn.setEnabled(False)
		self.approve_btn.setEnabled(False)
		self.reject_btn.setEnabled(False)
		self.refresh_btn.setEnabled(False)
		self.analytics_btn.setEnabled(False)
		self.reports_lw.setEnabled(False)

	def update(self, items):
		"""Update the view data source.

		Parameters
		----------
		items : list

		"""
		self.reports_lw.clear()
		self.reports_lw.addItems(items)


class Logic:

	@staticmethod
	def submitted_reports():
		"""Return the list of filenames found in Path.SUBMITTED_REPORTS.

		Raises
		------
		OSError
			Path.SUBMITTED_REPORTS was not found.

		"""
		try:
			return [item for item in os.listdir(Path.SUBMITTED_REPORTS) 
				if item != 'Thumbs.db']
		except OSError:
			raise

	@staticmethod
	def supervisors():
		"""Return the list of email addresses for 'Inspector' users."""
		return email_addresses('Supervisor')

	@staticmethod
	def selection_path(name):
		"""Prepend Path.SUBMITTED_REPORTS to a given input.

		Parameters
		----------
		name : str or None

		Returns
		-------
		str
			Absolute path to file ending in `name`.

		Raises
		------
		TypeError
			If `name` is None.

		"""
		return os.path.join(Path.SUBMITTED_REPORTS, name)

	@staticmethod
	def filepath(approve=True):
		"""Return the CSV filepath that pertains to a review decision.

		Parameters
		----------
		approve : {True, False}, optional

		"""
		if approve:
			return os.path.join(Path.DATA, 'approved.csv')
		else:
			return os.path.join(Path.DATA, 'rejected.csv')

	@staticmethod
	def save_to_file(filepath, data):
		"""Document the contents of a list to a CSV file.

		Parameters
		----------
		filepath : str
			Absolute path to CSV file.

		data : list

		Raises
		------
		IOError
			File is open by another user.

		"""
		try:
			with open(filepath, 'ab') as f:
				writer = csv.writer(f)
				writer.writerow(data)
		except IOError:
			raise

	@staticmethod
	def _rejection_link(name):
		"""
		Parameters
		----------
		name : str
			Rejected file.

		Returns
		-------
		str
			HTML formatted link to `name`.

		"""
		return 'View report now: <a href="%s">%s</a>' % (
			os.path.join(Path.REJECTED_REPORTS, name), name)

	@staticmethod
	def _rejection_subject(name):
		"""
		Parameters
		----------
		name : str
			Rejected filename.
		
		Returns
		-------
		str
			Subject line text of rejection email.

		"""
		return 'Rejected QC Report: %s' % name

	@classmethod
	def _rejection_body(cls, feedback):
		"""
		Parameters
		----------
		feedback : list
			Rejection feedback as defined by 'FeedbackDialog' class.

		Returns
		-------
		str
			Body text of rejection email.

		"""
		return 'Reason: %s<br><br>Explanation: %s<br><br>%s' % (
			feedback[1], feedback[2], cls._rejection_link(feedback[0]))

	@classmethod
	def rejection_email(cls, feedback):
		"""Send an email which describes a rejected inspection report.

		Parameters
		----------
		feedback : list
			Rejection feedback as defined by `FeedbackDialog`.

		"""
		send_email(cls.supervisors(), [], cls._rejection_subject(feedback[0]),
			cls._rejection_body(feedback))


class DrawingError(Exception):
	"""
	Raised when a specified drawing cannot be found.

	Parameters
	----------
	error : Exception subclass
	destination : {True, False}, optional
		True only if related to a DestinationError.

	"""
	def __init__(self, error, destination=False):
		self.message = 'The following error occured while trying to open the '\
			'corresponding drawing:\n\n'
		self.message = self.message + error.message
		if destination:
			self._outro = '\n\nThe root folder will be opened instead.'
			self.message = self.message + self._outro


class ReviewError(Exception):
	"""
	Raised when an error occurs during an approval or rejection decision.

	Parameters
	----------
	error : Exception subclass
	approve : {True, False}, optional

	"""
	def __init__(self, error, approve=True):
		self._action = 'approve' if approve is True else 'reject'
		self.message = 'The following error occured while trying to %s the '\
			'selected file:\n\n' % self._action
		self._msg = error.message if len(error.message) > 1 else str(error)
		self.message = self.message + self._msg


class WorkCenterDialog(Dialog):
	"""
	Represents an interface to query Supervisor	users for the appropriate work 
	center for an approved project.

	Attributes
	----------
	selection : {'Balance', 'Assembly', 'Blading'}

	"""
	def __init__(self):
		super(WorkCenterDialog, self).__init__('Work Center')
		self._selection = None
		self._v_layout = QtGui.QVBoxLayout()
		self.setFixedWidth(220)
		self._balance_rb = QtGui.QRadioButton('Balance')
		self._assembly_rb = QtGui.QRadioButton('Assembly')
		self._blading_rb = QtGui.QRadioButton('Blading')
		self._group = QtGui.QButtonGroup(self)
		self._group.addButton(self._balance_rb)
		self._group.addButton(self._assembly_rb)
		self._group.addButton(self._blading_rb)
		self._group.buttonClicked['QAbstractButton *'].connect(self._setter)
		self._v_layout.addWidget(self._balance_rb)
		self._v_layout.addWidget(self._assembly_rb)
		self._v_layout.addWidget(self._blading_rb)
		self._intro_lb = QtGui.QLabel(
			'Select the appropriate work center for this project.')
		self._intro_lb.setWordWrap(True)
		self.layout.setSpacing(15)
		self.layout.addWidget(self._intro_lb)
		self.layout.addLayout(self._v_layout)
		self._ok = DialogButtonBox(self.layout, 'ok')
		self._ok.accepted.connect(self.accept)
		
	def _setter(self, button):
		self._selection = str(button.text()).lower()
	
	@property
	def selection(self):
		"""str: The seleced work center."""
		return self._selection


class FeedbackDialog(Dialog):
	"""
	Represents an interface to query Supervisor	users for feedback regarding 
	rejected reports.

	Parameters
	----------
	rejected_item : str

	Attributes
	----------
	feedback

	"""

	_REASONS = [
		'Out of Tolerance',
		'Missing Features',
		'Part Distortion',
		'Other'
	]

	_DIVISIONS = ['Core', 'MFG', 'Vendor']

	def __init__(self, rejected_item):
		self._rejected_item = rejected_item
		super(FeedbackDialog, self).__init__('Feedback')
		self._intro_lb = QtGui.QLabel(
			'Please describe why this report was rejected. '\
			'Your feedback will be used to help improve shop processes.')
		self._intro_lb.setWordWrap(True)
		self._reasons_cb = ComboBox(self._REASONS)
		self._division_cb = ComboBox(self._DIVISIONS)
		self._form_layout = QtGui.QFormLayout()
		self._form_layout.addRow('Report:', QtGui.QLabel(self._rejected_item))
		self._form_layout.addRow('Reason:', self._reasons_cb)
		self._form_layout.addRow('Division:', self._division_cb)
		self._explain_te = QtGui.QPlainTextEdit()
		self.layout.setSpacing(15)
		self.layout.addWidget(self._intro_lb)
		self.layout.addLayout(self._form_layout)
		self.layout.addWidget(self._explain_te)
		self._buttons = DialogButtonBox(self.layout, 'okcancel')
		self._buttons.accepted.connect(self.accept)
		self._buttons.rejected.connect(self.reject)

	def _reason(self):
		"""Returns the selected rejection reason."""
		return str(self._reasons_cb.currentText())

	def _explanation(self):
		"""Returns the detailed reasoning for a rejection."""
		return str(self._explain_te.toPlainText())

	def _division(self):
		return str(self._division_cb.currentText())

	@property
	def feedback(self):
		"""Returns a list of rejection feedback."""
		return [
			self._rejected_item, 
			self._reason(), 
			self._explanation(),
			getpass.getuser(), 
			datetime.now(),
			self._division()
		]


if __name__ == "__main__":
	# Test
	app = QtGui.QApplication(sys.argv)
	app.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
	test = ReviewerInterface()
	test.view.show()
	app.exec_()
