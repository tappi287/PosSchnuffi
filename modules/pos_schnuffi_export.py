from datetime import datetime
from pathlib import Path
from typing import Union, Tuple, List

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from lxml import etree

from modules.pos_schnuffi_msg import Msg
from modules.pos_schnuffi_xml_diff import PosXml
from modules.utils.gui_utils import iterate_widget_items_flat, XmlHelper
from modules.utils.language import get_translation
from modules.utils.log import init_logging
from modules.utils.settings import KnechtSettings

# translate strings
lang = get_translation()
lang.install()
_ = lang.gettext

LOGGER = init_logging(__name__)


class ExportActionList(object):
    xml_dom = {'root': 'stateMachine', 'sub_lvl_1': 'stateEngine'}
    err_msg = Msg.POS_ERR_MSG_LS

    def __init__(self, pos_app, pos_ui):
        """ Export selected items as Xml ActionList """
        self.pos_app, self.pos_ui = pos_app, pos_ui
        self.err = self.pos_app.err_sig

    def _prepare_export(self):
        widget = self._get_widget()
        if not widget:
            self.err.emit(self.err_msg[0])
            return None, None, None

        # Collect QTreeWidgetItems
        items = widget.selectedItems()
        if not items:
            self.err.emit(self.err_msg[1])
            return None, None, None

        # Set export file
        file = self.set_file()
        if not file:
            self.err.emit(self.err_msg[2])
            return None, None, None
        file = Path(file)
        LOGGER.debug('POS Schnuffi Export file set to %s', file.as_posix())

        action_list_names = self.collect_action_list_names(items)
        LOGGER.debug('Found %s actionLists to export.', len(action_list_names))

        return action_list_names, file, widget

    def export_selection(self):
        """
            ### GUI Btn "Export selection" points here ###
            Export the selected widget action list items as custom user Xml
        """
        action_list_names, file, widget = self._prepare_export()
        if not file or not action_list_names:
            self.err.emit(_('Keine actionLists zum Exportieren gefunden.'))
            return

        if not self.export_custom_xml(action_list_names, file):
            # break on error
            return

        self.pos_app.export_sig.emit()

    def export_updated_pos_xml(self):
        """
            ### GUI Btn "Export updated Xml" points here ###
            Export an updated version of the old POS Xml:
                - updating selected action lists from new POS Xml, if in "changed" widget
                - adding selected action lists from new POS Xml, if in "NewXml_actionList" widget
        """
        action_list_names, file, widget = self._prepare_export()
        if not file:
            return

        if widget is self.pos_ui.ModifiedWidget:
            if not action_list_names:
                self.err.emit(_('Nichts zum Exportieren gewählt.'))
                return
            if not self.update_old_pos_xml_with_changed_action_lists(action_list_names, file):
                return
        elif widget in (self.pos_ui.posNewWidget, self.pos_ui.posOldWidget):
            if not self.update_pos_xml_from_pos_widget(file, widget):
                return
        else:
            self.err.emit(_('Exportieren aus diesem Baum wird nicht unterstützt.'))
            return

        self.pos_app.export_sig.emit()

    def update_pos_xml_from_pos_widget(self, out_file: Path, widget: QtWidgets.QTreeWidget) -> bool:
        if widget is self.pos_ui.posNewWidget:
            # Get new PosXml as base
            _, pos_xml = self.get_pos_xmls()
        else:
            # Get old PosXml as base
            pos_xml, _ = self.get_pos_xmls()

        al_items = [i for i in iterate_widget_items_flat(widget) if not i.parent()]
        al_names = [i.data(0, Qt.DisplayRole) for i in al_items]
        al_updated = list()

        for e in pos_xml.iterate_xml_action_list_elements():
            if e.get('name') not in al_names:
                continue

            al_list_index = al_names.index(e.get('name'))
            al_item = al_items[al_list_index]

            if al_item.data(0, Qt.UserRole) != True:
                # Skip unedited items
                continue

            LOGGER.debug('Found edited actionList in widget: %s', e.get('name'))
            al_updated.append(e.get('name'))

            # Remove old Action elements
            for old_action in e.iter('action'):
                e.remove(old_action)

            # Create Action elements from widget
            for c in range(0, al_item.childCount()):
                actor_item = al_item.child(c)

                # <action>
                action_element = etree.SubElement(e, 'action')
                # <action type="">
                action_element.attrib['type'] = actor_item.data(2, Qt.DisplayRole) or 'None'
                # /<actor>
                actor_element = etree.SubElement(action_element, 'actor')
                actor_element.text = actor_item.data(0, Qt.DisplayRole)
                # /<value>
                value_element = etree.SubElement(action_element, 'value')
                value_element.text = actor_item.data(1, Qt.DisplayRole)
                # /<description>
                desc_element = etree.SubElement(action_element, 'description')

        # Try to write the POS mess as a file, this will fail with xml.etree
        LOGGER.info('Exporting POS Xml with updated action lists:\n%s', ', '.join(al_updated))
        self.add_export_info_comment(pos_xml.xml_tree.getroot(), al_updated, Path('.'), pos_xml.xml_file)

        try:
            pos_xml.write_xml_tree(out_file)
            self.err.emit(Msg.POS_EXPORT_MSG.format(out_file.as_posix()))
            return True
        except Exception as e:
            self.err.emit(self.err_msg[5])
            LOGGER.error('POS Xml is malformed and could not be written/serialized.\n%s', e)

        return False

    @staticmethod
    def _collect_action_list(et: etree._ElementTree, action_list_name: str) \
            -> Tuple[Union[None, etree._Element], Union[None, etree._Element], List[Union[None, etree._Element]]]:
        al_elem = et.find(f"*actionList[@name='{action_list_name}']")
        condition = et.xpath(f"*/condition/actionListName[text()='{action_list_name}']/..")[0]

        if al_elem is None or condition is None:
            return None, None, [None]

        # Collect affected state objects
        state_objects = list()
        for state_object_name in condition.xpath(f"stateCondition/stateObjectName"):
            state_object = et.find(f"*stateObject[@name='{state_object_name.text}']")
            if state_object is not None:
                state_objects.append(state_object)

        return al_elem, condition, state_objects

    @staticmethod
    def _replace_element(parent, old_element, new_element):
        idx = parent.index(old_element)
        parent.remove(old_element)
        parent.insert(idx, new_element)

    def update_old_pos_xml_with_changed_action_lists(self, action_list_names, out_file):
        """
        Export an updated version of the old POS Xml, updating selected action lists with the
        content from the new POS Xml.
        """
        # Read old and new POS Xml and return as PosXml class objects
        pos_xml, new_xml = self.get_pos_xmls()
        if not pos_xml or not new_xml:
            return False

        # Prepare storage of updated POS Xml
        updated_et = etree.ElementTree(pos_xml.xml_tree.getroot())
        updated_elements = set()

        for al_name in action_list_names:
            parent = updated_et.find(f'*actionList[@name="{al_name}"]/..')
            old_al, old_condition, old_states = self._collect_action_list(updated_et, al_name)
            new_al, new_condition, new_states = self._collect_action_list(new_xml.xml_tree, al_name)

            if parent is None or old_al is None or new_al is None or old_condition is None or new_condition is None:
                # Skip elements not present in both POS Xml's
                continue

            # Replace old actionList and condition
            self._replace_element(parent, old_al, new_al)
            self._replace_element(parent, old_condition, new_condition)

            for old_state, new_state in zip(old_states, new_states):
                self._replace_element(parent, old_state, new_state)

            updated_elements.add(al_name)

        if not updated_elements:
            # No elements to update found
            # ActionList needs to be available in old and new document
            # adding ActionList is not supported yet
            self.err.emit(self.err_msg[4])
            return False

        # Add info comment
        self.add_export_info_comment(updated_et.getroot(), updated_elements,
                                     self.pos_app.file_win.old_file_dlg.path,
                                     self.pos_app.file_win.new_file_dlg.path)

        # Try to write the POS mess as a file, this will fail with xml.etree
        LOGGER.info('Exporting POS Xml with the following action lists replaced:\n%s', updated_elements)
        try:
            XmlHelper.write_xml_tree(out_file, updated_et)
            self.err.emit(Msg.POS_EXPORT_MSG.format(out_file.as_posix()))
        except Exception as e:
            self.err.emit(self.err_msg[5])
            LOGGER.error('POS Xml is malformed and could not be written/serialized.\n%s', e)
            return False

        return True

    def export_custom_xml(self, action_list_names: set, out_file):
        _, new_xml = self.get_pos_xmls()
        if not new_xml:
            self.err.emit(self.err_msg[3])
            return False

        # Prepare export Xml
        root, state_engine = self._prepare_custom_xml_export()

        for al_name in action_list_names:
            al, condition, state_objects = self._collect_action_list(new_xml.xml_tree, al_name)
            if al is None or condition is None:
                continue

            LOGGER.debug('Adding actionList Xml element %s', al_name)
            state_engine.append(al)
            state_engine.append(condition)
            for e in state_objects:
                state_engine.insert(0, e)

        try:
            tree = etree.ElementTree(root)
            XmlHelper.write_xml_tree(out_file, tree)
            self.err.emit(Msg.POS_EXPORT_MSG.format(out_file.as_posix()))
        except Exception as e:
            self.err.emit(self.err_msg[4])
            LOGGER.error('POS Xml is malformed and could not be written/serialized.\n%s', e)
            return False

        return True

    def _prepare_custom_xml_export(self) -> Tuple[etree._Element, etree._Element]:
        root = etree.Element(self.xml_dom['root'])
        state_engine = etree.SubElement(root, self.xml_dom['sub_lvl_1'])
        state_engine.set('autoType', 'variant')

        return root, state_engine

    def _get_widget(self):
        return self.pos_ui.widget_with_focus()

    def set_file(self):
        """ open a file dialog and return the file name """
        file, file_type = QtWidgets.QFileDialog.getSaveFileName(
            self.pos_ui,
            Msg.SAVE_DIALOG_TITLE,
            KnechtSettings.app.get('current_path') or '',
            Msg.SAVE_FILTER
            )

        return file

    def get_pos_xmls(self) -> Tuple[Union[None, PosXml], Union[None, PosXml]]:
        """ Read old and new POS Xml and return as PosXml class objects """
        if self.pos_app.file_win:
            old_pos_xml_file = self.pos_app.file_win.old_file_dlg.path
            new_pos_xml_file = self.pos_app.file_win.new_file_dlg.path
        else:
            return None, None

        # Parse old and new xml file
        pos_xml = self.parse_pos_xml(old_pos_xml_file)
        if not pos_xml:
            self.err.emit(self.err_msg[3])
            return None, None
        new_xml = self.parse_pos_xml(new_pos_xml_file)
        if not new_xml:
            self.err.emit(self.err_msg[3])
            return None, None

        return pos_xml, new_xml

    @staticmethod
    def parse_pos_xml(xml_file_path: Path) -> Union[PosXml, None]:
        # Parse to Xml
        if xml_file_path.exists():
            try:
                pos_xml = PosXml(xml_file_path)
                return pos_xml
            except Exception as e:
                LOGGER.debug('Error parsing POS Xml: %s', e)
                return
        else:
            return

    @staticmethod
    def collect_action_list_names(items):
        """ Collect actionList names from QTreeWidgetItems """
        action_list_names = set()
        for i in items:
            if i.parent():
                continue  # Skip children
            action_list_names.add(i.text(0))

        return action_list_names

    @staticmethod
    def add_export_info_comment(element, updated_items, old_path, new_path):
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item_str = ''

        for item in updated_items:
            item_str += f'{item}, '

        msg_ls = [f' #1 modified with RenderKnecht POS Schnuffi on {current_date} ',
                  f' #2 actionList elements updated: {item_str[:-2]} ',
                  f' #3 updated actionList elements from source document: {Path(new_path).name} ',
                  f' #4 base document: {Path(old_path).name or "-Direct Edit-"} ']

        for msg in msg_ls:
            element.addprevious(etree.Comment(msg))
