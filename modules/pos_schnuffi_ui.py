import logging
from pathlib import Path
from queue import Queue

from PySide2 import QtCore, QtWidgets
from PySide2.QtGui import QBrush, QColor
from PySide2.QtWidgets import QGroupBox, QLineEdit, QUndoStack, QUndoGroup, QMenu

from modules.filter_tree_widget import TreeWidgetFilter
from modules.item_edit_undo import KnechtValueDelegate
from modules.pos_schnuffi_compare import GuiCompare
from modules.pos_schnuffi_export import ExportActionList
from modules.utils.globals import Resource, UI_MAIN_WINDOW
from modules.utils.gui_utils import SetupWidget, sort_widget
from modules.utils.language import get_translation
from modules.utils.log import init_logging
from modules.utils.ui_overlay import InfoOverlay
from modules.widgets import FileWindow

LOGGER = init_logging(__name__)

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext


class SchnuffiWindow(QtWidgets.QMainWindow):
    # Error signal
    err_sig = QtCore.Signal(str)
    export_sig = QtCore.Signal()
    
    def __init__(self, pos_app):
        """

        :param modules.main_app.SchnuffiApp pos_app:
        """
        super(SchnuffiWindow, self).__init__()
        self.pos_app = pos_app

        LOGGER.setLevel(logging.ERROR)
        SetupWidget.from_ui_file(self, Resource.ui_paths.get(UI_MAIN_WINDOW))
        LOGGER.setLevel(logging.DEBUG)

        self.file_win = None

        # -- Comparision thread --
        self.cmp_thread = QtCore.QThread(self)
        self.cmp_queue = Queue(-1)
        
        # -- Timer --
        self.intro_timer = QtCore.QTimer()
        self.intro_timer.setSingleShot(True)
        self.intro_timer.setInterval(500)

        # -- Add item worker --
        self.item_worker = QtCore.QTimer()
        self.item_worker.setInterval(15)
        self.remaining_items = 0
        self.item_chunk_size = 35
        
        self.export = ExportActionList(self, self)

        self.info_overlay = InfoOverlay(self)

        self.undo_grp = QUndoGroup(self)
        self.widget_list = [self.AddedWidget, self.ModifiedWidget, self.RemovedWidget,
                            self.switchesWidget, self.looksWidget, self.posOldWidget,
                            self.posNewWidget]
        self.setup_widgets()

        # --- Create undo menu ---
        self.undo_menu = QMenu(_('Undo'), self)
        # Create undo/redo actions from undo_grp
        self.redo = self.undo_grp.createRedoAction(self, _('Wiederherstellen'))
        self.redo.changed.connect(self.undo_action_changed)
        self.undo = self.undo_grp.createUndoAction(self, _('Rückgängig'))
        self.undo.changed.connect(self.undo_action_changed)
        # add menu
        self.undo_menu.addActions((self.undo, self.redo))
        self.menuBar().addMenu(self.undo_menu)

        self.show()

    def undo_action_changed(self):
        obj = self.sender()

        if obj == self.redo:
            pass
        elif obj == self.undo:
            pass

    def setup_widgets(self):
        # Buttons
        self.filterLabel.mouseDoubleClickEvent = self.sort_all_headers
        self.expandBtn.pressed.connect(self.expand_all_items)

        # Work Timer
        self.item_worker.timeout.connect(self.add_widget_item)

        self.progressBar.hide()

        # Menu
        self.actionOpen.triggered.connect(self.open_file_window)
        self.actionBeenden.triggered.connect(self.close)
        self.actionExport.triggered.connect(self.export.export_selection)
        self.actionExportPos.triggered.connect(self.export.export_updated_pos_xml)

        # File display
        self.file_name_box: QGroupBox
        self.file_name_box.setTitle(_('Dateien Alt - Neu'))

        # Filter Line Edit
        self.lineEditFilter: QLineEdit
        self.lineEditFilter.setPlaceholderText(_('Zum filtern im Baum tippen. Leerzeichen separierte Begriffe werden '
                                                 'mit UND gefunden. zB. t_mirko ks_bunt findet alle bunten Mirkos.'))

        for widget in self.widget_list:
            widget.clear()
            widget.undo_stack = QUndoStack(self.undo_grp)
            widget.setItemDelegate(KnechtValueDelegate(widget))

            # Overlay
            widget.info_overlay = InfoOverlay(widget)
            # Setup Filtering
            widget.filter = TreeWidgetFilter(self, widget, self.lineEditFilter)
            widget.setAlternatingRowColors(True)

        self.intro_timer.timeout.connect(self.show_intro_msg)
        self.intro_timer.start()

        # Exporter signals
        self.err_sig.connect(self.error_msg)
        self.export_sig.connect(self.export_success)

        # Tab Changed
        self.widgetTabs.currentChanged.connect(self.tab_changed)

    @staticmethod
    def get_tree_name(widget):
        return widget.objectName()

    def widget_with_focus(self):
        """ Return the current or last QTreeWidget in focus """
        return self.pos_app.tree_with_focus()

    def tab_changed(self, idx):
        tab_widget = self.widgetTabs.widget(idx)
        LOGGER.debug('Tab change: %s, %s', idx, tab_widget.objectName())

        # Apply filter to active tab
        for widget in tab_widget.children():
            if widget in self.widget_list:
                widget.filter.start()

    def closeEvent(self, close_event):
        if self.cmp_thread:
            self.cmp_thread.quit()
            self.cmp_thread.wait(800)
            
        close_event.accept()

    def show_intro_msg(self):
        self.info_overlay.display_confirm(
            _('<h4><img src=":/main/assignment.svg" width="21" height="21" style="float: left;">'
              'POS Schnuffi</h4>'
              '<p>Lädt zwei POS Xml Dateien und vergleicht hinzugefügte, entfernte und geänderte '
              'Action Listen.</p>'
              '<p>Zeigt nur Änderungen in actors vom Typ <i>appearance</i> und <i>switch</i> an! '
              'State Objects werden ignoriert da sie nur innerhalb derselben Xml relevant sind.</p>'),
            (('[X]', None), ))

    def export_success(self):
        self.info_overlay.display('Export succeeded.')

    def error_msg(self, error_str):
        # self.widgetTabs.setCurrentIndex(0)
        self.info_overlay.display_exit()
        self.info_overlay.display_confirm(error_str, (('[X]', None), ))

    def sort_all_headers(self, event=None):
        for widget in self.widget_list:
            sort_widget(widget)

    def expand_all_items(self):
        for widget in self.widget_list:
            widget.hide()
            widget.expandAll()

        for widget in self.widget_list:
            widget.show()

    def open_file_window(self):
        self.file_win = FileWindow(self, self)

    def compare(self):
        self.clear_item_queue()

        if self.cmp_thread is not None:
            if self.cmp_thread.isRunning():
                self.error_msg(_('POS Schnuffi Vergleichsthread läuft bereits.'))
                return

        for widget in self.widget_list:
            widget.clear()
            widget.hide()

        self.cmp_thread = GuiCompare(self.file_win.old_file_dlg.path,
                                     self.file_win.new_file_dlg.path,
                                     self.widget_list,
                                     self.cmp_queue)

        self.cmp_thread.add_item.connect(self.request_item_add)
        self.cmp_thread.no_difference.connect(self.no_difference_msg)
        self.cmp_thread.finished.connect(self.finished_compare)
        self.cmp_thread.error_report.connect(self.add_error_report)

        # Prepare add item worker
        self.item_worker.stop()
        self.remaining_items = 0
        self.progressBar.setMaximum(0)
        self.progressBar.setValue(0)

        self.cmp_thread.start()
        self.statusBar().showMessage(_('POS Daten werden geladen und verglichen...'), 8000)

    def finished_compare(self):
        self.sort_all_headers()
        self.statusBar().showMessage(_('POS Daten laden und vergleichen abgeschlossen. Bäume werden befüllt.'), 8000)

        self.old_file_label.setText(Path(self.file_win.old_file_dlg.path).name)
        self.new_file_label.setText(Path(self.file_win.new_file_dlg.path).name)

    def _item_worker_finished(self):
        for widget in self.widget_list:
            widget.show()

        self.widgetTabs.setCurrentIndex(0)

        # self.info_overlay.display_exit()
        self.info_overlay.display(_('POS Daten laden und vergleichen abgeschlossen.'), 5000, True)

    def no_difference_msg(self):
        self.info_overlay.display_confirm(_('Keine Unterschiede gefunden.'), (('[X]', None),))
        self.statusBar().showMessage(_('POS Daten laden und vergleichen abgeschlossen. Keine Unterschiede gefunden.')
                                     , 8000)
        self._item_worker_finished()

    def request_item_add(self):
        self.remaining_items += 1
        self.progressBar.setMaximum(max(self.remaining_items, self.progressBar.maximum()))

        if not self.item_worker.isActive():
            self.item_worker.start()
            self.progressBar.show()

    def add_widget_item(self):
        if not self.remaining_items:
            self.item_worker.stop()
            self.progressBar.hide()
            self._item_worker_finished()

            return

        count = 0

        while self.remaining_items:
            item, target_widget = self.cmp_queue.get()
            self.color_items(item)
            target_widget.addTopLevelItem(item)

            self.remaining_items -= 1
            self.cmp_queue.task_done()

            count += 1

            self.progressBar.setValue(self.progressBar.value() + 1)

            if count >= self.item_chunk_size:
                break

    def add_error_report(self, error_report, error_num):
        # Reset error tab name
        widget_idx = self.widgetTabs.indexOf(self.errorsTab)
        self.widgetTabs.setTabText(widget_idx, _('Error'))

        if error_num:
            # Switch to error tab and report number of errors in tab title
            self.widgetTabs.setCurrentIndex(widget_idx)
            self.widgetTabs.setTabText(widget_idx, f'Error ({error_num})')

        self.errorTextWidget.clear()
        self.errorTextWidget.append(error_report)

    @staticmethod
    def color_items(parent_item):
        for c in range(0, parent_item.childCount()):
            item = parent_item.child(c)
            value = item.text(1)
            old_value = item.text(2)

            # Skip actor's without values
            if not value and not old_value:
                continue

            if not value:
                # No new value, actor removed
                for c in range(0, 4):
                    item.setForeground(c, QBrush(QColor(190, 90, 90)))
            elif not old_value and value:
                # New actor added
                for c in range(0, 4):
                    item.setForeground(c, QBrush(QColor(90, 140, 90)))

    def clear_item_queue(self):
        if self.cmp_queue.qsize():
            LOGGER.debug('Clearing %s items from the queue.', self.cmp_queue.qsize())

        while not self.cmp_queue.empty():
            try:
                _, _ = self.cmp_queue.get()
            except Exception as e:
                LOGGER.error('Error clearing queue %s', e)

            self.cmp_queue.task_done()

        LOGGER.debug('Queue cleared!')
