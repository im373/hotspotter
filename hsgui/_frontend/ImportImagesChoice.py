# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/ImportImagesChoice.ui'
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
        Dialog.resize(385, 208)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setMinimumSize(QtCore.QSize(0, 88))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.horizontalLayout.addWidget(self.pushButton)
        self.pushButton_2 = QtWidgets.QPushButton(Dialog)
        self.pushButton_2.setEnabled(False)
        self.pushButton_2.setMinimumSize(QtCore.QSize(0, 88))
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.horizontalLayout.addWidget(self.pushButton_2)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.checkBox_3 = QtWidgets.QCheckBox(Dialog)
        self.checkBox_3.setObjectName(_fromUtf8("checkBox_3"))
        self.verticalLayout_2.addWidget(self.checkBox_3)
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
        self.pushButton.setText(QtWidgets.QApplication.translate("Dialog", "Import Images and \n"
"copy into the database.", None))
        self.pushButton_2.setText(QtWidgets.QApplication.translate("Dialog", "Import Images but\n"
" leave them where they are.", None))
        self.checkBox_3.setText(QtWidgets.QApplication.translate("Dialog", "The images are the chips. ", None))
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
