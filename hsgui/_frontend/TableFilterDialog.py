"""Table filter editor used by the main HotSpotter window."""

from PyQt5 import QtWidgets


def _translate(text):
    return QtWidgets.QApplication.translate('TableFilterDialog', text)


class TableFilterDialog(QtWidgets.QDialog):
    """Modal editor for a table's per-column filter conditions."""

    def __init__(self, headers, conditions, parent=None):
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
        for header in headers:
            editor = QtWidgets.QLineEdit(editor_widget)
            editor.setPlaceholderText(_translate('None'))
            condition = conditions.get(header)
            if condition is not None:
                editor.setText(str(condition))
            form_layout.addRow(str(header), editor)
            self._editors.append((header, editor))
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
            header: str(editor.text()).strip()
            for header, editor in self._editors
        }