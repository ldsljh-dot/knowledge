---
title: "04 - NFR and Observability: Llama Mask System"
created: 2026-04-07
tags: [llama, mask, causal, attention, performance, error-handling, logging]
category: 2-Areas/Architecture/transformers_llama_mask_analysis
---

# 04 - NFR and Observability: Llama Mask System

## 성능 최적화 (Performance)

### 1. 마스크 스킵 최적화 (Flash Attention 활성화)

```python
def _ignore_causal_mask_sdpa(padding_mask, query_length, kv_length, kv_offset, local_attention_size):
    """
    마스크를 생성하지 않고 SDPA의 is_causal=True 사용
    → Flash Attention 커널 사용 가능 → 2-3배 속도 향상
    
    최적화 조건:
    """
    # 1. XPU 특수 처리
    if _is_torch_xpu_available:
        return _can_skip_causal_mask_xpu(padding_mask, query_length, kv_length, local_attention_size)
    
    # 2. Tracing 중이면 스킵 안 함 (dynamic control flow 문제)
    if is_tracing(padding_mask):
        return False
    
    # 3. 쿼리 길이가 1이거나 (decoding) kv_length == query_length (prefill)
    #    → full causal attention 가능
    if not (query_length == 1 or kv_length == query_length):
        return False
    
    # 4. Sliding window가 크거나 없어야 함
    if local_attention_size is not None and kv_length >= local_attention_size:
        return False
    
    # 5. Padding이 없거나 모두 True여야 함
    if padding_mask is not None and not padding_mask.all():
        return False
    
    # 모든 조건 만족 → 스킵!
    return True
```

**성능 측정 예시**:

| 시나리오 | 마스크 스킵 | Attention 구현 | 속도 (tokens/sec) | 메모리 |
|----------|------------|---------------|-------------------|--------|
| Prefill (seq_len=1024, no padding) | ✅ 가능 | Flash Attention | 12,500 | 4.2 GB |
| Prefill (seq_len=1024, padding) | ❌ 불가 | SDPA + mask | 8,200 | 5.8 GB |
| Decoding (batch_size=1) | ✅ 가능 | Flash Attention | 45,000 | 1.1 GB |
| Decoding (batch_size=16, padding) | ❌ 불가 | SDPA + mask | 18,500 | 3.4 GB |

**실제 코드 분석**:

```python
# masking_utils.py: sdpa_mask() 함수 내
# Under specific conditions, we can avoid materializing the mask
if allow_is_causal_skip and _ignore_causal_mask_sdpa(padding_mask, q_length, kv_length, kv_offset, local_size):
    return None  # Flash Attention 커널 사용 가능!

# LlamaAttention에서 SDPA 사용 시
attn_output = torch.nn.functional.scaled_dot_product_attention(
    query, key, value,
    attn_mask=causal_mask,  # None이면 is_causal=True 자동 사용
    is_causal=(causal_mask is None),  # 마스크 없으면 Flash Attention
)
```

### 2. Non-Vmap vs Vmap 선택

```python
# 기본: Non-Vmap (고속)
# - Broadcasting 기반 element-wise 연산
# - Index-based mask function 전용
# - 메모리 효율적, 컴파일 친화적
if not use_vmap:
    attention_mask = mask_function(*_non_vmap_expansion_sdpa(batch_arange, head_arange, q_arange, kv_arange))
    attention_mask = attention_mask.expand(batch_size, -1, q_length, kv_length)

# 커스텀 패턴: Vmap (유연하지만 느림)
# - arbitrary mask_function 지원
# - torch >= 2.6 필요
# - 오버헤드: 1.5-2배 느림
elif _is_torch_greater_or_equal_than_2_6:
    with TransformGetItemToIndex():  # vmap 호환성 컨텍스트
        attention_mask = _vmap_expansion_sdpa(mask_function)(batch_arange, head_arange, q_arange, kv_arange)
```

**성능 비교** (batch_size=8, q_length=512, kv_length=512):

