---
topic: flexmemoryLLM Architecture & System Strategy
date: 2026-02-26
tags: [MemoryLLM, flexmemoryLLM, FFN-Decoupling, ToLs, TKV, On-device-AI, Interpretability]
---

# flexmemoryLLM: 효율적이고 해석 가능한 거대 모델 아키텍처 및 시스템 전략

## 1. 배경 및 문제 정의
기존 트랜스포머 모델의 **FFN(Feed-Forward Network)**은 전체 파라미터의 대부분을 차지하며 사실적 지식을 저장하지만, 연산 과정이 **Attention 출력에 종속(Context-aware)**되어 있어 두 가지 근본적인 문제를 야기함:
1. **해석 불가능성:** 입력 패턴이 무한대에 가까워 FFN이 특정 정보를 인출하는 메커니즘을 분석하기 어려움.
2. **연산 비효율성:** 모든 레이어에서 고비용의 행렬 연산이 필요하여, 특히 온디바이스(On-device) 환경에서 메모리와 전력 소모가 극심함.

## 2. 핵심 아키텍처: Attention-FFN 분리 및 ToLs
이 문제를 해결하기 위해 FFN의 입력을 Attention 출력에서 분리하고 **Input Token으로 고정**하는 구조를 제안함.

### 2.1 Context-free Memory Path (FFN-M)
* **메커니즘:** FFN의 입력을 항상 원래의 입력 토큰($x_{input}$)으로 고정하여 문맥 독립적인 정보 인출을 수행.
* **ToLs (Token-wise Lookups):** 모든 토큰과 FFN 가중치 간의 연산 결과를 사전에 계산하여 **TKV (Token-Key-Value)** 프레임워크로 저장.
* **이점:** 추론 시 행렬 연산을 수행하지 않고 메모리에서 '데이터 읽기(Read)'만으로 FFN 연산을 대체 가능.

### 2.2 확률적 해석 가능성 (Probabilistic Interpretability)
* 문맥 정보가 배제된 입력 토큰에 의해 정보가 인출되므로, 특정 토큰이 입력되었을 때 모델이 제공하는 지식의 **확률 분포를 통계적으로 분석 및 제어**할 수 있음.

## 3. flexmemoryLLM: 하이브리드 성능 최적화
Context-free 구조의 정확도 저하 문제를 해결하기 위해 **Compute**와 **Memory** 경로를 이원화한 하이브리드 모델.

| 구성 요소 | FFN Compute (FFN-C) | FFN Memory (FFN-M) |
| :--- | :--- | :--- |
| **입력** | Attention 출력 (Context-aware) | Input Token (Context-free) |
| **연산** | 실시간 행렬 연산 (Compute) | ToLs 기반 데이터 조회 (Data Read) |
| **역할** | 논리 추론, 문맥 유지, 시퀀스 생성 | 사실적 지식 인출, 효율적 지식 저장 |

* **효과:** 순수 MemoryLLM 대비 정확도를 15~20% 개선하면서도, 지식 저장의 대부분을 데이터 읽기로 처리하여 효율성 극대화.

## 4. 시스템 오프로딩 및 하드웨어 매핑 전략
하드웨어 자원의 효율적 배분을 위한 계층적 오프로딩(Offloading) 설계.

### 4.1 레이어별 계층적 배치 (Layer-wise Heterogeneous Offloading)
1. **상위 레이어 (Input 근접):** **FFN-C** 위주로 구성. GPU/NPU 가속기를 통해 문맥 기반 추론 수행.
2. **하위 레이어 (Output 근접):** **FFN-M** 위주로 구성. 대용량 메모리/스토리지 카드(CXL/SSD)에 ToLs를 배치하여 연산을 데이터 읽기로 대치.

### 4.2 스토리지 계층화 및 Prefetching
* **Hot ToLs (DRAM):** 빈번하게 인출되는 토큰 정보를 시스템 메모리에 저장.
* **Cold ToLs (NAND/SSD):** 방대한 지식 베이스를 스토리지에 저장하되, 추론 초기 단계에서 **Prefetching**을 통해 후반부 레이어의 데이터 읽기 지연시간(Latency)을 은닉함.

## 5. 결론 및 향후 전망
flexmemoryLLM은 **"지능은 연산하고, 지식은 읽어온다"**는 원칙 아래, LLM을 해석 가능한 지식 엔진으로 변모시킴. 이는 특히 고가의 GPU 자원이 부족한 환경이나, 실시간 지식 업데이트가 필요한 전문 도메인 AI 구축에 핵심적인 역할을 할 것으로 기대됨.
