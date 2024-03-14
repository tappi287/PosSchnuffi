import logging
from typing import List, Optional

from PySide6.QtGui import QUndoCommand
from qtpy import QtWidgets

from modules.utils.language import get_translation
from modules.utils.log import init_logging

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