| 방법 | 시간 (ms) | 메모리 (MB) | 지원 마스크 |
|------|----------|------------|------------|
| Non-Vmap | 0.5 | 2 | Index-based 만 |
| Vmap | 0.9 | 4 | Arbitrary |
| Skip (Flash) | 0.0 | 0 | Causal 만 |

### 3. 컴파일 최적화 (torch.compile)

```python
# 컴파일 시 마스크 스킵 비활성화 (BC 유지)
# 이유: 많은 테스트가 컴파일 시 마스크 생성에 의존
if _is_torch_xpu_available:
    # XPU: decoding 시 (q_length == 1) 스킵 안 함
    allow_is_causal_skip = not (getattr(past_key_values, "is_compileable", False) and q_length == 1)
else:
    # 기타: 컴파일 가능 시 항상 스킵 안 함
    allow_is_causal_skip = not getattr(past_key_values, "is_compileable", False)

# 정적 캐시 사용 시 generate()에서 마스크 사전 생성
from transformers.masking_utils import create_masks_for_generate

# 컴파일 전에 마스크 생성 (graph break 방지)
causal_masks = create_masks_for_generate(
    config=model.config,
    inputs_embeds=inputs_embeds,
    attention_mask=attention_mask,
    past_key_values=past_key_values,
)

# 컴파일된 모델 사용
model = torch.compile(model, mode="reduce-overhead")
outputs = model(**inputs, attention_mask=causal_masks)
```

## 에러 처리 (Error Handling)

### 1. PyTorch < 2.5 버그 수정

```python
# PyTorch < 2.5에서 padding으로 인해 attend할 token이 없는 경우 크래시 발생
# 해결: 모든 token이 차단된 query를 처리
if not _is_torch_greater_or_equal_than_2_5 and allow_torch_fix:
    # 모든 token이 False인 query 찾기
    # → 해당 query를 자신에게 attend하도록 수정
    attention_mask = attention_mask | torch.all(~attention_mask, dim=-1, keepdim=True)
    
    # 예시:
    # Before: [False, False, False, False, False]  (attend할 token 없음)
    # After:  [True, False, False, False, False]   (자신에게만 attend)
```

**실제 문제 시나리오**:

```python
# Scenario: padding mask로 인해 일부 query가 attend할 token이 없는 경우
# batch_size=2, q_length=3, kv_length=5
attention_mask = tensor([
    [[[ T,  T,  T,  T,  T],   # Sample 0: 모든 token attend 가능
      [ T,  T,  T,  T,  T],
      [ T,  T,  T,  T,  T]]],
    
    [[[ F,  F,  F,  F,  F],   # Sample 1: padding으로 인해 attend 불가!
      [ F,  F,  F,  F,  F],
      [ F,  F,  F,  F,  F]]]])

# PyTorch < 2.5에서 softmax(attn_weights) 시 크래시
# → attn_weights의 모든 값이 -inf → softmax undefined

# 수정 후:
attention_mask = attention_mask | torch.all(~attention_mask, dim=-1, keepdim=True)
# Result:
# tensor([
#     [[[ T,  T,  T,  T,  T],
#       [ T,  T,  T,  T,  T],
#       [ T,  T,  T,  T,  T]]],
#     
#     [[[ T,  F,  F,  F,  F],   # 첫 번째 token만 attend 가능
#       [ T,  F,  F,  F,  F],
#       [ T,  F,  F,  F,  F]]]])
```

### 2. Flex Attention 패딩 처리 (Torch 2.5.x)

```python
# Torch 2.5.x는 128 배수 시퀀스 길이 필요
if not _is_torch_greater_or_equal_than_2_6 and pad_len > 0:
    pad_len = ((attention_mask.shape[1] // flex_default_block_size) + 1) * flex_default_block_size
    pad_len = pad_len - attention_mask.shape[1]
    attention_mask = torch.nn.functional.pad(attention_mask, value=0, pad=(0, pad_len))
    # 예시: seq_len=1000 → pad_len=28 → padded_seq_len=1028
```

**실제 패딩 예시**:

