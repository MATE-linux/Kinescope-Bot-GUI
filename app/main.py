
import customtkinter as ctk
import os

from KinescopeGUI import KinescopeGUI

"""
KINESCOPE BOT GUI v1.0 – Графический интерфейс на CustomTkinter
================================================================
Основан на BotV5_3_1.py. Поддерживает все три режима работы:
1. Массовая рассылка (кассета)
2. Интерактивный режим с умным переиспользованием ботов
3. Обратный отсчёт с азаточасами
"""

if __name__ == "__main__":
    os.environ["CUSTOMTKINTER_FONT_SHAPES"] = "circle_shapes"
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = KinescopeGUI()
    app.mainloop()