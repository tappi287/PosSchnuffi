import logging
from pathlib import Path

from PySide2 import QtWidgets
from PySide2.QtCore import Signal
from PySide2.QtWidgets import QWidget, QMessageBox

from modules.utils.globals import Resource, UI_FILE_DIALOG
from modules.utils.gui_utils import SetupWidget

from modules.utils.language import get_translation
from modules.utils.log import init_logging
from modules.utils.path_util import SetDirectoryPath
from modules.utils.settings import KnechtSettings
from modules.utils.ui_resource import IconRsc

LOGGER = init_logging(__name__)

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext


def get_msg_box_icon(icon_key):
    if not icon_key:
        return IconRsc.get_icon('RK_Icon')
    else:
        return IconRsc.get_icon(icon_key)


class GenericMsgBox(QMessageBox):
    def __init__(self, parent, title: str = 'Message Box', text: str = 'Message Box.', icon_key=None, *__args):
        super(GenericMsgBox, self).__init__()
        self.parent = parent

        self.setWindowIcon(get_msg_box_icon(icon_key))

        self.setWindowTitle(title)
        self.setText(text)


class GenericErrorBox(GenericMsgBox):
    title = _('Fehler')
    txt = _('Allgemeiner Fehler')
    icon_key = 'RK_Icon'

    def __init__(self, parent):
        super(GenericErrorBox, self).__init__(parent, self.title, self.txt, self.icon_key)
        self.setIcon(QMessageBox.Warning)

    def set_error_msg(self, error_msg: str):
        self.setInformativeText(error_msg)


class FileDropWidget(QWidget):
    """ QWidget that accepts file drops """
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super(FileDropWidget, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls:
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e is None or not e.mimeData().hasUrls:
            e.ignore()
            return

        for url in e.mimeData().urls():
            if url.isLocalFile():
                file_url = url.toLocalFile()
                LOGGER.info('Dropped URL: %s', file_url)
                self.file_dropped.emit(file_url)
        e.accept()


class FileWindow(QtWidgets.QWidget):

    def __init__(self, pos_ui, pos_app):
        super(FileWindow, self).__init__()
        self.pos_ui, self.pos_app = pos_ui, pos_app

        LOGGER.setLevel(logging.ERROR)
        SetupWidget.from_ui_file(self, Resource.ui_paths.get(UI_FILE_DIALOG))
        LOGGER.setLevel(logging.DEBUG)

        self.old_file_dlg = SetDirectoryPath(self,
                                             mode='file',
                                             line_edit=self.OldLineEdit,
                                             tool_button=self.OldToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )
        self.old_file_dlg.path_changed.connect(self.save_old_path_setting)

        self.new_file_dlg = SetDirectoryPath(self,
                                             mode='file',
                                             line_edit=self.NewLineEdit,
                                             tool_button=self.NewToolButton,
                                             dialog_args=('POS XML wählen', 'DeltaGen POS Datei (*.xml;*.pos)'),
                                             reject_invalid_path_edits=True,
                                             )
        self.new_file_dlg.path_changed.connect(self.save_new_path_setting)

        self.okBtn.setEnabled(True)
        self.okBtn.pressed.connect(self.validate_and_close)
        self.cancelBtn.pressed.connect(self.close)
        self.swapBtn.pressed.connect(self.swap_paths)

        self.load_settings()

        self.show()

    def swap_paths(self):
        old_path = self.old_file_dlg.path
        new_path = self.new_file_dlg.path

        if old_path is None or new_path is None:
            return

        self.old_file_dlg.set_path(new_path)
        self.new_file_dlg.set_path(old_path)

    def validate_and_close(self):
        if not self.validate_paths():
            self.okLabel.setText('Gültigen Pfad für alte und neue POS Datei angeben.')
            return
        else:
            self.okBtn.setEnabled(False)
            self.okLabel.setText('')
            self.pos_app.compare()
            self.close()

    def validate_paths(self):
        if not self.verify_pos_path(self.old_file_dlg.path) or not self.verify_pos_path(self.new_file_dlg.path):
            return False

        return True

    def load_settings(self):
        old_path = Path(KnechtSettings.app.get('pos_old_path') or '')
        new_path = Path(KnechtSettings.app.get('pos_new_path') or '')

        if self.verify_pos_path(old_path):
            self.old_file_dlg.set_path(old_path)

        if self.verify_pos_path(new_path):
            self.new_file_dlg.set_path(new_path)

    @staticmethod
    def save_old_path_setting(old_path: Path):
        KnechtSettings.app['pos_old_path'] = old_path.as_posix()

    @staticmethod
    def save_new_path_setting(new_path: Path):
        KnechtSettings.app['pos_new_path'] = new_path.as_posix()

    @staticmethod
    def verify_pos_path(pos_path: Path):
        if not pos_path:
            return False

        if pos_path.suffix.casefold() not in ['.pos', '.xml']:
            return False

        if not pos_path.exists():
            return False

        return True