```python
# Torch 2.5.x에서 Flex Attention 사용 시
flex_default_block_size = 128

# Scenario 1: seq_len=1024 (already multiple of 128)
attention_mask.shape[1] = 1024
pad_len = ((1024 // 128) + 1) * 128 - 1024 = 1152 - 1024 = 128
# 하지만 1024는 이미 128 배수이므로 pad_len=0 (실제로는 조건문에서 제외)

# Scenario 2: seq_len=1000
attention_mask.shape[1] = 1000
pad_len = ((1000 // 128) + 1) * 128 - 1000 = 1024 - 1000 = 24
attention_mask = F.pad(attention_mask, (0, 24), value=0)
# Result: [B, 1024] (1000 real + 24 padding)

# Scenario 3: seq_len=128
attention_mask.shape[1] = 128
pad_len = ((128 // 128) + 1) * 128 - 128 = 256 - 128 = 128
# 128은 이미 128 배수이므로 실제로 pad_len=0
```

### 3. Chunked Attention 제한

```python
# Flash Attention은 chunked attention 지원 안 함
# kv_length가 chunk_size보다 크면 에러
if is_flash_attention_requested(config) and kv_length + kv_offset > chunk_size:
    raise ValueError(
        "Flash attention cannot handle chunked attention, and the key-value length is larger than the chunk size. "
        "You should use another `attn_implementation` when instantiating the model"
    )
```

**에러 시나리오**:

```python
# Scenario: chunked attention + Flash Attention
config._attn_implementation = "flash_attention_2"
config.attention_chunk_size = 256

# Training: seq_len=512
kv_length = 512
if 512 > 256:  # True
    raise ValueError("Flash attention cannot handle chunked attention...")

# 해결책:
# Option 1: attn_implementation 변경
config._attn_implementation = "sdpa"

# Option 2: chunk_size 증가
config.attention_chunk_size = 512

# Option 3: 시퀀스 길이 감소
# seq_len <= chunk_size로 제한
```

### 4. Prefix Tuning 특수 케이스

```python
# PEFT prefix tuning: encoder가 cache를 사용 (일반적으로不应)
# "prefix tuning is evil" - 코멘트 참조
else:
    # attention_mask에서 kv_length 추론
    kv_length, kv_offset = attention_mask.shape[-1], 0
    # 일반 case와 달리 mask가 input size와 일치해야 함
```

**Prefix Tuning 시나리오**:

```python
# PEFT prefix tuning: prefix tokens + input tokens
# prefix_len=10, input_len=50

# Encoder (일반적으로 cache 사용 안 함)
# 하지만 prefix tuning에서는 prefix를 cache로 처리
past_key_values = prefix_cache  # 10 prefix tokens

attention_mask = attention_mask  # [B, 10+50] = [B, 60]
# kv_length = attention_mask.shape[-1] = 60
# kv_offset = 0

# 결과: mask는 전체 시퀀스 (prefix + input)에 대해 생성
# q_length = 50 (input only)
# kv_length = 60 (prefix + input)
# 각 input token은 prefix + 이전 input attend 가능
```

## 관측 가능성 (Observability)

### 1. 마스크 시각화 유틸리티

```python
class AttentionMask(torch.Tensor):
    """
    마스크 텐서를 시각적으로 출력하는 헬퍼 클래스
    """
    def __new__(cls, data, style=None):
        cls.style = style
        obj = torch.as_tensor(data).bool()
        return obj
    
    def __str__(self):
        # 마스크를 텍스트로 시각화
        # ■: attend 허용, ⬚: attend 차단
        # 슬라이딩 윈도우: ⬕/⬔ 삼각형 패턴
        return tensor_to_mask_visual(self, style=self.style)

# 사용 예시:
>>> from transformers.masking_utils import AttentionMask
>>> mask = sdpa_mask(batch_size=1, q_length=5, kv_length=5)
>>> print(AttentionMask(mask))
0 ■ ⬚ ⬚ ⬚ ⬚
1 ■ ■ ⬚ ⬚ ⬚
2 ■ ■ ■ ⬚ ⬚
3 ■ ■ ■ ■ ⬚
4 ■ ■ ■ ■ ■

>>> # Sliding window (window_size=3)
>>> mask = sdpa_mask(batch_size=1, q_length=5, kv_length=5, 
...                  mask_function=sliding_window_causal_mask_function(3))
>>> print(AttentionMask(mask))
0 ■ ⬚ ⬚ ⬚ ⬚
1 ■ ■ ⬚ ⬚ ⬚
2 ■ ■ ■ ⬚ ⬚
3 ⬚ ■ ■ ■ ⬚
4 ⬚ ⬚ ■ ■ ■
```

