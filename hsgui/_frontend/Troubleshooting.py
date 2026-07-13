# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/Troubleshooting.ui'
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(510, 217)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setMinimumSize(QtCore.QSize(0, 100))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.horizontalLayout.addWidget(self.pushButton)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.pushButton_2 = QtWidgets.QPushButton(Dialog)
        self.pushButton_2.setMinimumSize(QtCore.QSize(0, 25))
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.verticalLayout_3.addWidget(self.pushButton_2)
        self.pushButton_4 = QtWidgets.QPushButton(Dialog)
        self.pushButton_4.setMinimumSize(QtCore.QSize(0, 25))
        self.pushButton_4.setObjectName(_fromUtf8("pushButton_4"))
        self.verticalLayout_3.addWidget(self.pushButton_4)
        self.pushButton_5 = QtWidgets.QPushButton(Dialog)
        self.pushButton_5.setMinimumSize(QtCore.QSize(0, 25))
        self.pushButton_5.setObjectName(_fromUtf8("pushButton_5"))
        self.verticalLayout_3.addWidget(self.pushButton_5)
        self.pushButton_3 = QtWidgets.QPushButton(Dialog)
        self.pushButton_3.setMinimumSize(QtCore.QSize(0, 25))
        self.pushButton_3.setObjectName(_fromUtf8("pushButton_3"))
        self.verticalLayout_3.addWidget(self.pushButton_3)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.pushButton_6 = QtWidgets.QPushButton(Dialog)
        self.pushButton_6.setMinimumSize(QtCore.QSize(0, 100))
        self.pushButton_6.setObjectName(_fromUtf8("pushButton_6"))
        self.horizontalLayout.addWidget(self.pushButton_6)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.checkBox = QtWidgets.QCheckBox(Dialog)
        self.checkBox.setEnabled(False)
        self.checkBox.setObjectName(_fromUtf8("checkBox"))
        self.verticalLayout_2.addWidget(self.checkBox)
        self.checkBox_2 = QtWidgets.QCheckBox(Dialog)
        self.checkBox_2.setEnabled(False)
        self.checkBox_2.setObjectName(_fromUtf8("checkBox_2"))
        self.verticalLayout_2.addWidget(self.checkBox_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout_2.addWidget(self.buttonBox)

        self.retranslateUi(Dialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), Dialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Dialog", None))
        self.pushButton.setText(QtWidgets.QApplication.translate("Dialog", "Delete Preference Directory", None))
        self.pushButton_2.setText(QtWidgets.QApplication.translate("Dialog", "Delete Entire Computed Directory", None))
        self.pushButton_4.setText(QtWidgets.QApplication.translate("Dialog", "Delete Chips", None))
        self.pushButton_5.setText(QtWidgets.QApplication.translate("Dialog", "Delete Chip Representations", None))
        self.pushButton_3.setText(QtWidgets.QApplication.translate("Dialog", "Delete Visual Model", None))
        self.pushButton_6.setText(QtWidgets.QApplication.translate("Dialog", "Email Developer to Report a Bug\n"
"crallj@rpi.edu", None))
        self.checkBox.setText(QtWidgets.QApplication.translate("Dialog", "Rembember Until End of Run", None))
        self.checkBox_2.setText(QtWidgets.QApplication.translate("Dialog", "Remember In Preference File: %{pref_fname}", None))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
