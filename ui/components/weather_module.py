# -*- coding: utf-8 -*-
"""
首页天气水滴模块：IP 定位 + 城市查询 + 实况展示。
- QTimer 启动后全程轮询（5 分钟），不因切页/迷你/滚动而 stop
- 网络仅在 QThread；成功经信号回传并刷新 UI
- 失败保留旧数据；无数据库持久化（仅内存展示）
"""

from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFrame, QSizePolicy,
)

from ui.components.droplet_card import DropletCard
from ui.components.weather_icon import WeatherIconWidget
from ui.components.text_label_util import configure_wrap_label, ElideLabel
from ui.styles import set_secondary_button
from utils.location_tool import locate_city_or_default, DEFAULT_CITY
from utils.weather_tool import get_weather_by_city, clear_weather_cache
from utils import weather_state

_AUTO_REFRESH_MS = 300_000
_THREAD_WAIT_MS = 8_000


class WeatherFetchThread(QThread):
    """独立子线程拉取天气（禁止主线程访问网络）。"""

    success = pyqtSignal(dict)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, city=None, auto_locate=False, force_refresh=True, parent=None):
        super().__init__(parent)
        self.city = (city or "").strip() or None
        self.auto_locate = bool(auto_locate)
        self.force_refresh = bool(force_refresh)
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            if self._cancelled:
                return
            city = self.city
            if self.auto_locate or not city:
                self.status.emit("正在定位城市…")
                if self._cancelled:
                    return
                city, from_ip, _ = locate_city_or_default()
                if self._cancelled:
                    return
                tip = f"定位成功：{city}" if from_ip else f"使用默认城市「{city}」"
                self.status.emit(f"{tip}，拉取天气…")
            else:
                self.status.emit(f"正在查询「{city}」…")

            if self._cancelled:
                return
            if self.force_refresh:
                clear_weather_cache(city)
            data = get_weather_by_city(city, use_cache=False)
            if self._cancelled:
                return
            if not isinstance(data, dict) or not data:
                raise RuntimeError("天气接口返回空数据")
            self.success.emit(data)
        except TimeoutError as e:
            if not self._cancelled:
                self.failed.emit(f"请求超时：{e}")
        except Exception as e:
            if not self._cancelled:
                self.failed.emit(str(e))


