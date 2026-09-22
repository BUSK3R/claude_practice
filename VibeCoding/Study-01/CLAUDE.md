# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`handwriting_digit_recognition/` — a small PyTorch project that trains a CNN on MNIST and lets a user draw a digit in a Tkinter GUI to have it recognized.

## Commands

Run all commands from `handwriting_digit_recognition/`.

```
python train.py              # trains DigitCNN on MNIST, saves weights to mnist_cnn.pt
python draw_and_predict.py   # launches Tkinter GUI; draw a digit, prediction shown on release
```

There is no test suite, linter, or requirements file in this repo. Dependencies used across the code: `torch`, `torchvision`, `Pillow` (PIL), and Tkinter (stdlib, needs a system Python with Tk support).

`train.py` downloads MNIST into `./data` on first run via `torchvision.datasets.MNIST(download=True)` if it isn't already present.

## Architecture

Three files form the whole pipeline, and each depends on the previous:

- `model.py` — defines `DigitCNN`, a small 2-conv-layer CNN (28x28x1 -> conv/pool x2 -> 7x7x64 -> fc -> 10 classes). This is the single source of truth for model architecture; both training and inference import it.
- `train.py` — standard train/eval loop over MNIST, saves weights via `torch.save(model.state_dict(), ...)` to `mnist_cnn.pt` at the repo root. Auto-selects CUDA if available.
- `draw_and_predict.py` — Tkinter app with a canvas the user draws on with the mouse. Maintains a parallel in-memory PIL `Image` (`L` mode, black background) alongside the visible canvas so it can preprocess for the model without reading back canvas pixels. On mouse release, it downscales the 280x280 canvas image to 28x28, applies the same MNIST normalization used in training (mean 0.1307, std 0.3081), and runs it through `DigitCNN` loaded from `mnist_cnn.pt`.

Key invariant: any change to `DigitCNN`'s architecture in `model.py` invalidates `mnist_cnn.pt` — `train.py` must be rerun to regenerate weights matching the new architecture before `draw_and_predict.py` will load correctly (`load_state_dict` will fail on shape mismatch).

The preprocessing in `draw_and_predict.py::preprocess()` must stay in sync with the `transforms.Normalize` values in `train.py` — both hardcode the same MNIST mean/std rather than sharing a constant.
