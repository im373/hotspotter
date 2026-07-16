"""Table filter editor used by the main HotSpotter window."""

from PyQt5 import QtWidgets


def _translate(text):
    return QtWidgets.QApplication.translate('TableFilterDialog', text)


class TableFilterDialog(QtWidgets.QDialog):
    """Modal editor for a table's per-column filter conditions."""

    def __init__(self, columns, conditions, parent=None):
        super(TableFilterDialog, self).__init__(parent)
        self.setWindowTitle(_translate('Filter Table'))
        self.setModal(True)
        self.resize(520, 600)
        self._editors = []

        layout = QtWidgets.QVBoxLayout(self)
        help_label = QtWidgets.QLabel(
            _translate(
                'Plain text matches exactly. Use *, ?, or [abc] as wildcards; '
                'prefix a raw regular expression with re:. Blank or None means '
                'no filter.'
            )
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        editor_widget = QtWidgets.QWidget(scroll_area)
        form_layout = QtWidgets.QFormLayout(editor_widget)
        for column_key, display_label in columns:
            editor = QtWidgets.QLineEdit(editor_widget)
            editor.setPlaceholderText(_translate('None'))
            condition = conditions.get(column_key)
            if condition is not None:
                editor.setText(str(condition))
            form_layout.addRow(str(display_label), editor)
            self._editors.append((column_key, editor))
        scroll_area.setWidget(editor_widget)
        layout.addWidget(scroll_area)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        clear_button = button_box.addButton(
            _translate('Clear Filters'),
            QtWidgets.QDialogButtonBox.ResetRole,
        )
        clear_button.clicked.connect(self.clear_filters)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def clear_filters(self):
        for _, editor in self._editors:
            editor.clear()

    def conditions(self):
        return {
            column_key: str(editor.text()).strip()
            for column_key, editor in self._editors
        }
