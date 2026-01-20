from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QLabel
from PyQt5.QtCore import QTimer
from classes.logger import log
from classes.app import get_app

class TextPreview(QDialog):
    def __init__(self, file=None, preview=False):
        super().__init__()

        _ = get_app()._tr
        self.file = file
        self.file_path = file.absolute_path()
        
        # UI
        self.setWindowTitle("Text Preview")
        self.verticalLayout = QVBoxLayout()
        self.setLayout(self.verticalLayout)

        # 説明ラベル（Cutting の lblInstructions みたいに）
        self.lblInstructions = QLabel("Text Preview")
        if preview:
            self.lblInstructions.setVisible(False)
        self.verticalLayout.addWidget(self.lblInstructions)
        
        # テキスト表示ウィジェット（Cutting の VideoWidget の代わり）
        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        font = self.textEdit.font()
        font.setPointSize(14)   # ← ここで文字サイズを指定（例：14pt）
        self.textEdit.setFont(font)

        self.verticalLayout.addWidget(self.textEdit)
        
        # ファイル読み込み
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Failed to load file:\n{e}"
        self.textEdit.setText(content)
        
        # Optional: preview フラグでウィンドウタイトル変更
        if preview:
            self.setWindowTitle(_("Preview"))
        log.info("set preview")
 