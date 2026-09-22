"""Tkinter GUI: draw a Hangul character with the mouse and recognize it."""

import os
import time
import tkinter as tk
from tkinter import font as tkfont

import numpy as np
from PIL import Image, ImageDraw

from .predict import HangulRecognizer

CANVAS_SIZE = 400
PEN_WIDTH = 16

# 디버깅용: Predict를 누를 때마다 원본/전처리 이미지를 저장할 폴더
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts", "debug")


class HangulDrawingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Hangul Handwriting Recognition")

        self.recognizer = HangulRecognizer()

        # 캔버스와 동일한 내용을 유지하는 PIL 이미지 (추론 입력용)
        self.image = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "white")
        self.draw = ImageDraw.Draw(self.image)

        self._build_widgets()

        self.last_x, self.last_y = None, None

    def _build_widgets(self):
        container = tk.Frame(self.root)
        container.pack(padx=12, pady=12)

        self.canvas = tk.Canvas(container, width=CANVAS_SIZE, height=CANVAS_SIZE,
                                 bg="white", cursor="pencil", highlightthickness=1,
                                 highlightbackground="gray")
        self.canvas.grid(row=0, column=0, rowspan=4)
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        side_panel = tk.Frame(container)
        side_panel.grid(row=0, column=1, sticky="n", padx=(16, 0))

        button_row = tk.Frame(side_panel)
        button_row.pack(fill="x")
        tk.Button(button_row, text="Predict", command=self.on_predict).pack(side="left", padx=4)
        tk.Button(button_row, text="Clear", command=self.on_clear).pack(side="left", padx=4)

        big_font = tkfont.Font(family="Malgun Gothic", size=48)
        self.result_label = tk.Label(side_panel, text="?", font=big_font, width=3)
        self.result_label.pack(pady=(16, 8))

        self.candidates_label = tk.Label(side_panel, text="", font=("Malgun Gothic", 12),
                                          justify="left", anchor="w")
        self.candidates_label.pack(fill="x")

    def _on_press(self, event):
        self.last_x, self.last_y = event.x, event.y

    def _on_drag(self, event):
        if self.last_x is not None:
            self.canvas.create_line(self.last_x, self.last_y, event.x, event.y,
                                     width=PEN_WIDTH, fill="black",
                                     capstyle=tk.ROUND, smooth=True)
            self.draw.line([self.last_x, self.last_y, event.x, event.y],
                            fill="black", width=PEN_WIDTH, joint="curve")
        self.last_x, self.last_y = event.x, event.y

    def _on_release(self, _event):
        self.last_x, self.last_y = None, None

    def on_clear(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.result_label.config(text="?")
        self.candidates_label.config(text="")

    def on_predict(self):
        results = self.recognizer.predict_topk(self.image, k=5)
        top_char, top_prob = results[0]
        self.result_label.config(text=top_char)

        lines = [f"{i + 1}. {c}  ({p * 100:.1f}%)" for i, (c, p) in enumerate(results)]
        self.candidates_label.config(text="\n".join(lines))

        self._save_debug_snapshot()

    def _save_debug_snapshot(self):
        """원본 캔버스와 모델이 실제로 보는 전처리 이미지를 파일로 남긴다."""
        os.makedirs(DEBUG_DIR, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")

        self.image.save(os.path.join(DEBUG_DIR, f"{stamp}_raw.png"))

        tensor = self.recognizer.preprocess(self.image)
        arr = tensor.squeeze().cpu().numpy()
        arr = ((1.0 - arr) * 255).astype(np.uint8)  # 학습 표현을 다시 흰 배경/검은 잉크로 되돌림
        Image.fromarray(arr).resize((256, 256), Image.NEAREST).save(
            os.path.join(DEBUG_DIR, f"{stamp}_model_input.png")
        )


def main():
    root = tk.Tk()
    HangulDrawingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
