"""Loads the trained model and runs inference on a hand-drawn image."""

import json
import os

import numpy as np
import torch
from PIL import Image

from .model import HangulCNN

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "hangul_cnn.pt")
LABELS_PATH = os.path.join(ARTIFACT_DIR, "labels.json")

MODEL_SIZE = 64


class HangulRecognizer:
    def __init__(self, model_path: str = MODEL_PATH, labels_path: str = LABELS_PATH):
        with open(labels_path, "r", encoding="utf-8") as f:
            self.labels = json.load(f)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = HangulCNN(num_classes=len(self.labels)).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

    def preprocess(self, pil_image: Image.Image) -> torch.Tensor:
        """캔버스에 그려진 이미지(흰 배경 + 검은 잉크)를 모델 입력 형태로 변환한다."""
        gray = pil_image.convert("L")
        arr = np.asarray(gray, dtype=np.float32)

        # 잉크(어두운 픽셀)가 있는 영역만 잘라내어 여백을 없앤다
        ink_mask = arr < 250
        if not ink_mask.any():
            # 아무것도 그려지지 않은 경우 빈 이미지를 그대로 사용
            cropped = arr
        else:
            rows = np.any(ink_mask, axis=1)
            cols = np.any(ink_mask, axis=0)
            top, bottom = np.where(rows)[0][[0, -1]]
            left, right = np.where(cols)[0][[0, -1]]
            cropped = arr[top:bottom + 1, left:right + 1]

        # 정사각형이 되도록 흰색으로 패딩한 뒤 여백을 살짝 추가
        h, w = cropped.shape
        side = max(h, w)
        pad = side // 5
        square = np.full((side + 2 * pad, side + 2 * pad), 255.0, dtype=np.float32)
        y_off = pad + (side - h) // 2
        x_off = pad + (side - w) // 2
        square[y_off:y_off + h, x_off:x_off + w] = cropped

        resized = Image.fromarray(square.astype(np.uint8)).resize((MODEL_SIZE, MODEL_SIZE), Image.LANCZOS)
        norm = np.asarray(resized, dtype=np.float32) / 255.0
        norm = 1.0 - norm  # 학습 때와 동일하게 배경 0, 잉크 1
        tensor = torch.from_numpy(norm).unsqueeze(0).unsqueeze(0)  # (1, 1, H, W)
        return tensor.to(self.device)

    def predict_topk(self, pil_image: Image.Image, k: int = 5):
        tensor = self.preprocess(pil_image)
        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0)
        top_probs, top_idx = torch.topk(probs, k)
        return [(self.labels[i], top_probs[j].item()) for j, i in enumerate(top_idx.tolist())]
