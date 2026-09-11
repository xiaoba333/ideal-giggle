# -*- coding: utf-8 -*-
"""
迷你天气：定时器全程 5 分钟轮询，网络在子线程；失败保留旧数据。
迷你窗仅居中展示：天气图标 + 温度。
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, QTimer, pyqtSignal, Qt
from PyQt6.QtWidgets import QLabel, QSizePolicy, QHBoxLayout

from ui.components.droplet_card import DropletCard
from ui.components.weather_icon import WeatherIconWidget
from utils.location_tool import locate_city_or_default, DEFAULT_CITY
from utils.weather_tool import get_weather_by_city, clear_weather_cache
from utils import weather_state

_AUTO_REFRESH_MS = 300_000
_THREAD_WAIT_MS = 8_000


class _MiniWeatherWorker(QThread):
    success = pyqtSignal(dict)
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, city=None, auto_locate=True, force_refresh=True, parent=None):
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
                if self._cancelled:
                    return
                city, _, _ = locate_city_or_default()
                if self._cancelled:
                    return
            if self._cancelled:
                return
            if self.force_refresh:
                clear_weather_cache(city)
            data = get_weather_by_city(city, use_cache=False)
            if self._cancelled:
                return
            if not isinstance(data, dict) or not data:
                raise RuntimeError("空数据")
            self.success.emit(data)
        except TimeoutError as e:
            if not self._cancelled:
                self.failed.emit(f"超时：{e}")
        except Exception as e:
            if not self._cancelled:
                self.failed.emit(str(e))


class MiniWeatherWidget(DropletCard):
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None, strip=False):
        super().__init__(parent, min_width=40, min_height=28 if strip else 40)
        self._strip = bool(strip)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setProperty("compact", True)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.content().setContentsMargins(0, 0, 0, 0)
        self.set_shadow_enabled(False)

        self._worker: _MiniWeatherWorker | None = None
        self._shutting_down = False
        self._ui_active = True
        self._session_city: str | None = None
        self._last_weather = None
        self._refresh_pending = False
        self._network_enabled = True

        self._build_ui()
        self._apply_empty()

        self._timer = QTimer(self)
        self._timer.setInterval(_AUTO_REFRESH_MS)
        self._timer.timeout.connect(self.refresh_requested.emit)
        self.refresh_requested.connect(self._on_refresh_requested)
        self._timer.start(_AUTO_REFRESH_MS)

    def _build_ui(self):
        lay = self.content()
        if self._strip:
            # 横条：缩小图标 + 温度，放在时间下方
            lay.setContentsMargins(4, 0, 4, 2)
            lay.setSpacing(0)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            row.addStretch(1)
            self.icon = WeatherIconWidget(size=26)
            self.icon.setToolTip("")
            row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)
            self.lbl_temp = QLabel()
            self.lbl_temp.setObjectName("weatherTemp")
            self.lbl_temp.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self.lbl_temp.setMinimumHeight(22)
            row.addWidget(self.lbl_temp, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addStretch(1)
            lay.addLayout(row)
            return

        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(2)
        lay.addStretch(1)

        icon_row = QHBoxLayout()
        icon_row.setContentsMargins(0, 0, 0, 0)
        icon_row.addStretch(1)
        self.icon = WeatherIconWidget(size=40)
        self.icon.setToolTip("")
        icon_row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignCenter)
        icon_row.addStretch(1)
        lay.addLayout(icon_row)

        self.lbl_temp = QLabel()
        self.lbl_temp.setObjectName("weatherTemp")
        self.lbl_temp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_temp.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self.lbl_temp.setMinimumHeight(28)
        lay.addWidget(self.lbl_temp)

        lay.addStretch(1)

    def shutdown(self):
        self._shutting_down = True
        self._ui_active = False
        self._network_enabled = False
        if self._timer.isActive():
            self._timer.stop()
        worker = self._worker
        if worker is not None:
            worker.cancel()
            if worker.isRunning():
                worker.wait(_THREAD_WAIT_MS)
            self._worker = None

    def stop_network(self):
        self.pause_ui()

    def start_network(self, reload=True):
        self.resume_ui(reload=reload)

    def pause_ui(self):
        self._ui_active = False
        self._network_enabled = False

    def resume_ui(self, reload=False):
        self._ui_active = True
        self._network_enabled = True
        self._shutting_down = False
        if not self._timer.isActive():
            self._timer.start(_AUTO_REFRESH_MS)
        # 先套用大屏共享快照，保证图标立刻一致
        shared = weather_state.get_last_weather()
        if shared:
            self._last_weather = shared
            q = (shared.get("query_city") or "").strip()
            if q:
                self._session_city = q
            if self._ui_active:
                self._apply(shared)
        if reload:
            self.refresh()
        elif self._last_weather:
            self._apply(self._last_weather)

    def seed_from(self, data: dict | None, city: str | None = None):
        """切迷你前由主窗灌入大屏天气，避免重新定位拿到不同城市。"""
        if isinstance(data, dict) and data:
            self._last_weather = dict(data)
            weather_state.set_last_weather(data)
            if self._ui_active:
                self._apply(self._last_weather)
        city = (city or "").strip() or None
        if city:
            self._session_city = city
            weather_state.set_preferred_city(city)
        elif weather_state.get_preferred_city():
            self._session_city = weather_state.get_preferred_city()

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    def _on_refresh_requested(self):
        if self._shutting_down:
            return
        self.refresh()

    def refresh(self):
        if self._shutting_down:
            return
        # 优先沿用大屏/共享城市，不再每次强制清空后重新 IP 定位
        city = self._session_city or weather_state.get_preferred_city()
        if city:
            self._session_city = city
            self._start_worker(city=city, auto_locate=False, force_refresh=True)
        else:
            self._start_worker(auto_locate=True, force_refresh=True)

    def set_temp_city(self, city: str):
        city = (city or "").strip()
        if not city:
            self.clear_temp_city()
            return
        self._session_city = city
        weather_state.set_preferred_city(city)
        self._start_worker(city=city, auto_locate=False, force_refresh=True)

    def clear_temp_city(self):
        self._session_city = None
        weather_state.clear_preferred_city()
        self._start_worker(auto_locate=True, force_refresh=True)

    def temp_city(self) -> str | None:
        return self._session_city

    def _start_worker(self, city=None, auto_locate=True, force_refresh=True):
        if self._shutting_down:
            return
        if self._worker is not None and self._worker.isRunning():
            self._refresh_pending = True
            return
        self._worker = _MiniWeatherWorker(
            city=city,
            auto_locate=auto_locate,
            force_refresh=force_refresh,
            parent=self,
        )
        self._worker.success.connect(self._on_success)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_thread_finished)
        self._worker.start()

    def _on_success(self, data: dict):
        if self._shutting_down or not isinstance(data, dict):
            return
        new = dict(data)
        changed = (
            self._last_weather is None
            or self._fingerprint(self._last_weather) != self._fingerprint(new)
        )
        self._last_weather = new
        weather_state.set_last_weather(new)
        if self._ui_active and changed:
            self._apply(self._last_weather)

    @staticmethod
    def _fingerprint(data: dict):
        return (
            data.get("condition"),
            data.get("temperature"),
            data.get("weather_code"),
        )

    def _apply(self, data: dict):
        condition = data.get("condition") or ""
        temperature = data.get("temperature") or "--℃"
        self.icon.set_from_weather(condition, data.get("weather_code"))
        tip = condition.strip() or "天气"
        self.icon.setToolTip(tip)
        self.lbl_temp.setToolTip(tip)
        self.lbl_temp.setText(temperature)

    def _on_failed(self, message: str):
        if self._shutting_down:
            return
        if self._last_weather is None:
            if self._ui_active:
                self._apply_empty()
            return

    def _apply_empty(self, title: str = ""):
        self.icon.set_kind("cloudy")
        self.icon.setToolTip(title or "天气加载中")
        self.lbl_temp.setText("--℃")
        self.lbl_temp.setToolTip("")

    def _on_thread_finished(self):
        sender = self.sender()
        if sender is self._worker:
            self._worker = None
        if self._shutting_down:
            return
        if self._refresh_pending:
            self._refresh_pending = False
            self.refresh()
