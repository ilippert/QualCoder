# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_attribute.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DialogAddAttribute(object):
    def setupUi(self, DialogAddAttribute):
        DialogAddAttribute.setObjectName("DialogAddAttribute")
        DialogAddAttribute.resize(379, 213)
        self.buttonBox = QtWidgets.QDialogButtonBox(DialogAddAttribute)
        self.buttonBox.setGeometry(QtCore.QRect(20, 160, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.label_att_name = QtWidgets.QLabel(DialogAddAttribute)
        self.label_att_name.setGeometry(QtCore.QRect(50, 10, 301, 28))
        self.label_att_name.setObjectName("label_att_name")
        self.lineEdit_name = QtWidgets.QLineEdit(DialogAddAttribute)
        self.lineEdit_name.setGeometry(QtCore.QRect(50, 40, 241, 25))
        self.lineEdit_name.setObjectName("lineEdit_name")
        self.radioButton_character = QtWidgets.QRadioButton(DialogAddAttribute)
        self.radioButton_character.setGeometry(QtCore.QRect(50, 80, 241, 23))
        self.radioButton_character.setObjectName("radioButton_character")
        self.radioButton_numeric = QtWidgets.QRadioButton(DialogAddAttribute)
        self.radioButton_numeric.setGeometry(QtCore.QRect(50, 120, 241, 23))
        self.radioButton_numeric.setObjectName("radioButton_numeric")

        self.retranslateUi(DialogAddAttribute)
        self.buttonBox.accepted.connect(DialogAddAttribute.accept)
        self.buttonBox.rejected.connect(DialogAddAttribute.reject)
        QtCore.QMetaObject.connectSlotsByName(DialogAddAttribute)

    def retranslateUi(self, DialogAddAttribute):
        _translate = QtCore.QCoreApplication.translate
        DialogAddAttribute.setWindowTitle(_translate("DialogAddAttribute", "Add Attribute"))
        self.label_att_name.setText(_translate("DialogAddAttribute", "Attribute name:"))
        self.radioButton_character.setText(_translate("DialogAddAttribute", "Character"))
        self.radioButton_numeric.setText(_translate("DialogAddAttribute", "Numeric"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    DialogAddAttribute = QtWidgets.QDialog()
    ui = Ui_DialogAddAttribute()
    ui.setupUi(DialogAddAttribute)
    DialogAddAttribute.show()
    sys.exit(app.exec_())
