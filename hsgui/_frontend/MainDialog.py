# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/MainDialog.ui'
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
        Dialog.resize(454, 443)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.verticalLayout_3 = QtWidgets.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.pushButton_2 = QtWidgets.QPushButton(Dialog)
        self.pushButton_2.setMinimumSize(QtCore.QSize(0, 62))
        self.pushButton_2.setObjectName(_fromUtf8("pushButton_2"))
        self.verticalLayout_3.addWidget(self.pushButton_2)
        self.pushButton_5 = QtWidgets.QPushButton(Dialog)
        self.pushButton_5.setMinimumSize(QtCore.QSize(0, 62))
        self.pushButton_5.setObjectName(_fromUtf8("pushButton_5"))
        self.verticalLayout_3.addWidget(self.pushButton_5)
        self.pushButton_3 = QtWidgets.QPushButton(Dialog)
        self.pushButton_3.setMinimumSize(QtCore.QSize(0, 62))
        self.pushButton_3.setObjectName(_fromUtf8("pushButton_3"))
        self.verticalLayout_3.addWidget(self.pushButton_3)
        self.pushButton_4 = QtWidgets.QPushButton(Dialog)
        self.pushButton_4.setMinimumSize(QtCore.QSize(0, 62))
        self.pushButton_4.setObjectName(_fromUtf8("pushButton_4"))
        self.verticalLayout_3.addWidget(self.pushButton_4)
        self.pushButton = QtWidgets.QPushButton(Dialog)
        self.pushButton.setMinimumSize(QtCore.QSize(0, 62))
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.verticalLayout_3.addWidget(self.pushButton)
        self.pushButton_8 = QtWidgets.QPushButton(Dialog)
        self.pushButton_8.setObjectName(_fromUtf8("pushButton_8"))
        self.verticalLayout_3.addWidget(self.pushButton_8)
        self.pushButton_6 = QtWidgets.QPushButton(Dialog)
        self.pushButton_6.setObjectName(_fromUtf8("pushButton_6"))
        self.verticalLayout_3.addWidget(self.pushButton_6)
        self.pushButton_7 = QtWidgets.QPushButton(Dialog)
        self.pushButton_7.setObjectName(_fromUtf8("pushButton_7"))
        self.verticalLayout_3.addWidget(self.pushButton_7)
        self.verticalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtWidgets.QApplication.translate("Dialog", "Dialog", None))
        self.pushButton_2.setText(QtWidgets.QApplication.translate("Dialog", "Open Database\n"
" Currently open:\n"
"%{db_path}s", None))
        self.pushButton_5.setText(QtWidgets.QApplication.translate("Dialog", "Peruse Database\n"
" Num Identified: %d{nNames} ; Num Unchecked Images: %d ;  Num Unrefined Rois: %d", None))
        self.pushButton_3.setText(QtWidgets.QApplication.translate("Dialog", "1. Add Images\n"
"Current number of tracked images: \n"
" Internally: %{nImg_internal}d ; Externally: %{nImg_external}d", None))
        self.pushButton_4.setText(QtWidgets.QApplication.translate("Dialog", "2. Mark Regions of Interest\n"
"Current number of tracked chips: %d{nChips}d", None))
        self.pushButton.setText(QtWidgets.QApplication.translate("Dialog", "3. Run Queries\n"
"Current number of unidentified animals: %d{nUnidentified}", None))
        self.pushButton_8.setText(QtWidgets.QApplication.translate("Dialog", "Preferences", None))
        self.pushButton_6.setText(QtWidgets.QApplication.translate("Dialog", "Help", None))
        self.pushButton_7.setText(QtWidgets.QApplication.translate("Dialog", "Quit", None))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
