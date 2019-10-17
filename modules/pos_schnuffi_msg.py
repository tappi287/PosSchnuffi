

class Msg:
    """ Set GUI strings as class attributes for easy import and access """

    POS_INTRO = '<h4><img src=":/main/assignment.svg" width="21" height="21" style="float: left;">' \
                'POS Schnuffi</h4>' \
                '<p>Lädt zwei POS Xml Dateien und vergleicht hinzugefügte, entfernte und geänderte ' \
                'Action Listen.</p>' \
                '<p>Zeigt nur Änderungen in actors vom Typ <i>appearance</i> und <i>switch</i> an! ' \
                'State Objects werden ignoriert da sie nur innerhalb derselben Xml relevant sind.</p>'
    POS_RUNNING_TITLE = 'POS Schnuffi'
    POS_RUNNING_MSG = 'POS Schnuffi Prozess läuft. Trotzdem beenden?'
    POS_ALREADY_RUNNING = 'POS Schnuffi Vergleichsthread läuft bereits.'
    POS_ERR_MSG_LS = ['Kann nicht exportieren: kein fokusierter Baum erkannt. Element(e) im Baum selektieren.',
                      'Kann nicht exportieren: keine selektierten Elemente erkannt.',
                      'Kann nicht exportieren: keine Exportdatei gewählt.',
                      'Kann Nichts exportieren: Keine POS Xml geladen.',
                      'Kann Nichts exportieren: Keine geänderten Action Listen erkannt. ActionList muss in '
                      'alter und neuer POS Xml vorhanden sein.',
                      'Fehler beim Export. Das Quelldokument ist keine gültige Xml Datei.']
    POS_EXPORT_MSG = 'POS Xml exportiert in:<br>{}'
    POS_AL_ERROR = '<p style="color: red">Fehlende actionList Element(e):</p>'
    POS_CO_ERROR = '<p style="color: red">Fehlende condition Element(e):</p>'
    POS_NO_ERROR = 'actionList und condition Elemente weisen keine Differenz aus. (Duplikate ignoriert falls vorhanden)'
    POS_ERROR_TAB = 'Error'

    NO_FILE_MSG = 'Keine Datei, oder Datei vom falschen Typ ausgewählt.'
    NO_FILE_INFO = '<i>Nicht als Datei gespeichert</i>'

    ERROR_BOX_TITLE = 'Kritischer Fehler'

    EXCEL_TITLE = 'V Plus Browser Excel Dateien *.xlxs auswählen'
    EXCEL_FILTER = 'V Plus Browser Excel Dateien (*.xlsx);'

    CMD_TITLE = 'Variants *.CMD auswählen'
    CMD_FILTER = 'Variant CMD Dateien (*.cmd);'

    FAKOM_TITLE = 'DeltaGen POS Varianten *.xml oder *.pos auswählen'
    FAKOM_FILTER = 'DeltaGen POS Datei (*.xml;*.pos)'

    SAVE_DIALOG_TITLE = 'Benutzer Presets als *.XML speichern...'
    SAVE_FILTER = 'Variant Preset Dateien (*.xml)'

    DIALOG_TITLE = 'Variants *.XML auswählen'
    FILTER = 'Variant Preset Dateien (*.xml);'