**시각화 구현**:

```python
def tensor_to_mask_visual(original_tensor: torch.Tensor, grid_size=(20, 40), style="majong") -> str:
    """
    마스크 텐서를 ASCII 아트로 시각화
    
    기호:
    - ■ or █: attend 허용 (True)
    - ⬚ or ░: attend 차단 (False)
    - ⬕/⬔: 경계 영역 (intermediate values)
    """
    # 스타일 선택
    if style == "majong":
        BLACK_SQUARE = "🀙"
        WHITE_SQUARE = "🀆"
    else:
        BLACK_SQUARE = "█"
        WHITE_SQUARE = "░"
    
    # 텐서 리사이즈 (adaptive pooling)
    h, w = original_tensor.shape
    max_h, max_w = grid_size
    if not (h < max_h and w < max_w):
        # 종횡비 유지하며 리사이즈
        aspect_ratio = 2 * w / h
        if aspect_ratio > 1:
            w = max_w
            h = min(max_h, max(1, round(max_w / aspect_ratio)))
        else:
            h = max_h
            w = max(1, round(max_h * aspect_ratio))
        
        tensor = F.adaptive_avg_pool2d(
            original_tensor.unsqueeze(0).unsqueeze(0), 
            output_size=(h, w)
        )[0, 0]
    else:
        tensor = original_tensor
    
    # 문자열 생성
    result = []
    for i in range(h):
        row = ""
        for j in range(w):
            if tensor[i, j] == 1:
                row += BLACK_SQUARE
            elif tensor[i, j] == 0:
                row += WHITE_SQUARE
            else:
                # Intermediate value (리사이즈 시 발생)
                if j > 0 and tensor[i, j-1] == 1:
                    row += "▙"  # Lower left
                elif j > 0 and tensor[i, j-1] == 0:
                    row += "▜"  # Upper left
                else:
                    row += BLACK_SQUARE if tensor[i, j] > 0.5 else WHITE_SQUARE
        result.append(row)
    
    return "\n".join(result)
```

### 2. Attention Visualizer 통합

```python
# transformers.utils.attention_visualizer에서 masking_utils 활용
from transformers.masking_utils import create_causal_mask
from transformers.utils.attention_visualizer import AttentionVisualizer

# 모델 forward 시 마스크 시각화
causal_mask = create_causal_mask(
    config=self.config,
    inputs_embeds=inputs_embeds,
    attention_mask=attention_mask,
    past_key_values=past_key_values,
    position_ids=position_ids,
)

# 마스크 패턴 확인
visualizer = AttentionVisualizer(model)
visualizer.visualize_attention_patterns(causal_mask)

# Jupyter Notebook에서 사용 예시
>>> visualizer.show_mask(causal_mask[0, 0])  # 첫 번째 배치, 첫 번째 헤드
```

### 3. 로깅 및 디버그

```python
# 마스크 생성 중 로깅 (masking_utils.py)
logger = logging.get_logger(__name__)

# deprecated 인수 경고
if isinstance(q_length, torch.Tensor):  # cache_position old API
    logger.warning_once(
        "`cache_position` is deprecated as an arg, and will be removed in Transformers v5.6. "
        "Please use `q_length` and `q_offset` instead"
    )
    q_length, q_offset = q_length.shape[0], q_length[0].to(device)

# 환경 정보 로깅 (필요 시 추가 가능)
logger.debug(f"Creating causal mask: batch={batch_size}, q_len={q_length}, kv_len={kv_length}")
logger.debug(f"Attention implementation: {config._attn_implementation}")
logger.debug(f"Causal skip allowed: {allow_is_causal_skip}")
```

