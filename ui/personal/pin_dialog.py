# -*- coding: utf-8 -*-
"""个人模式 PIN 验证弹窗（米色+棕色，匹配主界面风格）。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QFormLayout, QWidget,
)

from utils import personal_pin
from ui.styles import set_secondary_button, get_global_qss


class ChangePinDialog(QDialog):
    """修改 PIN：须验证旧密码。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("personalPinDialog")
        self.setWindowTitle("修改 PIN 码")
        self.setModal(True)
        self.resize(400, 260)
        self.setStyleSheet(get_global_qss())

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        title = QLabel("修改 PIN 码")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        tip = QLabel("请先验证旧 PIN，再设置 4~6 位新 PIN")
        tip.setObjectName("hintLabel")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        form = QFormLayout()
        self.edit_old = QLineEdit()
        self.edit_old.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_old.setMaxLength(6)
        self.edit_new = QLineEdit()
        self.edit_new.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_new.setMaxLength(6)
        self.edit_new2 = QLineEdit()
        self.edit_new2.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_new2.setMaxLength(6)
        form.addRow("旧 PIN", self.edit_old)
        form.addRow("新 PIN", self.edit_new)
        form.addRow("确认新 PIN", self.edit_new2)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        set_secondary_button(btn_cancel)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存")
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)
        self.edit_old.setFocus()

    def _on_ok(self):
        old_pin = self.edit_old.text().strip()
        new_pin = self.edit_new.text().strip()
        new2 = self.edit_new2.text().strip()
        try:
            personal_pin.validate_pin_format(new_pin)
            if new_pin != new2:
                raise ValueError("两次输入的新 PIN 不一致")
            personal_pin.change_pin(old_pin, new_pin)
        except ValueError as e:
            QMessageBox.warning(self, "提示", str(e))
            return
        QMessageBox.information(self, "成功", "PIN 码已修改")
        self.accept()


class PersonalPinDialog(QDialog):
    """首次设置 / 后续校验 PIN；支持修改密码（需验证旧 PIN）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("personalPinDialog")
        self.setWindowTitle("个人模式安全验证")
        self.setModal(True)
        self.resize(400, 280)
        self.setStyleSheet(get_global_qss())
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(16, 16, 16, 16)
        self._root.setSpacing(12)
        self._body = QWidget()
        self._root.addWidget(self._body)
        self._rebuild()

    def _is_setup(self) -> bool:
        return not personal_pin.has_pin()

    def _clear_body(self):
        old = self._body
        self._body = QWidget()
        self._root.replaceWidget(old, self._body)
        old.deleteLater()

    def _rebuild(self):
        self._clear_body()
        lay = QVBoxLayout(self._body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        title = QLabel("进入个人模式")
        title.setObjectName("pageTitle")
        lay.addWidget(title)

        if self._is_setup():
            tip = QLabel("首次进入：请设置 4~6 位数字 PIN 码（本地加密保存）")
        else:
            tip = QLabel("请输入 PIN 码以进入个人空间")
        tip.setObjectName("hintLabel")
        tip.setWordWrap(True)
        lay.addWidget(tip)

        form = QFormLayout()
        self.edit_pin = QLineEdit()
        self.edit_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_pin.setMaxLength(6)
        self.edit_pin.setPlaceholderText("4~6 位数字")
        form.addRow("PIN 码", self.edit_pin)

        self.edit_pin2 = None
        if self._is_setup():
            self.edit_pin2 = QLineEdit()
            self.edit_pin2.setEchoMode(QLineEdit.EchoMode.Password)
            self.edit_pin2.setMaxLength(6)
            self.edit_pin2.setPlaceholderText("再次确认")
            form.addRow("确认 PIN", self.edit_pin2)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        if not self._is_setup():
            btn_change = QPushButton("修改密码")
            set_secondary_button(btn_change)
            btn_change.clicked.connect(self._on_change_pin)
            btn_row.addWidget(btn_change)
        btn_row.addStretch()
        btn_cancel = QPushButton("取消")
        set_secondary_button(btn_cancel)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("保存并进入" if self._is_setup() else "进入")
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)
        self.edit_pin.returnPressed.connect(self._on_ok)
        self.edit_pin.setFocus()

    def _on_ok(self):
        pin = self.edit_pin.text().strip()
        try:
            if self._is_setup():
                personal_pin.validate_pin_format(pin)
                if not self.edit_pin2 or self.edit_pin2.text().strip() != pin:
                    raise ValueError("两次输入的 PIN 不一致")
                personal_pin.set_pin(pin)
            else:
                if not personal_pin.verify_pin(pin):
                    QMessageBox.warning(self, "验证失败", "PIN 码错误，请重试")
                    self.edit_pin.clear()
                    self.edit_pin.setFocus()
                    return
            self.accept()
        except ValueError as e:
            QMessageBox.warning(self, "提示", str(e))

    def _on_change_pin(self):
        dlg = ChangePinDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.edit_pin.clear()
            self.edit_pin.setFocus()


def run_personal_pin_gate(parent=None) -> bool:
    """弹出 PIN 门禁；True 表示可进入个人模式。"""
    dlg = PersonalPinDialog(parent)
    return dlg.exec() == QDialog.DialogCode.Accepted
