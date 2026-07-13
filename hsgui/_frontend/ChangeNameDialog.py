# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/ChangeNameDialog.ui'
#
# Created: Mon Feb 10 13:40:41 2014
#      by: PyQt5-compatible UI module
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore
from PyQt5 import QtWidgets


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_changeNameDialog(object):
    def setupUi(self, changeNameDialog):
        changeNameDialog.setObjectName(_fromUtf8("changeNameDialog"))
        changeNameDialog.resize(441, 109)
        self.verticalLayout = QtWidgets.QVBoxLayout(changeNameDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtWidgets.QLabel(changeNameDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.label_2 = QtWidgets.QLabel(changeNameDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.newNameEdit = QtWidgets.QLineEdit(changeNameDialog)
        self.newNameEdit.setObjectName(_fromUtf8("newNameEdit"))
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.newNameEdit)
        self.oldNameEdit = QtWidgets.QLineEdit(changeNameDialog)
        self.oldNameEdit.setObjectName(_fromUtf8("oldNameEdit"))
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.oldNameEdit)
        self.verticalLayout.addLayout(self.formLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(changeNameDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(changeNameDialog)
        QtCore.QMetaObject.connectSlotsByName(changeNameDialog)

    def retranslateUi(self, changeNameDialog):
        changeNameDialog.setWindowTitle(QtWidgets.QApplication.translate("changeNameDialog", "Change Name Dialog", None))
        self.label.setText(QtWidgets.QApplication.translate("changeNameDialog", "Change all names matching:", None))
        self.label_2.setText(QtWidgets.QApplication.translate("changeNameDialog", "To the new name:", None))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    changeNameDialog = QtWidgets.QDialog()
    ui = Ui_changeNameDialog()
    ui.setupUi(changeNameDialog)
    changeNameDialog.show()
    sys.exit(app.exec_())
