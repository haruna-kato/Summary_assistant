from PyQt5.QtWidgets import QWidget, QTextEdit, QHBoxLayout, QApplication, QMessageBox, QDialog, QSizePolicy, QSlider, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import pyqtSignal, QTimer, QThread, QEventLoop
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import Qt, QEvent


import sys
import os
import json
import openshot
import functools

from windows.video_widget import VideoWidget
from windows.preview_thread import PreviewParent
from classes import info, ui_util, time_parts
from classes.app import get_app
from classes.logger import log

from windows.preview_thread import PreviewParent
from windows.video_widget import VideoWidget


class VideoTextWindow(QDialog):
    
    # Path to ui file
    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'video-text.ui')

    # Signals for preview thread
    previewFrameSignal = pyqtSignal(int)
    refreshFrameSignal = pyqtSignal()
    LoadFileSignal = pyqtSignal(str)
    PlaySignal = pyqtSignal()
    PauseSignal = pyqtSignal()
    SeekSignal = pyqtSignal(int)
    SpeedSignal = pyqtSignal(float)
    StopSignal = pyqtSignal()
    
    def __init__(self, video_file, steps_json, parent=None):
        super().__init__()
        _ = get_app()._tr

        # Create dialog class
        QDialog.__init__(self)

        # Load UI from designer
        ui_util.load_ui(self, self.ui_path)

        # Init UI
        ui_util.init_ui(self)
        # breakpoint()

        self.setWindowTitle("Video + Text Editor")
        self.resize(1200, 600)

        self.video_file = video_file
        self.video_length = int(video_file.data['video_length'])
        self.fps_num = int(video_file.data['fps']['num'])
        self.fps_den = int(video_file.data['fps']['den'])
        self.fps = float(self.fps_num) / float(self.fps_den)
        self.sample_rate = int(video_file.data.get('sample_rate', 48000))
        self.channels = int(video_file.data.get('channels', 2))
        self.channel_layout = int(video_file.data.get('channel_layout', 3))

        layout = QHBoxLayout(self)
    
        # 左：VideoWidget（仮）  
        
        # If preview, hide cutting controls
        if self.video_file is not None:
            self.lblInstructions.setVisible(False)
            self.widgetControls.setVisible(False)

        # Add Video Widget        
        self.video_widget = VideoWidget()
        self.video_widget.setObjectName("videoWidget")
        self.video_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.verticalLayout.insertWidget(0, self.video_widget)
        # # self.horizontalLayoutMain.insertWidget(0, self.video_widget, 2)
        # self.video_placeholder_layout = QHBoxLayout(self.video_placeholder)
        # self.video_placeholder_layout.setContentsMargins(0, 0, 0, 0)
        # self.video_placeholder_layout.addWidget(self.video_widget)

        # layout.addWidget(self.video_widget, 2)  # 左 2/3
        
        
        # Timeline の準備
        viewport_rect = self.video_widget.centeredViewport(640, 360)
        self.r = openshot.Timeline(
            viewport_rect.width(),
            viewport_rect.height(),
            openshot.Fraction(self.fps_num, self.fps_den),
            self.sample_rate,
            self.channels,
            self.channel_layout
        )

        # Clip の追加
        self.clip = openshot.Clip(video_file.absolute_path())
        self.clip.SetJson(json.dumps({"reader": video_file.data}))
        self.clip.Start(0)
        self.clip.End(video_file.data['duration'])
        self.clip.display = openshot.FRAME_DISPLAY_CLIP
        self.r.AddClip(self.clip)
        self.r.Open()

        # プレビュースレッド開始
        self.preview_parent = PreviewParent()
        self.preview_parent.Init(self, self.r, self.video_widget, self.video_length)
        self.preview_thread = self.preview_parent.worker

        # Set slider constraints
        self.sliderIgnoreSignal = False
        self.sliderVideo.setMinimum(1)
        self.sliderVideo.setMaximum(self.video_length)
        self.sliderVideo.setSingleStep(1)
        self.sliderVideo.setSingleStep(1)
        self.sliderVideo.setPageStep(24)


        # Connect signals
        self.actionPlay.triggered.connect(self.actionPlay_Triggered)
        self.btnPlay.clicked.connect(self.btnPlay_clicked)
        self.sliderVideo.valueChanged.connect(self.sliderVideo_valueChanged)
        # self.btnStart.clicked.connect(self.btnStart_clicked)
        # self.btnEnd.clicked.connect(self.btnEnd_clicked)
        # self.btnClear.clicked.connect(self.btnClear_clicked)
        # self.btnAddClip.clicked.connect(self.btnAddClip_clicked)
        # # self.txtName.installEventFilter(self)
        self.sliderVideo.installEventFilter(self)
        self.initialized = True

        
        # 右：テキスト編集
        # steps = json.loads(steps_json)
        # breakpoint()
        # text_content = self.format_steps(steps_json)
        # self.textEditSteps.setPlainText(text_content)
        
        self.update_steps_table(steps_json)

    def update_content_safe(self, video_file, steps_json):
        self.video_file = video_file
        self.video_length = int(video_file.data['video_length'])
        # print("Update window")
        
        if self.video_widget:
            self.video_widget.deleteLater()
            self.video_widget = None
        self.preview_parent.Stop()

        # Close readers
        self.r.Close()
        self.clip.Close()
        self.r.ClearAllCache()
        
        if self.preview_parent:
            # 非同期で停止
            QTimer.singleShot(0, self.preview_parent.Stop)

         # --- Clip 更新 ---
        if hasattr(self, 'clip') and self.clip is not None:
            try:
                # Timeline から削除
                self.r.RemoveClip(self.clip)
                # Clip を安全に Close
                self.clip.Close()
            except Exception as e:
                print("Warning: failed to close existing clip:", e)
            self.clip = None
            

        # VideoWidget は削除せず使い回す
        if not hasattr(self, 'video_widget') or self.video_widget is None:
            self.video_widget = VideoWidget()
            self.video_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            self.verticalLayout.insertWidget(0, self.video_widget)
        self.video_widget.show()

        # 新しい Clip 作成
        print(video_file)
        self.clip = openshot.Clip(video_file.absolute_path())
        self.clip.SetJson(json.dumps({"reader": video_file.data}))
        self.clip.Start(0)
        self.clip.End(video_file.data.get('duration', self.video_length))
        self.clip.display = openshot.FRAME_DISPLAY_CLIP
        self.r.AddClip(self.clip)
        
        
        
        self.preview_parent = PreviewParent()
        self.preview_parent.Init(self, self.r, self.video_widget, self.video_length)
        self.preview_thread = self.preview_parent.worker

        # Set slider constraints
        self.sliderIgnoreSignal = False
        self.sliderVideo.setMinimum(1)
        self.sliderVideo.setMaximum(self.video_length)
        self.sliderVideo.setSingleStep(1)
        self.sliderVideo.setSingleStep(1)
        self.sliderVideo.setPageStep(24)


        # Connect signals
        self.actionPlay.triggered.connect(self.actionPlay_Triggered)
        self.btnPlay.clicked.connect(self.btnPlay_clicked)
        self.sliderVideo.valueChanged.connect(self.sliderVideo_valueChanged)
        self.sliderVideo.installEventFilter(self)
        self.initialized = True

        # --- テキスト更新 ---
        self.update_steps_table(steps_json)
        
        # print("Update complete")


    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress and obj is self.txtName:
            # Handle ENTER key to create new clip
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if self.btnAddClip.isEnabled():
                    self.btnAddClip_clicked()
                    return True
        if event.type() == QEvent.MouseButtonPress and isinstance(obj, QSlider):
            # Handle QSlider click, jump to cursor position
            if event.button() == Qt.LeftButton:
                min_val = obj.minimum()
                max_val = obj.maximum()

                click_position = event.pos().x() if obj.orientation() == Qt.Horizontal else event.pos().y()
                slider_length = obj.width() if obj.orientation() == Qt.Horizontal else obj.height()
                new_value = min_val + ((max_val - min_val) * click_position) / slider_length

                obj.setValue(int(new_value))
                event.accept()
        return super().eventFilter(obj, event)

    def actionPlay_Triggered(self):
        # Trigger play button (This action is invoked from the preview thread, so it must exist here)
        self.btnPlay.click()

    def movePlayhead(self, frame_number):
        """Update the playhead position"""

        # Move slider to correct frame position
        self.sliderIgnoreSignal = True
        self.sliderVideo.setValue(frame_number)
        self.sliderIgnoreSignal = False

        # Convert frame to seconds
        seconds = (frame_number-1) / self.fps

        # Convert seconds to time stamp
        time_text = time_parts.secondsToTime(seconds, self.fps_num, self.fps_den)
        timestamp = "%s:%s:%s:%s" % (time_text["hour"], time_text["min"], time_text["sec"], time_text["frame"])

        # Update label
        self.lblVideoTime.setText(timestamp)

    def btnPlay_clicked(self, force=None):
        # log.info("btnPlay_clicked")

        if force == "pause":
            self.btnPlay.setChecked(False)
        elif force == "play":
            self.btnPlay.setChecked(True)

        if self.btnPlay.isChecked():
            # log.info('play (icon to pause)')
            ui_util.setup_icon(self, self.btnPlay, "actionPlay", "media-playback-pause")
            self.preview_thread.Play()
        else:
            # log.info('pause (icon to play)')
            ui_util.setup_icon(self, self.btnPlay, "actionPlay", "media-playback-start")  # to default
            self.preview_thread.Pause()

        # Send focus back to toolbar
        self.sliderVideo.setFocus()

    def sliderVideo_valueChanged(self, new_frame):
        if self.preview_thread and not self.sliderIgnoreSignal:
            # log.info('sliderVideo_valueChanged')

            # Pause video
            self.btnPlay_clicked(force="pause")

            # Seek to new frame
            self.preview_thread.previewFrame(new_frame)
    
    def closeEvent(self, event):
        # print("closeEvent")
        # breakpoint()
        # Stop playback
        get_app().updates.disconnect_listener(self.video_widget)
        if self.video_widget:
            self.video_widget.deleteLater()
            self.video_widget = None
        self.preview_parent.Stop()

        # Close readers
        self.r.Close()
        self.clip.Close()
        self.r.ClearAllCache()

        
    def format_steps(self,steps_json):

        steps = json.loads(steps_json)
        lines = []
        for i, step in enumerate(steps, start=1):
            start_sec = int(step.get('start', 0))
            end_sec = int(step.get('end', 0))
            text = step.get('text', '')

            # 秒 → mm:ss
            start_str = f"{start_sec // 60:02}:{start_sec % 60:02}"
            end_str   = f"{end_sec // 60:02}:{end_sec % 60:02}"

            # 行を作る（手順番号 | 時間 | テキスト）
            line = f"{i} | {start_str}-{end_str} | {text}"
            lines.append(line)

        return "\n".join(lines)
    
    def update_steps_table(self, steps_json):
        """QTableWidget にステップ情報を反映"""
        steps = json.loads(steps_json)
        table = self.tableSteps
        table.clearContents()
        self.tableSteps.verticalHeader().setVisible(False)

         # 行をステップ数に合わせる
        table.setRowCount(len(steps))
        table.setColumnCount(4)  # 番号 | 開始 | 終了 | 手順
        table.setHorizontalHeaderLabels(["番号", "開始", "終了", "手順"])
        # 見出しを左寄せ
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for i, step in enumerate(steps):
            start_sec = int(step.get('start', 0))
            end_sec   = int(step.get('end', 0))
            text      = step.get('text', '')

            start_str = f"{start_sec // 60:02}:{start_sec % 60:02}"
            end_str   = f"{end_sec // 60:02}:{end_sec % 60:02}"

            table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            table.setItem(i, 1, QTableWidgetItem(start_str))
            table.setItem(i, 2, QTableWidgetItem(end_str))
            table.setItem(i, 3, QTableWidgetItem(text))

        # 列幅調整
        header = table.horizontalHeader()
        # 最後の列（手順）だけ伸ばす
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)


    # def btnStart_clicked(self):
    #     """Start of clip button was clicked"""
    #     _ = get_app()._tr

    #     # Pause video
    #     self.btnPlay_clicked(force="pause")

    #     # Get the current frame
    #     current_frame = self.sliderVideo.value()

    #     # Check if starting frame less than end frame
    #     if self.btnEnd.isEnabled() and current_frame >= self.end_frame:
    #         # Handle exception
    #         msg = QMessageBox()
    #         msg.setText(_("Please choose valid 'start' and 'end' values for your clip."))
    #         msg.exec_()
    #         return

    #     # remember frame #
    #     self.start_frame = current_frame

    #     # Save thumbnail image
    #     self.start_image = os.path.join(info.USER_PATH, 'thumbnail', '%s.png' % self.start_frame)
    #     self.r.GetFrame(self.start_frame).Thumbnail(self.start_image, 160, 90, '', '', '#000000', True, 'png', 85)

    #     # Set CSS on button
    #     self.btnStart.setStyleSheet('background-image: url(%s);' % self.start_image.replace('\\', '/'))

    #     # Enable end button
    #     self.btnEnd.setEnabled(True)
    #     self.btnClear.setEnabled(True)

    #     # Send focus back to toolbar
    #     self.sliderVideo.setFocus()

    #     log.info('btnStart_clicked, current frame: %s' % self.start_frame)

    # def btnEnd_clicked(self):
    #     """End of clip button was clicked"""
    #     _ = get_app()._tr

    #     # Pause video
    #     self.btnPlay_clicked(force="pause")

    #     # Get the current frame
    #     current_frame = self.sliderVideo.value()

    #     # Check if ending frame greater than start frame
    #     if current_frame <= self.start_frame:
    #         # Handle exception
    #         msg = QMessageBox()
    #         msg.setText(_("Please choose valid 'start' and 'end' values for your clip."))
    #         msg.exec_()
    #         return

    #     # remember frame #
    #     self.end_frame = current_frame

    #     # Save thumbnail image
    #     self.end_image = os.path.join(info.USER_PATH, 'thumbnail', '%s.png' % self.end_frame)
    #     self.r.GetFrame(self.end_frame).Thumbnail(self.end_image, 160, 90, '', '', '#000000', True, 'png', 85)

    #     # Set CSS on button
    #     self.btnEnd.setStyleSheet('background-image: url(%s);' % self.end_image.replace('\\', '/'))

    #     # Enable create button
    #     self.btnAddClip.setEnabled(True)

    #     # Send focus back to toolbar
    #     self.sliderVideo.setFocus()

    #     log.info('btnEnd_clicked, current frame: %s' % self.end_frame)

    # def btnClear_clicked(self):
    #     """Clear the current clip and reset the form"""
    #     log.info('btnClear_clicked')

    #     # Reset form
    #     self.clearForm()

    # def clearForm(self):
    #     """Clear all form controls"""
    #     # Clear buttons
    #     self.start_frame = 1
    #     self.end_frame = 1
    #     self.start_image = ''
    #     self.end_image = ''
    #     self.btnStart.setStyleSheet('background-image: None;')
    #     self.btnEnd.setStyleSheet('background-image: None;')

    #     # Clear text
    #     self.txtName.setText('')

    #     # Disable buttons
    #     self.btnEnd.setEnabled(False)
    #     self.btnAddClip.setEnabled(False)
    #     self.btnClear.setEnabled(False)

    # def btnAddClip_clicked(self):
    #     """Add the selected clip to the project"""
    #     log.info('btnAddClip_clicked')

    #     # Remove unneeded attributes
    #     if 'name' in self.file.data:
    #         self.file.data.pop('name')

    #     # Get initial start / end properties (if any)
    #     previous_start = self.file.data.get("start", 0.0)

    #     # Save new file
    #     self.file.id = None
    #     self.file.key = None
    #     self.file.type = 'insert'
    #     self.file.data['start'] = previous_start + ((self.start_frame - 1) / self.fps)
    #     self.file.data['end'] = previous_start + (self.end_frame / self.fps)
    #     if self.txtName.text():
    #         self.file.data['name'] = self.txtName.text()
    #     self.file.save()

    #     # Move to next frame
    #     self.sliderVideo.setValue(self.end_frame + 1)

    #     # Reset form
    #     self.clearForm()

