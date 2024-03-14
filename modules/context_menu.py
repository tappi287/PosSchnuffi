from qtpy.QtGui import QUndoCommand
from qtpy import QtCore, QtWidgets

from modules.item_add_undo import ItemAddUndo
from utils.language import get_translation
from utils.log import init_logging

LOGGER = init_logging(__name__)

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext


class ContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        parent.installEventFilter(self)
        parent.context_menu = self

        new_item = QtWidgets.QAction(_('New Action List'), self)
        new_item.triggered.connect(self.new_item)
        remove_item = QtWidgets.QAction(_('Remove selected Action List(s)'), self)
        remove_item.triggered.connect(self.remove_item)

        self.addActions([new_item, remove_item])

    def _add_undo_command(self, undo_cmd: QUndoCommand):
        self.parent().undo_stack.push(undo_cmd)
        self.parent().undo_stack.setActive(True)

    def new_item(self):
        self._add_undo_command(ItemAddUndo(self.parent()))

    def remove_item(self):
        self._add_undo_command(ItemAddUndo(self.parent(), remove=True))

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if self.parent() is not watched:
            return False

        if event.type() == QtCore.QEvent.ContextMenu:
            self.exec(event.globalPos())
            return True

        return False
