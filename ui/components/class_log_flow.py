# -*- coding: utf-8 -*-
"""首页班级日志卡片流组件（直接展示，无需跳转）。"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy, QPushButton,
)

from service import classlog_service
from utils.date_util import format_date, format_datetime
from utils.log_image_util import normalize_image_path, load_thumbnail, image_file_exists
from ui.components.text_label_util import configure_wrap_label, ElideLabel
from ui.styles import set_secondary_button
from ui.components.image_preview_dialog import open_log_image_preview


class LogFlowCard(QFrame):
    """单条日志简约卡片（含可选图片缩略图 / 查看）。"""

    def __init__(self, log, parent=None):
        super().__init__(parent)
        self._log = log or {}
        self._image_path = normalize_image_path(self._log.get("image_path"))
        self.setObjectName("logFlowCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        date_lbl = ElideLabel(format_date(log.get("log_date")))
        date_lbl.setObjectName("logFlowDate")
        date_lbl.setMinimumWidth(80)
        top.addWidget(date_lbl, 0)
        top.addStretch()
        time_lbl = ElideLabel(format_datetime(log.get("create_time")))
        time_lbl.setObjectName("dropletSub")
        time_lbl.setMinimumWidth(100)
        top.addWidget(time_lbl, 1)
        lay.addLayout(top)

        title = QLabel(classlog_service.format_type(log))
        title.setObjectName("logFlowTitle")
        configure_wrap_label(title, min_height=22)
        lay.addWidget(title)

        people = classlog_service.format_participants(log)
        if people:
            part = QLabel(f"参与：{people}")
            part.setObjectName("logFlowParticipants")
            configure_wrap_label(part, min_height=18)
            lay.addWidget(part)

        moral = classlog_service.format_moral(log)
        if moral and moral != "无变动":
            mlab = QLabel(f"德育：{moral}")
            mlab.setObjectName("logFlowParticipants")
            configure_wrap_label(mlab, min_height=18)
            lay.addWidget(mlab)

        content = (log.get("content") or "").strip()
        body = QLabel(content if content else "（无正文）")
        body.setObjectName("logFlowContent")
        configure_wrap_label(body, min_height=20)
        lay.addWidget(body)

        if self._image_path:
            foot = QHBoxLayout()
            foot.setContentsMargins(0, 2, 0, 0)
            foot.setSpacing(8)

            thumb = QLabel()
            thumb.setObjectName("logFlowThumb")
            thumb.setFixedSize(40, 40)
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setScaledContents(False)
            if image_file_exists(self._image_path):
                pix = load_thumbnail(self._image_path, edge=40)
                if not pix.isNull():
                    thumb.setPixmap(pix)
                else:
                    thumb.setText("图")
            else:
                thumb.setText("缺")
            foot.addWidget(thumb, 0)

            foot.addStretch(1)

            btn = QPushButton("查看图片")
            btn.setObjectName("logFlowViewImage")
            set_secondary_button(btn)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self._on_view_image)
            foot.addWidget(btn, 0)
            lay.addLayout(foot)

    def _on_view_image(self):
        open_log_image_preview(self.window(), self._image_path)


class ClassLogFlow(QWidget):
    """
    班级日志流式卡片列表。
    nested_scroll=False：由外层首页滚动承载（推荐）。
    """

    def __init__(self, parent=None, max_items=30, nested_scroll=False):
        super().__init__(parent)
        self.max_items = max_items
        self.nested_scroll = nested_scroll
        self._build_ui()
        self.reload()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(8)
        caption = ElideLabel("班级日志")
        caption.setObjectName("todoScrollCaption")
        caption.setMinimumHeight(24)
        head.addWidget(caption, 1)
        self.lbl_count = ElideLabel()
        self.lbl_count.setObjectName("todoScrollHint")
        self.lbl_count.setMinimumWidth(60)
        head.addWidget(self.lbl_count, 0)
        root.addLayout(head)

        self.host = QWidget()
        self.host.setObjectName("logFlowHost")
        self.host_layout = QVBoxLayout(self.host)
        self.host_layout.setContentsMargins(2, 2, 2, 2)
        self.host_layout.setSpacing(12)

        root.addWidget(self.host)

    def reload(self):
        try:
            rows = classlog_service.list_all()
        except Exception as e:
            rows = []
            print(f"[班级日志流] 加载失败: {e}")

        rows = rows[: self.max_items]

        while self.host_layout.count():
            item = self.host_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not rows:
            empty = QLabel("暂无班级日志")
            empty.setObjectName("todoScrollHint")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setMinimumHeight(40)
            self.host_layout.addWidget(empty)
        else:
            for log in rows:
                self.host_layout.addWidget(LogFlowCard(log))

        self.lbl_count.setText(f"共 {len(rows)} 条")
