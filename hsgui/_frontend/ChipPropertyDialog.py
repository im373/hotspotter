"""Editor for a user-defined chip-table property definition."""

from PyQt5 import QtWidgets

from hotspotter import chip_properties


def _translate(text):
    return QtWidgets.QApplication.translate('ChipPropertyDialog', text)


class ChipPropertyDialog(QtWidgets.QDialog):
    """Collect a property name, datatype, and importance level."""

    def __init__(self, definition=None, parent=None):
        super(ChipPropertyDialog, self).__init__(parent)
        definition = definition or {
            'name': '',
            'datatype': 'str',
            'importance': 0,
        }
        is_edit = bool(definition.get('name'))
        self.setWindowTitle(_translate(
            'Edit Chip Property' if is_edit else 'New Chip Property'
        ))
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.name_edit = QtWidgets.QLineEdit(self)
        self.name_edit.setText(str(definition.get('name', '')))
        form.addRow(_translate('Column name'), self.name_edit)

        self.datatype_combo = QtWidgets.QComboBox(self)
        for datatype in chip_properties.PROPERTY_DATATYPES:
            self.datatype_combo.addItem(datatype, datatype)
        datatype = str(definition.get('datatype', 'str'))
        datatype_index = self.datatype_combo.findData(datatype)
        self.datatype_combo.setCurrentIndex(max(0, datatype_index))
        form.addRow(_translate('Datatype'), self.datatype_combo)

        self.importance_combo = QtWidgets.QComboBox(self)
        for importance, label in chip_properties.PROPERTY_IMPORTANCE.items():
            self.importance_combo.addItem(
                '%d - %s' % (importance, _translate(label)),
                importance,
            )
        importance = int(definition.get('importance', 0))
        importance_index = self.importance_combo.findData(importance)
        self.importance_combo.setCurrentIndex(max(0, importance_index))
        form.addRow(_translate('Importance'), self.importance_combo)
        layout.addLayout(form)

        help_label = QtWidgets.QLabel(
            _translate(
                'Importance: 0 is not significant, 1 is an important feature, '
                'and 2 is a permanent feature. Definitions are stored in a '
                'separate JSON file when the database is saved. Permanent '
                'values restrict query comparisons; empty cells are wildcards.'
            ),
            self,
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def definition(self):
        return {
            'name': str(self.name_edit.text()).strip(),
            'datatype': str(self.datatype_combo.currentData()),
            'importance': int(self.importance_combo.currentData()),
        }
