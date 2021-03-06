# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_dialog_cases.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Dialog_cases(object):
    def setupUi(self, Dialog_cases):
        Dialog_cases.setObjectName("Dialog_cases")
        Dialog_cases.resize(1216, 694)
        self.gridLayout = QtWidgets.QGridLayout(Dialog_cases)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_2 = QtWidgets.QGroupBox(Dialog_cases)
        self.groupBox_2.setTitle("")
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label = QtWidgets.QLabel(self.groupBox_2)
        self.label.setMinimumSize(QtCore.QSize(0, 20))
        self.label.setMaximumSize(QtCore.QSize(16777215, 60))
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 2, 0, 1, 1)
        self.splitter = QtWidgets.QSplitter(self.groupBox_2)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName("splitter")
        self.tableWidget = QtWidgets.QTableWidget(self.splitter)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(0)
        self.tableWidget.setRowCount(0)
        self.textBrowser = QtWidgets.QTextBrowser(self.splitter)
        self.textBrowser.setObjectName("textBrowser")
        self.gridLayout_2.addWidget(self.splitter, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox_2, 2, 1, 1, 1)
        self.label_filename = QtWidgets.QLabel(Dialog_cases)
        self.label_filename.setMinimumSize(QtCore.QSize(0, 32))
        self.label_filename.setMaximumSize(QtCore.QSize(16777215, 32))
        self.label_filename.setWordWrap(True)
        self.label_filename.setObjectName("label_filename")
        self.gridLayout.addWidget(self.label_filename, 1, 1, 1, 1)
        self.groupBox = QtWidgets.QGroupBox(Dialog_cases)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setMinimumSize(QtCore.QSize(0, 72))
        self.groupBox.setMaximumSize(QtCore.QSize(16777215, 72))
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.pushButton_addfiles = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_addfiles.setGeometry(QtCore.QRect(150, 0, 231, 32))
        self.pushButton_addfiles.setObjectName("pushButton_addfiles")
        self.pushButton_autoassign = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_autoassign.setGeometry(QtCore.QRect(560, 0, 311, 32))
        self.pushButton_autoassign.setObjectName("pushButton_autoassign")
        self.pushButton_openfile = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_openfile.setGeometry(QtCore.QRect(150, 40, 541, 32))
        self.pushButton_openfile.setObjectName("pushButton_openfile")
        self.pushButton_view = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_view.setGeometry(QtCore.QRect(10, 40, 141, 32))
        self.pushButton_view.setObjectName("pushButton_view")
        self.pushButton_add = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_add.setGeometry(QtCore.QRect(10, 0, 141, 32))
        self.pushButton_add.setObjectName("pushButton_add")
        self.pushButton_delete = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_delete.setGeometry(QtCore.QRect(1010, 40, 171, 32))
        self.pushButton_delete.setObjectName("pushButton_delete")
        self.pushButton_import_cases = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_import_cases.setGeometry(QtCore.QRect(380, 0, 181, 32))
        self.pushButton_import_cases.setObjectName("pushButton_import_cases")
        self.pushButton_add_attribute = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_add_attribute.setGeometry(QtCore.QRect(870, 0, 191, 31))
        self.pushButton_add_attribute.setObjectName("pushButton_add_attribute")
        self.gridLayout.addWidget(self.groupBox, 0, 1, 1, 1)

        self.retranslateUi(Dialog_cases)
        QtCore.QMetaObject.connectSlotsByName(Dialog_cases)

    def retranslateUi(self, Dialog_cases):
        _translate = QtCore.QCoreApplication.translate
        Dialog_cases.setWindowTitle(_translate("Dialog_cases", "Cases"))
        self.label.setText(_translate("Dialog_cases", "If a case is selected and a file is open, right click on selected text in the file to mark as belonging to a case. Selected text can also be removed from a case. Text assigned to the selected case is underlined in red."))
        self.label_filename.setText(_translate("Dialog_cases", "."))
        self.pushButton_addfiles.setText(_translate("Dialog_cases", "Add File to case"))
        self.pushButton_autoassign.setToolTip(_translate("Dialog_cases", "<html><head/><body><p>Portions of file text can be assigned to a case through user determined start and end marks.</p></body></html>"))
        self.pushButton_autoassign.setText(_translate("Dialog_cases", "Auto assign file text"))
        self.pushButton_openfile.setText(_translate("Dialog_cases", "Open file to view and assign text to case"))
        self.pushButton_view.setToolTip(_translate("Dialog_cases", "<html><head/><body><p>View all the text assigned to the selected case.</p></body></html>"))
        self.pushButton_view.setText(_translate("Dialog_cases", "View case"))
        self.pushButton_add.setText(_translate("Dialog_cases", "Add case"))
        self.pushButton_delete.setText(_translate("Dialog_cases", "Delete case"))
        self.pushButton_import_cases.setToolTip(_translate("Dialog_cases", "<html><head/><body><p>Import from a <span style=\" font-weight:600;\">comma delimited</span> csv file.</p><p>The file must have a header row and the first column must have the unique case names or identifiers. Subsequent columns are attributes for each case.</p></body></html>"))
        self.pushButton_import_cases.setText(_translate("Dialog_cases", "Import cases"))
        self.pushButton_add_attribute.setText(_translate("Dialog_cases", "Add attribute"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog_cases = QtWidgets.QDialog()
    ui = Ui_Dialog_cases()
    ui.setupUi(Dialog_cases)
    Dialog_cases.show()
    sys.exit(app.exec_())

