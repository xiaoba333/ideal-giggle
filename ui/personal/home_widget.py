# -*- coding: utf-8 -*-
"""个人模式首页：放大日历填满可视区；日记仅从此入口进入。"""

from __future__ import annotations

from datetime import date, timedelta

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QDialog,
)

from service import personal_service
from ui.personal.personal_calendar import PersonalCalendar
from ui.personal.leaf_button import LeafButton
from ui.personal.dialogs import DiaryFormDialog, MilestoneFormDialog, MoodFormDialog


class PersonalHomeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._build_ui()
        self.reload_marks()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("个人空间")
        title.setObjectName("pageTitle")
        head.addWidget(title)
        head.addStretch()
        self.lbl_sel = QLabel("")
        self.lbl_sel.setObjectName("hintLabel")
        head.addWidget(self.lbl_sel)
        root.addLayout(head)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_diary = LeafButton("日记")
        self.btn_ms = LeafButton("里程碑")
        self.btn_mood = LeafButton("标心情")
        self.btn_view_ms = LeafButton("查看里程碑", tone="soft")
        self.btn_diary.clicked.connect(self._on_diary)
        self.btn_ms.clicked.connect(self._on_add_milestone)
        self.btn_mood.clicked.connect(self._on_set_mood)
        self.btn_view_ms.clicked.connect(self._on_view_milestones)
        actions.addWidget(self.btn_diary)
        actions.addWidget(self.btn_ms)
        actions.addWidget(self.btn_mood)
        actions.addWidget(self.btn_view_ms)
        actions.addStretch()
        root.addLayout(actions)

        self.calendar = PersonalCalendar()
        self.calendar.date_selected.connect(self._on_date)
        self.calendar.month_changed.connect(lambda *_: self.reload_marks())
        root.addWidget(self.calendar, 1)

        self._update_sel_label(self.calendar.selected_date())

    def _date_str(self) -> str:
        qd = self.calendar.selected_date() or QDate.currentDate()
        return qd.toString("yyyy-MM-dd")

    def _update_sel_label(self, qd: QDate | None):
        if not qd or not qd.isValid():
            self.lbl_sel.setText("")
            return
        mood = personal_service.get_mood(qd.toString("yyyy-MM-dd"))
        mood_txt = personal_service.mood_display(mood) if mood else "未标注"
        has_diary = False
        try:
            rows = personal_service.list_diaries_by_date(qd.toString("yyyy-MM-dd"))
            has_diary = bool(rows)
        except Exception:
            pass
        diary_txt = "有日记" if has_diary else "无日记"
        self.lbl_sel.setText(
            f"选中 {qd.toString('yyyy-MM-dd')}　心情：{mood_txt}　{diary_txt}"
        )

    def _on_date(self, qd: QDate):
        self._update_sel_label(qd)

    def reload_marks(self):
        y, m = self.calendar.year(), self.calendar.month()
        start = date(y, m, 1) - timedelta(days=7)
        if m == 12:
            end = date(y + 1, 1, 1) + timedelta(days=7)
        else:
            end = date(y, m + 1, 1) + timedelta(days=7)
        try:
            marks = personal_service.calendar_marks(start, end)
        except Exception as e:
            print(f"[个人日历] 加载标记失败: {e}")
            marks = {"diary_dates": set(), "milestone_dates": set(), "moods": {}}
        self.calendar.set_marks(
            milestone_dates=marks["milestone_dates"],
            diary_dates=marks["diary_dates"],
            moods=marks["moods"],
        )
        self._update_sel_label(self.calendar.selected_date())

    def refresh(self):
        self.reload_marks()

    def _on_diary(self):
        """有日记则打开最近一篇重编；无则新建。"""
        ds = self._date_str()
        diary = None
        try:
            rows = personal_service.list_diaries_by_date(ds)
            if rows:
                diary = rows[0]
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return

        dlg = DiaryFormDialog(self, diary=diary, default_date=ds)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if dlg.deleted:
            if diary:
                try:
                    personal_service.remove_diary(diary["id"])
                    QMessageBox.information(self, "成功", "日记已删除")
                    self.reload_marks()
                except Exception as e:
                    QMessageBox.warning(self, "失败", str(e))
            return

        data = dlg.get_data()
        try:
            if diary:
                # edit_diary 不改日期，去掉冗余参数
                data.pop("diary_date", None)
                personal_service.edit_diary(diary["id"], **data)
                QMessageBox.information(self, "成功", "日记已更新")
            else:
                personal_service.add_diary(**data)
                QMessageBox.information(self, "成功", "日记已保存")
            self.reload_marks()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_add_milestone(self):
        dlg = MilestoneFormDialog(self, default_date=self._date_str())
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.deleted:
            return
        data = dlg.get_data()
        try:
            personal_service.add_milestone(**data)
            QMessageBox.information(self, "成功", "里程碑已保存")
            self.reload_marks()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_set_mood(self):
        ds = self._date_str()
        cur = personal_service.get_mood(ds)
        dlg = MoodFormDialog(self, date_str=ds, current_mood=cur)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            if dlg.cleared:
                personal_service.clear_mood(ds)
                QMessageBox.information(self, "成功", "已清空心情")
            else:
                personal_service.set_mood(ds, dlg.selected_mood())
                QMessageBox.information(self, "成功", "心情已更新")
            self.reload_marks()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def _on_view_milestones(self):
        ds = self._date_str()
        try:
            rows = personal_service.list_milestones_by_date(ds)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return
        if not rows:
            QMessageBox.information(self, "提示", f"{ds} 暂无里程碑")
            return
        ms = rows[0]
        if len(rows) > 1:
            titles = "\n".join(f"- {r.get('title')}" for r in rows)
            QMessageBox.information(
                self, f"{ds} 里程碑", f"共 {len(rows)} 条，将打开最新一条：\n{titles}"
            )
        dlg = MilestoneFormDialog(self, milestone=ms)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        if dlg.deleted:
            try:
                personal_service.remove_milestone(ms["id"])
                self.reload_marks()
            except Exception as e:
                QMessageBox.warning(self, "失败", str(e))
            return
        data = dlg.get_data()
        try:
            personal_service.edit_milestone(ms["id"], data["title"], data["content"])
            self.reload_marks()
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
