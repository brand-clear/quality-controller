

import os
import sys
import csv
import shutil
import getpass
from datetime import datetime
from PyQt4 import QtGui
from sulzer.sos import Sos
from sulzer.extract import (
    Extract, 
    JobNumberError, 
    ProjectsFolderRootError, 
    DestinationError
)
from pyqtauto.widgets import (
    ImageButton, 
    Dialog, 
    ComboBox, 
    ExceptionMessageBox,
    OrphanMessageBox,
    DialogButtonBox
)
from pywinscript.msoffice import send_email
from defaults import Path, Icon, user_data



class SupervisorController(object):
    """The SupervisorController Class combines the views and logic required to
    interact with Supervisor users.

    Attributes
    ----------
    logic : SupervisorLogic
    view : SupervisorView
    """
    def __init__(self):
        self.logic = SupervisorLogic()
        self.view = SupervisorView()
        self.view.open_btn.clicked.connect(self.on_click_open)
        self.view.refresh_btn.clicked.connect(self.update_view)
        self.view.approve_btn.clicked.connect(self.on_click_approve)
        self.view.reject_btn.clicked.connect(self.on_click_reject)
        self.view.reports_lw.itemDoubleClicked.connect(self.on_click_open)
        self.update_view()

    def update_view(self):
        try:
            self.view.update(self.logic.submitted_reports)
        except OSError as error:
            # Broken NFS connection
            ExceptionMessageBox(error).exec_()

    def on_click_open(self):
        try:
            selection = self.view.selection
            # Open selection and corresponding print
            Sos.open_path(self.logic.selection_path(selection))
            Sos.open_path(Extract.issued_print_pdf(selection))
            
        except IndexError:
            return  # No selection

        except (JobNumberError, ProjectsFolderRootError) as error:
            # This indicates that either a job number could not be extracted  
            # from 'selection' or no projects folder has been created for the
            # job number.
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
            shutil.move(
                self.logic.selection_path(selection), 
                os.path.join(np_folder, selection)
            )

            # Save approval to file
            self.logic.save_to_file(
                self.logic.filepath(), 
                [selection, getpass.getuser(), datetime.now()]
            )

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
                shutil.move(
                    self.logic.selection_path(selection), 
                    os.path.join(Path.REJECTED_REPORTS, selection)
                )

                # Save rejection to file
                self.logic.save_to_file(
                    self.logic.filepath(False), 
                    feedback.feedback
                )

                # Notify inspector with email
                self.logic.email(feedback.feedback)

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


class SupervisorView(QtGui.QWidget):
    """The SupervisorView Class represents an interface that allows Supervisor 
    users to view, approve, or reject submitted report data.

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
        super(SupervisorView, self).__init__()
        self._build_ui()

    def _build_ui(self):
        self._layout = QtGui.QVBoxLayout(self)
        self._button_layout = QtGui.QHBoxLayout()
        self.open_btn = ImageButton(
            Icon.OPEN, 
            self._button_layout, 
            tooltip='Open'
        )
        self.approve_btn = ImageButton(
            Icon.APPROVE,
            self._button_layout,
            tooltip='Approve'
        )
        self.reject_btn = ImageButton(
            Icon.REJECT,
            self._button_layout,
            tooltip='Reject'
        )
        self.refresh_btn = ImageButton(
            Icon.REFRESH,
            self._button_layout,
            tooltip='Refresh'
        )
        self.analytics_btn = ImageButton(
            Icon.ANALYTICS,
            self._button_layout,
            tooltip='Analytics'
        )
        self._layout.addLayout(self._button_layout)
        self.reports_lw = QtGui.QListWidget()
        self._layout.addWidget(self.reports_lw)

    @property
    def selection(self):
        """Return the name of the selected item in reports_lw.

        Returns
        -------
        str
            Selected reports_lw item.

        Raises
        ------
        IndexError
            No reports_lw item was selected.

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
        """Call on reports_lw to show a given list of items.

        Parameters
        ----------
        items : list

        """
        self.reports_lw.clear()
        self.reports_lw.addItems(items)


class SupervisorLogic(object):
    """The SupervisorLogic Class represents the logical backend to the
    SupervisorView Class.

    """
    def __init__(self):
        pass

    @property
    def submitted_reports(self):
        """Get the list of filenames found in Path.SUBMITTED_REPORTS.

        Returns
        -------
        list
            Filenames found in Path.SUBMITTED_REPORTS.

        Raises
        ------
        OSError
            Path.SUBMITTED_REPORTS was not found (broken NFS connection).

        """
        try:
            return [
                item for item in os.listdir(Path.SUBMITTED_REPORTS) 
                if item != 'Thumbs.db'
            ]

        except OSError:
            raise

    @property
    def inspectors(self):
        """Return the list of email addresses for 'inspector' users.

        Returns
        -------
        list
            Inspector email addresses.
        
        """
        users = user_data()
        inspectors = users[users['Level'] == 'Inspector']
        return inspectors['Email'].tolist()

    def selection_path(self, name):
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
            `name` was not of type ``str`` (``NoneType``).

        """
        return os.path.join(Path.SUBMITTED_REPORTS, name)

    def filepath(self, approve=True):
        """Return the CSV filepath that pertains to a given review decision.

        Parameters
        ----------
        approve : {True, False}, optional
            
        Returns
        -------
        str
            Absolute path to appropriate CSV file.
        """
        if approve:
            return os.path.join(Path.DATA, 'approved.csv')
        else:
            return os.path.join(Path.DATA, 'rejected.csv')

    def save_to_file(self, filepath, data):
        """Document the contents of a given list to a given file.

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

    def _rejection_link(self, name):
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
            os.path.join(Path.REJECTED_REPORTS, name),
            name
        )

    def _rejection_subject(self, name):
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

    def _rejection_body(self, feedback):
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
            feedback[1],
            feedback[2],
            self._rejection_link(feedback[0])
        )

    def email(self, feedback):
        """Send an email per a given list of review feedback.

        Parameters
        ----------
        feedback : list
            Rejection feedback as defined by 'FeedbackDialog' class.

        """
        send_email(
            self.inspectors,
            [],
            self._rejection_subject(feedback[0]),
            self._rejection_body(feedback)
        )


