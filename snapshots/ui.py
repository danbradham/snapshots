# Standard library imports
import sys
from math import trunc

# Local imports
from . import core, resources
from .vendor.Qt import QtWidgets, QtCore, QtGui


class SyncTaskReporter(QtCore.QObject):

    event = QtCore.Signal(object)

    def __init__(self, name, total=100, parent=None):
        super(SyncTaskReporter, self).__init__(parent)
        self.name = name
        self.total = total
        self.amount = 0
        self.percent = 0

    def new_event(self, **data):
        event = {
            'name': self.name,
            'total': self.total,
            'amount': self.amount,
            'percent': self.percent,
        }
        event.update(data)
        return event

    def set_total(self, value):
        self.total = value
        self.event.emit(self.new_event(type='total'))

    def info(self, message):
        self.event.emit(self.new_event(type='info', message=message))

    def start(self, message):
        self.event.emit(self.new_event(type='start', message=message))

    def step(self, amount, message):
        self.amount += amount
        self.percent = self.amount / self.total * 100
        self.event.emit(self.new_event(type='step', message=message))

    def done(self, message):
        self.event.emit(self.new_event(type='done', message=message))


class SyncTask(QtCore.QThread):

    def __init__(self, method, options, parent=None):
        super(SyncTask, self).__init__(parent=parent)
        self.method = method
        self.options = options

    def run(self):
        self.method(**self.options)


class FolderSelector(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(FolderSelector, self).__init__(parent=parent)

        self.editor = QtWidgets.QLineEdit()
        self.editor.setFixedHeight(20)
        self.button = QtWidgets.QToolButton()
        self.button.setIcon(QtGui.QIcon(resources.get('folder_open.png')))
        self.button.setIconSize(QtCore.QSize(16, 16))
        self.button.clicked.connect(self.browse)
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.editor)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

    def set(self, path):
        self.editor.setText(path)

    def get(self):
        return self.editor.text()

    def browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self)
        if folder:
            self.editor.setText(folder)


class SyncReport(QtWidgets.QDialog):

    def __init__(self, report, parent=None):
        super(SyncReport, self).__init__(parent=parent)
        self.text = QtWidgets.QTextEdit(parent=self)
        self.text.setText(report)
        self.text.setLineWrapMode(self.text.NoWrap)
        self.text.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.button = QtWidgets.QPushButton('Dismiss')
        self.button.clicked.connect(self.accept)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.setWindowTitle('Sync Report')
        self.setWindowIcon(QtGui.QIcon(resources.get('sync.png')))


