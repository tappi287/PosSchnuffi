import logging
from statistics import mean

from pathlib import Path
from time import time
from datetime import datetime

from PySide2 import QtWidgets, QtCore
from PySide2.QtCore import QFile, QObject, Slot, QEvent, Signal, QTimer, Qt
from PySide2.QtGui import QMouseEvent
from PySide2.QtWidgets import QWidget

from modules.utils.globals import UI_PATH, get_settings_dir, get_current_modules_dir
from modules.utils.ui_loader import loadUi
from modules.utils.log import init_logging

LOGGER = init_logging(__name__)


def replace_widget(old_widget, new_widget):
    parent = old_widget.parent()
    layout = parent.layout()
    layout.replaceWidget(old_widget, new_widget)
    old_widget.deleteLater()

    return new_widget


def time_string(time_f: float) -> str:
    """ Converts time in float seconds to display format

        Returned formats based on detected size (hours > minutes > seconds > milliseconds)

        * 01h:01min:01sec
        * 01min:01sec
        * 01sec
        * 001msec
    """
    m, s = divmod(time_f, 60)
    h, m = divmod(m, 60)

    if h < 1:
        if m < 1 and s < 1:
            msec = int(s * 1000)
            return '{:=03d}msec'.format(msec)

        if m < 1:
            return '{:=02.0f}sec'.format(s)

        return '{:=02.0f}min:{:=02.0f}sec'.format(m, s)
    else:
        return '{:=01.0f}h:{:=02.0f}min:{:=02.0f}sec'.format(h, m, s)


class SetupWidget(QObject):
    @staticmethod
    def from_ui_file(widget_cls, ui_file, custom_widgets=dict()):
        """ Load a Qt .ui file to setup the provided widget """
        # Store current log level and set it to ERROR for Ui load
        LOGGER.info('Loading UI File: %s - %s', type(widget_cls), ui_file)

        current_log_level = logging.root.getEffectiveLevel()
        logging.root.setLevel(logging.ERROR)

        # Load the Ui file
        ui_file = Path(get_current_modules_dir()) / UI_PATH / ui_file
        file = QFile(ui_file.as_posix())
        file.open(QFile.ReadOnly)
        loadUi(file, widget_cls, custom_widgets)
        file.close()

        # Restore previous log level
        logging.root.setLevel(current_log_level)


class ConnectCall(QObject):
    def __init__(self, *args, target=None, parent=None):
        super(ConnectCall, self).__init__(parent=parent)
        self.args = args
        self.target = target

    @Slot()
    def call(self):
        self.target(*self.args)


class PredictProgressTime(QObject):
    def __init__(self, num_steps: int, step_size: int=1):
        super(PredictProgressTime, self).__init__()
        if not isinstance(step_size, int) or step_size < 1:
            raise Exception('Step size must be integer greater than 1.')

        # Number of steps that need to be processed
        self.max_steps = int(round(num_steps / step_size))

        # Number of items already processed
        self.progressed_steps = 0

        # List of measured step durations
        self.step_durations = []

        self.progress_start = time()
        self.step_start_time = time()

    def _set_step_start_time(self):
        self.step_start_time = time()

    def update(self):
        return time_string(
            self._predict_remaining_time()
            )

    def _predict_remaining_time(self) -> float:
        self.progressed_steps += 1
        self.step_durations.append(time() - self.step_start_time)

        average_step_duration = self._average_duration()

        remaining_steps = self.max_steps - self.progressed_steps
        self._set_step_start_time()

        return average_step_duration * remaining_steps

    def _average_duration(self):
        return mean(self.step_durations)


