"""Trains the HangulCNN on synthetically generated, augmented font images."""

import json
import os
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from .charset import CHARSET
from .dataset import HangulSyntheticDataset
from .model import HangulCNN

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "artifacts")
MODEL_PATH = os.path.join(MODEL_DIR, "hangul_cnn.pt")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")


def evaluate(model, loader, device):
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            preds = model(images).argmax(dim=1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / total


def train(epochs: int = 28, samples_per_class: int = 24, batch_size: int = 128, lr: float = 1e-3):
    os.makedirs(MODEL_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device: {device}, num_classes: {len(CHARSET)}")

    train_ds = HangulSyntheticDataset(samples_per_class=samples_per_class, train=True)
    val_ds = HangulSyntheticDataset(samples_per_class=4, train=False)

    # 이미지 생성이 CPU 연산 위주이므로 여러 워커 프로세스로 병렬화한다
    # (반드시 `if __name__ == "__main__"` 가드 안에서 실행되어야 Windows에서 안전함)
    num_workers = min(12, os.cpu_count() or 0)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, persistent_workers=num_workers > 0,
    )
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = HangulCNN(num_classes=len(CHARSET)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_acc = 0.0
    for epoch in range(1, epochs + 1):
        start = time.time()
        model.train()
        running_loss = 0.0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)
        scheduler.step()

        train_loss = running_loss / len(train_ds)
        val_acc = evaluate(model, val_loader, device)
        elapsed = time.time() - start
        print(f"[epoch {epoch:02d}/{epochs}] loss={train_loss:.4f} val_acc={val_acc:.4f} ({elapsed:.1f}s)")

        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)

    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(CHARSET, f, ensure_ascii=False)

    print(f"[train] best val_acc={best_acc:.4f}, model saved to {MODEL_PATH}")


if __name__ == "__main__":
    train()
