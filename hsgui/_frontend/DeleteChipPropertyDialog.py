"""Confirmation dialog for deleting a user-defined chip property."""

from PyQt5 import QtWidgets


def _translate(text):
    return QtWidgets.QApplication.translate('DeleteChipPropertyDialog', text)


class DeleteChipPropertyDialog(QtWidgets.QDialog):
    """Confirm deletion of a property column and all of its values."""

    def __init__(self, property_name, parent=None):
        super(DeleteChipPropertyDialog, self).__init__(parent)
        self.setWindowTitle(_translate('Delete Chip Property'))
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        message = QtWidgets.QLabel(
            _translate(
                'Delete property column %r and all values stored in it?'
            ) % property_name,
            self,
        )
        message.setWordWrap(True)
        layout.addWidget(message)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        delete_button = button_box.addButton(
            _translate('Delete Property'),
            QtWidgets.QDialogButtonBox.DestructiveRole,
        )
        delete_button.clicked.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
