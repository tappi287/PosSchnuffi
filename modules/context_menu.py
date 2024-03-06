import logging
from typing import List, Optional

from qtpy.QtGui import QUndoCommand
from qtpy import QtCore, QtWidgets

from utils.language import get_translation
from utils.log import init_logging

LOGGER = init_logging(__name__)

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext


class ItemAddUndo(QUndoCommand):
    def __init__(self, widget: QtWidgets.QTreeWidget, remove=False, parent_cmd=None):
        super().__init__(parent_cmd)
        self.widget = widget
        self.items: Optional[List[QtWidgets.QTreeWidgetItem]] = None
        self.remove = remove

        if not remove:
            self.setText(_(f"Eintrag hinzufügen in {widget.objectName()}"))
        else:
            self.setText(_(f"Einträge entfernen in {widget.objectName()}"))
            self.items = self.widget.selectedItems()

    def add_items(self):
        if self.items:
            self.widget.addTopLevelItems(self.items)
        else:
            self.items = [QtWidgets.QTreeWidgetItem(self.widget, ['NewActionList'])]

    def remove_items(self):
        if not self.items:
            logging.error('Can not undo. Items no longer exist!?')
            return

        for item in self.items:
            self.widget.takeTopLevelItem(self.widget.indexOfTopLevelItem(item))

    def _do(self, redo=True):
        if (self.remove and redo) or (not self.remove and not redo):
            self.remove_items()
            return
        self.add_items()

    def redo(self):
        self._do()

    def undo(self):
        self._do(False)


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
