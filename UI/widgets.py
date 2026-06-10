from __future__ import annotations

import math
import tkinter as tk
from datetime import datetime

from UI.theme import THEME


class OrbWidget(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            highlightthickness=0,
            bg=THEME["bg"],
            bd=0,
            **kwargs,
        )
        self.state_color = THEME["idle"]
        self.phase = 0.0
        self.bind("<Configure>", lambda _: self.draw())

    def set_color(self, color: str) -> None:
        self.state_color = color

    def animate(self) -> None:
        self.phase += 0.08
        self.draw()

    def draw(self) -> None:
        self.delete("all")
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        size = min(width, height)
        cx = width / 2
        cy = height / 2
        base = size * 0.24

        glow_steps = [
            (base * 2.1, 22),
            (base * 1.8, 16),
            (base * 1.5, 10),
        ]
        for radius, alpha in glow_steps:
            color = self._blend(self.state_color, THEME["bg"], 1 - alpha / 24)
            self.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline=color,
                width=max(1, int(radius * 0.08)),
            )

        wobble = 1.0 + (0.03 * (1 + math.sin(self.phase * 1.7)))
        core_radius = base * 1.18 * wobble
        self.create_oval(
            cx - core_radius,
            cy - core_radius,
            cx + core_radius,
            cy + core_radius,
            fill=self._darken(self.state_color, 0.45),
            outline=self.state_color,
            width=max(2, int(size * 0.015)),
        )

        for index in range(10):
            angle = self.phase * 60 + index * 36
            offset = 1.0 + 0.22 * math.sin(self.phase * 4 + index)
            line_radius = core_radius * 1.25 * offset
            x1 = cx + line_radius * math.cos(math.radians(angle))
            y1 = cy + line_radius * math.sin(math.radians(angle))
            x2 = cx + (line_radius + 14) * math.cos(math.radians(angle))
            y2 = cy + (line_radius + 14) * math.sin(math.radians(angle))
            self.create_line(
                x1,
                y1,
                x2,
                y2,
                fill=self._blend(self.state_color, THEME["bg"], 0.35),
                width=2,
                smooth=True,
            )

    def _blend(self, fg: str, bg: str, ratio: float) -> str:
        fg_r, fg_g, fg_b = self.winfo_rgb(fg)
        bg_r, bg_g, bg_b = self.winfo_rgb(bg)
        r = int((fg_r * ratio + bg_r * (1 - ratio)) / 256)
        g = int((fg_g * ratio + bg_g * (1 - ratio)) / 256)
        b = int((fg_b * ratio + bg_b * (1 - ratio)) / 256)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _darken(self, color: str, factor: float) -> str:
        r, g, b = self.winfo_rgb(color)
        return f"#{int(r / 256 * factor):02x}{int(g / 256 * factor):02x}{int(b / 256 * factor):02x}"


class MetricBlock(tk.Frame):
    def __init__(self, master, title: str, value: str = "--", **kwargs):
        super().__init__(
            master,
            bg=THEME["panel"],
            highlightbackground=THEME["edge"],
            highlightthickness=1,
            **kwargs,
        )
        self.title_label = tk.Label(
            self,
            text=title,
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        self.value_label = tk.Label(
            self,
            text=value,
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 12, "bold"),
            anchor="w",
            justify="left",
            wraplength=160,
        )
        self.title_label.pack(anchor="w", padx=10, pady=(8, 0))
        self.value_label.pack(anchor="w", padx=10, pady=(2, 8))

    def set_value(self, value: str) -> None:
        self.value_label.config(text=value)


class StatusStrip(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            bg=THEME["panel_alt"],
            highlightbackground=THEME["edge"],
            highlightthickness=1,
            **kwargs,
        )
        self.label = tk.Label(
            self,
            text="Hazir",
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            font=("Segoe UI", 10),
            anchor="w",
        )
        self.label.pack(anchor="w", padx=12, pady=8)

    def set_text(self, text: str) -> None:
        self.label.config(text=text)


def current_time_text() -> str:
    return datetime.now().strftime("%H:%M:%S")

