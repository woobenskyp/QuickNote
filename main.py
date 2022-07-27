import os

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QAction, Qt, QFont, QPaintEvent, QKeySequence, QMouseEvent, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QListWidget, QListWidgetItem, QMenu, QPushButton, QVBoxLayout, \
    QWidget, QHBoxLayout, QSizePolicy, QLabel, QAbstractItemView
from NoteWindow import NoteWindow
import sqlite3
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(400, 500)
        self.setMinimumHeight(500)
        self.setMinimumWidth(390)
        self.setWindowTitle("Quick Note")
        self.setWindowIcon(QIcon('logo.svg'))

        self.noteWindows = []

        menubar = self.menuBar()
        addNew = QAction("New", self)
        addNew.setShortcut(QKeySequence("Ctrl+N"))
        addNew.triggered.connect(self.createNewNote)
        menubar.addAction(addNew)

        self.listWidget = ListWidget(self)
        self.listWidget.setFlow(QListWidget.LeftToRight)
        self.listWidget.setResizeMode(QListWidget.Adjust)
        self.listWidget.setGridSize(QSize(180, 200))
        self.listWidget.setViewMode(QListWidget.IconMode)
        self.setUpDateBase()
        self.listWidget.itemClicked.connect(self.openNote)
        self.loadNotes()

    def setMainWidget(self):
        if self.listWidget.count():
            self.setCentralWidget(self.listWidget)
        else:
            noNoteLabel = QLabel("You don't have any notes yet\nClick on the \"New\" button to create a new one")
            noNoteLabel.setAlignment(Qt.AlignCenter)
            noNoteLabel.setStyleSheet('font-size: 14px;')
            self.setCentralWidget(noNoteLabel)

    def createQuickNoteFolder(self):
        try:
            os.mkdir(os.path.join(str(Path.home()), 'Quick Note'))
        except:
            return

    def setUpDateBase(self):
        self.createQuickNoteFolder()
        self.connection = sqlite3.connect("note.db")
        self.cursor = self.connection.cursor()
        self.cursor.execute("CREATE TABLE IF NOT EXISTS Note (id int AUTO_INCREMENT PRIMARY KEY, title text, content text, creationDate text, modificationDate text)")
        self.connection.commit()

    def deleteNote(self, id):
        self.cursor.execute("Delete from Note where rowid = " + str(id))
        self.connection.commit()
        self.loadNotes()

    def loadNotes(self):
        results = self.cursor.execute("Select rowid, title, content from Note order by modificationDate desc")
        self.listWidget.clear()
        for (id, title, content) in results:
            itemWidget = Title(self.listWidget, id, title, content)
            itemWidget.clicked.connect(self.openNoteById)
            itemWidget.deleted.connect(self.deleteNote)
            item = QListWidgetItem()
            item.setSizeHint(QSize(180, 200))
            self.listWidget.addItem(item)
            self.listWidget.setItemWidget(item, itemWidget)
        self.setMainWidget()

    def openNoteById(self, item:int):
        self.noteWindows.append(NoteWindow(self, self.connection, item))

    def openNote(self, item:QListWidgetItem):
        itemWidget = self.listWidget.itemWidget(item)
        self.noteWindows.append(NoteWindow(self, self.connection, itemWidget.id))

    def createNewNote(self):
        self.noteWindows.append(NoteWindow(self, self.connection))

class Title(QWidget):
    clicked = Signal(int)
    deleted = Signal(int)

    def __init__(self, parent, id, title, content):
        super().__init__()
        self.parent = parent
        self.id = id
        self.title = title
        self.content = content

        self.titleWidget = QLabel(self.title)
        self.titleWidget.setStyleSheet('border: 0px;')
        self.titleWidget.setWordWrap(True)
        titleFont = QFont()
        titleFont.setPointSize(14)
        titleFont.setBold(True)
        self.titleWidget.setFont(titleFont)

        self.contentWidget = QLabel(self.content)
        self.contentWidget.setStyleSheet('border: 0px;')
        self.contentWidget.setFont(titleFont)
        self.contentWidget.setWordWrap(True)


        mainWidget = QWidget()
        mainWidget.setStyleSheet('background: white; box-shadow: 10px 10px 8px black; border-radius: 8px; border: 1px solid silver;')
        layout = QVBoxLayout()

        layout.addWidget(self.titleWidget)
        layout.addWidget(self.contentWidget)
        mainWidget.setLayout(layout)

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(8, 6, 8, 6)
        mainLayout.addWidget(mainWidget)

        self.setLayout(mainLayout)

    def mousePressEvent(self, event:QMouseEvent):
        if event.button() == Qt.LeftButton and not self.parent.contextJustClosed:
            self.clicked.emit(self.id)
        elif event.button() == Qt.LeftButton:
            self.parent.contextJustClosed = False
        elif event.button() == Qt.RightButton:
            self.on_context_menu(event.pos())


    def on_context_menu(self, pos):
        context = QMenu(self)
        deleteNoteAction = QAction("Delete Note", self)
        deleteNoteAction.triggered.connect(self.deleteNote)
        context.addAction(deleteNoteAction)
        context.exec(self.mapToGlobal(pos))
        self.parent.contextJustClosed = True

    def deleteNote(self):
        self.deleted.emit(self.id)


class ListWidget(QListWidget):
    def __init__(self, parentWindow):
        super().__init__()
        self.parentWindow = parentWindow
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.contextJustClosed = False

app = QApplication([])

window = MainWindow()
window.show()

app.exec()
