import sqlite3

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QImage, QPixmap, QPainter, QTextCharFormat, QTextListFormat, \
    QKeyEvent, QTextBlockFormat, QTextCursor, QKeySequence
from PySide6.QtWidgets import QMainWindow, QApplication, QTextEdit, QToolBar, QColorDialog, QLineEdit, QVBoxLayout, \
    QWidget, QMessageBox, QMenu, QPushButton
from datetime import datetime


class NoteContent(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("li { margin: 16px}")

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() == 16777220: #enter pressed
            if self.textCursor().currentList():
                currentList = self.textCursor().currentList()
                listItemCount = currentList.count()
                if listItemCount > 1 and (len(currentList.item(listItemCount - 1).text()) == 0 and len(
                        currentList.item(listItemCount - 2).text()) == 0):
                    currentList.removeItem(listItemCount - 1)
                    currentList.removeItem(listItemCount - 2)
                    self.resetCursorInPlace()
        elif e.key() == 16777219: #backspace pressed
            if self.textCursor().currentList():
                currentList = self.textCursor().currentList()
                listItemCount = currentList.count()
                if listItemCount == 1 and len(currentList.item(0).text()) == 0:
                    currentList.removeItem(0)
                    self.resetCursorInPlace()



    def setPreviousWidget(self, widget):
        self.previousWidget = widget

    def resetCursorInPlace(self):
        format = QTextBlockFormat()
        format.setIndent(0)
        self.textCursor().deletePreviousChar()
        self.textCursor().setBlockFormat(format)


class TitleEdit(QLineEdit):

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() == 16777220:
            self.nextWidget.setFocus()

    def setNextWidget(self, widget):
        self.nextWidget = widget


class NoteWindow(QMainWindow):
    def __init__(self, parentWindow, sqliteConnection, id=None):
        super().__init__()
        self.setWindowTitle("Quick Notes")
        self.setWindowIcon(QIcon('logo.svg'))

        self.setMinimumHeight(500)
        self.setMinimumWidth(380)

        self.parentWindow = parentWindow
        self.sqliteConnection = sqliteConnection
        self.id = id
        self.changeIsSaved = True

        self.currentColor = 'black'
        self.userChangedFormat = False

        self.title = TitleEdit()
        self.noteContent = NoteContent()
        self.setupWritingFields()

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(1, 1, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(self.title)
        mainLayout.addWidget(self.noteContent)

        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)

        self.toolbar = QToolBar("Main toolbar")
        self.setupToolbar()
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

        menuBar = self.menuBar()
        saveAction = QAction('Save', self)
        saveAction.setShortcut(QKeySequence('Ctrl+S'))
        saveAction.triggered.connect(self.saveNote)
        menuBar.addAction(saveAction)

        if self.id:
            self.loadNote()
        else:
            self.noteContent.textChanged.connect(self.changeOccured)
            self.title.textChanged.connect(self.changeOccured)
        self.show()

    def setupWritingFields(self):
        self.title.setStyleSheet("padding: 8px; padding-top: 8px; border: white")
        titleFont = QFont("Roboto", 12)
        titleFont.setBold(True)
        self.title.setFont(titleFont)
        self.title.setPlaceholderText("Title")

        self.title.setNextWidget(self.noteContent)
        self.noteContent.setPreviousWidget(self.title)
        self.noteContent.setAcceptRichText(True)
        self.noteContent.setStyleSheet("padding: 0px 6px; background: white; border: white;")
        self.noteContent.setFont(QFont("open sans", 11))
        self.noteContent.currentCharFormatChanged.connect(self.formatChanged)
        self.noteContent.cursorPositionChanged.connect(self.onListFormatChanged)

    def setupToolbar(self):
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setStyleSheet("QToolBar{background: white; padding: 0px 4px;} QToolButton{padding: 4px 4px;}")
        self.toolbar.setMovable(False)
        self.toolbar.visibilityChanged.connect(self.onRemoveToolbar)

        self.checkList = QAction(QIcon('checklist.svg'), 'Check List', self)
        self.checkList.setCheckable(True)
        self.checkList.triggered.connect(self.onCheckListActionClicked)
        self.toolbar.addAction(self.checkList)

        self.bulletList = QAction(QIcon('bulletlist.svg'), 'Bullet List', self)
        self.bulletList.setCheckable(True)
        self.bulletList.triggered.connect(self.onBulletListActionClicked)
        self.toolbar.addAction(self.bulletList)

        self.orderedList = QAction(QIcon('orderedlist.svg'), 'Ordered List', self)
        self.orderedList.setCheckable(True)
        self.orderedList.triggered.connect(self.onOrderedListActionClicked)
        self.toolbar.addAction(self.orderedList)

        self.toolbar.addSeparator()

        self.bold = QAction(QIcon("bold.svg"), "Bold", self)
        self.bold.setCheckable(True)
        self.bold.triggered.connect(self.onBoldClicked)
        self.toolbar.addAction(self.bold)

        self.italic = QAction(QIcon('italic.svg'), 'Italic', self)
        self.italic.setCheckable(True)
        self.italic.triggered.connect(self.onItalicClicked)
        self.toolbar.addAction(self.italic)

        self.underlined = QAction(QIcon("underlined.svg"), 'Underline', self)
        self.underlined.setCheckable(True)
        self.underlined.triggered.connect(self.onUnderlinedClicked)
        self.toolbar.addAction(self.underlined)

        self.colorIconImage = QPixmap("color.svg")
        self.changeColorAction = QAction(self.imageToColoredSvg(self.colorIconImage), "Change Color", self)
        self.changeColorAction.triggered.connect(self.openColorDialog)
        self.toolbar.addAction(self.changeColorAction)

    def changeOccured(self):
        self.changeIsSaved = False

    def loadNote(self):
        title, content = self.sqliteConnection.cursor().execute("Select title, content from Note where rowid=" + str(self.id)).fetchone()
        self.setWindowTitle(title)
        self.title.setText(title)
        self.noteContent.setHtml(content)
        self.fixBadLists()

        self.title.textChanged.connect(self.changeTitle)
        self.noteContent.textChanged.connect(self.changeOccured)
        self.title.textChanged.connect(self.changeOccured)

    def changeTitle(self, title):
        if len(title):
            self.setWindowTitle(title)
        else:
            self.setWindowTitle("Quick Note")


    def fixBadLists(self):
        self.noteContent.setFocus()
        for i in range(len(self.noteContent.toPlainText())):
            cursor = self.noteContent.textCursor()
            cursor.setPosition(i)
            self.noteContent.setTextCursor(cursor)

            if self.noteContent.textCursor().currentList():
                if self.noteContent.textCursor().currentList().format().style() == QTextListFormat.ListCircle:
                    self.onCheckListActionClicked(True)
        cursor = self.noteContent.textCursor()
        cursor.setPosition(0)
        self.noteContent.setTextCursor(cursor)

    def closeEvent(self, e):
        if self.parentWindow.isVisible():
            self.parentWindow.loadNotes()
        if not self.changeIsSaved:
            userDecision = QMessageBox.question(self, "Quick Note", "Save your changes or Discard them", buttons=QMessageBox.Cancel|QMessageBox.Discard|QMessageBox.Save)
            print(e)
            if userDecision == QMessageBox.Discard:
                pass
            elif userDecision == QMessageBox.Save:
                self.saveNote()
            else:
                e.ignore()


    def saveNote(self):
        if self.id:
            query = "Update Note set title=?, content=?, modificationDate=? where rowid =?"
            self.sqliteConnection.cursor().execute(query, (self.title.text(), self.noteContent.toHtml(), datetime.now().strftime('%m/%d/%Y, %H:%M:%S'), self.id))
            self.sqliteConnection.commit()
        else:
            self.sqliteConnection.cursor().execute('INSERT INTO Note (title, content, creationDate, modificationDate) VALUES (?, ?, ?, ?)', (self.title.text(), self.noteContent.toHtml(), datetime.now().strftime('%m/%d/%Y, %H:%M:%S'), datetime.now().strftime('%m/%d/%Y, %H:%M:%S')))
            self.sqliteConnection.commit()
        QMessageBox.information(self, "Quick Note", "The note has been saved")
        self.changeIsSaved = True

    def onRemoveToolbar(self):
        self.toolbar.setVisible(True)

    def onBoldClicked(self, checked):
        self.userChangedFormat = True
        if checked:
            self.noteContent.setFontWeight(QFont.Bold)
        else:
            self.noteContent.setFontWeight(QFont.Normal)

    def onItalicClicked(self, checked):
        self.userChangedFormat = True
        self.noteContent.setFontItalic(checked)

    def onUnderlinedClicked(self, checked):
        self.userChangedFormat = True
        self.noteContent.setFontUnderline(checked)

    def openColorDialog(self):
        self.userChangedFormat = True
        self.currentColor = QColorDialog.getColor(QColor(self.currentColor), self)
        self.noteContent.setTextColor(self.currentColor)
        self.changeColorAction.setIcon(self.imageToColoredSvg(self.colorIconImage, self.currentColor))

    def imageToColoredSvg(self, image, color='black'):
        qp = QPainter(image)
        qp.setCompositionMode(QPainter.CompositionMode_SourceIn)
        qp.fillRect(image.rect(), QColor(color))
        qp.end()
        return QIcon(image)

    def formatChanged(self, format):
        if (self.userChangedFormat):
            self.userChangedFormat = False
        else:
            self.bold.setChecked(format.fontWeight() == QFont.Bold)
            self.italic.setChecked(format.fontItalic())
            self.underlined.setChecked(format.fontUnderline())
            self.changeColorAction.setIcon(self.imageToColoredSvg(self.colorIconImage, format.foreground().color()))

    def onListFormatChanged(self):
        isBulletList = False
        isOrderedList = False
        isCheckList = False
        if self.noteContent.textCursor().currentList():
            if self.noteContent.textCursor().currentList().format().style() == QTextListFormat.ListDisc:
                isBulletList = True
            elif self.noteContent.textCursor().currentList().format().style() == QTextListFormat.ListDecimal:
                isOrderedList = True
            elif self.noteContent.textCursor().block().blockFormat().marker() == QTextBlockFormat.MarkerType.Unchecked or \
                    self.noteContent.textCursor().block().blockFormat().marker() == QTextBlockFormat.MarkerType.Checked:
                isCheckList = True

        self.bulletList.setChecked(isBulletList)
        self.orderedList.setChecked(isOrderedList)
        self.checkList.setChecked(isCheckList)

    def onCheckListActionClicked(self, checked):
        self.userChangedFormat = True
        if checked:
            format = QTextBlockFormat()
            format.setIndent(0)
            format.setLeftMargin(-26)
            format.setMarker(QTextBlockFormat.MarkerType.Unchecked)
            self.noteContent.textCursor().setBlockFormat(format)
            self.noteContent.textCursor().createList(QTextListFormat.ListCircle)

            self.orderedList.setChecked(False)
            self.bulletList.setChecked(False)
        else:
            format = QTextBlockFormat()
            format.setIndent(0)
            self.noteContent.textCursor().setBlockFormat(format)

    def onBulletListActionClicked(self, checked):
        self.userChangedFormat = True
        if checked:
            format = QTextBlockFormat()
            format.setIndent(0)
            format.setLeftMargin(0)
            self.noteContent.textCursor().setBlockFormat(format)
            self.noteContent.textCursor().createList(QTextListFormat.ListDisc)


            self.orderedList.setChecked(False)
            self.checkList.setChecked(False)
        else:
            format = QTextBlockFormat()
            format.setIndent(0)
            self.noteContent.textCursor().setBlockFormat(format)

    def onOrderedListActionClicked(self, checked):
        self.userChangedFormat = True
        if checked:
            self.bulletList.setChecked(False)
            self.checkList.setChecked(False)
            self.onCheckListActionClicked(False)

            self.noteContent.textCursor().createList(QTextListFormat.ListDecimal)
        else:
            format = QTextBlockFormat()
            format.setIndent(0)
            self.noteContent.textCursor().setBlockFormat(format)