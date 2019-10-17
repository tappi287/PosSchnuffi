import sys

from PySide2.QtWidgets import QApplication, QTreeWidget, QWidget

from modules.pos_schnuffi_ui import SchnuffiWindow
from modules.utils.globals import APP_NAME
from modules.utils.gui_utils import KnechtExceptionHook
from modules.utils.language import get_translation
from modules.utils.log import init_logging

# translate strings
from modules.widgets import GenericErrorBox

lang = get_translation()
lang.install()
_ = lang.gettext

LOGGER = init_logging(__name__)


class SchnuffiApp(QApplication):

    def __init__(self, version: str):
        super(SchnuffiApp, self).__init__(sys.argv)
        self.setApplicationName(APP_NAME)
        self.setApplicationVersion(version)
        self.setApplicationDisplayName(self.applicationName())
        self.last_focus_tree = QWidget()

        self.pos_ui = SchnuffiWindow(self)
        self.last_focus_tree.deleteLater()
        self.last_focus_tree = self.pos_ui.ModifiedWidget
        self.focusChanged.connect(self.app_focus_changed)

        # Prepare exception handling
        self.error_message_box = GenericErrorBox(self.pos_ui)

        KnechtExceptionHook.app = self
        KnechtExceptionHook.setup_signal_destination(self.report_exception)

    def app_focus_changed(self, old_widget: QWidget, new_widget: QWidget):
        if isinstance(new_widget, QTreeWidget):
            self.last_focus_tree = new_widget

    def tree_with_focus(self) -> QTreeWidget:
        """ Return the current or last known QTreeView in focus """
        widget_in_focus = self.focusWidget()

        if isinstance(widget_in_focus, QTreeWidget):
            self.last_focus_tree = widget_in_focus

        return self.last_focus_tree

    def report_exception(self, msg):
        """ Receives KnechtExceptHook exception signal """
        msg = _('<h3>Hoppla!</h3>Eine schwerwiegende Anwendungsausnahme ist aufgetreten. Speichern Sie '
                'Ihre Daten und starten Sie die Anwendung neu.<br><br>') + msg.replace('\n', '<br>')

        self.error_message_box.setWindowTitle(_('Anwendungsausnahme'))
        self.error_message_box.set_error_msg(msg)

        self.error_message_box.exec_()
