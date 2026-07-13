# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/OpenDatabaseDialog.ui'
#
# Created: Mon Feb 10 13:40:40 2014
#      by: PyQt5-compatible UI module
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore
from PyQt5 import QtWidgets


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(387, 211)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout_2.addWidget(self.label)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.new_db_but = QtWidgets.QPushButton(Dialog)
        self.new_db_but.setMinimumSize(QtCore.QSize(0, 100))
        self.new_db_but.setObjectName(_fromUtf8("new_db_but"))
        self.horizontalLayout.addWidget(self.new_db_but)
        self.open_db_but = QtWidgets.QPushButton(Dialog)
        self.open_db_but.setMinimumSize(QtCore.QSize(0, 100))
        self.open_db_but.setObjectName(_fromUtf8("open_db_but"))
        self.horizontalLayout.addWidget(self.open_db_but)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Dialog", None))
        self.label.setText(QtWidgets.QApplication.translate("Dialog", "HotSpotter - Animal Instance Recognition (dev version)", None))
        self.new_db_but.setText(QtWidgets.QApplication.translate("Dialog", "New Database", None))
        self.open_db_but.setText(QtWidgets.QApplication.translate("Dialog", "Open Database", None))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
