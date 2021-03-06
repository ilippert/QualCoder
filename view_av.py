# -*- coding: utf-8 -*-

'''
Copyright (c) 2020 Colin Curtain

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Author: Colin Curtain (ccbogel)
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
'''

from copy import deepcopy
import datetime
import logging
import os
import platform
from random import randint
import re
import sys
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.Qt import QHelpEvent
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush
vlc_msg = ""
try:
    import vlc
except Exception as e:
    if sys.platform.startswith("win"):
        imp = False
    if not imp:
        msg = "view_av. Cannot import vlc\n"
        msg += str(e) + "\n"
        msg += "Ensure you have 64 bit python AND 64 bit VLC installed OR\n"
        msg += "32 bit python AND 32 bit VLC installed."
        print(msg)
        vlc_msg = msg

from add_item_name import DialogAddItemName
from color_selector import DialogColorSelect
from color_selector import colors
from confirm_delete import DialogConfirmDelete
from GUI.ui_dialog_code_av import Ui_Dialog_code_av
from GUI.ui_dialog_view_av import Ui_Dialog_view_av
from memo import DialogMemo
from select_file import DialogSelectFile

path = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


def exception_handler(exception_type, value, tb_obj):
    """ Global exception handler useful in GUIs.
    tb_obj: exception.__traceback__ """
    tb = '\n'.join(traceback.format_tb(tb_obj))
    text = 'Traceback (most recent call last):\n' + tb + '\n' + exception_type.__name__ + ': ' + str(value)
    print(text)
    logger.error(_("Uncaught exception: ") + text)
    QtWidgets.QMessageBox.critical(None, _('Uncaught Exception'), text)

def msecs_to_mins_and_secs(msecs):
    """ Convert milliseconds to minutes and seconds.
    msecs is an integer. Minutes and seconds output is a string."""

    secs = int(msecs / 1000)
    mins = int(secs / 60)
    remainder_secs = str(secs - mins * 60)
    if len(remainder_secs) == 1:
        remainder_secs = "0" + remainder_secs
    return str(mins) + "." + remainder_secs