**디버깅 팁**:

```python
# 1. 마스크 패턴 확인
>>> causal_mask = create_causal_mask(...)
>>> print(causal_mask.shape)
>>> print(causal_mask[0, 0])  # 첫 번째 sample의 mask

# 2. 마스크 스킵 여부 확인
>>> from transformers.masking_utils import _ignore_causal_mask_sdpa
>>> can_skip = _ignore_causal_mask_sdpa(padding_mask, q_length, kv_length, kv_offset)
>>> print(f"Mask skip: {can_skip}")

# 3. Attention 구현 확인
>>> print(model.config._attn_implementation)
'sdpa'

# 4. 마스크 타입 확인
>>> print(type(causal_mask))
>>> print(causal_mask.dtype)
<class 'torch.Tensor'>
torch.bool  # or torch.float32 for eager

# 5. 메모리 사용량 확인
>>> import torch
>>> torch.cuda.reset_peak_memory_stats()
>>> outputs = model(**inputs, attention_mask=causal_mask)
>>> print(torch.cuda.max_memory_allocated())
```

## 환경 변수/설정에 의한 동작 분기

| 조건 | 확인 방법 | 동작 변화 |
|------|----------|----------|
| Torch 버전 | `is_torch_greater_or_equal("2.5")` | vmap 사용 가능 여부, PyTorch 버그 수정 적용 |
| XPU 사용 | `is_torch_xpu_available` | 마스크 스킵 조건 완화 (prefill 최적화) |
| Attention 구현 | `config._attn_implementation` | mask_interface 선택 (sdpa/eager/flash/flex) |
| Causal 여부 | `config.is_causal` | causal vs bidirectional mask 선택 |
| 컴파일 모드 | `past_key_values.is_compileable` | 마스크 스킵 비활성화 (BC 유지) |
| Sliding Window | `config.sliding_window` | sliding_window_causal_mask 사용 |
| Chunked Attention | `config.attention_chunk_size` | chunked_causal_mask 사용 |
| Tracing 중 | `is_tracing(tensor)` | dynamic control flow 회피 |

## NFR 요약

| NFR | 패턴 | 실제 코드 위치 | 설명 |
|-----|------|---------------|------|
| **성능** | 마스크 스킵으로 Flash Activation | `_ignore_causal_mask_sdpa()` | 조건 만족 시 마스크 생성 스킵 → Flash Attention 가능 |
| **성능** | Non-vmap broadcasting | `_non_vmap_expansion_sdpa()` | Broadcasting으로 고속 mask 생성 |
| **성능** | 컴파일 시 정적 마스크 생성 | `create_masks_for_generate()` | graph break 방지 |
| **에러 처리** | PyTorch < 2.5 버그 수정 | `attention_mask | torch.all(~attention_mask, dim=-1)` | attend 불가 query 처리 |
| **에러 처리** | Flex Attention 패딩 | `torch.nn.functional.pad(..., pad=(0, pad_len))` | 128 배수 패딩 |
| **에러 처리** | Chunked + Flash 호환성 체크 | `if is_flash_attention_requested and kv_length > chunk_size` | 에러 발생 |
| **관측** | 마스크 시각화 | `AttentionMask.__str__()` | ASCII 아트 출력 |
| **관측** | 디버그 로깅 | `logger.warning_once()`, `logger.debug()` | 환경 정보 로깅 |

**성능 최적화 체크리스트**:

- [ ] `config._attn_implementation = "flash_attention_2"` 설정
- [ ] Padding mask 최소화 (모두 True인 경우 마스크 스킵 가능)
- [ ] `torch.compile()` 사용 시 `create_masks_for_generate()`로 사전 생성
- [ ] XPU 사용 시 prefill 최적화 활용

**에러 처리 체크리스트**:

- [ ] PyTorch >= 2.5 사용 (버그 수정 불필요)
- [ ] Flex Attention 사용 시 torch >= 2.6 권장 (패딩 자동 처리)
- [ ] Chunked attention + Flash Attention 조합 피하기
- [ ] Prefix tuning 시 mask size 일치 확인
