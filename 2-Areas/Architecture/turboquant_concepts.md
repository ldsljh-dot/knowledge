# TurboQuant: KV Cache Compression for LLM Inference

> Google Research, 2025/2026
> 출처: [Google Research Blog](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/)

---

## 1. 배경: 왜 KV Cache 압축이 필요한가?

### KV Cache란?
- LLM이 autoregressive하게(토큰 하나씩) 텍스트를 생성할 때, 매 단계마다 이전 토큰들의 **Key(K)**와 **Value(V)** 벡터를 캐시에 저장
- 없으면 매 단계마다 모든 이전 토큰의 attention을 다시 계산해야 함 → 계산량이 시퀀스 길이에 대해 **O(n²)**으로 증가
- KV cache를 사용하면 매 단계에서 **새 토큰의 Query(Q)만 계산**하고, 나머지는 캐시에서 가져옴 → inference 속도 3~5배 향상

### 문제: 메모리 병목
- KV cache는 시퀀스 길이에 비례하여 선형적으로 증가 **O(n)**
- 긴 컨텍스트나 큰 모델에서는 cache가 VRAM을 빠르게 소모
- 메모리 부족 → batch size 축소, 메모리 스와핑, OOM 오류 발생
- **속도 이점을 메모리 제한이 상쇄**하는 상황

---

## 2. TurboQuant 개요

| 항목 | 내용 |
|------|------|
| **개발** | Google Research |
| **목적** | KV cache를 3비트/밸류까지 압축하여 메모리 사용량 6배 이상 감소 |
| **특징** | 정확도 손실 제로, fine-tuning 불필요, training-free |
| **핵심 기술** | PolarQuant + Quantized Johnson-Lindenstrauss (QJL) |
| **성과** | LongBench에서 full-precision과 동일 점수, Needle-in-a-Haystack 0.997 |
| **속도** | H100 GPU에서 attention logit 계산 최대 8배 가속 (4-bit vs 32-bit) |

---

## 3. 기존 양자화 기법과의 비교

### 3.1 Weight Quantization (GPTQ, AWQ)
| | GPTQ / AWQ | TurboQuant |
|--|-----------|------------|
| **대상** | 정적 모델 가중치 (오프라인 양자화) | 동적 KV 캐시 (런타임, 요청마다 다름) |
| **보정** | 오프라인 calibration pass, Hessian 계산 필요 | **Zero-calibration**, 완전 온라인 |
| **튜닝** | 모델별 튜닝 필요 | 모델/레이어/헤드 범용 |
| **적용 시점** | 배포 전 한 번 | autoregressive decoding 중 토큰마다 실시간 |

### 3.2 기존 KV Cache Quantization
| 기법 | 특징 | TurboQuant 대비 |
|------|------|----------------|
| **KIVI** | 학습 기반 codebook 사용 | TurboQuant: codebook 사전 계산, 학습 불필요 |
| **PyramidKV** | 계층별 다른 비트 할당 | TurboQuant: 균일 3비트, 이론적 왜곡 한계 근접 |
| **SnapKV** | 중요도 기반 토큰 선택적 보존 | TurboQuant: 모든 토큰 보존, 정보 손실 없음 |
| **RaBitQ / QuaRot** | 회전 기반 양자화 | TurboQuant: 회전 + 최적 Lloyd-Max codebook + formal distortion bound |

### 3.3 Needle-in-a-Haystack 비교 (4x 압축 시)
| 방법 | 점수 |
|------|------|
| **TurboQuant** | **0.997** |
| KIVI | 0.981 |
| PyramidKV | 0.895 |
| SnapKV | 0.858 |

---

## 4. 핵심 기술 1: PolarQuant

### 개념
- 직교 좌표계(Cartesian)의 벡터를 **극 좌표계(Polar: 반지름 + 각도)**로 변환하여 양자화

### 알고리즘
1. **Fast Walsh-Hadamard Transform (FWHT)**로 벡터를 무작위 회전
   - 회전 후 데이터 분포가 예측 가능해짐 (Beta 분포 수렴)
2. **좌표쌍을 극좌표로 변환**: 각 (x, y) 쌍을 (r, θ)로
   - **r (반지름)**: 크기(magnitude) 인코딩
   - **θ (각도)**: 방향(direction) 인코딩
3. **재귀적 적용**: 반지름들을 다시 쌍으로 묶어 극좌표 변환 반복
   - 최종적으로 **하나의 전체 반지름 + 각도 집합**으로 distill
