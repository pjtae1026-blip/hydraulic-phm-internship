# Week 1 Progress Report
**Hydraulic System Multi-Fault Diagnosis**
2026-05-16 | 박정태 | 학자연 교수님 랩

---

## 1. 주제 변경 제안

**기존**: CWRU 베어링 결함 진단
**변경**: UCI Hydraulic Systems 다중-결함 동시진단

**변경 근거**:
- CWRU 베어링 데이터셋은 data leakage 비판이 정식 논문화될 정도로 포화 상태
- UCI Hydraulic은 17개 센서, 4개 컴포넌트 동시진단이라는 차별점 존재
- 복합결함(multi-fault) 동시진단 연구는 아직 gap이 큼

## 2. 문헌 조사

13편 핵심 논문을 5개 축(Axis)으로 정리 완료 (별첨: ReadingList.docx)
- Axis 1: 원전 (Helwig 2015, LDA baseline)
- Axis 2: DL baseline (LSTM-AE, MS-CNN, TSO-CNN-BiLSTM)
- Axis 3: 복합결함 동시진단 (핵심 gap)
- Axis 4: 도메인 적응
- Axis 5: 최신 패러다임 (MFPCA, Transformer)

## 3. 예비 결과 — LDA 5-Fold CV Baseline

| Target | Classes | LDA Accuracy |
|--------|---------|-------------|
| Cooler | 3 (total failure / reduced / full) | **99.95%** (±0.09%) |
| Valve | 4 (optimal / small lag / severe lag / total failure) | **99.86%** (±0.18%) |
| Pump | 3 (no leakage / weak / severe) | **99.77%** (±0.14%) |
| Accumulator | 4 (optimal / slightly reduced / severely reduced / total failure) | **98.19%** (±0.20%) |

> 17개 센서 × 11개 시간도메인 특성 = 187 features, StandardScaler + LDA, 5-fold Stratified CV

## 4. 연구 가설 (H1-H5)

1. **H1**: 압력센서 쌍(PS1-PS6) cross-correlation이 복합결함 커플링을 포착
2. **H2**: Multi-rate 센서 융합 (학습된 보간 > naive upsampling)
3. **H3**: MFPCA가 시간적 형상 정보를 보존하여 결함 분리도 향상
4. **H4**: Multi-task learning (공유 backbone + 결함별 head)
5. **H5**: Transformer attention이 장거리 시간 의존성 포착

**제안**: H1 → H3 점진 확장

## 5. Week 2 계획

- Helwig 2015 LDA 정밀 재현 (target: cooler 99%, valve 98%, pump 95%, accu 98%)
- RF, XGBoost, LightGBM, Extra Trees 비교
- `02_baseline_lda.ipynb`, `03_baseline_ml.ipynb` 작성

## 6. 교수님께 확인 사항

1. 베어링 → UCI Hydraulic 주제 변경 승인
2. 가설 H1~H5 중 연구실 방향에 맞는 것은?
3. Python 100% 진행 — MATLAB이 필요한 부분이 있는지?
4. 최종 산출물 형태: 논문 초고 / 학회 포스터 / 발표자료 중 목표는?
