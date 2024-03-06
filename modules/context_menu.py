import logging

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
    def __init__(self, widget: QtWidgets.QTreeWidget, remove=False):
        super().__init__()
        self.widget = widget
        self.item: QtWidgets.QTreeWidgetItem = None
        self.remove = remove
        self.setText(f"Eintrag hinzufügen in {widget.objectName()}")

    def add_item(self):
        self.item = QtWidgets.QTreeWidgetItem(self.widget, ['NewActionList'])

    def remove_item(self):
        if not self.item:
            logging.error('Can not undo. Item no longer exists!?')
            return
        _item = self.widget.takeTopLevelItem(self.widget.indexOfTopLevelItem(self.item))
        self.item = None
        del _item

    def do(self, redo=True):
        if self.remove and redo:
            self.remove_item()
            return

        self.add_item()

    def redo(self):
        self.do()

    def undo(self):
        self.do(False)


class ContextMenu(QtWidgets.QMenu):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        parent.installEventFilter(self)
        parent.context_menu = self

        new_item = QtWidgets.QAction('New Action List', self)
        new_item.triggered.connect(self.new_item)
        self.addAction(new_item)

    def new_item(self):
        undo_cmd = ItemAddUndo(self.parent())
        self.parent().undo_stack.push(undo_cmd)
        self.parent().undo_stack.setActive(True)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if self.parent() is not watched:
            return False

        if event.type() == QtCore.QEvent.ContextMenu:
            self.exec(event.globalPos())
            return True

        return False
