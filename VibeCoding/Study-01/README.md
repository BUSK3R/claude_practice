# Study-01: 손글씨 숫자 인식 (MNIST)

PyTorch로 MNIST 데이터셋을 학습시킨 CNN 모델로, Tkinter GUI에서 마우스로 직접 숫자를 그리면 실시간으로 인식하는 프로젝트입니다.

## 구성

- `model.py` — `DigitCNN` 모델 정의 (28x28x1 입력 → conv/pool 2회 → 7x7x64 → fc → 10개 클래스 출력). 학습과 추론 모두 이 파일의 모델을 그대로 가져다 씁니다.
- `train.py` — MNIST 데이터로 학습/평가를 수행하고, 가중치를 `mnist_cnn.pt`로 저장합니다. CUDA 사용 가능 시 자동으로 GPU를 사용합니다.
- `draw_and_predict.py` — Tkinter 캔버스에 숫자를 그리면, 마우스를 뗄 때 28x28로 축소 후 학습 때와 동일한 정규화(mean 0.1307, std 0.3081)를 적용해 `mnist_cnn.pt`로 예측합니다.

## 실행 방법

모든 명령은 `handwriting_digit_recognition/` 폴더 안에서 실행합니다.

```bash
python train.py              # DigitCNN을 MNIST로 학습시키고 mnist_cnn.pt에 가중치 저장
python draw_and_predict.py   # Tkinter GUI 실행, 숫자를 그리고 마우스를 떼면 예측 결과 표시
```

`train.py`를 처음 실행하면 `./data` 폴더에 MNIST 데이터셋이 자동으로 다운로드됩니다.

## 의존성

`torch`, `torchvision`, `Pillow`(PIL), `tkinter`(표준 라이브러리, Tk 지원이 포함된 Python 필요). 별도의 테스트 코드나 requirements 파일은 없습니다.

## 주의사항

- `model.py`에서 `DigitCNN`의 구조를 바꾸면 기존 `mnist_cnn.pt`와 맞지 않게 되므로, `train.py`를 다시 실행해 가중치를 새로 생성해야 합니다. 그렇지 않으면 `draw_and_predict.py`에서 `load_state_dict` 시 shape mismatch 오류가 발생합니다.
- `draw_and_predict.py`의 전처리 로직과 `train.py`의 `transforms.Normalize` 값(mean/std)은 서로 동기화되어 있어야 합니다. 현재는 두 파일에 동일한 값이 각각 하드코딩되어 있습니다.