class WeatherModule(DropletCard):
    """首页天气：定时器全程运行；仅 shutdown() 时停止。"""

    refresh_requested = pyqtSignal()  # 定时器触发的刷新信号

    def __init__(self, parent=None, compact=False, local_only=False):
        self._compact = compact
        self._local_only = local_only or compact
        min_w = 160 if compact else 240
        min_h = 140 if self._local_only else (170 if compact else 260)
        super().__init__(parent, min_width=min_w, min_height=min_h)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if compact:
            self.setProperty("compact", True)

        self._worker = None
        self._shutting_down = False
        self._ui_active = True  # 迷你模式时可置 False，但不停定时器
        self._session_city = None
        self._last_weather = None
        self._refresh_pending = False

        self._build_content()
        self._apply_empty_state("准备加载天气…")

        self._timer = QTimer(self)
        self._timer.setInterval(_AUTO_REFRESH_MS)
        self._timer.timeout.connect(self.refresh_requested.emit)
        self.refresh_requested.connect(self._on_refresh_requested)
        # 初始化即开启 5 分钟轮询（全程不停，直至 shutdown）
        self._timer.start(_AUTO_REFRESH_MS)

        if not compact:
            self._bootstrap()

    # ---------- 生命周期 ----------
    def shutdown(self):
        """仅程序关闭时调用：停定时器并等待网络线程结束。"""
        self._shutting_down = True
        self._ui_active = False
        if self._timer.isActive():
            self._timer.stop()
        self._wait_worker()

    def stop_network(self):
        """兼容旧调用：不再停止定时器，仅标记 UI 非活跃。"""
        self._ui_active = False

    def start_network(self, reload=True):
        """兼容旧调用：恢复 UI 活跃；定时器若意外未启动则拉起。"""
        self._ui_active = True
        self._shutting_down = False
        if not self._timer.isActive():
            self._timer.start(_AUTO_REFRESH_MS)
        self._set_buttons_enabled(True)
        if reload:
            self.request_refresh(force=True)

    def pause_ui(self):
        """切迷你等场景：隐藏刷新，不停定时器。"""
        self._ui_active = False

    def resume_ui(self, reload=False):
        self._ui_active = True
        if not self._timer.isActive():
            self._timer.start(_AUTO_REFRESH_MS)
        # 先用共享快照对齐小窗，避免图标短暂不一致
        shared = weather_state.get_last_weather()
        if shared and (
            self._last_weather is None
            or self._weather_fingerprint(self._last_weather)
            != self._weather_fingerprint(shared)
        ):
            self._last_weather = shared
            self._apply_weather_data(shared)
        if reload:
            self.request_refresh(force=True)
        elif self._last_weather:
            self._apply_weather_data(self._last_weather)

    def last_weather(self):
        return dict(self._last_weather) if self._last_weather else None

    def session_city(self):
        return self._session_city or weather_state.get_preferred_city()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    # ---------- UI ----------
    def _build_content(self):
        lay = self.content()
        lay.setSpacing(6 if self._compact else 10)
        if self._compact:
            lay.setContentsMargins(12, 10, 12, 10)

        title = ElideLabel("当地天气" if self._local_only else "今日天气")
        title.setObjectName("dropletTitle")
        title.setMinimumHeight(20 if self._compact else 24)
        lay.addWidget(title)

        if self._local_only:
            row = QHBoxLayout()
            row.setSpacing(6)
            tip = ElideLabel("当前定位城市实况")
            tip.setObjectName("dropletSub")
            row.addWidget(tip, 1)
            self.btn_refresh = QPushButton("手动刷新")
            self.btn_refresh.setMinimumSize(72, 26)
            self.btn_refresh.setToolTip("立即拉取最新天气")
            set_secondary_button(self.btn_refresh)
            self.btn_refresh.clicked.connect(self._on_manual_refresh)
            row.addWidget(self.btn_refresh)
            self.btn_local = QPushButton("重定位")
            self.btn_local.setMinimumSize(64, 26)
            self.btn_local.clicked.connect(self._on_local_weather)
            row.addWidget(self.btn_local)
            lay.addLayout(row)
            self.edit_city = None
            self.btn_query = None
        else:
            row = QHBoxLayout()
            row.setSpacing(6)
            self.edit_city = QLineEdit()
            self.edit_city.setObjectName("weatherCityEdit")
            self.edit_city.setPlaceholderText("输入城市，如：杭州（仅本次有效）")
            self.edit_city.setMinimumHeight(30)
            self.edit_city.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            self.edit_city.returnPressed.connect(self._on_query_clicked)
            row.addWidget(self.edit_city, 1)

            self.btn_query = QPushButton("查询")
            self.btn_query.setMinimumSize(64, 30)
            self.btn_query.clicked.connect(self._on_query_clicked)
            row.addWidget(self.btn_query)

            self.btn_refresh = QPushButton("手动刷新")
            self.btn_refresh.setMinimumSize(80, 30)
            self.btn_refresh.setToolTip("立刻拉取最新天气，用于验证接口")
            set_secondary_button(self.btn_refresh)
            self.btn_refresh.clicked.connect(self._on_manual_refresh)
            row.addWidget(self.btn_refresh)

            self.btn_local = QPushButton("本地天气")
            self.btn_local.setMinimumSize(80, 30)
            self.btn_local.clicked.connect(self._on_local_weather)
            row.addWidget(self.btn_local)
            lay.addLayout(row)

        info = QHBoxLayout()
        info.setSpacing(10 if self._compact else 14)
        info.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon_size = 56 if self._compact else 88
        self.icon = WeatherIconWidget(size=icon_size)
        self.icon.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        info.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4 if self._compact else 8)
        text_col.setContentsMargins(0, 2, 0, 0)

        self.lbl_city = QLabel()
        self.lbl_city.setObjectName("dropletSub")
        configure_wrap_label(self.lbl_city, min_height=18 if self._compact else 22)
        text_col.addWidget(self.lbl_city)

        self.lbl_condition = QLabel()
        self.lbl_condition.setObjectName("weatherCondition")
        configure_wrap_label(self.lbl_condition, min_height=20 if self._compact else 26)
        text_col.addWidget(self.lbl_condition)

        self.lbl_temp = ElideLabel()
        self.lbl_temp.setObjectName("weatherTemp")
        self.lbl_temp.setMinimumHeight(28 if self._compact else 40)
        text_col.addWidget(self.lbl_temp)

        self.lbl_detail = QLabel()
        self.lbl_detail.setObjectName("weatherBody")
        configure_wrap_label(self.lbl_detail, min_height=28 if self._compact else 40)
        text_col.addWidget(self.lbl_detail)

        text_col.addStretch()
        info.addLayout(text_col, 1)
        lay.addLayout(info, 1)

        line = QFrame()
        line.setObjectName("weatherDivider")
        line.setFixedHeight(1)
        lay.addWidget(line)

        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("dropletSub")
        configure_wrap_label(self.lbl_status, min_height=22 if self._compact else 36)
        lay.addWidget(self.lbl_status)

    def _set_buttons_enabled(self, enabled: bool):
        if self.btn_query is not None and not self._local_only:
            self.btn_query.setEnabled(enabled)
        if self.btn_local is not None:
            self.btn_local.setEnabled(enabled)
        if self.btn_refresh is not None:
            self.btn_refresh.setEnabled(enabled)

    # ---------- 刷新入口 ----------
    def _bootstrap(self):
        self._session_city = None
        if self.edit_city is not None:
            self.edit_city.clear()
        self.request_refresh(force=True, auto_locate=True)

    def _on_refresh_requested(self):
        """定时器信号：只触发刷新，网络在子线程。"""
        if self._shutting_down:
            return
        self.request_refresh(force=True)

    def _on_manual_refresh(self):
        self.request_refresh(force=True)

    def refresh(self, force: bool = False):
        """兼容首页 refresh() 调用。"""
        self.request_refresh(force=force)

    def flush_deferred_ui(self):
        """兼容滚动结束回调（已不再因滚动丢弃天气更新）。"""
        if self._last_weather and self._ui_active:
            self._apply_weather_data(self._last_weather)

    def request_refresh(self, force: bool = True, auto_locate=None):
        if self._shutting_down:
            return
        if self._worker is not None and self._worker.isRunning():
            self._refresh_pending = True
            if self._ui_active:
                self.lbl_status.setText("正在请求中，请稍候…")
            return

        if self._local_only:
            city, locate = None, True
        elif self._session_city:
            city, locate = self._session_city, False
            if self.edit_city is not None:
                self.edit_city.setText(self._session_city)
        else:
            # 与小窗共用已成功查询过的城市，避免各自 IP 定位结果不同
            shared_city = weather_state.get_preferred_city()
            if shared_city:
                city, locate = shared_city, False
            else:
                city, locate = None, True

        if auto_locate is not None:
            locate = bool(auto_locate)
            if locate:
                city = None

        self._start_worker(city=city, auto_locate=locate, force_refresh=force)

    def set_temp_city(self, city: str):
        city = (city or "").strip()
        if not city:
            self._on_local_weather()
            return
        self._session_city = city
        weather_state.set_preferred_city(city)
        if self.edit_city is not None:
            self.edit_city.setText(city)
        self.request_refresh(force=True, auto_locate=False)

    def _on_query_clicked(self):
        if self._local_only:
            self._on_local_weather()
            return
        city = self.edit_city.text().strip() if self.edit_city else ""
        if not city:
            self.lbl_status.setText("请输入城市名称后再查询")
            return
        self._session_city = city
        weather_state.set_preferred_city(city)
        self.request_refresh(force=True, auto_locate=False)

    def _on_local_weather(self):
        self._session_city = None
        weather_state.clear_preferred_city()
        if self.edit_city is not None:
            self.edit_city.clear()
        self.request_refresh(force=True, auto_locate=True)

    # ---------- 线程 ----------
    def _wait_worker(self):
        worker = self._worker
        if worker is None:
            return
        worker.cancel()
        if worker.isRunning():
            worker.wait(_THREAD_WAIT_MS)
        self._worker = None

    def _start_worker(self, city=None, auto_locate=False, force_refresh=True):
        if self._shutting_down:
            return
        if self._worker is not None and self._worker.isRunning():
            self._refresh_pending = True
            return

        self._set_buttons_enabled(False)
        worker = WeatherFetchThread(
            city=city,
            auto_locate=auto_locate,
            force_refresh=force_refresh,
            parent=self,
        )
        self._worker = worker
        worker.status.connect(self._on_status)
        worker.success.connect(self._on_success)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_thread_finished)
        worker.start()

    def _on_status(self, text):
        if self._ui_active and not self._shutting_down:
            self.lbl_status.setText(text)

    def _on_success(self, data):
        """信号回传 → 仅数据实际变化时刷新 UI。"""
        if self._shutting_down:
            return
        if not isinstance(data, dict) or not data:
            return
        new = dict(data)
        changed = (
            self._last_weather is None
            or self._weather_fingerprint(self._last_weather) != self._weather_fingerprint(new)
        )
        self._last_weather = new
        weather_state.set_last_weather(new)
        if self._ui_active and changed:
            self._apply_weather_data(self._last_weather)

    @staticmethod
    def _weather_fingerprint(data: dict):
        return (
            data.get("city") or data.get("query_city"),
            data.get("condition"),
            data.get("temperature"),
            data.get("humidity"),
            data.get("wind"),
            data.get("weather_code"),
        )

    def _apply_weather_data(self, data):
        city = data.get("city") or data.get("query_city") or ""
        condition = data.get("condition") or "--"
        temperature = data.get("temperature") or "--℃"
        humidity = data.get("humidity") or "--"
        wind = data.get("wind") or "--"

        self.icon.set_from_weather(condition, data.get("weather_code"))
        self.lbl_city.setText(f"城市　{city}")
        self.lbl_condition.setText(condition)
        self.lbl_temp.setText(temperature)
        self.lbl_detail.setText(f"风力 {wind}\n湿度 {humidity}")
        self.lbl_status.setText("天气已更新")
        if self.edit_city is not None and self._session_city:
            self.edit_city.setText(self._session_city)

    def _on_failed(self, message):
        """失败丢弃本次请求，绝不覆盖已有正常数据。"""
        if self._shutting_down:
            return
        if self._last_weather is None:
            if self._ui_active:
                self._apply_empty_state("暂无法获取天气")
                self.lbl_status.setText(f"网络异常：{message}")
            return
        if self._ui_active:
            self.lbl_status.setText(f"刷新失败：{message}（仍显示上次天气）")

    def _apply_empty_state(self, title):
        self.icon.set_kind("cloudy")
        self.lbl_city.setText(f"城市　{DEFAULT_CITY}（待确认）")
        self.lbl_condition.setText(title)
        self.lbl_temp.setText("--℃")
        self.lbl_detail.setText("风力 --\n湿度 --")

    def _on_thread_finished(self):
        sender = self.sender()
        if sender is self._worker:
            self._worker = None
        if self._shutting_down:
            return
        self._set_buttons_enabled(True)
        if self._refresh_pending:
            self._refresh_pending = False
            self.request_refresh(force=True)