4. **미리 계산된 Lloyd-Max codebook**으로 테이블 룩업 양자화

### 왜 효과적인가?
- 고차원 벡터를 무작위 회전하면 각도 분포가 **Beta 분포**로 수렴 (차원이 클수록 집중됨)
- 이 분포를 미리 알 수 있으므로 **오프라인으로 최적 quantizer 설계** 가능
- **런타임에 per-block 정규화(min/max 계산 등) 불필요** → 기존 quantization의 1~2비트 오버헤드 제거
- 정보 이론적 하한(information-theoretic limit)의 **~2.7배** 내 왜곡 달성

---

## 5. 핵심 기술 2: Quantized Johnson-Lindenstrauss (QJL)

### 개념
- Johnson-Lindenstrauss 보조정리: 고차원 데이터를 저차원으로 축소해도 거리 관계가 보존됨
- TurboQuant에서는 이를 **양자화 버전**으로 적용

### 동작 방식
1. **PolarQuant**로 핵심 벡터 정보를 압축
2. **잔여(residual) 1비트**를 할당하여 양자화 오류 보정
   - 각 값을 **+1 또는 -1**의 sign bit로만 표현
   - 메모리 오버헤드 **제로**
3. 특수 추정기(estimator)로 **고정밀 쿼리 + 저정밀 데이터** 밸런스 조절
4. attention score 계산 정확도 유지

---

## 6. TurboQuant 전체 파이프라인

```
입력 KV 벡터
    │
    ▼
┌─────────────────────┐
│ 1. FWHT 무작위 회전  │  ← 데이터 분포를 예측 가능하게
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ 2. PolarQuant       │  ← 극좌표 변환 + Lloyd-Max codebook 룩업
│    (주요 압축)       │    핵심 정보 캡처
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ 3. QJL              │  ← 1비트 residual로 오류 보정
│    (오류 수정)       │    attention score 정확도 보장
└────────┬────────────┘
         │
         ▼
    3비트 KV 캐시
```

### 주요 특성
- **Training-free**: 학습, calibration, fine-tuning 불필요
- **Data-oblivious**: 모델/레이어/헤드에 관계없이 동일 codebook 적용
- **Stateless**: 매 토큰 독립 처리, 상태 유지 안 함
- **Fully vectorized**: SIMD/GPU 가속 용이

---

## 7. 벤치마크 결과

### Long-Context LLM 평가
- **데이터셋**: LongBench, Needle In A Haystack, ZeroSCROLLS, RULER, L-Eval
- **모델**: Gemma, Mistral, Llama-3.1-8B-Instruct
- **결과**: 3비트에서 **정확도 손실 제로**

### Vector Search 평가
- **데이터셋**: GloVe (d=200)
- **지표**: 1@k recall
- **결과**: PQ, RabbiQ 등 기존 baseline 능가

### 하드웨어 성능 (H100 GPU)
- KV 메모리 풋프린트: **≥6배 감소**
- Attention logit 계산: **최대 8배 가속** (4-bit vs 32-bit)
- 런타임 오버헤드: **무시 가능 수준**

---

## 8. 용어 정리

| 용어 | 설명 |
|------|------|
| **KV Cache** | Attention의 Key/Value 벡터 저장소. autoregressive decoding에서 재계산 방지 |
| **Quantization** | 고정밀(float32/16) 값을 저비트 정수로 근사화하여 메모리 절약 |
| **PolarQuant** | 직교→극좌표 변환을 이용한 KV cache 양자화 기법 |
| **QJL** | Quantized Johnson-Lindenstrauss. 1비트 residual로 오류 보정 |
| **Lloyd-Max** | 왜곡을 최소화하는 최적 scalar quantizer 설계 알고리즘 |
| **FWHT** | Fast Walsh-Hadamard Transform. O(n log n) 무작위 회전 |
| **Distortion** | 양자화로 인한 벡터 정보 손실 정도 |
| **Beta 분포** | PolarQuant 회전 후 각도가 따르는 확률 분포 |

---

## 9. 참고 자료

- [Google Research: TurboQuant 공식 발표](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/)
- [PolarQuant: NeurIPS 2025 Poster](https://neurips.cc/virtual/2025/poster/118745)
- [The ML Surgeon: TurboQuant 분석](https://themlsurgeon.substack.com/p/turboquant-what-3-bit-kv-caches-actually)
