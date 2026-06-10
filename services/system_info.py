from __future__ import annotations

import ctypes
import platform
import time
from dataclasses import dataclass


try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None


@dataclass
class SystemSnapshot:
    cpu_percent: float | None
    cpu_temp_c: float | None
    ram_percent: float | None
    ram_used_gb: float | None
    ram_total_gb: float | None
    cpu_name: str
    platform_name: str


class SystemInfoSampler:
    def __init__(self) -> None:
        self._prev_idle = None
        self._prev_kernel = None
        self._prev_user = None
        self._last_sample_time = 0.0

    def snapshot(self) -> SystemSnapshot:
        cpu_percent = self._cpu_percent()
        ram_percent, used_gb, total_gb = self._memory_percent()
        cpu_temp = self._cpu_temp()

        return SystemSnapshot(
            cpu_percent=cpu_percent,
            cpu_temp_c=cpu_temp,
            ram_percent=ram_percent,
            ram_used_gb=used_gb,
            ram_total_gb=total_gb,
            cpu_name=platform.processor() or platform.machine(),
            platform_name=platform.platform(),
        )

    def _cpu_percent(self) -> float | None:
        if psutil is not None:
            try:
                return float(psutil.cpu_percent(interval=None))
            except Exception:
                pass

        idle, kernel, user = self._win_cpu_times()
        if idle is None:
            return None

        if self._prev_idle is None:
            self._prev_idle, self._prev_kernel, self._prev_user = idle, kernel, user
            return None

        idle_delta = idle - self._prev_idle
        kernel_delta = kernel - self._prev_kernel
        user_delta = user - self._prev_user
        system_delta = kernel_delta + user_delta
        self._prev_idle, self._prev_kernel, self._prev_user = idle, kernel, user

        if system_delta <= 0:
            return 0.0

        busy = system_delta - idle_delta
        return max(0.0, min(100.0, busy * 100.0 / system_delta))

    def _win_cpu_times(self):
        class FILETIME(ctypes.Structure):
            _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]

        idle_time = FILETIME()
        kernel_time = FILETIME()
        user_time = FILETIME()
        success = ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle_time), ctypes.byref(kernel_time), ctypes.byref(user_time)
        )
        if not success:
            return None, None, None

        def to_int(ft):
            return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

        return to_int(idle_time), to_int(kernel_time), to_int(user_time)

    def _memory_percent(self) -> tuple[float | None, float | None, float | None]:
        if psutil is not None:
            try:
                vm = psutil.virtual_memory()
                return float(vm.percent), round(vm.used / (1024**3), 2), round(vm.total / (1024**3), 2)
            except Exception:
                pass

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return None, None, None
        total = state.ullTotalPhys / (1024**3)
        used = (state.ullTotalPhys - state.ullAvailPhys) / (1024**3)
        return float(state.dwMemoryLoad), round(used, 2), round(total, 2)

    def _cpu_temp(self) -> float | None:
        if psutil is not None:
            try:
                temps = psutil.sensors_temperatures(fahrenheit=False)
                for entries in temps.values():
                    for entry in entries:
                        if entry.current is not None:
                            return float(entry.current)
            except Exception:
                pass
        return None


def format_system_snapshot(snapshot: SystemSnapshot) -> list[str]:
    cpu = f"CPU {snapshot.cpu_percent:.0f}%" if snapshot.cpu_percent is not None else "CPU --"
    ram = (
        f"RAM {snapshot.ram_percent:.0f}%"
        if snapshot.ram_percent is not None
        else "RAM --"
    )
    temp = f"{snapshot.cpu_temp_c:.0f}C" if snapshot.cpu_temp_c is not None else "--"
    memory = (
        f"{snapshot.ram_used_gb:.1f}/{snapshot.ram_total_gb:.1f} GB"
        if snapshot.ram_used_gb is not None and snapshot.ram_total_gb is not None
        else "--"
    )
    return [cpu, ram, f"Temp {temp}", f"Mem {memory}"]