class DialogCodeAV(QtWidgets.QDialog):
    """ View and code audio and video segments.
    Create codes and categories.  """

    app = None
    dialog_list = None
    parent_textEdit = None
    filename = None
    files = []
    file_ = None
    codes = []
    categories = []
    code_text = []
    ddialog = None
    media_data = None
    instance = None
    media_player = None
    media = None
    metadata = None
    is_paused = False
    segment = {}
    segments = []
    text_for_segment = {}  # when linking text to segment
    segment_for_text = None  # when linking segment to text
    timer = QtCore.QTimer()
    play_segment_end = None

    # for transcribed text
    annotations = []
    code_text = []
    transcription = None  # A tuple of id, fulltext, name
    # transcribed timepositions as list of [text_pos0, text_pos1, milliseconds]
    time_positions = []

    def __init__(self, app, parent_textEdit, dialog_list):
        """ Show list of audio and video files.
        Can create a transcribe file from the audio / video.
        """

        super(DialogCodeAV,self).__init__()
        sys.excepthook = exception_handler
        self.app = app
        self.dialog_list = dialog_list
        self.parent_textEdit = parent_textEdit
        if vlc_msg != "":
            self.parent_textEdit.append(vlc_msg)
        self.codes = []
        self.categories = []
        self.annotations = []
        self.code_text = []
        self.time_positions = []
        self.transcription = None
        self.media_data = None
        self.segment['start'] = None
        self.segment['end'] = None
        self.segment['start_msecs'] = None
        self.segment['end_msecs'] = None
        self.play_segment_end = None
        self.segments = []
        self.text_for_segment = {'cid': None, 'fid': None, 'seltext': None, 'pos0': None, 'pos1': None, 'owner': None, 'memo': None, 'date': None, 'avid': None}
        self.segment_for_text = None
        self.get_codes_and_categories()
        QtWidgets.QDialog.__init__(self)
        self.ui = Ui_Dialog_code_av()
        self.ui.setupUi(self)
        self.ui.splitter.setSizes([100, 200])
        # until any media is selected disable some widgets
        self.ui.pushButton_play.setEnabled(False)
        self.ui.pushButton_stop.setEnabled(False)
        self.ui.pushButton_coding.setEnabled(False)
        self.ui.horizontalSlider.setEnabled(False)

        # Prepare textEdit for coding transcribed text
        self.ui.textEdit.setPlainText("")
        self.ui.textEdit.setAutoFillBackground(True)
        self.ui.textEdit.setToolTip("")
        self.ui.textEdit.setMouseTracking(True)
        self.ui.textEdit.setReadOnly(True)
        self.eventFilterTT = ToolTip_EventFilter()
        self.ui.textEdit.installEventFilter(self.eventFilterTT)
        self.ui.textEdit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.textEdit.customContextMenuRequested.connect(self.textEdit_menu)

        font = 'font: ' + str(self.app.settings['fontsize']) + 'pt '
        font += '"' + self.app.settings['font'] + '";'
        self.setStyleSheet(font)
        font = 'font: ' + str(self.app.settings['treefontsize']) + 'pt '
        font += '"' + self.app.settings['font'] + '";'
        self.ui.treeWidget.setStyleSheet(font)
        self.ui.label_coder.setText(_("Coder: ") + self.app.settings['codername'])
        self.setWindowTitle(_("Media coding"))
        self.ui.pushButton_select.pressed.connect(self.select_media)
        #self.ui.checkBox_show_coders.stateChanged.connect(self.show_or_hide_coders)
        self.ui.treeWidget.setDragEnabled(True)
        self.ui.treeWidget.setAcceptDrops(True)
        self.ui.treeWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.ui.treeWidget.viewport().installEventFilter(self)
        self.ui.treeWidget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.treeWidget.customContextMenuRequested.connect(self.tree_menu)
        self.fill_tree()

        # My solution to getting gui mouse events by putting vlc video in another dialog
        # A display-dialog named ddialog
        # Otherwise, the vlc player hogs all the mouse events
        self.ddialog = QtWidgets.QDialog()
        # Enable custom window hint
        self.ddialog.setWindowFlags(self.ddialog.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        # Disable close button, only close through closing the Ui_Dialog_code_av
        self.ddialog.setWindowFlags(self.ddialog.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.ddialog.resize(640, 480)
        self.ddialog.gridLayout = QtWidgets.QGridLayout(self.ddialog)
        self.ddialog.dframe = QtWidgets.QFrame(self.ddialog)
        self.ddialog.dframe.setObjectName("frame")
        if platform.system() == "Darwin":  # For MacOS
            self.ddialog.dframe = QtWidgets.QMacCocoaViewContainer(0)
        self.palette = self.ddialog.dframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
        self.ddialog.dframe.setPalette(self.palette)
        self.ddialog.dframe.setAutoFillBackground(True)
        self.ddialog.gridLayout.addWidget(self.ddialog.dframe, 0, 0, 0, 0)
        self.ddialog.move(self.mapToGlobal(QtCore.QPoint(40, 20)))
        self.ddialog.show()

        # Create a vlc instance with an empty vlc media player
        self.instance = vlc.Instance()
        self.mediaplayer = self.instance.media_player_new()
        self.mediaplayer.video_set_mouse_input(False)
        self.mediaplayer.video_set_key_input(False)
        self.ui.horizontalSlider.sliderMoved.connect(self.set_position)
        self.ui.horizontalSlider.sliderPressed.connect(self.set_position)
        self.ui.pushButton_play.clicked.connect(self.play_pause)
        self.ui.pushButton_stop.clicked.connect(self.stop)
        self.ui.horizontalSlider_vol.valueChanged.connect(self.set_volume)
        self.ui.pushButton_coding.pressed.connect(self.create_or_clear_segment)
        self.ui.comboBox_tracks.currentIndexChanged.connect(self.audio_track_changed)

        # Set the scene for coding stripes
        # Matches the designer file graphics view size
        self.scene_width = 990
        self.scene_height = 110
        self.scene = GraphicsScene(self.scene_width, self.scene_height)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

    def get_codes_and_categories(self):
        """ Called from init, delete category/code, event_filter. """

        self.codes, self.categories = self.app.get_data()

    def fill_tree(self):
        """ Fill tree widget, tope level items are main categories and unlinked codes. """

        cats = deepcopy(self.categories)
        codes = deepcopy(self.codes)
        self.ui.treeWidget.clear()
        self.ui.treeWidget.setColumnCount(3)
        self.ui.treeWidget.setHeaderLabels([_("Name"), _("Id"), _("Memo")])
        if self.app.settings['showids'] == 'False':
            self.ui.treeWidget.setColumnHidden(1, True)
        self.ui.treeWidget.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.ui.treeWidget.header().setStretchLastSection(False)
        # add top level categories
        remove_list = []
        for c in cats:
            if c['supercatid'] is None:
                memo = ""
                if c['memo'] != "":
                    memo = "Memo"
                top_item = QtWidgets.QTreeWidgetItem([c['name'], 'catid:' + str(c['catid']), memo])
                top_item.setToolTip(0, c['owner'] + "\n" + c['date'])
                self.ui.treeWidget.addTopLevelItem(top_item)
                remove_list.append(c)
        for item in remove_list:
            #try:
            cats.remove(item)
            #except Exception as e:
            #    print(e, item)

        ''' Add child categories. Look at each unmatched category, iterate through tree
        to add as child, then remove matched categories from the list. '''
        count = 0
        while len(cats) > 0 or count < 10000:
            remove_list = []
            #logger.debug("cats:" + str(cats))
            for c in cats:
                it = QtWidgets.QTreeWidgetItemIterator(self.ui.treeWidget)
                item = it.value()
                while item:  # while there is an item in the list
                    if item.text(1) == 'catid:' + str(c['supercatid']):
                        memo = ""
                        if c['memo'] != "":
                            memo = "Memo"
                        child = QtWidgets.QTreeWidgetItem([c['name'], 'catid:' + str(c['catid']), memo])
                        child.setToolTip(0, c['owner'] + "\n" + c['date'])
                        item.addChild(child)
                        remove_list.append(c)
                    it += 1
                    item = it.value()
            for item in remove_list:
                cats.remove(item)
            count += 1

        # add unlinked codes as top level items
        remove_items = []
        for c in codes:
            if c['catid'] is None:
                memo = ""
                if c['memo'] != "":
                    memo = "Memo"
                top_item = QtWidgets.QTreeWidgetItem([c['name'], 'cid:' + str(c['cid']), memo])
                top_item.setToolTip(0, c['owner'] + "\n" + c['date'])
                top_item.setBackground(0, QBrush(QtGui.QColor(c['color']), Qt.SolidPattern))
                top_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
                self.ui.treeWidget.addTopLevelItem(top_item)
                remove_items.append(c)
        for item in remove_items:
            codes.remove(item)

        # add codes as children
        for c in codes:
            it = QtWidgets.QTreeWidgetItemIterator(self.ui.treeWidget)
            item = it.value()
            while item:
                if item.text(1) == 'catid:' + str(c['catid']):
                    memo = ""
                    if c['memo'] != "":
                        memo = _("Memo")
                    child = QtWidgets.QTreeWidgetItem([c['name'], 'cid:' + str(c['cid']), memo])
                    child.setBackground(0, QBrush(QtGui.QColor(c['color']), Qt.SolidPattern))
                    child.setToolTip(0, c['owner'] + "\n" + c['date'])
                    child.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsDragEnabled)
                    item.addChild(child)
                    c['catid'] = -1  # make unmatchable
                it += 1
                item = it.value()
        self.ui.treeWidget.expandAll()

    def select_media(self):
        """ Get all the media files. A dialog of filenames is presented to the user.
        The selected media file is then displayed for coding. """

        media_files = []
        cur = self.app.conn.cursor()
        cur.execute("select name, id, memo, owner, date, mediapath from source where \
            substr(mediapath,1,6) in ('/audio','/video') order by name")
        result = cur.fetchall()
        for row in result:
            media_files.append({'name': row[0], 'id': row[1], 'memo': row[2],
                'owner': row[3], 'date': row[4], 'mediapath': row[5]})

        ui = DialogSelectFile(media_files, _("Select file to view"), "single")
        ok = ui.exec_()
        if not ok:
            return
        self.media_data = ui.get_selected()
        self.ui.pushButton_play.setEnabled(True)
        self.ui.pushButton_stop.setEnabled(True)
        self.ui.horizontalSlider.setEnabled(True)
        self.ui.pushButton_coding.setEnabled(True)
        self.load_media()
        self.load_segments()

    def load_segments(self):
        """ Get coded segments for this file and for this coder.
        Called from select_media. """

        if self.media_data is None:
            return
        self.segments = []
        sql = "select avid, id, pos0, pos1, code_av.cid, code_av.memo, code_av.date, "
        sql += " code_av.owner, code_name.name, code_name.color from code_av"
        sql += " join code_name on code_name.cid=code_av.cid"
        sql += " where id=? "
        sql += " and code_av.owner=? "
        values = [self.media_data['id']]
        values.append(self.app.settings['codername'])
        cur = self.app.conn.cursor()
        cur.execute(sql, values)
        code_results = cur.fetchall()
        for row in code_results:
            self.segments.append({'avid': row[0], 'id': row[1], 'pos0': row[2],
            'pos1': row[3], 'cid':row[4], 'memo': row[5], 'date': row[6],
            'owner': row[7], 'codename': row[8], 'color': row[9], 'y': 10})
        # Fix overlapping segments by incrementing y values so segment is shown on a different line
        for i in range(0, len(self.segments) - 1):
            for j in range(i + 1, len(self.segments)):
                if (self.segments[j]['pos0'] >= self.segments[i]['pos0'] and  \
                self.segments[j]['pos0'] <= self.segments[i]['pos1'] and \
                self.segments[i]['y'] == self.segments[j]['y']) or \
                (self.segments[j]['pos0'] <= self.segments[i]['pos0'] and  \
                self.segments[j]['pos1'] >= self.segments[i]['pos0'] and \
                self.segments[i]['y'] == self.segments[j]['y']):
                    #print("\nOVERLAP i:", self.segments[i]['pos0'], self.segments[i]['pos1'], self.segments[i]['y'], self.segments[i]['codename'])
                    #print("OVERLAP j:", self.segments[j]['pos0'], self.segments[j]['pos1'], self.segments[j]['y'], self.segments[j]['codename'])
                    # to overcome the overlap, add to the y value of the i segment
                    self.segments[j]['y'] += 10
        # Draw coded segments in scene
        scaler = self.scene_width / self.media.get_duration()
        self.scene.clear()
        for s in self.segments:
            self.scene.addItem(SegmentGraphicsItem(s, scaler, self.text_for_segment, self))

    def load_media(self):
        """ Add media to media dialog. """

        self.ddialog.setWindowTitle(self.media_data['mediapath'])
        self.setWindowTitle(self.media_data['mediapath'])
        try:
            self.media = self.instance.media_new(self.app.project_path + self.media_data['mediapath'])
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, _("Media not found"),
                str(e) +"\n" + self.app.project_path + self.media_data['mediapath'])
            self.closeEvent()
            return
        # clear comboBox tracks options and reload when playing/pausing
        self.ui.comboBox_tracks.clear()
        # Put the media in the media player
        self.mediaplayer.set_media(self.media)
        # Parse the metadata of the file
        self.media.parse()
        self.mediaplayer.video_set_mouse_input(False)
        self.mediaplayer.video_set_key_input(False)
        # The media player has to be connected to the QFrame (otherwise the
        # video would be displayed in it's own window). This is platform
        # specific, so we must give the ID of the QFrame (or similar object) to
        # vlc. Different platforms have different functions for this
        if platform.system() == "Linux": # for Linux using the X Server
            #self.mediaplayer.set_xwindow(int(self.ui.frame.winId()))
            self.mediaplayer.set_xwindow(int(self.ddialog.dframe.winId()))
        elif platform.system() == "Windows": # for Windows
            self.mediaplayer.set_hwnd(int(self.ddialog.winId()))
        elif platform.system() == "Darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.ddialog.winId()))
        msecs = self.media.get_duration()
        self.media_duration_text = "Duration: " + msecs_to_mins_and_secs(msecs)
        self.ui.label_time_2.setText(self.media_duration_text)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)
        # Get the transcribed text and fill textedit
        cur = self.app.conn.cursor()
        cur.execute("select id, fulltext, name from source where name = ?", [self.media_data['name'] + ".transcribed"])
        self.transcription = cur.fetchone()
        if self.transcription is None:
            return
        self.ui.textEdit.setText(self.transcription[1])
        self.ui.textEdit.ensureCursorVisible()
        self.get_timestamps_from_transcription()

        # get text annotations
        cur = self.app.conn.cursor()
        cur.execute("select anid, fid, pos0, pos1, memo, owner, date from annotation where owner=? and fid=?",
            [self.app.settings['codername'], self.transcription[0]])
        result = cur.fetchall()
        for row in result:
            self.annotations.append({'anid': row[0], 'fid': row[1], 'pos0': row[2],
            'pos1': row[3], 'memo': row[4], 'owner': row[5], 'date': row[6]})
        self.get_coded_text_update_eventfilter_tooltips()

    def get_coded_text_update_eventfilter_tooltips(self):
        """ Called by load_media, update_dialog_codes_and_categories,
        Segment_Graphics_Item.link_text_to_segment. """

        if self.transcription is None:
            return
        # Get code text for this file and for this coder
        values = [self.transcription[0], self.app.settings['codername']]
        cur = self.app.conn.cursor()
        self.code_text = []
        sql = "select code_text.cid, code_text.fid, seltext, code_text.pos0, code_text.pos1, "
        sql += "code_text.owner, code_text.date, code_text.memo, code_text.avid,code_av.pos0, code_av.pos1 "
        sql += "from code_text left join code_av on code_text.avid = code_av.avid "
        sql += " where code_text.fid=? and code_text.owner=?"
        cur.execute(sql, values)
        code_results = cur.fetchall()
        for row in code_results:
            self.code_text.append({'cid': row[0], 'fid': row[1], 'seltext': row[2],
            'pos0': row[3], 'pos1': row[4], 'owner': row[5], 'date': row[6],
            'memo': row[7], 'avid': row[8], 'av_pos0': row[9], 'av_pos1': row[10]})

        # Update filter for tooltip and redo formatting
        self.eventFilterTT.setCodes(self.code_text, self.codes)
        self.unlight()
        self.highlight()

    def get_timestamps_from_transcription(self):
        """ Get a list of starting/ending characterpositions and time in milliseconds
        from transcribed text file.

        Example formats:  [00:34:12] [45:33] [01.23.45] [02.34] #00:12:34.567#
        09:33:04,100 --> 09:33:09,600

        Converts hh mm ss to milliseconds with text positions stored in a list
        The list contains lists of [text_pos0, text_pos1, milliseconds] """

        mmss1 = "\[[0-9]?[0-9]:[0-9][0-9]\]"
        hhmmss1 = "\[[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\]"
        mmss2 = "\[[0-9]?[0-9]\.[0-9][0-9]\]"
        hhmmss2 = "\[[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9]\]"
        hhmmss_sss = "#[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9]{1,3}#"  # allow for 1 to 3 msecs digits
        srt = "[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]\s-->\s[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]"

        self.time_positions = []
        for match in re.finditer(mmss1, self.transcription[1]):
            stamp = match.group()[1:-1]
            s = stamp.split(':')
            try:
                msecs = (int(s[0]) * 60 + int(s[1])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss1, self.transcription[1]):
            stamp = match.group()[1:-1]
            s = stamp.split(':')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s[2])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(mmss2, self.transcription[1]):
            stamp = match.group()[1:-1]
            s = stamp.split('.')
            try:
                msecs = (int(s[0]) * 60 + int(s[1])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss2, self.transcription[1]):
            stamp = match.group()[1:-1]
            s = stamp.split('.')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s[2])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss_sss, self.transcription[1]):
            # Format #00:12:34.567#
            stamp = match.group()[1:-1]
            text_hms = stamp.split(':')
            text_secs = text_hms[2].split('.')[0]
            text_msecs = text_hms[2].split('.')[1]
            # adjust msecs to 1000's for 1 or 2 digit strings
            if len(text_msecs) == 1:
                text_msecs += "00"
            if len(text_msecs) == 2:
                text_msecs += "0"
            try:
                msecs = (int(text_hms[0]) * 3600 + int(text_hms[1]) * 60 + int(text_secs)) * 1000 + int(text_msecs)
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(srt, self.transcription[1]):
            # Format 09:33:04,100 --> 09:33:09,600  skip the arrow and second time position
            stamp = match.group()[0:12]
            s = stamp.split(':')
            s2 = s[2].split(',')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s2[0])) * 1000 + int(s2[1])
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        #print(self.time_positions)

    def set_position(self):
        """ Set the movie position according to the position slider.
        The vlc MediaPlayer needs a float value between 0 and 1, Qt uses
        integer variables, so you need a factor; the higher the factor, the
        more precise are the results (1000 should suffice).
        """

        self.timer.stop()
        pos = self.ui.horizontalSlider.value()
        self.mediaplayer.set_position(pos / 1000.0)
        self.timer.start()

    def audio_track_changed(self):
        """ Audio track changed.
        The video needs to be playing/paused before the combobox is filled with track options.
        The combobox only has positive integers."""

        text = self.ui.comboBox_tracks.currentText()
        if text == "":
            text = 1
        #print("text: ", text)
        success = self.mediaplayer.audio_set_track(int(text))
        #print("changed audio ", success)

    def play_pause(self):
        """ Toggle play or pause status. """

        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.ui.pushButton_play.setText(_("Play"))
            self.is_paused = True
            self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return
            self.mediaplayer.play()
            self.ui.pushButton_play.setText(_("Pause"))
            self.timer.start()
            self.is_paused = False
            self.play_segment_end = None

    def stop(self):
        """ Stop vlc player. Set position slider to the start.
         If multiple audio tracks are shown in the combobox, set the audio track to the first index.
         This is because when beginning play again, the audio track reverts to the first track.
         Programatically setting the audio track to other values does not work."""

        self.mediaplayer.stop()
        self.ui.pushButton_play.setText(_("Play"))
        self.timer.stop()
        self.ui.horizontalSlider.setProperty("value", 0)
        self.play_segment_end = None

        # set combobox display of audio track to the first one, or leave it blank if it contains no items
        if self.ui.comboBox_tracks.count() > 0:
            self.ui.comboBox_tracks.setCurrentIndex(0)

    def set_volume(self, volume):
        """ Set the volume. """

        self.mediaplayer.audio_set_volume(volume)

    def update_ui(self):
        """ Updates the user interface. Update the slider position to match media.
         Adds audio track options to combobox.
         Updates the current displayed media time. """

        # update audio track list, only works if media is playing
        if self.mediaplayer.audio_get_track_count() > 0 and self.ui.comboBox_tracks.count() == 0:
            tracks = self.mediaplayer.audio_get_track_description()
            for t in tracks:
                if t[0] > 0:
                    #print(t[0], t[1])  # track number and track name
                    self.ui.comboBox_tracks.addItem(str(t[0]))

        # Set the slider's position to its corresponding media position
        # Note that the setValue function only takes values of type int,
        # so we must first convert the corresponding media position.
        media_pos = int(self.mediaplayer.get_position() * 1000)
        self.ui.horizontalSlider.setValue(media_pos)

        # update label_time
        msecs = self.mediaplayer.get_time()
        self.ui.label_time.setText(_("Time: ") + msecs_to_mins_and_secs(msecs))

        # Check if segments need to be reloaded
        # This only updates if the media is playing, not ideal, but works
        for i in self.scene.items():
            if isinstance(i, SegmentGraphicsItem) and i.reload_segment is True:
                self.load_segments()

        """ For long transcripts, update the relevant text position in the textEdit to match the
        video's current position.
        time_postion list item: [text_pos0, text_pos1, milliseconds]
        """
        if self.ui.checkBox_scroll_transcript.isChecked() and self.transcription is not None and self.ui.textEdit.toPlainText() != "":
            for i in range(1, len(self.time_positions)):
                if msecs > self.time_positions[i - 1][2] and msecs < self.time_positions[i][2]:
                    text_pos = self.time_positions[i][0]
                    textCursor = self.ui.textEdit.textCursor()
                    textCursor.setPosition(text_pos)
                    self.ui.textEdit.setTextCursor(textCursor)

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()
            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.stop()

        # If only playing a segment, need to pause at end of segment
        if self.play_segment_end is not None:
            if self.play_segment_end < msecs:
                self.play_segment_end = None
                self.play_pause()

    def closeEvent(self, event):
        """ Stop the vlc player on close. """

        self.ddialog.close()
        self.stop()

    def create_or_clear_segment(self):
        """ Make the start end end points of the segment of time.
        Use minutes and seconds, and milliseconds formats for the time.
        Can also clear the segment by pressing the button when it says Clear segment.
        clear segment text is changed to Start segment once a segment is assigned to a code.
        """

        if self.ui.pushButton_coding.text() == _("Clear segment"):
            self.clear_segment()
            return
        time = self.ui.label_time.text()
        time = time[6:]
        time_msecs = self.mediaplayer.get_time()
        if self.segment['start'] is None:
            self.segment['start'] = time
            self.segment['start_msecs'] = time_msecs
            self.segment['memo'] = ""
            self.ui.pushButton_coding.setText(_("End segment"))
            self.ui.label_segment.setText(_("Segment: ") + str(self.segment['start']) + " - ")
            return
        if self.segment['start'] is not None and self.segment['end'] is None:
            self.segment['end'] = time
            self.segment['end_msecs'] = time_msecs
            self.ui.pushButton_coding.setText(_("Clear segment"))

            # check and reverse start and end times if start is greater than the end
            if float(self.segment['start']) > float(self.segment['end']):
                tmp = self.segment['start']
                tmp_msecs = self.segment['start_msecs']
                self.segment['start'] = self.segment['end']
                self.segment['start_msecs'] = self.segment['end_msecs']
                self.segment['end'] = tmp
                self.segment['end_msecs'] = tmp_msecs
            text = _("Segment: ") + str(self.segment['start']) + " - " + self.segment['end']
            self.ui.label_segment.setText(text)

    def tree_menu(self, position):
        """ Context menu for treeWidget items.
        Add, rename, memo, move or delete code or category. Change code color. """

        menu = QtWidgets.QMenu()
        selected = self.ui.treeWidget.currentItem()
        #logger.debug("selected paremt: " + str(selected.parent()))
        #logger.debug("index: " + str(self.ui.treeWidget.currentIndex()))
        ActionItemAssignSegment = None
        if self.segment['end_msecs'] is not None and self.segment['start_msecs'] is not None:
            ActionItemAssignSegment = menu.addAction("Assign segment to code")
        ActionItemAddCode = menu.addAction(_("Add a new code"))
        ActionItemAddCategory = menu.addAction(_("Add a new category"))
        ActionItemRename = menu.addAction(_("Rename"))
        ActionItemEditMemo = menu.addAction(_("View or edit memo"))
        ActionItemDelete = menu.addAction(_("Delete"))
        if selected is not None and selected.text(1)[0:3] == 'cid':
            ActionItemChangeColor = menu.addAction(_("Change code color"))

        action = menu.exec_(self.ui.treeWidget.mapToGlobal(position))
        if selected is not None and selected.text(1)[0:3] == 'cid' and action == ActionItemChangeColor:
            self.change_code_color(selected)
        if action == ActionItemAddCategory:
            self.add_category()
        if action == ActionItemAddCode:
            self.add_code()
        if selected is not None and action == ActionItemRename:
            self.rename_category_or_code(selected)
        if selected is not None and action == ActionItemEditMemo:
            self.add_edit_code_memo(selected)
        if selected is not None and action == ActionItemDelete:
            self.delete_category_or_code(selected)
        if action == ActionItemAssignSegment:
            self.assign_segment_to_code(selected)

    def update_dialog_codes_and_categories(self):
        """ Update code and category tree in DialogCodeImage, DialogCodeAV,
        DialogCodeText, DialogReportCodes.
        Not using isinstance for other classes, as could not import. There was an import error.
        Using try except blocks for each instance, as instance may have been deleted. """

        for d in self.dialog_list:
            if str(type(d)) == "<class 'code_text.DialogCodeText'>":
                try:
                    d.get_codes_and_categories()
                    d.fill_tree()
                    d.unlight()
                    d.highlight()
                    d.get_coded_text_update_eventfilter_tooltips()
                except RuntimeError as e:
                    pass
            if isinstance(d, DialogCodeAV):
                try:
                    d.get_codes_and_categories()
                    d.fill_tree()
                    d.load_segments()
                    d.unlight()
                    d.highlight()
                    d.get_coded_text_update_eventfilter_tooltips()
                except RuntimeError as e:
                    pass
            if str(type(d)) == "<class 'view_image.DialogCodeImage'>":
                try:
                    d.get_codes_and_categories()
                    d.fill_tree()
                    d.get_coded_areas()
                    d.draw_coded_areas()
                except RuntimeError as e:
                    pass
            if str(type(d)) == "<class 'reports.DialogReportCodes'>":
                try:
                    d.get_data()
                    d.fill_tree()
                except RuntimeError as e:
                    pass

    def eventFilter(self, object, event):
        """ Using this event filter to identify treeWidgetItem drop events.
        http://doc.qt.io/qt-5/qevent.html#Type-enum
        QEvent::Drop 63 A drag and drop operation is completed (QDropEvent).
        https://stackoverflow.com/questions/28994494/why-does-qtreeview-not-fire-a-drop-or-move-event-during-drag-and-drop
        Also use eventFilter for QGraphicsView.
        """

        if object is self.ui.treeWidget.viewport():
            if event.type() == QtCore.QEvent.Drop:
                item = self.ui.treeWidget.currentItem()
                parent = self.ui.treeWidget.itemAt(event.pos())
                self.item_moved_update_data(item, parent)
        return False

    def assign_segment_to_code(self, selected):
        """ Assign time segment to selected code. Insert an entry into the database.
        Then clear the segment for re-use."""

        if self.media_data is None or self.segment['start_msecs'] is None or self.segment['end_msecs'] is None:
            self.clear_segment()
            return
        sql = "insert into code_av (id, pos0, pos1, cid, memo, date, owner) values(?,?,?,?,?,?,?)"
        cid = int(selected.text(1).split(':')[1])
        values = [self.media_data['id'], self.segment['start_msecs'],
            self.segment['end_msecs'], cid, self.segment['memo'],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            self.app.settings['codername']]
        cur = self.app.conn.cursor()
        cur.execute(sql, values)
        self.app.conn.commit()
        self.load_segments()
        self.clear_segment()

    def clear_segment(self):
        """ Called by assign_segment_to code. """

        self.segment['start'] = None
        self.segment['start_msecs'] = None
        self.segment['end'] = None
        self.segment['end_msecs'] = None
        self.segment['memo'] = ""
        self.ui.label_segment.setText(_("Segment:"))
        self.ui.pushButton_coding.setText(_("Start segment"))

    def item_moved_update_data(self, item, parent):
        """ Called from drop event in treeWidget view port.
        identify code or category to move.
        Also merge codes if one code is dropped on another code. """

        # find the category in the list
        if item.text(1)[0:3] == 'cat':
            found = -1
            for i in range(0, len(self.categories)):
                if self.categories[i]['catid'] == int(item.text(1)[6:]):
                    found = i
            if found == -1:
                return
            if parent is None:
                self.categories[found]['supercatid'] = None
            else:
                if parent.text(1).split(':')[0] == 'cid':
                    # parent is code (leaf) cannot add child
                    return
                supercatid = int(parent.text(1).split(':')[1])
                if supercatid == self.categories[found]['catid']:
                    # something went wrong
                    logger.debug("supercatid== self.categories[found][catid]")
                    return
                self.categories[found]['supercatid'] = supercatid
            cur = self.app.conn.cursor()
            cur.execute("update code_cat set supercatid=? where catid=?",
            [self.categories[found]['supercatid'], self.categories[found]['catid']])
            self.app.conn.commit()
            self.update_dialog_codes_and_categories()

        # find the code in the list
        if item.text(1)[0:3] == 'cid':
            found = -1
            for i in range(0, len(self.codes)):
                if self.codes[i]['cid'] == int(item.text(1)[4:]):
                    found = i
            if found == -1:
                return
            if parent is None:
                self.codes[found]['catid'] = None
            else:
                if parent.text(1).split(':')[0] == 'cid':
                    # parent is code (leaf) cannot add child, but can merge
                    self.merge_codes(self.codes[found], parent)
                    return
                catid = int(parent.text(1).split(':')[1])
                self.codes[found]['catid'] = catid
            cur = self.app.conn.cursor()
            cur.execute("update code_name set catid=? where cid=?",
            [self.codes[found]['catid'], self.codes[found]['cid']])
            self.app.conn.commit()
            self.update_dialog_codes_and_categories()

    def merge_codes(self, item, parent):
        """ Merge code or category with another code or category.
        Called by item_moved_update_data when a code is moved onto another code. """

        msg = _("Merge code: ") + item['name'] + " ==> " + parent.text(0)
        reply = QtWidgets.QMessageBox.question(None, _('Merge codes'),
        msg, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return
        cur = self.app.conn.cursor()
        old_cid = item['cid']
        new_cid = int(parent.text(1).split(':')[1])
        try:
            cur.execute("update code_av set cid=? where cid=?", [new_cid, old_cid])
            cur.execute("update code_image set cid=? where cid=?", [new_cid, old_cid])
            cur.execute("update code_text set cid=? where cid=?", [new_cid, old_cid])
            self.app.conn.commit()
        except Exception as e:
            e = str(e)
            msg = _("Cannot merge codes, unmark overlapping text.") + "\n" + e
            QtWidgets.QInformationDialog(None, _("Cannot merge"), msg)
            return
        cur.execute("delete from code_name where cid=?", [old_cid, ])
        self.app.conn.commit()
        self.update_dialog_codes_and_categories()
        self.parent_textEdit.append(msg)
        self.load_segments()

    def add_code(self):
        """ Use add_item dialog to get new code text.
        Add_code_name dialog checks for duplicate code name.
        New code is added to data and database. """

        ui = DialogAddItemName(self.codes, _("Add new code"))
        ui.exec_()
        new_name = ui.get_new_name()
        if new_name is None:
            return
        code_color = colors[randint(0, len(colors) - 1)]
        item = {'name': new_name, 'memo': "", 'owner': self.app.settings['codername'],
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),'catid': None, 'color': code_color}
        cur = self.app.conn.cursor()
        cur.execute("insert into code_name (name,memo,owner,date,catid,color) values(?,?,?,?,?,?)"
            , (item['name'], item['memo'], item['owner'], item['date'], item['catid'], item['color']))
        self.app.conn.commit()
        self.parent_textEdit.append(_("Code added: ") + item['name'])
        self.update_dialog_codes_and_categories()

    def add_category(self):
        """ Add a new category.
        Note: the addItem dialog does the checking for duplicate category names
        Add the new category as a top level item. """

        ui = DialogAddItemName(self.categories, _("Category"))
        ui.exec_()
        new_name = ui.get_new_name()
        if new_name is None:
            return
        # add to database
        item = {'name': new_name, 'cid': None, 'memo': "",
        'owner': self.app.settings['codername'],
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        cur = self.app.conn.cursor()
        cur.execute("insert into code_cat (name, memo, owner, date, supercatid) values(?,?,?,?,?)"
            , (item['name'], item['memo'], item['owner'], item['date'], None))
        self.app.conn.commit()
        self.update_dialog_codes_and_categories()

    def delete_category_or_code(self, selected):
        """ Determine if category or code is to be deleted. """

        if selected.text(1)[0:3] == 'cat':
            self.delete_category(selected)
            return  # avoid error as selected is now None
        if selected.text(1)[0:3] == 'cid':
            self.delete_code(selected)

    def delete_code(self, selected):
        """ Find code, remove from database, refresh and code_name data and fill
        treeWidget. """

        # find the code_in the list, check to delete
        found = -1
        for i in range(0, len(self.codes)):
            if self.codes[i]['cid'] == int(selected.text(1)[4:]):
                found = i
        if found == -1:
            return
        code_ = self.codes[found]
        ui = DialogConfirmDelete(_("Code: ") + selected.text(0))
        ok = ui.exec_()
        if not ok:
            return
        cur = self.app.conn.cursor()
        cur.execute("delete from code_name where cid=?", [code_['cid'], ])
        cur.execute("delete from code_av where cid=?", [code_['cid'], ])
        cur.execute("delete from code_image where cid=?", [code_['cid'], ])
        cur.execute("delete from code_text where cid=?", [code_['cid'], ])
        self.app.conn.commit()
        self.parent_textEdit.append(_("Code deleted: ") + code_['name'])
        selected = None
        self.update_dialog_codes_and_categories()

    def delete_category(self, selected):
        """ Find category, remove from database, refresh categories and code data
        and fill treeWidget. """

        found = -1
        for i in range(0, len(self.categories)):
            if self.categories[i]['catid'] == int(selected.text(1)[6:]):
                found = i
        if found == -1:
            return
        category = self.categories[found]
        ui = DialogConfirmDelete(_("Category: ") + selected.text(0))
        ok = ui.exec_()
        if not ok:
            return
        cur = self.app.conn.cursor()
        cur.execute("update code_name set catid=null where catid=?", [category['catid'], ])
        cur.execute("update code_cat set supercatid=null where catid = ?", [category['catid'], ])
        cur.execute("delete from code_cat where catid = ?", [category['catid'], ])
        self.app.conn.commit()
        self.parent_textEdit.append(_("Category deleted: ") + category['name'])
        selected = None
        self.update_dialog_codes_and_categories()

    def add_edit_code_memo(self, selected):
        """ View and edit a memo. """

        if selected.text(1)[0:3] == 'cid':
            # find the code in the list
            found = -1
            for i in range(0, len(self.codes)):
                if self.codes[i]['cid'] == int(selected.text(1)[4:]):
                    found = i
            if found == -1:
                return
            ui = DialogMemo(self.app, _("Memo for Code ") + self.codes[found]['name'],
            self.codes[found]['memo'])
            ui.exec_()
            memo = ui.memo
            if memo == "":
                selected.setData(2, QtCore.Qt.DisplayRole, "")
            else:
                selected.setData(2, QtCore.Qt.DisplayRole, _("Memo"))
            # update codes list and database
            if memo != self.codes[found]['memo']:
                self.codes[found]['memo'] = memo
                cur = self.app.conn.cursor()
                cur.execute("update code_name set memo=? where cid=?", (memo, self.codes[found]['cid']))
                self.app.conn.commit()

        if selected.text(1)[0:3] == 'cat':
            # find the category in the list
            found = -1
            for i in range(0, len(self.categories)):
                if self.categories[i]['catid'] == int(selected.text(1)[6:]):
                    found = i
            if found == -1:
                return
            ui = DialogMemo(self.app, _("Memo for Category ") + self.categories[found]['name'],
            self.categories[found]['memo'])
            ui.exec_()
            memo = ui.memo
            if memo == "":
                selected.setData(2, QtCore.Qt.DisplayRole, "")
            else:
                selected.setData(2, QtCore.Qt.DisplayRole, _("Memo"))
            # update codes list and database
            if memo != self.categories[found]['memo']:
                self.categories[found]['memo'] = memo
                cur = self.app.conn.cursor()
                cur.execute("update code_cat set memo=? where catid=?", (memo, self.categories[found]['catid']))
                self.app.conn.commit()
        self.update_dialog_codes_and_categories()

    def rename_category_or_code(self, selected):
        """ Rename a code or category. Checks that the proposed code or category name is
        not currently in use. """

        if selected.text(1)[0:3] == 'cid':
            new_name, ok = QtWidgets.QInputDialog.getText(self, _("Rename code"), _("New code name:"),
            QtWidgets.QLineEdit.Normal, selected.text(0))
            if not ok or new_name == '':
                return
            # check that no other code has this text
            for c in self.codes:
                if c['name'] == new_name:
                    QtWidgets.QMessageBox.warning(None, _("Name in use"),
                    new_name + _(" Name already in use, choose another."), QtWidgets.QMessageBox.Ok)
                    return
            # find the code in the list
            found = -1
            for i in range(0, len(self.codes)):
                if self.codes[i]['cid'] == int(selected.text(1)[4:]):
                    found = i
            if found == -1:
                return
            # update codes list and database
            cur = self.app.conn.cursor()
            cur.execute("update code_name set name=? where cid=?", (new_name, self.codes[found]['cid']))
            self.app.conn.commit()
            self.parent_textEdit.append(_("Code renamed: ") + self.codes[found]['name'] + " ==> " + new_name)
            self.update_dialog_codes_and_categories()
            return

        if selected.text(1)[0:3] == 'cat':
            new_name, ok = QtWidgets.QInputDialog.getText(self, _("Rename category"), _("New category name:"),
            QtWidgets.QLineEdit.Normal, selected.text(0))
            if not ok or new_name == '':
                return
            # check that no other category has this text
            for c in self.categories:
                if c['name'] == new_name:
                    msg = _("This category name is already in use")
                    QtWidgets.QMessageBox.warning(None, _("Duplicate category name"), msg, QtWidgets.QMessageBox.Ok)
                    return
            # find the category in the list
            found = -1
            for i in range(0, len(self.categories)):
                if self.categories[i]['catid'] == int(selected.text(1)[6:]):
                    found = i
            if found == -1:
                return
            # update category list and database
            cur = self.app.conn.cursor()
            cur.execute("update code_cat set name=? where catid=?",
            (new_name, self.categories[found]['catid']))
            self.app.conn.commit()
            self.parent_textEdit.append(_("Category renamed: ") + self.categories[found]['name'] + " ==> " + new_name)
            self.update_dialog_codes_and_categories()

    def change_code_color(self, selected):
        """ Change the color of the currently selected code. """

        cid = int(selected.text(1)[4:])
        found = -1
        for i in range(0, len(self.codes)):
            if self.codes[i]['cid'] == cid:
                found = i
        if found == -1:
            return
        ui = DialogColorSelect(self.codes[found]['color'])
        ok = ui.exec_()
        if not ok:
            return
        new_color = ui.get_color()
        if new_color is None:
            return
        selected.setBackground(0, QBrush(QtGui.QColor(new_color), Qt.SolidPattern))
        #update codes list and database
        self.codes[found]['color'] = new_color
        cur = self.app.conn.cursor()
        cur.execute("update code_name set color=? where cid=?",
        (self.codes[found]['color'], self.codes[found]['cid']))
        self.app.conn.commit()
        self.update_dialog_codes_and_categories()
        #self.load_segments()

    # Methods used with the textEdit transcribed text
    def unlight(self):
        """ Remove all text highlighting from current file. """

        if self.transcription is None or self.ui.textEdit.toPlainText() == "":
            return
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(0, QtGui.QTextCursor.MoveAnchor)
        cursor.setPosition(len(self.transcription[1]) - 1, QtGui.QTextCursor.KeepAnchor)
        cursor.setCharFormat(QtGui.QTextCharFormat())

    def highlight(self):
        """ Apply text highlighting to current file.
        If no colour has been assigned to a code, those coded text fragments are coloured gray.
        Each code text item contains: fid, date, pos0, pos1, seltext, cid, status, memo,
        name, owner. """

        fmt = QtGui.QTextCharFormat()
        cursor = self.ui.textEdit.textCursor()

        # add coding highlights
        for item in self.code_text:
            cursor.setPosition(int(item['pos0']), QtGui.QTextCursor.MoveAnchor)
            cursor.setPosition(int(item['pos1']), QtGui.QTextCursor.KeepAnchor)
            color = "#F8E0E0"  # default light red
            for fcode in self.codes:
                if fcode['cid'] == item['cid']:
                    color = fcode['color']
            fmt.setBackground(QtGui.QBrush(QtGui.QColor(color)))
            # highlight codes with memos - these are italicised
            if item['memo'] is not None and item['memo'] != "":
                fmt.setFontItalic(True)
            else:
                fmt.setFontItalic(False)
                fmt.setFontWeight(QtGui.QFont.Normal)
            cursor.setCharFormat(fmt)

        # add annotation marks - these are in bold
        for note in self.annotations:
            if note['fid'] == self.transcription[0]:
                cursor.setPosition(int(note['pos0']), QtGui.QTextCursor.MoveAnchor)
                cursor.setPosition(int(note['pos1']), QtGui.QTextCursor.KeepAnchor)
                formatB = QtGui.QTextCharFormat()
                formatB.setFontWeight(QtGui.QFont.Bold)
                cursor.mergeCharFormat(formatB)

    def textEdit_menu(self, position):
        """ Context menu for textEdit. Mark, unmark, annotate, copy. """

        if self.ui.checkBox_scroll_transcript.isChecked():
            return

        cursor = self.ui.textEdit.cursorForPosition(position)
        selectedText = self.ui.textEdit.textCursor().selectedText()
        menu = QtWidgets.QMenu()
        action_unmark = None
        action_play_text = None
        play_text_avid = None
        for item in self.code_text:
            if cursor.position() >= item['pos0'] and cursor.position() <= item['pos1']:
                if item['avid'] is not None:
                    action_play_text = menu.addAction(_("Play text"))
                    play_text_avid = item['avid']
                action_unmark = menu.addAction(_("Unmark"))
                break
        if selectedText != "":
            action_mark = menu.addAction(_("Mark"))
            action_annotate = menu.addAction(_("Annotate"))
            action_copy = menu.addAction(_("Copy to clipboard"))
            if self.segment_for_text is None:
                action_link_text_to_segment = menu.addAction(_("Prepare text_link to segment"))
            if self.segment_for_text is not None:
                action_link_segment_to_text = menu.addAction(_("Link to segment to text"))
        action_video_position_timestamp = -1
        for ts in self.time_positions:
            #print(ts, cursor.position())
            if cursor.position() >= ts[0] and cursor.position() <= ts[1]:
                action_video_position_timestamp = menu.addAction(_("Video position to timestamp"))
        action = menu.exec_(self.ui.textEdit.mapToGlobal(position))
        if selectedText != "" and action == action_copy:
            self.copy_selected_text_to_clipboard()
        if selectedText != "" and action == action_mark:
            self.mark()
        if action_unmark is not None and action == action_unmark:
            self.unmark(cursor.position())
        if action_play_text is not None and action == action_play_text:
            self.play_text(play_text_avid)
        if selectedText != "" and action == action_annotate:
            self.annotate(cursor.position())
        try:
            if action == action_video_position_timestamp:
                self.set_video_to_timestamp_position(cursor.position())
        except:
            pass
        if self.segment_for_text is None and selectedText != "" and action == action_link_text_to_segment:
            self.prepare_link_text_to_segment()
        if self.segment_for_text is not None and selectedText != "" and action == action_link_segment_to_text:
            self.link_segment_to_text()

    def play_text(self, avid):
        """ Play the audio/video for this coded text selection that is mapped to an a/v segment. """

        segment = None
        for s in self.segments:
            if s['avid'] == avid:
                segment = s
                break
        if segment is None:
            return
        pos = segment['pos0'] / self.mediaplayer.get_media().get_duration()
        self.mediaplayer.play()
        self.mediaplayer.set_position(pos)
        self.is_paused = False
        self.ui.pushButton_play.setText(_("Pause"))
        self.play_segment_end = segment['pos1']
        self.timer.start()

    def link_segment_to_text(self):
        """ Link selected segment to selected text """

        item = {}
        item['cid'] = self.segment_for_text['cid']
        item['fid'] = self.transcription[0]
        item['seltext'] = self.ui.textEdit.textCursor().selectedText()
        item['pos0'] = self.ui.textEdit.textCursor().selectionStart()
        item['pos1'] = self.ui.textEdit.textCursor().selectionEnd()
        item['owner'] = self.app.settings['codername']
        item['memo'] = ""
        item['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        item['avid'] = self.segment_for_text['avid']
        print("TOLINK TO PLONK IN DB\n", item)

    def prepare_link_text_to_segment(self):
        """ Select text in transcription and prepare variable to be linked to a/v segment. """

        selectedText = self.ui.textEdit.textCursor().selectedText()
        pos0 = self.ui.textEdit.textCursor().selectionStart()
        pos1 = self.ui.textEdit.textCursor().selectionEnd()
        if pos0 == pos1:
            return
        self.text_for_segment['cid'] = None
        self.text_for_segment['fid'] = self.transcription[0]
        self.text_for_segment['seltext'] = selectedText
        self.text_for_segment['pos0'] = pos0
        self.text_for_segment['pos1'] = pos1
        self.text_for_segment['owner'] = self.app.settings['codername']
        self.text_for_segment['memo'] = ""
        self.text_for_segment['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.text_for_segment['avid'] = None
        #print(self.text_for_segment)

    def set_video_to_timestamp_position(self, position):
        """ Set the video position to this time stamp.
        The horizontal slider will move to match the position of the video (in update_ui).
        """

        timestamp = None
        for ts in self.time_positions:
            if position >= ts[0] and position <= ts[1]:
                timestamp = ts
        if timestamp is None:
            return
        self.timer.stop()
        self.mediaplayer.set_position(timestamp[2] / self.media.get_duration())
        self.timer.start()

    def copy_selected_text_to_clipboard(self):
        """ Copy text to clipboard for external use.
        For example adding text to another document. """

        selectedText = self.ui.textEdit.textCursor().selectedText()
        cb = QtWidgets.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(selectedText, mode=cb.Clipboard)

    def mark(self):
        """ Mark selected text in file with currently selected code.
       Need to check for multiple same codes at same pos0 and pos1.
       """

        if self.transcription is None or self.ui.textEdit.toPlainText() == "":
            QtWidgets.QMessageBox.warning(None, _('Warning'), _("No transcription"), QtWidgets.QMessageBox.Ok)
            return
        item = self.ui.treeWidget.currentItem()
        if item is None:
            QtWidgets.QMessageBox.warning(None, _('Warning'), _("No code was selected"), QtWidgets.QMessageBox.Ok)
            return
        if item.text(1).split(':')[0] == 'catid':  # must be a code
            return
        cid = int(item.text(1).split(':')[1])
        selectedText = self.ui.textEdit.textCursor().selectedText()
        pos0 = self.ui.textEdit.textCursor().selectionStart()
        pos1 = self.ui.textEdit.textCursor().selectionEnd()
        if pos0 == pos1:  # Something quirky happened
            return
        # add the coded section to code text, add to database and update GUI
        coded = {'cid': cid, 'fid': self.transcription[0], 'seltext': selectedText,
        'pos0': pos0, 'pos1': pos1, 'owner': self.app.settings['codername'], 'memo': "",
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        self.code_text.append(coded)
        self.highlight()
        cur = self.app.conn.cursor()
        # check for an existing duplicated marking first
        cur.execute("select * from code_text where cid = ? and fid=? and pos0=? and pos1=? and owner=?",
            (coded['cid'], coded['fid'], coded['pos0'], coded['pos1'], coded['owner']))
        result = cur.fetchall()
        if len(result) > 0:
            QtWidgets.QMessageBox.warning(None, _("Already Coded"),
            _("This segment has already been coded with this code by ") + coded['owner'],
            QtWidgets.QMessageBox.Ok)
            return

        #TODO should not get sqlite3.IntegrityError:
        #TODO UNIQUE constraint failed: code_text.cid, code_text.fid, code_text.pos0, code_text.pos1
        try:
            cur.execute("insert into code_text (cid,fid,seltext,pos0,pos1,owner,\
                memo,date) values(?,?,?,?,?,?,?,?)", (coded['cid'], coded['fid'],
                coded['seltext'], coded['pos0'], coded['pos1'], coded['owner'],
                coded['memo'], coded['date']))
            self.app.conn.commit()
        except Exception as e:
            logger.debug(str(e))
        # update filter for tooltip
        self.eventFilterTT.setCodes(self.code_text, self.codes)

    def unmark(self, location):
        """ Remove code marking by this coder from selected text in current file. """

        if self.transcription is None or self.ui.textEdit.toPlainText() == "":
            return
        unmarked = None
        for item in self.code_text:
            if location >= item['pos0'] and location <= item['pos1'] and item['owner'] == self.app.settings['codername']:
                unmarked = item
        if unmarked is None:
            return

        # delete from db, remove from coding and update highlights
        cur = self.app.conn.cursor()
        cur.execute("delete from code_text where cid=? and pos0=? and pos1=? and owner=?",
            (unmarked['cid'], unmarked['pos0'], unmarked['pos1'], self.app.settings['codername']))
        self.app.conn.commit()
        if unmarked in self.code_text:
            self.code_text.remove(unmarked)

        # update filter for tooltip and update code colours
        self.eventFilterTT.setCodes(self.code_text, self.codes)
        self.unlight()
        self.highlight()

    def annotate(self, location):
        """ Add view, or remove an annotation for selected text.
        Annotation positions are displayed as bold text.
        """

        if self.transcription is None or self.ui.textEdit.toPlainText() == "":
            QtWidgets.QMessageBox.warning(None, _('Warning'), _("No media transcription selected"))
            return
        pos0 = self.ui.textEdit.textCursor().selectionStart()
        pos1 = self.ui.textEdit.textCursor().selectionEnd()
        text_length = len(self.ui.textEdit.toPlainText())
        if pos0 >= text_length or pos1 >= text_length:
            return
        item = None
        details = ""
        annotation = ""
        # find existing annotation at this position for this file
        for note in self.annotations:
            if location >= note['pos0'] and location <= note['pos1'] and note['fid'] == self.transcription[0]:
                item = note  # use existing annotation
                details = item['owner'] + " " + item['date']
        # exit method if no text selected and there is not annotation at this position
        if pos0 == pos1 and item is None:
            return
        # add new item to annotations, add to database and update GUI
        if item is None:
            item = {'fid': self.transcription[0], 'pos0': pos0, 'pos1': pos1,
            'memo': str(annotation), 'owner': self.app.settings['codername'],
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'anid': -1}
        ui = DialogMemo(self.app, _("Annotation: ") + details, item['memo'])
        ui.exec_()
        item['memo'] = ui.memo
        if item['memo'] != "":
            cur = self.app.conn.cursor()
            cur.execute("insert into annotation (fid,pos0, pos1,memo,owner,date) \
                values(?,?,?,?,?,?)" ,(item['fid'], item['pos0'], item['pos1'],
                item['memo'], item['owner'], item['date']))
            self.app.conn.commit()
            cur.execute("select last_insert_rowid()")
            anid = cur.fetchone()[0]
            item['anid'] = anid
            self.annotations.append(item)
            self.highlight()
            self.parent_textEdit.append(_("Annotation added at position: ") \
                + str(item['pos0']) + "-" + str(item['pos1']) + _(" for: ") + self.transcription[2])
        # if blank delete the annotation
        if item['memo'] == "":
            cur = self.app.conn.cursor()
            cur.execute("delete from annotation where pos0 = ?", (item['pos0'], ))
            self.app.conn.commit()
            for note in self.annotations:
                if note['pos0'] == item['pos0'] and note['fid'] == item['fid']:
                    self.annotations.remove(note)
            self.parent_textEdit.append(_("Annotation removed from position ") \
                + str(item['pos0']) + _(" for: ") + self.transcription[2])
        self.unlight()
        self.highlight()


class ToolTip_EventFilter(QtCore.QObject):
    """ Used to add a dynamic tooltip for the textEdit.
    The tool top text is changed according to its position in the text.
    If over a coded section the codename is displayed in the tooltip.
    Need to add av time segments to the code_text where relevant.
    """

    codes = None
    code_text = None

    def setCodes(self, code_text, codes):
        self.code_text = code_text
        self.codes = codes
        for item in self.code_text:
            for c in self.codes:
                if item['cid'] == c['cid']:
                    item['name'] = c['name']

    def eventFilter(self, receiver, event):
        #QtGui.QToolTip.showText(QtGui.QCursor.pos(), tip)
        if event.type() == QtCore.QEvent.ToolTip:
            helpEvent = QHelpEvent(event)
            cursor = QtGui.QTextCursor()
            cursor = receiver.cursorForPosition(helpEvent.pos())
            pos = cursor.position()
            receiver.setToolTip("")
            text = ""
            # occasional None type error
            if self.code_text is None:
                #Call Base Class Method to Continue Normal Event Processing
                return super(ToolTip_EventFilter, self).eventFilter(receiver, event)
            for item in self.code_text:
                if item['pos0'] <= pos and item['pos1'] >= pos:
                    #print(item)
                    try:
                        if text != "":
                            text = text + "\n"
                        text += item['name']  # += as can have multiple codes on same position
                        if item['avid'] is not None:
                            text += " [" + msecs_to_mins_and_secs(item['av_pos0'])
                            text += " - " + msecs_to_mins_and_secs(item['av_pos1']) + "]"
                    except Exception as e:
                        msg = "Codes ToolTipEventFilter " + str(e) + ". Possible key error: "
                        msg += str(item) + "\n" + str(self.code_text)
                        logger.error(msg)
            if text != "":
                receiver.setToolTip(text)
        #Call Base Class Method to Continue Normal Event Processing
        return super(ToolTip_EventFilter, self).eventFilter(receiver, event)


class GraphicsScene(QtWidgets.QGraphicsScene):
    """ set the scene for the graphics objects and re-draw events. """

    def __init__ (self, width, height, parent=None):
        super(GraphicsScene, self).__init__ (parent)
        self.scene_width = width
        self.scene_height = height
        self.setSceneRect(QtCore.QRectF(0, 0, self.scene_width, self.scene_height))

    '''def set_width(self, width):
        """ Resize scene width. Not currently used. """

        self.sceneWidth = width
        self.setSceneRect(QtCore.QRectF(0, 0, self.scene_width, self.scene_height))

    def set_height(self, height):
        """ Resize scene height. Not currently used. """

        self.sceneHeight = height
        self.setSceneRect(QtCore.QRectF(0, 0, self.scene_width, self.scene_height))

    def get_width(self):
        """ Return scene width. Not currently used. """

        return self.scene_width

    def get_height(self):
        """ Return scene height. Not currently used. """

        return self.scene_height

    def mouseMoveEvent(self, mouseEvent):
        super(GraphicsScene, self).mousePressEvent(mouseEvent)

        for i in self.scene.items():
            if isinstance(i, SegmentGraphicsItem) and i.reload_segment is True:
                self.load_segments()
        self.update()'''

    """def mousePressEvent(self, mouseEvent):
        super(GraphicsScene, self).mousePressEvent(mouseEvent)
        #position = QtCore.QPointF(event.scenePos())
        #logger.debug("pressed here: " + str(position.x()) + ", " + str(position.y()))
        for item in self.items(): # item is QGraphicsProxyWidget
            if isinstance(item, LinkItem):
                item.redraw()
        self.update(self.sceneRect())"""

    """def mouseReleaseEvent(self, mouseEvent):
        ''' On mouse release, an item might be repositioned so need to redraw all the
        link_items '''

        super(GraphicsScene, self).mouseReleaseEvent(mouseEvent)
        for item in self.items():
            if isinstance(item, LinkGraphicsItem):
                item.redraw()
        self.update(self.sceneRect())"""


class SegmentGraphicsItem(QtWidgets.QGraphicsLineItem):
    """ Draws coded segment line. The media duration determines the scaler for the line length and position.
    y values are pre-calculated and stored in the segment data.
    Refernces Dialog_code_av for variables and methods.
    """

    segment = None
    scaler = None
    reload_segment = False
    text_for_segment = None
    code_av_dialog = None

    def __init__(self, segment, scaler, text_for_segment, code_av_dialog):
            super(SegmentGraphicsItem, self).__init__(None)

            self.segment = segment
            self.scaler = scaler
            self.text_for_segment = text_for_segment
            self.code_av_dialog = code_av_dialog
            self.reload_segment = False
            self.setFlag(self.ItemIsSelectable, True)
            tooltip = self.segment['codename'] + " "
            seg_time = "[" + msecs_to_mins_and_secs(self.segment['pos0']) + " - "
            seg_time += msecs_to_mins_and_secs(self.segment['pos1']) + "]"
            tooltip += seg_time
            if self.segment['memo'] != "":
                tooltip += "\n" + _("Memo: ") + self.segment['memo']
            self.setToolTip(tooltip)
            self.draw_segment()

    def contextMenuEvent(self, event):
        """
        # https://riverbankcomputing.com/pipermail/pyqt/2010-July/027094.html
        I was not able to mapToGlobal position so, the menu maps to scene position plus
        the Dialog screen position.
        """

        menu = QtWidgets.QMenu()
        action_memo = menu.addAction(_('Memo for segment'))
        action_delete = menu.addAction(_('Delete segment'))
        action_play = menu.addAction(_('Play segment'))
        action_edit_start = menu.addAction(_('Edit segment start position'))
        action_edit_end = menu.addAction(_('Edit segment end position'))
        if self.text_for_segment['seltext'] is not None:
            action_link_text = menu.addAction(_('Link text to segment'))
        if self.text_for_segment['seltext'] is None and self.code_av_dialog.ui.textEdit.toPlainText() != "":
            action_link_segment = menu.addAction(_("Select segment to link to text"))
        action = menu.exec_(QtGui.QCursor.pos())
        if action is None:
            return
        if action == action_memo:
            self.edit_memo()
        if action == action_delete:
            self.delete()
        if action == action_play:
            self.play_segment()
        if action == action_edit_start:
            self.edit_segment_start()
        if action == action_edit_end:
            self.edit_segment_end()
        if self.text_for_segment['seltext'] is not None and action == action_link_text:
            self.link_text_to_segment()
        if self.text_for_segment['seltext'] is None and action == action_link_segment:
            self.link_segment_to_text()

    def link_segment_to_text(self):
        """ Prepare Dialog_code_av to link segment to text """

        self.code_av_dialog.segment_for_text = self.segment

    def link_text_to_segment(self):
        """ Link text to this segment. this will add a code to the text and insert
        a code_text entry into database. """

        self.text_for_segment['cid'] = self.segment['cid']
        self.text_for_segment['avid'] = self.segment['avid']
        # check for an existing duplicated marking first
        cur = self.code_av_dialog.app.conn.cursor()
        cur.execute("select * from code_text where cid = ? and fid=? and pos0=? and pos1=? and owner=?",
            (self.text_for_segment['cid'], self.text_for_segment['fid'], self.text_for_segment['pos0'], self.text_for_segment['pos1'], self.text_for_segment['owner']))
        result = cur.fetchall()
        if len(result) > 0:
            QtWidgets.QMessageBox.warning(None, _("Already Coded"),
            _("This segment has already been coded with this code."), QtWidgets.QMessageBox.Ok)
            return
        #print(self.text_for_segment)
        try:
            cur.execute("insert into code_text (cid,fid,seltext,pos0,pos1,owner,\
                memo,date, avid) values(?,?,?,?,?,?,?,?,?)", (self.text_for_segment['cid'],
                self.text_for_segment['fid'],self.text_for_segment['seltext'],
                self.text_for_segment['pos0'], self.text_for_segment['pos1'],
                self.text_for_segment['owner'], self.text_for_segment['memo'],
                self.text_for_segment['date'], self.text_for_segment['avid']))
            self.code_av_dialog.app.conn.commit()
        except Exception as e:
            logger.debug(str(e))
        self.code_av_dialog.get_coded_text_update_eventfilter_tooltips()
        self.text_for_segment = {'cid': None, 'fid': None, 'seltext': None, 'pos0': None, 'pos1': None, 'owner': None, 'memo': None, 'date': None, 'avid': None}

    def edit_segment_start(self):
        """ Edit segment start time. """

        i, ok_pressed = QtWidgets.QInputDialog.getInt(None, "Segment start in mseconds",
            "Edit time in milliseconds\n1000 msecs = 1 second:", self.segment['pos0'], 1,
            self.segment['pos1'] - 1, 5)
        if not ok_pressed:
            return
        if i < 1:
            return
        self.segment['pos0'] = i
        sql = "update code_av set pos0=? where avid=?"
        cur = self.code_av_dialog.app.conn.cursor()
        cur.execute(sql, [i, self.segment['avid']])
        self.code_av_dialog.app.conn.commit()
        self.draw_segment()

    def edit_segment_end(self):
        """ Edit segment end time """

        duration = self.code_av_dialog.media.get_duration()
        i, ok_pressed = QtWidgets.QInputDialog.getInt(None, "Segment end in mseconds",
            "Edit time in milliseconds\n1000 msecs = 1 second:", self.segment['pos1'],
            self.segment['pos0'] + 1, duration - 1, 5)
        if not ok_pressed:
            return
        if i < 1:
            return
        self.segment['pos1'] = i
        sql = "update code_av set pos1=? where avid=?"
        cur = self.code_av_dialog.app.conn.cursor()
        cur.execute(sql, [i, self.segment['avid']])
        self.code_av_dialog.app.conn.commit()
        self.draw_segment()

    def play_segment(self):
        """  """

        #self.timer.stop()
        #pos = self.ui.horizontalSlider.value()
        pos = self.segment['pos0'] / self.code_av_dialog.mediaplayer.get_media().get_duration()
        self.code_av_dialog.mediaplayer.play()
        self.code_av_dialog.mediaplayer.set_position(pos)
        self.code_av_dialog.is_paused = False
        self.code_av_dialog.ui.pushButton_play.setText(_("Pause"))
        self.code_av_dialog.play_segment_end = self.segment['pos1']
        self.code_av_dialog.timer.start()

    def delete(self):
        """ Mark segment for deletion. Does not actually delete segment item, but hides
        it from the scene. Reload_segment is set to True, so on playing media, the update
        event will reload all segments. """

        #print(self.segment)
        ui = DialogConfirmDelete(_("Segment: ") + self.segment['codename'] + "\n" + _("Memo: ") + self.segment['memo'])
        ok = ui.exec_()
        if not ok:
            return

        self.setToolTip("")
        self.setLine(-100, -100, -100, -100)
        self.segment['memo'] = ""
        self.segment['pos0'] = -100
        self.segment['pos1'] = -100
        self.segment['y'] = -100
        self.reload_segment = True
        sql = "delete from code_av where avid=?"
        values = [self.segment['avid']]
        cur = self.code_av_dialog.app.conn.cursor()
        cur.execute(sql, values)
        sql = "update code_text set avid=null where avid=?"
        cur.execute(sql, values)
        self.code_av_dialog.app.conn.commit()
        self.code_av_dialog.get_coded_text_update_eventfilter_tooltips()

    def edit_memo(self):
        """ View, edit or delete memo for this segment.
        Reload_segment is set to True, so on playing media, the update event will reload
        all segments. """

        ui = DialogMemo(self.code_av_dialog.app, _("Memo for segment"), self.segment["memo"])
        ui.exec_()
        if self.segment['memo'] == ui.memo:
            return
        self.reload_segment = True
        self.segment['memo'] = ui.memo
        sql = "update code_av set memo=?, date=? where avid=?"
        values = [self.segment['memo'],
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.segment['avid']]
        cur = self.code_av_dialog.app.conn.cursor()
        cur.execute(sql, values)
        self.code_av_dialog.app.conn.commit()
        tooltip = self.segment['codename'] + " "
        seg_time = "[" + msecs_to_mins_and_secs(self.segment['pos0']) + " - "
        seg_time += msecs_to_mins_and_secs(self.segment['pos1']) + "]"
        tooltip += seg_time
        if self.segment['memo'] != "":
            tooltip += "\nMemo: " + self.segment['memo']
        self.setToolTip(tooltip)

    def redraw(self):
        """ Called from mouse move and release events. Not currently used. """

        self.draw_segment()

    def draw_segment(self):
        """ Calculate the x values for the line. """

        from_x = self.segment['pos0'] * self.scaler
        to_x = self.segment['pos1'] * self.scaler
        line_width = 8
        color = QtGui.QColor(self.segment['color'])
        self.setPen(QtGui.QPen(color, line_width, QtCore.Qt.SolidLine))
        self.setLine(from_x, self.segment['y'], to_x, self.segment['y'])


class DialogViewAV(QtWidgets.QDialog):
    """ View Audio and Video using VLC. View and edit displayed memo.
    Mouse events did not work when the vlc play is in this dialog.
    Mouse events do work with the vlc player in a separate modal dialog.
    """

    app = None
    label = None
    media_data = None
    is_paused = False
    media_duration_text = ""
    displayframe = None
    ddialog = None
    instance = None
    mediaplayer = None
    media = None
    transcription = None
    time_positions = []
    speaker_list = []
    can_transcribe = True

    def __init__(self, app, media_data, parent=None):

        """ Media_data contains: {name, mediapath, owner, id, date, memo, fulltext}
        A separate modal dialog is created to display the video.
        """

        sys.excepthook = exception_handler
        self.app = app
        self.media_data = media_data
        self.is_paused = True
        self.time_positions = []
        self.speaker_list = []
        self.can_transcribe = True

        QtWidgets.QDialog.__init__(self)
        self.ui = Ui_Dialog_view_av()
        self.ui.setupUi(self)
        font = 'font: ' + str(self.app.settings['fontsize']) + 'pt '
        font += '"' + self.app.settings['font'] + '";'
        self.setStyleSheet(font)
        font = 'font: ' + str(self.app.settings['treefontsize']) + 'pt '
        font += '"' + self.app.settings['font'] + '";'
        self.ui.label_speakers.setStyleSheet(font)
        self.setWindowTitle(self.media_data['mediapath'])

        # Get the transcription text and fill textedit
        cur = self.app.conn.cursor()
        cur.execute("select id, fulltext from source where name=?", [media_data['name'] + ".transcribed"])
        self.transcription = cur.fetchone()
        if self.transcription is not None:
            self.ui.textEdit_transcription.installEventFilter(self)
            cur.execute("select cid from  code_text where fid=?", [self.transcription[0],])
            coded = cur.fetchall()
            cur.execute("select anid from  annotation where fid=?", [self.transcription[0],])
            annoted = cur.fetchall()
            if coded != [] and annoted != []:
                self.ui.textEdit_transcription.setReadOnly(True)
                self.can_transcribe = False
                self.ui.label_speakers.setVisible(False)
                self.ui.label_transcription.setToolTip("")
            else:
                self.ui.textEdit_transcription.installEventFilter(self)
                self.ui.label_memo.setText(_("Memo. In transcription area: ctrl+r ctrl+s ctrl+t ctrl+1-8"))
            self.ui.textEdit_transcription.setText(self.transcription[1])
            self.get_timestamps_from_transcription()
            self.get_speaker_names_from_bracketed_text()
            self.add_speaker_names_to_label()

        # My solution to getting gui mouse events by putting vlc video in another dialog
        self.ddialog = QtWidgets.QDialog()
        # enable custom window hint
        self.ddialog.setWindowFlags(self.ddialog.windowFlags() | QtCore.Qt.CustomizeWindowHint)
        # disable close button, only close through closing the Ui_Dialog_view_av
        self.ddialog.setWindowFlags(self.ddialog.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        self.ddialog.setWindowTitle(self.media_data['mediapath'])
        self.ddialog.resize(640, 480)
        self.ddialog.gridLayout = QtWidgets.QGridLayout(self.ddialog)
        self.ddialog.dframe = QtWidgets.QFrame(self.ddialog)
        self.ddialog.dframe.setObjectName("frame")
        if platform.system() == "Darwin": # for MacOS
            self.ddialog.dframe = QtWidgets.QMacCocoaViewContainer(0)
        self.palette = self.ddialog.dframe.palette()
        self.palette.setColor(QtGui.QPalette.Window, QtGui.QColor(30, 30, 30))
        self.ddialog.dframe.setPalette(self.palette)
        self.ddialog.dframe.setAutoFillBackground(True)
        self.ddialog.gridLayout.addWidget(self.ddialog.dframe, 0, 0, 0, 0)
        self.ddialog.move(self.mapToGlobal(QtCore.QPoint(40, 10)))
        self.ddialog.show()

        # Create a basic vlc instance
        self.instance = vlc.Instance()
        # Create an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()
        self.mediaplayer.video_set_mouse_input(False)
        self.mediaplayer.video_set_key_input(False)

        self.ui.horizontalSlider.sliderMoved.connect(self.set_position)
        self.ui.horizontalSlider.sliderPressed.connect(self.set_position)
        self.ui.pushButton_play.clicked.connect(self.play_pause)
        self.ui.pushButton_stop.clicked.connect(self.stop)
        self.ui.horizontalSlider_vol.valueChanged.connect(self.set_volume)
        self.ui.comboBox_tracks.currentIndexChanged.connect(self.audio_track_changed)

        try:
            self.media = self.instance.media_new(self.app.project_path + self.media_data['mediapath'])
        except Exception as e:
            QtWidgets.QMessageBox.warning(None, "Media not found",
                str(e) +"\n" + self.app.project_path + self.media_data['mediapath'])
            self.closeEvent()
            return

        # Put the media in the media player
        self.mediaplayer.set_media(self.media)
        # Parse the metadata of the file
        self.media.parse()
        self.mediaplayer.video_set_mouse_input(False)
        self.mediaplayer.video_set_key_input(False)
        # The media player has to be connected to the QFrame (otherwise the
        # video would be displayed in it's own window). This is platform
        # specific, so we must give the ID of the QFrame (or similar object) to
        # vlc. Different platforms have different functions for this
        if platform.system() == "Linux": # for Linux using the X Server
            #self.mediaplayer.set_xwindow(int(self.ui.frame.winId()))
            self.mediaplayer.set_xwindow(int(self.ddialog.dframe.winId()))
        elif platform.system() == "Windows": # for Windows
            self.mediaplayer.set_hwnd(int(self.ddialog.winId()))
        elif platform.system() == "Darwin": # for MacOS
            self.mediaplayer.set_nsobject(int(self.ddialog.winId()))
        msecs = self.media.get_duration()
        self.ui.label_time_2.setText("Duration: " + msecs_to_mins_and_secs(msecs))
        self.ui.textEdit.setText(self.media_data['memo'])
        self.ui.textEdit.ensureCursorVisible()
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.update_ui)

        self.ui.checkBox_scroll_transcript.stateChanged.connect(self.scroll_transcribed_checkbox_changed)
        #self.play_pause()

    def eventFilter(self, object, event):
        """ Add key options to textEdit_transcription to improve manual transcribing.
        Can only use htese options if the transcription is not coded.
        Options are:
            ctrl + r to rewind 3 seconds.
            xtrl + s to start/pause
            ctrl + t to insert timestamp in format [hh.mm.ss]
            ctrl + n to enter a new speakers name into shortcuts
            ctrl + 1 .. 8 to insert speaker in format [speaker name]
        """

        if object != self.ui.textEdit_transcription:
            return False
        if event.type() != 7:  # QtGui.QKeyEvent
            return False
        # Following options only available if can transcribe
        if not self.can_transcribe:
            return False
        key = event.key()
        mods = event.nativeModifiers()
        #print("KEY ", key, "MODS ", mods)

        # KEY  82 MODS  20 ctrl r
        # rewind 3 seconds
        if key == 82 and mods == 20:
            time_msecs = self.mediaplayer.get_time() - 3000
            if time_msecs < 0:
                time_msecs = 0
            pos = time_msecs / self.mediaplayer.get_media().get_duration()
            self.mediaplayer.play()
            self.mediaplayer.set_position(pos)

        # KEY  84 MODS  20  ctrl t
        # insert timestamp, format [hh.mm.ss]
        if key == 84 and mods == 20:
            time_msecs = self.mediaplayer.get_time()
            mins_secs = msecs_to_mins_and_secs(time_msecs)
            mins = int(mins_secs.split('.')[0])
            secs = mins_secs.split('.')[1]
            hours = int(mins / 60)
            remainder_mins = str(mins - hours * 60)
            hours = str(hours)
            if len(hours) == 1:
                hours = '0' + hours
            ts = '\n[' + str(hours) + '.' + remainder_mins + '.' + secs + ']'
            self.ui.textEdit_transcription.insertPlainText(ts)
        # KEY  49 .. 56 MODS  20  ctrl 1 .. 8
        # insert speaker
        if key in range(49, 57) and mods == 20:
            list_pos = key - 49
            speaker = ""
            try:
                speaker = self.speaker_list[list_pos]
            except:
                return False
            speaker = '[' + speaker + ']'
            self.ui.textEdit_transcription.insertPlainText(speaker)

        # KEY  78 MODS  20 ctrl + n
        if key == 78 and mods == 20:
            self.pause()
            name, ok = QtWidgets.QInputDialog.getText(self, "Speaker name","Name:", QtWidgets.QLineEdit.Normal, "")
            if name == "" or name.find('.') == 0 or name.find(':') == 0 or not ok:
                return False
            if len(self.speaker_list) < 8:
                self.speaker_list.append(name)
            if len(self.speaker_list) == 8:
                # replace last name in the list, if list over 8
                self.speaker_list.pop()
                self.speaker_list.append(name)
            self.add_speaker_names_to_label()
        # KEY  83 MODS  20 ctrl + s pause/play toggle
        if key == 83 and mods == 20:
            self.play_pause()
        return True

    def add_speaker_names_to_label(self):
        """ Add speaker names to label, four on each line. """

        text = ""
        for i, n in enumerate(self.speaker_list):
            if i == 4:
                text += "\n"
            text += str(i + 1) + ": " + n + "  "
        self.ui.label_speakers.setText(text)

    def get_speaker_names_from_bracketed_text(self):
        """ Parse text for [] to find speaker names.
        If needed limit to 8 names. """

        if self.transcription is None:
            return
        text = self.transcription[1]
        start = False
        ts_and_names = ""
        for c in text:
            if c == '[':
                start = True
            if c == ']':
                start = False
            if start:
                ts_and_names = ts_and_names + c
        ts_and_names = ts_and_names.split('[')
        names = []
        for n in ts_and_names:
            if n.find('.') == -1 and n.find(':') == -1 and n != '':
                tidy_n = n.replace('\n', '')
                tidy_n = n.strip()
                names.append(tidy_n)
        names = list(set(names))
        if len(names) > 8:
            names = names[0:8]
        self.speaker_list = names

    def scroll_transcribed_checkbox_changed(self):
        """ If checked, then cannot edit the textEdit_transcribed. """

        if not self.can_transcribe:
            # occurs if there is coded or annotated text.
            return
        if self.ui.checkBox_scroll_transcript.isChecked():
            self.ui.textEdit_transcription.setReadOnly(True)
        else:
            # redo timestamps as text may have been changed by user
            self.get_timestamps_from_transcription()
            self.ui.textEdit_transcription.setReadOnly(False)

    def get_timestamps_from_transcription(self):
        """ Get a list of starting/ending characterpositions and time in milliseconds
        from transcribed text file.

        Example formats:  [00:34:12] [45:33] [01.23.45] [02.34] #00:12:34.567#
        09:33:04,100 --> 09:33:09,600

        Converts hh mm ss to milliseconds with text positions stored in a list
        The list contains lists of [text_pos0, text_pos1, milliseconds] """

        mmss1 = "\[[0-9]?[0-9]:[0-9][0-9]\]"
        hhmmss1 = "\[[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\]"
        mmss2 = "\[[0-9]?[0-9]\.[0-9][0-9]\]"
        hhmmss2 = "\[[0-9][0-9]\.[0-9][0-9]\.[0-9][0-9]\]"
        hhmmss_sss = "#[0-9][0-9]:[0-9][0-9]:[0-9][0-9]\.[0-9][0-9][0-9]#"
        srt = "[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]\s-->\s[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]"

        transcription = self.ui.textEdit_transcription.toPlainText()
        self.time_positions = []
        for match in re.finditer(mmss1, transcription):
            stamp = match.group()[1:-1]
            s = stamp.split(':')
            try:
                msecs = (int(s[0]) * 60 + int(s[1])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss1, transcription):
            stamp = match.group()[1:-1]
            s = stamp.split(':')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s[2])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(mmss2, transcription):
            stamp = match.group()[1:-1]
            s = stamp.split('.')
            try:
                msecs = (int(s[0]) * 60 + int(s[1])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss2, transcription):
            stamp = match.group()[1:-1]
            s = stamp.split('.')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s[2])) * 1000
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(hhmmss_sss, transcription):
            # Format #00:12:34.567#
            stamp = match.group()[1:-1]
            s = stamp.split(':')
            s2 = s[2].split('.')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s2[0])) * 1000 + int(s2[1])
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        for match in re.finditer(srt, transcription):
            # Format 09:33:04,100 --> 09:33:09,600  skip the arrow and second time position
            stamp = match.group()[0:12]
            s = stamp.split(':')
            s2 = s[2].split(',')
            try:
                msecs = (int(s[0]) * 3600 + int(s[1]) * 60 + int(s2[0])) * 1000 + int(s2[1])
                self.time_positions.append([match.span()[0], match.span()[1], msecs])
            except:
                pass
        #print(self.time_positions)

    def set_position(self):
        """ Set the movie position according to the position slider.
        The vlc MediaPlayer needs a float value between 0 and 1, Qt uses
        integer variables, so you need a factor; the higher the factor, the
        more precise are the results (1000 should suffice).
        """

        # Set the media position to where the slider was dragged
        self.timer.stop()
        pos = self.ui.horizontalSlider.value()
        self.mediaplayer.set_position(pos / 1000.0)
        self.timer.start()

    def audio_track_changed(self):
        """ Audio track changed.
        The video needs to be playing/paused before the combobox is filled with track options.
        The combobox only has positive integers."""

        text = self.ui.comboBox_tracks.currentText()
        #print("text: ", text)
        if text == "":
            text = 1
        success = self.mediaplayer.audio_set_track(int(text))
        #print("changed audio ", success)

    def play_pause(self):
        """ Toggle play or pause status. """

        # check that QDialog containinv vlc is visible (i.e. has not been closed)

        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.ui.pushButton_play.setText(_("Play"))
            self.is_paused = True
            self.timer.stop()
        else:
            if self.mediaplayer.play() == -1:
                self.open_file()
                return

            self.mediaplayer.play()
            self.ui.pushButton_play.setText(_("Pause"))
            self.timer.start()
            self.is_paused = False

    def pause(self):
        """ Pause any playback. Called when entering a new speakers name
        during manual transcription. """

        if self.mediaplayer.is_playing():
            self.mediaplayer.pause()
            self.ui.pushButton_play.setText(_("Play"))
            self.is_paused = True
            self.timer.stop()

    def stop(self):
        """ Stop vlc player. Set position slider to the start.
         If multiple audio tracks are shown in the combobox, set the audio track to the first index.
         This is because when beginning play again, the audio track reverts to the first track.
         Programatically setting the audio track to other values does not work. """

        self.mediaplayer.stop()
        self.ui.pushButton_play.setText(_("Play"))
        self.ui.horizontalSlider.setProperty("value", 0)

        # set combobox display of audio track to the first one, or leave it blank if it contains no items
        if self.ui.comboBox_tracks.count() > 0:
            self.ui.comboBox_tracks.setCurrentIndex(0)

    def set_volume(self, volume):
        """ Set the volume. """

        self.mediaplayer.audio_set_volume(volume)

    def update_ui(self):
        """ Updates the user interface. Update the slider position to match media.
         Adds audio track options to combobox.
         Updates the current displayed media time. """

        # update audio track list, only works if media is playing
        if self.mediaplayer.audio_get_track_count() > 0 and self.ui.comboBox_tracks.count() == 0:
            tracks = self.mediaplayer.audio_get_track_description()
            for t in tracks:
                if t[0] > 0:
                    #print(t[0], t[1])  # track number and track name
                    self.ui.comboBox_tracks.addItem(str(t[0]))

        # Set the slider's position to its corresponding media position
        # Note that the setValue function only takes values of type int,
        # so we must first convert the corresponding media position.
        media_pos = int(self.mediaplayer.get_position() * 1000)
        self.ui.horizontalSlider.setValue(media_pos)
        msecs = self.mediaplayer.get_time()
        self.ui.label_time.setText(_("Time: ") + msecs_to_mins_and_secs(msecs))

        """ For long transcripts, update the relevant text position in the textEdit to match the
        video's current position.
        time_postion list itme: [text_pos0, text_pos1, milliseconds]
        """
        if self.ui.checkBox_scroll_transcript.isChecked() and self.transcription is not None and self.ui.textEdit_transcription.toPlainText() != "":
            for i in range(1, len(self.time_positions)):
                if msecs > self.time_positions[i - 1][2] and msecs < self.time_positions[i][2]:
                    text_pos = self.time_positions[i][0]
                    textCursor = self.ui.textEdit_transcription.textCursor()
                    textCursor.setPosition(text_pos)
                    self.ui.textEdit_transcription.setTextCursor(textCursor)

        # No need to call this function if nothing is played
        if not self.mediaplayer.is_playing():
            self.timer.stop()
            # After the video finished, the play button stills shows "Pause",
            # which is not the desired behavior of a media player.
            # This fixes that "bug".
            if not self.is_paused:
                self.stop()

    def closeEvent(self, event):
        """ Stop the vlc player on close. """

        self.ddialog.close()
        self.stop()
        memo = self.ui.textEdit.toPlainText()
        cur = self.app.conn.cursor()
        cur.execute('update source set memo=? where id=?', (memo, self.media_data['id']))
        self.app.conn.commit()
        if self.transcription is not None:
            text = self.ui.textEdit_transcription.toPlainText()
            cur.execute("update source set fulltext=? where id=?", [text, self.transcription[0]])
            self.app.conn.commit()








