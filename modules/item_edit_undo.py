from qtpy.QtCore import QEvent, QModelIndex, QObject, Qt, Slot
from qtpy.QtWidgets import QStyledItemDelegate, QTreeWidget, QUndoCommand, QStyleOptionViewItem, QWidget, QLineEdit

from modules.utils.language import get_translation
from modules.utils.log import init_logging
from modules.utils.ui_resource import FontRsc

LOGGER = init_logging(__name__)

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext

COLUMN_DESC = ('Actor', 'Wert', 'Typ', 'Typ', 'NA', 'NA')


class KnechtValueDelegate(QStyledItemDelegate):
    def __init__(self, view: QTreeWidget):
        """ Overwrite QTreeWidget Item Edit Behaviour

        :param QTreeWidget view: View we replace delegates in
        """
        super(KnechtValueDelegate, self).__init__(view)
        self.view = view
        self.default_delegate = QStyledItemDelegate(view)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        current_value = index.model().data(index, Qt.EditRole)
        editor.setText(current_value)

        return editor

    def setModelData(self, editor, model, index):
        current_value = index.data(Qt.DisplayRole)
        new_value = editor.text()

        if new_value == current_value:
            return

        if not index.parent().isValid():
            # Do not edit Top-Level items
            self.view.info_overlay.display(_('Action List Namen können nicht editieren werden.'), 3000)
            return

        LOGGER.debug('Editor Model Data %s %s %s %s', new_value,
                     index.data(Qt.DisplayRole), index.row(), index.parent().row())

        undo_cmd = ItemEditUndoCommand(current_value, new_value, index, view_name=self.view.objectName())
        self.view.undo_stack.push(undo_cmd)
        self.view.undo_stack.setActive(True)

        return self.default_delegate.setModelData(editor, model, index)


class ItemEditUndoCommand(QUndoCommand):
    """ Undo Command holding user edits on items """
    def __init__(self, previous_data, current_data, index, parent_cmd=None, view_name: str = ''):
        super(ItemEditUndoCommand, self).__init__(parent_cmd)
        self.index = index

        self.current_data = current_data
        self.previous_data = previous_data

        self.setText(_("{0} ändern {1} ... in {2}").format(
            COLUMN_DESC[self.index.column()], current_data[:15], view_name
            )
            )

        # Set a user flag in parent item that it has been edited
        self.current_parent_user_data = True
        # Remember the previous/current state of this flag
        self.previous_parent_user_data = None

        if index.parent().isValid():
            self.previous_parent_user_data = index.parent().siblingAtColumn(0).data(Qt.UserRole)

        # Update parent cmd undo text
        if isinstance(parent_cmd, QUndoCommand):
            parent_cmd.setText(_("{0} für {1} ändern {2} ... in {3}").format(
                COLUMN_DESC[self.index.column()], parent_cmd.childCount(), current_data[:15], view_name
                )
                )

    def redo(self):
        self._do_children(is_undo=False)
        self._set_data(self.index, self.current_data, self.current_parent_user_data)

    def undo(self):
        self._do_children(is_undo=True)
        self._set_data(self.index, self.previous_data, self.previous_parent_user_data)

    def _do_children(self, is_undo: bool):
        for c in range(self.childCount()):
            if is_undo:
                self.child(c).undo()
            else:
                self.child(c).redo()

    @staticmethod
    def _set_data(index: QModelIndex, data, parent_user_data):
        model = index.model()
        model.setData(index, data)

        # Flag the parent with UserData that some child has been edited(or not on Undo)
        if index.parent().isValid():
            result = model.setData(index.parent().siblingAtColumn(0), parent_user_data, Qt.UserRole)

            if result and parent_user_data:
                # Style italic, children contain item edits
                model.setData(index.parent().siblingAtColumn(0), FontRsc.italic, Qt.FontRole)
            else:
                # Style regular, children have not been edited
                model.setData(index.parent().siblingAtColumn(0), FontRsc.regular, Qt.FontRole)
