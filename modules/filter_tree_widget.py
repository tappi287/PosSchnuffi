import re
from typing import Tuple

from qtpy.QtCore import QEvent, QModelIndex, QObject, QTimer, Qt, Signal
from qtpy.QtWidgets import QLineEdit, QTreeWidgetItemIterator, QWidget

from modules.utils.animation import BgrAnimation
from modules.utils.gui_utils import iterate_widget_items_flat
from modules.utils.log import init_logging

LOGGER = init_logging(__name__)


class TreeWidgetFilter(QObject):
    change_item = Signal(QModelIndex, bool, int)
    scroll_to_signal = Signal(QModelIndex)

    def __init__(self, ui, widget: QWidget, line_edit: QWidget, columns: Tuple=(0, 1, 2)):
        super(TreeWidgetFilter, self).__init__(widget)
        self.ui = ui
        self.widget = widget
        self.columns = columns
        self.clean = True

        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.setInterval(1500)
        self.filter_timer.timeout.connect(self.search)

        self.restore_timer = QTimer()
        self.restore_timer.setSingleShot(True)
        self.restore_timer.setInterval(500)
        self.restore_timer.timeout.connect(self.restore)

        self.busy_timer = QTimer()
        self.busy_timer.setSingleShot(True)
        self.busy_timer.setInterval(100)
        self.busy_timer.timeout.connect(self.filtering_finished)

        self.line_edit: QLineEdit = line_edit
        self.line_edit.textChanged.connect(self._line_edit_text_changed)

        self.bgr_animation = BgrAnimation(self.line_edit, (255, 255, 255, 255))

        self.change_item.connect(self.apply_item_change)
        self.scroll_to_signal.connect(self.scroll_to_item)

        self.widget.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self.ui.widget_with_focus() is not watched:
            return False

        if not event.type() == QEvent.KeyPress:
            return False

        if event.key() in (Qt.Key_Backspace, Qt.Key_Escape):
            self.line_edit.clear()
            self.restore()
            self.widget.info_overlay.display(f'Clearing filter.', 1500, True)
            return True

        # Send alphanumeric keys to LineEdit filter widget
        filter_keys = [Qt.Key_Space, Qt.Key_Underscore, Qt.Key_Minus]

        if event.text().isalnum() or event.key() in filter_keys:
            filter_txt = self.line_edit.text()
            filter_txt += event.text()

            if filter_txt:
                self.widget.info_overlay.display(f'Filtering: {filter_txt}', 1500, True)
            self.line_edit.setText(filter_txt)

            return True

        return False

    def start(self):
        if self.line_edit.text():
            self.filter_timer.start()
        else:
            if not self.clean:
                self.restore_timer.start()

    def _line_edit_text_changed(self, txt):
        if self.ui.widget_with_focus() is not self.widget:
            return

        self.start()

    def _prepare_filtering(self):
        LOGGER.debug('Running filter on: %s', self.widget.objectName())

        # Display actual filter
        t = ''
        for word in self.line_edit.text().split(' '):
            t += f'{word} AND '

        if self.line_edit.text():
            self.widget.info_overlay.display(f'Filtering: {t[:-5]}', 4500, True)
        else:
            self.widget.info_overlay.display(f'Filter Reset', 3000, True)

        self.bgr_animation.blink()
        self.widget.hide()
        self.busy_timer.start()

    def filtering_finished(self):
        LOGGER.debug('Filter operation finished on: %s', self.widget.objectName())
        self.widget.show()

        if self.line_edit.text():
            self.clean = False
        else:
            self.clean = True

    def search(self):
        self._prepare_filtering()

        for item in iterate_widget_items_flat(self.widget):
            txt = ''
            for c in self.columns:
                # Match any column text with OR '|'
                txt += f'{item.text(c)}|'

            if txt:
                txt = txt[:-1]

            # Show everything and collapse parents
            index = self.widget.indexFromItem(item)
            parent_index = self.widget.indexFromItem(item.parent())

            results = list()

            # Match space separated filter strings with AND
            for word in self.line_edit.text().split(' '):
                results.append(True if re.search(word, txt, flags=re.IGNORECASE) else False)

            if not all(results):
                # Hide all non-matching items
                self.change_item.emit(index, True, 0)
                continue

            # Un-hide
            self.change_item.emit(index, False, 0)
        
            if parent_index:
                # Show and expand parent
                self.change_item.emit(parent_index, False, 1)
        
            # Scroll to selection
            if item.isSelected():
                self.scroll_to_signal.emit(index)

    def restore(self):
        self._prepare_filtering()

        for item in iterate_widget_items_flat(self.widget):
            # Show everything and collapse parents
            index = self.widget.indexFromItem(item)
            parent_index = self.widget.indexFromItem(item.parent())

            if not parent_index.isValid():
                # Show and collapse top level items
                self.change_item.emit(index, False, 2)
            else:
                # Un-hide all
                self.change_item.emit(index, False, 0)

            # Scroll to selection
            if item.isSelected():
                self.widget.horizontalScrollBar().setSliderPosition(0)
                self.widget.scrollToItem(item)

    def scroll_to_item(self, index: QModelIndex):
        item = self.widget.itemFromIndex(index)
        self.widget.horizontalScrollBar().setSliderPosition(0)
        self.widget.scrollToItem(item)

    def apply_item_change(self, index, hide=False, expand: int = 0):
        """ Receives signal to hide/unhide or expand/collapse items """
        item = self.widget.itemFromIndex(index)

        if not item:
            return

        self.busy_timer.start()

        if hide:
            item.setHidden(True)
        else:
            item.setHidden(False)

        if expand == 1:
            item.setExpanded(True)
        elif expand == 2:
            item.setExpanded(False)