class DrawingError(Exception):
    """The DrawingError Class formats a given exception's error message where
    a specified drawing cannot be found.

    Parameters
    ----------
    error : Exception subclass
    destination : {True, False}, optional
        True for DestinationError exception, else False.

    """
    def __init__(self, error, destination=False):
        self.message = 'The following error occured while trying to open the '\
            'corresponding drawing:\n\n'
        self.message = self.message + error.message
        if destination:
            self._outro = '\n\nThe root folder will be opened instead.'
            self.message = self.message + self._outro


class ReviewError(Exception):
    """The ReviewError Class formats a given exception's error message per a 
    given review action.

    Parameters
    ----------
    error : Exception subclass
    approve : {True, False}, optional
        Review action.

    """
    def __init__(self, error, approve=True):
        self._action = 'approve' if approve is True else 'reject'
        self.message = 'The following error occured while trying to %s the '\
            'selected file:\n\n' % self._action
        self._msg = error.message if len(error.message) > 1 else str(error)
        self.message = self.message + self._msg


class WorkCenterDialog(Dialog):
    """The WorkCenterDialog Class represents an interface to query Supervisor
    users for the appropriate work center for a particular project.

    Attributes
    ----------
    selection

    """
    def __init__(self):
        super(WorkCenterDialog, self).__init__('Work Center')
        self._selection = None
        self._build_ui()

    def _build_ui(self):
        self._form_layout = QtGui.QFormLayout()
        self.setFixedWidth(220)
        self._balance_rb = QtGui.QRadioButton('Balance')
        self._assembly_rb = QtGui.QRadioButton('Assembly')
        self._group = QtGui.QButtonGroup(self)
        self._group.addButton(self._balance_rb)
        self._group.addButton(self._assembly_rb)
        self._form_layout.addRow(self._balance_rb, self._assembly_rb)
        self._intro_lb = QtGui.QLabel(
            'Select the appropriate work center for this project:'
        )
        self._intro_lb.setWordWrap(True)
        self.layout.addWidget(self._intro_lb)
        self.layout.addLayout(self._form_layout)
        self._ok = DialogButtonBox(self.layout, 'ok')
        self._ok.accepted.connect(self.accept)
        self._group.buttonClicked['QAbstractButton *'].connect(self._setter)

    def _setter(self, button):
        self._selection = str(button.text()).lower()
    
    @property
    def selection(self):
        """
        Returns
        -------
        str
            Work center selected via QRadioButtons.
        """
        return self._selection


class FeedbackDialog(Dialog):
    """The FeedbackDialog Class represents an interface to query Supervisor
    users for feedback regarding rejected quality assurance reports.

    Parameters
    ----------
    rejected_item : str

    Attributes
    ----------
    feedback

    """

    _REASONS = [
        'Out of Tolerance',
        'Missing Information',
        'Other'
    ]

    def __init__(self, rejected_item):
        self._rejected_item = rejected_item
        super(FeedbackDialog, self).__init__('Feedback')
        self._build_ui()

    def _build_ui(self):
        self._intro_lb = QtGui.QLabel(
            'Please describe why this report was rejected. '\
            'Your feedback will be used to help train the inspector.'
        )
        self._intro_lb.setWordWrap(True)
        self.layout.addWidget(self._intro_lb)
        self._reasons_cb = ComboBox(self._REASONS)
        self._form_layout = QtGui.QFormLayout()
        self._form_layout.addRow(
            QtGui.QLabel('Report:'), 
            QtGui.QLabel(self._rejected_item)
        )
        self._form_layout.addRow(
            QtGui.QLabel('Reason:'), 
            self._reasons_cb
        )
        self.layout.addLayout(self._form_layout)
        self._explain_te = QtGui.QPlainTextEdit()
        self.layout.addWidget(self._explain_te)
        self._buttons = DialogButtonBox(self.layout, 'okcancel')
        self._buttons.accepted.connect(lambda: self.accept())
        self._buttons.rejected.connect(lambda: self.reject())

    @property
    def _reason(self):
        """
        Returns
        -------
        str
            {'Out of Tolerance, 'Missing Information', 'Other'}

        """
        return str(self._reasons_cb.currentText())

    @property
    def _explanation(self):
        """
        Returns
        -------
        str
            Detailed reasoning for rejection.

        """
        return str(self._explain_te.toPlainText())

    @property
    def feedback(self):
        """Return the list of feedback provided by a supervisor user.

        Returns
        -------
        list
            Compilation of all rejection feedback.

        """
        return [
            self._rejected_item,
            self._reason,
            self._explanation,
            getpass.getuser(),
            datetime.now()
        ]


if __name__ == "__main__":
    # Test module
    app = QtGui.QApplication(sys.argv)
    app.setStyle(QtGui.QStyleFactory.create('cleanlooks'))
    test = SupervisorController()
    test.view.show()
    app.exec_()
