---
name: Obsidian PARA 폴더 재구조화
description: 2026-04-01 Obsidian vault를 PARA 구조에 맞게 재정리하고 knowledge_tutor 워크플로우 개선
type: project
---

PARA 구조(1-Projects / 2-Areas / 3-Resources / 4-Archieve)에 맞게 Obsidian vault를 재정리함.

**Why:** 지식 폴더가 Inbox에 무분별하게 쌓이고, 유사 주제 폴더가 멀리 흩어져 있었음.

**How to apply:** 이후 새 주제 저장 시 항상 PARA 경로를 확인하고 적절한 위치에 배치.

## 확정된 2-Areas/Hardware 구조
- Hardware/NPU/ ← Systolic_array 포함 (NPU 연산 아키텍처 관련)
- Hardware/Accelerator/ ← NVIDIA_GROQ_LPU, Chiplet (추론 전용 칩)
- Hardware/Storage/ ← Microchip_NVMe, MemQ, PolarStore

## Inbox → 2-Areas 이동 완료 항목
- Mamba_Architecture → LLM/Models
- llama4, FFN/MoE → LLM/Models
- mem0 → LLM/Memory
- MLIR x2, PyTorch_Codegen → Compiler (신규)
- Systolic_array → Hardware/NPU
- NVIDIA_GROQ, Chiplet → Hardware/Accelerator
- Microchip_NVMe → Hardware/Storage
- System/MemQ, PolarStore → Hardware/Storage

## knowledge_tutor 워크플로우 변경사항 (2026-04-01)
1. Step 0: Mem0 기억 있으면 목록 제시 후 "추가 웹 검색 필요?" 분기 추가
2. Step 1-1: CATEGORY 고정값 "Inbox" 제거 → PARA 트리 출력 후 자동 추천 + 사용자 확인
3. 전체 경로 패턴: SAFE_CATEGORY 제거, $OBSIDIAN_VAULT_PATH/{CATEGORY}/$SAFE_TOPIC 으로 통일
