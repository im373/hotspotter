"""Confirmation dialog for removing zero-chip rows from the name table."""

from PyQt5 import QtWidgets


def _translate(text):
    return QtWidgets.QApplication.translate('CleanNameTableDialog', text)


class CleanNameTableDialog(QtWidgets.QDialog):
    """Show the names that will be removed before modifying the database."""

    def __init__(self, unused_name_rows, parent=None):
        super(CleanNameTableDialog, self).__init__(parent)
        self.setWindowTitle(_translate('Clean Name Table'))
        self.setModal(True)
        self.resize(480, 420)

        layout = QtWidgets.QVBoxLayout(self)
        count = len(unused_name_rows)
        message = _translate(
            '%d name row%s %s no chips. Remove them from the database file?'
        ) % (
            count,
            '' if count == 1 else 's',
            'has' if count == 1 else 'have',
        )
        message_label = QtWidgets.QLabel(message, self)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        name_list = QtWidgets.QListWidget(self)
        for nx, name in unused_name_rows:
            name_list.addItem('%s: %s' % (nx, name))
        layout.addWidget(name_list)

        warning_label = QtWidgets.QLabel(
            _translate('This operation saves the database immediately.'),
            self,
        )
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
