"""Tkinter GUI: draw a digit with the mouse and recognize it with the trained CNN."""

import tkinter as tk

import torch
from PIL import Image, ImageDraw

from model import DigitCNN

MODEL_PATH = "./mnist_cnn.pt"
CANVAS_SIZE = 280  # displayed canvas size (10x the MNIST 28x28 size)
BRUSH_RADIUS = 10


class DigitRecognizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Handwritten Digit Recognizer")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DigitCNN().to(self.device)
        self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
        self.model.eval()

        # Canvas the user draws on
        self.canvas = tk.Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="black", cursor="cross")
        self.canvas.grid(row=0, column=0, columnspan=3, padx=10, pady=10)

        # In-memory image that mirrors the canvas, used for model input
        self.image = Image.new("L", (CANVAS_SIZE, CANVAS_SIZE), color=0)
        self.draw = ImageDraw.Draw(self.image)

        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<ButtonRelease-1>", lambda event: self.predict())

        self.result_label = tk.Label(root, text="Draw a digit (0-9)", font=("Arial", 20))
        self.result_label.grid(row=1, column=0, columnspan=3, pady=5)

        clear_button = tk.Button(root, text="Clear", command=self.clear_canvas)
        clear_button.grid(row=2, column=1, pady=10)

    def paint(self, event):
        x, y = event.x, event.y
        r = BRUSH_RADIUS
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="white", outline="white")
        self.draw.ellipse([x - r, y - r, x + r, y + r], fill=255)

    def clear_canvas(self):
        self.canvas.delete("all")
        self.image = Image.new("L", (CANVAS_SIZE, CANVAS_SIZE), color=0)
        self.draw = ImageDraw.Draw(self.image)
        self.result_label.config(text="Draw a digit (0-9)")

    def preprocess(self):
        # Downscale to MNIST's native 28x28 resolution
        small_image = self.image.resize((28, 28), Image.LANCZOS)
        tensor = torch.tensor(list(small_image.getdata()), dtype=torch.float32)
        tensor = tensor.view(1, 1, 28, 28) / 255.0
        # Match MNIST normalization used during training
        tensor = (tensor - 0.1307) / 0.3081
        return tensor.to(self.device)

    def predict(self):
        if not self.image.getbbox():
            return  # canvas is empty, nothing to predict
        tensor = self.preprocess()
        with torch.no_grad():
            output = self.model(tensor)
            probs = torch.softmax(output, dim=1)[0]
            predicted = int(probs.argmax().item())
            confidence = float(probs[predicted].item())
        self.result_label.config(text=f"Prediction: {predicted}  ({confidence * 100:.1f}%)")


def main():
    root = tk.Tk()
    DigitRecognizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