class Sync(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(Sync, self).__init__(parent=parent)

        # Holds a SyncTask thread.
        self._task = None
        self._records = []
        self.auto_accept = False
        self.auto_report = False

        self.widgets = {
            'progress': QtWidgets.QProgressBar(parent=self),
            'message': QtWidgets.QLabel(parent=self),
            'done': QtWidgets.QPushButton('Okay', parent=self),
            'report': QtWidgets.QPushButton('View Report', parent=self),
            'src': FolderSelector(parent=self),
            'dst': FolderSelector(parent=self),
            'mode': QtWidgets.QComboBox(parent=self),
            'replace_changed': QtWidgets.QCheckBox('Replace Modified', parent=self),
            'delete_files': QtWidgets.QCheckBox('Delete Missing', parent=self),
            'dry': QtWidgets.QCheckBox('Dry Run', parent=self),
            'sync': QtWidgets.QPushButton('Sync', parent=self),
        }
        self.widgets['progress'].setAlignment(QtCore.Qt.AlignCenter)
        self.widgets['report'].clicked.connect(self.show_report)
        self.widgets['done'].clicked.connect(self.accept)
        self.widgets['mode'].addItems(['One Way', 'Two Way'])
        self.widgets['mode'].setToolTip(
            'One Way: Sync files from Src to Dest.\n'
            'Two Way: Sync files in both directions (Src to Dst and Dst to Src).'
        )
        self.widgets['sync'].clicked.connect(self.sync)
        self.widgets['delete_files'].setChecked(False)
        self.widgets['delete_files'].setToolTip(
            'Delete files in Dst that are not in Src.'
        )
        self.widgets['replace_changed'].setChecked(False)
        self.widgets['replace_changed'].setToolTip('Replace modified files.')
        self.widgets['dry'].setChecked(False)
        self.widgets['dry'].setToolTip(
            'Do not perform any file operations.\n'
            'Show a list of operations that will be performed.'
        )

        self.options_layout = QtWidgets.QFormLayout()
        self.options_layout.setContentsMargins(0, 0, 0, 0)
        self.options_layout.addRow('Source', self.widgets['src'])
        self.options_layout.addRow('Destination', self.widgets['dst'])
        self.options_layout.addRow('Mode', self.widgets['mode'])
        self.options_layout.addRow('', self.widgets['replace_changed'])
        self.options_layout.addRow('', self.widgets['delete_files'])
        self.options_layout.addRow('', self.widgets['dry'])
        self.options_layout.addRow(self.widgets['sync'])
        self.options = QtWidgets.QWidget()
        self.options.setLayout(self.options_layout)

        self.progress_layout = QtWidgets.QGridLayout()
        self.progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_layout.addWidget(self.widgets['progress'], 0, 0, 1, 2)
        self.progress_layout.addWidget(self.widgets['message'], 1, 0, 1, 2)
        self.progress_layout.addWidget(self.widgets['report'], 2, 0)
        self.progress_layout.addWidget(self.widgets['done'], 2, 1)
        self.progress = QtWidgets.QWidget()
        self.progress.setLayout(self.progress_layout)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.options)
        self.setLayout(self.layout)

        self.setWindowTitle('Sync Folders')
        self.setWindowIcon(QtGui.QIcon(resources.get('sync.png')))
        self.set_state('options')

    def on_event(self, event):
        '''Handle events emitted by a SyncTaskReporter.'''

        if event['type'] == 'start':
            self._records.append(f'[{event["name"]}] {event["message"]}')
        elif event['type'] == 'total':
            self.widgets['progress'].setMaximum(event['total'])
            self._records.append(f'[{event["name"]}] Total set to {event["total"]}.')
        elif event['type'] == 'info':
            self._records.append(f'[{event["name"]}] {event["message"]}')
        elif event['type'] == 'step':
            self.widgets['progress'].setValue(event['amount'])
            self.widgets['message'].setText(event['message'])
            self._records.append('[{}] Progress {:>3d}% {}'.format(
                event['name'],
                trunc(event['percent']),
                event['message'],
            ))
        elif event['type'] == 'done':
            self.set_state('done')
            self._records.append(f'[{event["name"]}] {event["message"]}')
            self.widgets['message'].setText(event['message'])
            if event['total'] == 0:
                self.widgets['progress'].setMaximum(100)
                self.widgets['progress'].setValue(100)
            print('\n'.join(self._records))
            if self.auto_accept:
                self.accept()
            if self.auto_report:
                self.show_report()
        else:
            self._records.append(f'Unhandled event {event}')

    def set_auto_accept(self, value):
        '''Accept the dialog when sync is done.'''

        self.auto_accept = value

    def set_auto_report(self, value):
        '''Show the report when sync is done.'''

        self.auto_report = value

    def set_state(self, state):
        '''Set the state of the UI.'''

        if state == 'options':
            self.options.show()
            self.progress.hide()
            self.adjustSize()
        elif state == 'running':
            self.options.hide()
            self.progress.show()
            self.widgets['report'].hide()
            self.widgets['done'].hide()
            self.adjustSize()
        elif state == 'done':
            self.options.hide()
            self.progress.show()
            self.widgets['report'].show()
            self.widgets['done'].show()
            self.adjustSize()
        else:
            print(f'Unrecognizes state: {state}')

    def set_options(self, **options):
        '''Set Syncing options - update control widgets.

        Arguments:
            src (str): Source folder path.
            dst (str): Destination folder path.
            replace_changed (bool): If both locations have a file in common, the older
                file is replaced with the newer file when replace_changed is True.
            delete_files (bool): Files that exist in dst but not src are deleted when
                delete_files is True.
            dry (bool): Do not perform any file operations. Report is still generated.
            mode (int/str): 0 - One Way, 1 - Two Way.

        Modes:
            One Way (0): Sync files from Src to Dest.
            Two Way (1): Sync files in both directions (Src to Dst and Dst to Src).
        '''
        for k, v in options.items():
            if k in ['src', 'dst']:
                self.widgets[k].set(v)
            elif k in ['replace_changed', 'delete_files', 'dry']:
                self.widgets[k].setChecked(v)
            elif k in ['mode']:
                mode = {
                    'one_way': 'One Way',
                    'two_way': 'Two Way',
                    0: 'One Way',
                    1: 'Two Way',
                }.get(v, v)
                try:
                    self.widgets[k].setCurrentText(mode)
                except Exception:
                    pass

    def get_options(self):
        '''Get all Syncing options from control widgets.'''

        return {
            'src': self.widgets['src'].get(),
            'dst': self.widgets['dst'].get(),
            'replace_changed': self.widgets['replace_changed'].isChecked(),
            'delete_files': self.widgets['delete_files'].isChecked(),
            'dry': self.widgets['dry'].isChecked(),
            'mode': self.widgets['mode'].currentText(),
        }

    def show_report(self):
        '''Show a dialog presenting the records from the finished sync.'''

        report = SyncReport('\n'.join(self._records))
        report.exec_()

    def sync(self):
        '''Execute the sync operation.'''

        # Create reporter
        reporter = SyncTaskReporter('Sync', 100, self)
        reporter.event.connect(self.on_event)

        # Get SyncTask options and method
        options = self.get_options()
        options['reporter'] = reporter
        if options['mode'] == 'Two Way':
            options.pop('delete_files')
        method = {
            'One Way': core.sync,
            'Two Way': core.sync_bidirectional,
        }[options.pop('mode')]

        # Create SyncTask thread and start it!
        self._task = SyncTask(method, options)
        self._task.start()

        # Change UI state
        self.set_state('running')
