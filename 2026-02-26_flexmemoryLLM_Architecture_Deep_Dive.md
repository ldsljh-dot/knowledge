---
created: 2026-02-26 09:11
updated: 2026-02-26 09:11
tags: [AI_Study, AI_Study]
category: AI_Study
status: 🌳 tree
sources:
  - "[[MemoryLLM_Plug_n_Play_FFN_decoupling]]"
  - "[[MeKi_Efficient_LLM_Scaling]]"
---

# 📚 flexmemoryLLM_Architecture_Deep_Dive

## 📖 원본 자료
- [[MemoryLLM_Plug_n_Play_FFN_decoupling]] - MemoryLLM_Plug_n_Play_FFN_decoupling
- [[MeKi_Efficient_LLM_Scaling]] - MeKi_Efficient_LLM_Scaling

## 📚 flexmemoryLLM_Architecture_Deep_Dive\n\n### 📖 원본 자료 및 RAG 분석 결과\n- **주요 논문:** MemoryLLM, Plug-n-Play Feed-Forward Memory, MeKi (Memory-based Expert Knowledge Injection)\n- **핵심 수식:** ^{l}_{t} = \alpha^{l} \cdot \text{RMSNorm}(m^{l}_{static}(x_{t}) + \beta^{l} \cdot m^{l}_{dyn}(x_{t}))$\n- **성능 지표:** 활성 파라미터 약 5배 절감 효과 확인.\n\n### 💬 학습 및 분석 기록\n1. **FFN-M (Memory Path):** Attention 출력을 배제하고 오직 Input Token에 의존하는 Context-free 구조. 이를 통해 FFN 연산을 TKV(Token-Key-Value) Lookup으로 대체하여 메모리/스토리지 오프로딩 가능.\n2. **FFN-C (Compute Path):** 문맥 의존적인(Context-aware) 추론을 담당하여 성능 하락을 방어.\n3. **확률적 해석 가능성:** Input Token 고정에 의해 인출되는 지식의 확률 분포를 분석 가능하게 함.\n4. **시스템 전략:** 레이어 위치에 따라 FFN-C는 GPU/NPU로, FFN-M은 CXL 메모리나 스마트 스토리지로 계층적 오프로딩.\n\n### 🎯 핵심 요약\n- **지능은 연산하고 지식은 읽어온다:** LLM을 고정된 지식 DB와 유연한 추론 엔진으로 분리.\n- **효율성:** 파라미터 비중이 큰 FFN을 데이터화하여 VRAM 요구량 획기적 절감.\n- **해석 가능성:** 블랙박스였던 FFN 내부를 토큰 단위로 투명하게 관리 가능.\n\n### 🔗 관련 개념\n- ToLs (Token-wise Lookups)\n- Context-free TKV Framework\n- Hierarchical Offloading Strategy

## 🎯 핵심 요약
- FFN 입력을 Input Token으로 고정하여 해석 가능성 및 효율성 확보\n- FFN-C(Compute)와 FFN-M(Memory)의 하이브리드 구조로 성능 저하 방지\n- 활성 파라미터 5배 절감 및 계층적 오프로딩 전략 제시\n- 레이어별 결합 계수(alpha, beta)를 통한 지식 주입 최적화

## 🔗 관련 개념
<!-- 나중에 채워주세요 -->

## 📝 추가 노트
<!-- 나중에 채워주세요 -->
