# Hydraulic System Multi-Fault Diagnosis (UCI Dataset)

## Research Objective

UCI Hydraulic Systems 데이터셋의 17개 센서 신호로부터 4개 컴포넌트(cooler, valve, pump, accumulator)의
복합 결함을 **동시에** 진단하는 PHM(Prognostics & Health Management) 모델 개발.

## UCI Hydraulic Systems Dataset

| 항목 | 내용 |
|------|------|
| 출처 | [UCI ML Repository #447](https://archive.ics.uci.edu/dataset/447) |
| 사이클 수 | 2,205 |
| 센서 수 | 17 (물리 14 + 가상 3) |
| 샘플링 | 100Hz (PS1-6, EPS1), 10Hz (FS1-2), 1Hz (TS1-4, VS1, CE, CP, SE) |
| 사이클 길이 | 60초 |
| 타깃 | cooler (3 class), valve (4), pump (3), accumulator (4), stable (2) |

### Sensor Summary

| Sensor | Physical Quantity | Unit | Hz | Columns |
|--------|-------------------|------|----|---------|
| PS1-PS6 | Pressure | bar | 100 | 6000 |
| EPS1 | Motor power | W | 100 | 6000 |
| FS1, FS2 | Volume flow | l/min | 10 | 600 |
| TS1-TS4 | Temperature | C | 1 | 60 |
| VS1 | Vibration | mm/s | 1 | 60 |
| CE | Cooling efficiency | % | 1 | 60 |
| CP | Cooling power | kW | 1 | 60 |
| SE | Efficiency factor | % | 1 | 60 |

## Research Hypotheses

| ID | Hypothesis | Key Idea |
|----|-----------|----------|
| H1 | 압력센서 쌍 cross-correlation | PS1-PS6 간 상호상관이 단일센서 특징보다 복합결함 커플링을 더 잘 포착 |
| H2 | Multi-rate sensor fusion | 1/10/100Hz 신호를 학습된 보간으로 정렬하면 naive upsampling보다 우수 |
| H3 | MFPCA + Transformer | Multivariate Functional PCA가 수작업 특징이 놓치는 시간적 형상 보존 |
| H4 | Multi-task learning | 공유 backbone + 결함별 head가 라벨 상관을 활용하여 독립 분류보다 우수 |
| H5 | Multi-variable attention | Transformer attention이 CNN/LSTM이 놓치는 장거리 의존성 포착 |

## 4-Week Schedule

| Week | Period | Goal | Deliverables |
|------|--------|------|-------------|
| 1 | 5/12-5/16 | EDA + LDA baseline | 01_eda.ipynb, week1_meeting_brief.md |
| 2 | 5/18-5/22 | ML baseline 재현 | 02_baseline_lda.ipynb, 03_baseline_ml.ipynb |
| 3 | 5/25-5/29 | DL SOTA 재현 | 04_pytorch_baseline.ipynb, 05_multitask.ipynb |
| 4 | 6/1-6/5 | 본인 가설 검증 | 07_my_model.ipynb, final_report |

## Quick Start

```bash
# 1. conda 환경 생성 (최초 1회)
conda create -n hydraulic python=3.11 numpy pandas scipy scikit-learn matplotlib seaborn pywavelets jupyter nbconvert ipykernel xgboost -y
conda activate hydraulic
pip install scikit-fda umap-learn
pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m ipykernel install --user --name hydraulic --display-name "Python (hydraulic)"

# 2. 데이터 다운로드
python scripts/download_data.py

# 3. EDA 노트북 실행
jupyter notebook notebooks/01_eda.ipynb
```

## Project Structure

```
hydraulic_phm/
├── README.md
├── requirements.txt
├── .gitignore
├── scripts/
│   └── download_data.py
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── features.py
│   └── visualization.py
├── notebooks/
│   └── 01_eda.ipynb
├── reports/
│   └── week1_meeting_brief.md
└── data/
    └── uci/            (gitignored, auto-downloaded)
```
