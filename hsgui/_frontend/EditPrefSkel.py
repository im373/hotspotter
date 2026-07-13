# HotSpotter port notes:
# Converted generated Qt UI module to PyQt5 namespace imports.
# Updated widget references to QtWidgets for Python 3 / PyQt5 runtime.

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/joncrall/code/hotspotter/hsgui/_frontend/EditPrefSkel.ui'
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

class Ui_editPrefSkel(object):
    def setupUi(self, editPrefSkel):
        editPrefSkel.setObjectName(_fromUtf8("editPrefSkel"))
        editPrefSkel.resize(668, 530)
        self.verticalLayout = QtWidgets.QVBoxLayout(editPrefSkel)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.prefTreeView = QtWidgets.QTreeView(editPrefSkel)
        self.prefTreeView.setObjectName(_fromUtf8("prefTreeView"))
        self.verticalLayout.addWidget(self.prefTreeView)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.redrawBUT = QtWidgets.QPushButton(editPrefSkel)
        self.redrawBUT.setObjectName(_fromUtf8("redrawBUT"))
        self.horizontalLayout.addWidget(self.redrawBUT)
        self.unloadFeaturesAndModelsBUT = QtWidgets.QPushButton(editPrefSkel)
        self.unloadFeaturesAndModelsBUT.setObjectName(_fromUtf8("unloadFeaturesAndModelsBUT"))
        self.horizontalLayout.addWidget(self.unloadFeaturesAndModelsBUT)
        self.defaultPrefsBUT = QtWidgets.QPushButton(editPrefSkel)
        self.defaultPrefsBUT.setObjectName(_fromUtf8("defaultPrefsBUT"))
        self.horizontalLayout.addWidget(self.defaultPrefsBUT)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(editPrefSkel)
        QtCore.QMetaObject.connectSlotsByName(editPrefSkel)

    def retranslateUi(self, editPrefSkel):
        editPrefSkel.setWindowTitle(QtWidgets.QApplication.translate("editPrefSkel", "Edit Preferences", None))
        self.redrawBUT.setText(QtWidgets.QApplication.translate("editPrefSkel", "Redraw", None))
        self.unloadFeaturesAndModelsBUT.setText(QtWidgets.QApplication.translate("editPrefSkel", "Unload Features and Models", None))
        self.defaultPrefsBUT.setText(QtWidgets.QApplication.translate("editPrefSkel", "Defaults", None))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    editPrefSkel = QtWidgets.QWidget()
    ui = Ui_editPrefSkel()
    ui.setupUi(editPrefSkel)
    editPrefSkel.show()
    sys.exit(app.exec_())
