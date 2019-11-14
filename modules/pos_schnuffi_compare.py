from modules.pos_schnuffi_xml_diff import PosDiff

from PySide2.QtWidgets import QTreeWidgetItem
from PySide2 import QtCore


class GuiCompare(QtCore.QThread):
    add_item = QtCore.Signal()
    no_difference = QtCore.Signal()
    finished = QtCore.Signal()
    error_report = QtCore.Signal(str, int)

    item_flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)

    def __init__(self, old_path, new_path, widgets, cmp_queue):
        super(GuiCompare, self).__init__()
        self.old_path, self.new_path = old_path, new_path
        self.cmp_queue = cmp_queue

        self.widgets = widgets

    def run(self):
        diff = PosDiff(self.new_path, self.old_path)

        # Populate added tree widget
        self.add_action_list_items(diff.added_action_ls, 0)

        # Populate modified tree widget
        self.add_action_list_items(diff.modified_action_ls, 1)

        # Populate removed tree widget
        self.add_action_list_items(diff.removed_action_ls, 2)

        # Populate error tab widget
        self.error_report.emit(diff.error_report, diff.error_num)

        # Populate actor widgets
        self.add_actor_items(diff)

        # Populate PosOld
        self._create_pos_action_list_items(diff.old, 5)

        # Populate PosNew
        self._create_pos_action_list_items(diff.new, 6)

        self.finished.emit()

        if diff.no_difference:
            self.no_difference.emit()

    def _create_pos_action_list_items(self, xml_dict: dict, target: int):
        for al_name, al_dict in xml_dict.items():
            al = QTreeWidgetItem([al_name])
            al.setFlags(self.item_flags)

            for actor_name, actor_dict in al_dict.items():
                actor = QTreeWidgetItem(al, [actor_name, actor_dict.get('value'), actor_dict.get('type')])
                actor.setFlags(self.item_flags)

            if al.childCount():
                self.add_item_queued(al, self.widgets[target])

    def add_action_list_items(self, action_list, target: int=0):
        """
        Create QTreeWidgetItem and add to target[int]
            0 - added widget
            1 - modified widget
            2 - removed widget
        """
        for al in action_list:
            item = self.__create_action_list_item(al)
            self.add_item_queued(item, self.widgets[target])

    def add_actor_items(self, diff_cls: PosDiff):
        """
        Create switches/looks items
            target 0 - switches, 1 - looks
        """
        for target in range(0, 2):
            if target == 0:
                widget = self.widgets[3 + target]
                add_set, rem_set, mod_set = diff_cls.add_switches, diff_cls.rem_switches, diff_cls.mod_switches
            else:
                widget = self.widgets[3 + target]
                add_set, rem_set, mod_set = diff_cls.add_looks, diff_cls.rem_looks, diff_cls.mod_looks

            add_text = f'{len(add_set):03d} Actors - hinzugefügt(kommen -nur- in neuer Xml vor)'
            rem_text = f'{len(rem_set):03d} Actors - entfernt(in neuer Xml nicht mehr verwendet)'
            mod_text = f'{len(mod_set):03d} Actors - geändert(Häufigkeit der Verwendung oder Werte verändert)'

            item_num = 0
            for parent, actor_set, parent_text in zip(
                    (QTreeWidgetItem(), QTreeWidgetItem(), QTreeWidgetItem()),
                    (add_set, rem_set, mod_set),
                    (add_text, rem_text, mod_text)
                    ):
                for actor in actor_set:
                    item = QTreeWidgetItem(parent, [actor])
                    item.setFlags(self.item_flags)

                if parent.childCount():
                    parent.setData(0, QtCore.Qt.DisplayRole, f'{item_num} - {parent_text}')
                    self.add_item_queued(parent, widget)
                    item_num += 1
                else:
                    del parent

    def add_item_queued(self, item, widget):
        self.add_item.emit()
        __q = (item, widget)
        self.cmp_queue.put(__q, block=False)

    @classmethod
    def __create_action_list_item(cls, al):
        list_item = QTreeWidgetItem([al.name])
        list_item.setFlags(cls.item_flags)

        for __a in al.actors.items():
            actor, a = __a
            value = a.get('new_value') or ''
            old_value = a.get('old_value') or ''
            actor_type = a.get('type') or ''

            if not actor:
                actor = ''

            actor_item = QTreeWidgetItem(list_item, [actor, value, old_value, actor_type])
            actor_item.setFlags(cls.item_flags)

        return list_item