class IdleDetection(QObject):
    def __init__(self, parent):
        super(IdleDetection, self).__init__(parent)
        self._parent: QWidget = parent

        # Report user inactivity
        self._idle_timer = QTimer()
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setTimerType(Qt.VeryCoarseTimer)
        self._idle_timer.setInterval(10000)

        # Detect inactivity for automatic session save
        self._idle_timer.timeout.connect(self.set_inactive)
        self.idle = False

        self.parent.installEventFilter(self)

    def is_active(self):
        return self.idle

    def set_active(self):
        self.idle = False
        self._idle_timer.stop()

    def set_inactive(self):
        self.idle = True

    def eventFilter(self, obj, eve):
        if eve is None or obj is None:
            return False

        if eve.type() == QEvent.KeyPress or \
           eve.type() == QEvent.MouseMove or \
           eve.type() == QEvent.MouseButtonPress:
            self.set_active()
            return False

        if not self._idle_timer.isActive():
            self._idle_timer.start()

        return False


class MouseDblClickFilter(QObject):

    def __init__(self, widget_parent: QWidget, method_call: callable, *args):
        """ Capture Mouse double click events

        :param PySide2.QtWidgets.QWidget widget_parent: Widget the event filter will be installed on
        :param callable method_call: Method to call when event was triggered
        :param *args: Arguments to send to the method_call
        """
        super(MouseDblClickFilter, self).__init__(widget_parent)
        self.widget_parent = widget_parent
        self.method_call = method_call
        self.args = args

        self.widget_parent.installEventFilter(self)

    def eventFilter(self, obj, event: QEvent):
        if obj is None or event is None:
            return False

        if event.type() == QMouseEvent.MouseButtonDblClick:
            LOGGER.debug('Mouse Dbl Click: %s %s', obj, event)
            self.method_call(*self.args)
            event.accept()
            return True

        return False


class ExceptionSignal(QObject):
    exception_signal = Signal(str)


class KnechtExceptionHook:
    app = None
    signals = None
    signal_destination = None

    @classmethod
    def exception_hook(cls, etype, value, tb):
        """ sys.excepthook will call this method """
        import traceback

        # Print exception
        traceback.print_exception(etype, value, tb)

        # Log exception
        stacktrace_msg = ''.join(traceback.format_tb(tb))
        if etype:
            exception_msg = '{0}: {1}'.format(etype, value)
        else:
            exception_msg = 'Exception: {}'.format(value)

        LOGGER.critical(stacktrace_msg)
        LOGGER.critical(exception_msg)

        # Write to exception log file
        exception_file_name = datetime.now().strftime('RenderKnecht_Exception_%Y-%m-%d_%H%M%S.log')
        exception_file = Path(get_settings_dir()) / exception_file_name

        with open(exception_file, 'w') as f:
            traceback.print_exception(etype, value, tb, file=f)

        # Inform GUI of exception if QApplication set
        if cls.app:
            gui_msg = f'{stacktrace_msg}\n{exception_msg}'
            cls.send_exception_signal(gui_msg)

    @classmethod
    def setup_signal_destination(cls, dest):
        """ Setup GUI exception receiver from QApplication"""
        cls.signal_destination = dest

    @classmethod
    def send_exception_signal(cls, msg):
        """ This will fail if not run inside a QApplication """
        cls.signals = ExceptionSignal()
        cls.signals.exception_signal.connect(cls.signal_destination)
        cls.signals.exception_signal.emit(msg)


def sort_widget(widget, maximum_width: int=800):
    header = widget.header()
    header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)

    widget_width = max(100, widget.width())
    oversize_width = 0

    # First pass calculate complete oversized width if every item text would be visible
    for column in range(1, header.count() - 1):
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        column_width = header.sectionSize(column) + 40
        oversize_width += column_width

    # Add last and first column width
    oversize_width += header.sectionSize(header.count()) + header.sectionSize(0)

    # Calculate scale factor needed to fit columns inside visible area
    column_scale_factor = max(1, widget_width) / max(1, oversize_width)

    for column in range(1, header.count() - 1):
        width = min((header.sectionSize(column) * column_scale_factor), maximum_width)
        header.setSectionResizeMode(column, QtWidgets.QHeaderView.Interactive)
        header.resizeSection(column, width)

    # Set sorting order to ascending by column 0: order
    widget.sortByColumn(0, QtCore.Qt.AscendingOrder)