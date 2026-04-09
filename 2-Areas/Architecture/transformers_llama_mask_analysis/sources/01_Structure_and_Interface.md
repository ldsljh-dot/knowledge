---
title: "01 - Structure and Interface: Llama Mask System"
created: 2026-04-07
tags: [llama, mask, causal, attention, transformers, architecture, interface]
category: 2-Areas/Architecture/transformers_llama_mask_analysis
---

# 01 - Structure and Interface: Llama Mask System

## Layer 역할 및 개요

Llama 모델의 마스크 시스템은 **attention 패턴의 핵심 제어 메커니즘**으로, 다음과 같은 책임을 가집니다:

1. **Causal Masking**: Decoder-only 아키텍처에서 token이 자신과 이전 token만 attend하도록 보장
2. **Padding Masking**: 가변 길이 시퀀스에서 padding token 무시
3. **Multi-Interface Support**: SDPA, Flash Attention, Eager, Flex Attention에 맞는 포맷 제공
4. **Optimization**: 조건부 마스크 스킵으로 Flash Attention 커널 활성화

## 디렉토리 구조

```
src/transformers/
├── masking_utils.py                           # 마스크 생성 코어 (1609줄)
│   ├── AttentionMaskInterface                 # Interface 클래스
│   │   ├── sdpa_mask()                        # SDPA용 4D boolean mask
│   │   ├── eager_mask()                       # Eager용 4D float mask (0/-inf)
│   │   ├── flash_attention_mask()             # Flash Attention용 (None/2D)
│   │   └── flex_attention_mask()              # Flex Attention용 BlockMask
│   │
│   ├── Mask Functions                         # 마스크 패턴 정의
│   │   ├── causal_mask_function()             # kv_idx <= q_idx
│   │   ├── bidirectional_mask_function()      # q_idx >= 0 (full)
│   │   ├── sliding_window_causal_mask_function()
│   │   ├── chunked_causal_mask_function()
│   │   ├── padding_mask_function()
│   │   └── packed_sequence_mask_function()
│   │
│   ├── Mask Combinators                     # 마스크 조합
│   │   ├── and_masks()                      # 교집합 (AND)
│   │   └── or_masks()                       # 합집합 (OR)
│   │
│   ├── Creation Functions                    # 공개 API
│   │   ├── create_causal_mask()              # 메인 causal mask 생성
│   │   ├── create_sliding_window_causal_mask()
│   │   ├── create_chunked_causal_mask()
│   │   └── create_bidirectional_mask()
│   │
│   └── Utilities                            # 헬퍼 함수
│       ├── _preprocess_mask_arguments()      # 공통 전처리
│       ├── find_packed_sequence_indices()    # Packed sequence 감지
│       ├── _ignore_causal_mask_sdpa()        # 스킵 조건 검사
│       └── tensor_to_mask_visual()           # 시각화 유틸리티
│
└── models/llama/
    └── modeling_llama.py                     # Llama 모델 구현 (480줄)
        ├── LlamaModel
        │   └── forward()
        │       └── create_causal_mask()      # 마스크 생성 호출
        ├── LlamaAttention
        │   └── forward()
        │       └── attention_mask 전달       # 마스크 어텐션으로 전달
        └── eager_attention_forward()
            └── attn_weights + attention_mask # 마스크 적용
```

## 핵심 클래스 명세

### 1. AttentionMaskInterface

```python
class AttentionMaskInterface(GeneralInterface):
    """
    Attention Implementation별 마스크 생성 함수 등록 및 디스패치
    
    설계 의도:
    - Strategy Pattern: attention 구현에 따라 다른 마스크 생성 전략 사용
    - GeneralInterface 상속: 전역 등록 메커니즘 (모델 파일에서도 접근 가능)
    - 확장 가능: 새로운 attention 구현 추가 시 register()로 간단히 추가
    """
    _global_mapping = {
        "sdpa": sdpa_mask,                    # PyTorch SDPA (torch >= 2.5)
        "eager": eager_mask,                  # 수동 attention 계산
        "flash_attention_2": flash_attention_mask,  # Flash Attention 2
        "flash_attention_3": flash_attention_mask,  # Flash Attention 3
        "flash_attention_4": flash_attention_mask,  # Flash Attention 4
        "flex_attention": flex_attention_mask,      # Flex Attention (torch >= 2.5)
    }

# 사용 예시:
mask_interface = ALL_MASK_ATTENTION_FUNCTIONS[config._attn_implementation]
# config._attn_implementation = "sdpa" → mask_interface = sdpa_mask
causal_mask = mask_interface(batch_size=..., q_length=..., ...)
```

### 2. 마스크 함수들 (Mask Functions)

모든 마스크 함수는 동일한 시그니처를 가집니다:

```python
def mask_function(batch_idx: int, head_idx: int, q_idx: int, kv_idx: int) -> bool:
    """
    Args:
        batch_idx: 배치 인덱스 (0 ~ batch_size-1)
        head_idx: 어텐션 헤드 인덱스 (0 ~ num_heads-1)
        q_idx: 쿼리 시퀀스 인덱스
        kv_idx: 키-값 시퀀스 인덱스
    
    Returns:
        True: attend 허용, False: attend 차단
    """
```

#### causal_mask_function

```python
def causal_mask_function(batch_idx: int, head_idx: int, q_idx: int, kv_idx: int) -> bool:
    """
    Lower-diagonal causal mask
    
    설계 의도:
    - Decoder-only 모델의 핵심: 미래 정보 차단
    - kv_idx <= q_idx: 각 토큰은 자신과 이전 토큰만 attend
    - 모든 헤드, 배치를 동일하게 처리 (head_idx, batch_idx 미사용)
    
    마스크 패턴 (q_length=5, kv_length=5):
        kv_idx: 0  1  2  3  4
    q_idx=0:    ■  ⬚  ⬚  ⬚  ⬚
    q_idx=1:    ■  ■  ⬚  ⬚  ⬚
    q_idx=2:    ■  ■  ■  ⬚  ⬚
    q_idx=3:    ■  ■  ■  ■  ⬚
    q_idx=4:    ■  ■  ■  ■  ■
    
    where ■ = True (attend 허용), ⬚ = False (attend 차단)
    """
    return kv_idx <= q_idx
```

#### sliding_window_causal_mask_function

```python
def sliding_window_causal_mask_function(sliding_window: int) -> Callable:
    """
    Sliding window causal mask (Mistral에서 대중화)
    
    설계 의도:
    - Full attention의 O(n²) 메모리 문제 해결
    - 최근 sliding_window 개 토큰만 attend
    - Causal mask + Sliding window overlay 조합
    
    구성:
    1. causal_mask_function: kv_idx <= q_idx (causality)
    2. sliding_window_overlay: kv_idx > q_idx - sliding_window (window)
    3. and_masks(): 두 조건 모두 만족하는 토큰만 attend
    
    마스크 패턴 (sliding_window=3):
        kv_idx: 0  1  2  3  4
    q_idx=0:    ■  ⬚  ⬚  ⬚  ⬚
    q_idx=1:    ■  ■  ⬚  ⬚  ⬚
    q_idx=2:    ■  ■  ■  ⬚  ⬚
    q_idx=3:    ⬚  ■  ■  ■  ⬚  # q_idx-3 까지만 attend
    q_idx=4:    ⬚  ⬚  ■  ■  ■  # q_idx-3 까지만 attend
    """
    return and_masks(
        sliding_window_overlay(sliding_window),
        causal_mask_function
    )

def sliding_window_overlay(sliding_window: int) -> Callable:
    """Sliding window overlay"""
    def inner_mask(batch_idx, head_idx, q_idx, kv_idx):
        return kv_idx > q_idx - sliding_window
    return inner_mask
```

#### chunked_causal_mask_function

```python
def chunked_causal_mask_function(chunk_size: int, left_padding: torch.Tensor) -> Callable:
    """
    Chunked attention mask (Llama4에서 사용)
    
    설계 의도:
    - 시퀀스를 청크로 분할하여 attend
    - 동일 청크 내 토큰만 attend (cross-chunk attend 차단)
    - Left padding 보정: padding된 시퀀스의 청크 경계 조정
    
    사용 사례:
    - chunk_size=3, left_padding=[0]:
        kv_idx: 0  1  2  3  4
    q_idx=0:    ■  ⬚  ⬚  ⬚  ⬚
    q_idx=1:    ■  ■  ⬚  ⬚  ⬚
    q_idx=2:    ■  ■  ■  ⬚  ⬚
    q_idx=3:    ⬚  ⬚  ⬚  ■  ⬚  # new chunk 시작
    q_idx=4:    ⬚  ⬚  ⬚  ■  ■  # 동일 청크 내 attend
    """
    return and_masks(
        chunked_overlay(chunk_size, left_padding),
        causal_mask_function
    )

def chunked_overlay(chunk_size: int, left_padding: torch.Tensor) -> Callable:
    """Chunk overlay"""
    def inner_mask(batch_idx, head_idx, q_idx, kv_idx):
        return (kv_idx - left_padding[batch_idx]) // chunk_size == \
               (q_idx - left_padding[batch_idx]) // chunk_size
    return inner_mask
```

#### padding_mask_function

```python
def padding_mask_function(padding_mask: torch.Tensor) -> Callable:
    """
    Padding mask function
    
    설계 의도:
    - 2D attention_mask (batch_size, seq_len)를 4D mask 함수로 변환
    - Padding token (False) attend 차단
    - kv_idx 기준으로 padding_mask[batch_idx, kv_idx] 접근
    
    주의: padding_mask는 최소한 최대 kv_index 크기여야 함
    """
    def inner_mask(batch_idx, head_idx, q_idx, kv_idx):
        return padding_mask[batch_idx, kv_idx]
    return inner_mask
```

#### packed_sequence_mask_function

```python
def packed_sequence_mask_function(packed_sequence_mask: torch.Tensor) -> Callable:
    """
    Packed sequence mask
    
    설계 의도:
    - 여러 시퀀스를 한 배치로 묶은 packed tensor 형식 지원
    - 동일 시퀀스 내 토큰만 attend (cross-sequence attend 차단)
    - packed_sequence_mask[batch, idx] 값이 같은 토큰만 attend
    
    예시:
    - Sequence A: 2 tokens → packed_sequence_mask: [0, 0, ...]
    - Sequence B: 3 tokens → packed_sequence_mask: [1, 1, 1, ...]
    - Sequence C: 1 token  → packed_sequence_mask: [2, ...]
    
    Packed: [0, 0, 1, 1, 1, 2]
    → index 0,1 (Seq A) 서로 attend, but index 0,2 (Seq A,B) attend 불가
    """
    def inner_mask(batch_idx, head_idx, q_idx, kv_idx):
        return packed_sequence_mask[batch_idx, q_idx] == \
               packed_sequence_mask[batch_idx, kv_idx]
    return inner_mask
```

### 3. 마스크 조합 함수 (Mask Combinators)

```python
def and_masks(*mask_functions: Callable) -> Callable:
    """
    마스크 교집합 (AND 조합)
    
    설계 의도:
    - 모든 mask_function이 True일 때만 True 반환
    - 예: causal AND padding → 둘 다 만족하는 토큰만 attend
    
    사용 사례:
    - Sliding window causal: AND(causal, sliding_window)
    - Padding 적용: AND(causal, padding_mask)
    - Packed sequence: AND(causal, packed_sequence_mask)
    """
    def and_mask(batch_idx, head_idx, q_idx, kv_idx):
        result = q_idx.new_ones((), dtype=torch.bool)
        for mask in mask_functions:
            result = result & mask(batch_idx, head_idx, q_idx, kv_idx)
        return result
    return and_mask

def or_masks(*mask_functions: Callable) -> Callable:
    """
    마스크 합집합 (OR 조합)
    
    설계 의도:
    - 하나라도 True이면 True 반환
    - 예: causal OR image_token → 이미지 토큰 간 추가 attend 허용
    
    사용 사례:
    - 멀티모달: OR(causal, image_token_mask)
    - Custom pattern 추가
    """
    def or_mask(batch_idx, head_idx, q_idx, kv_idx):
        result = q_idx.new_zeros((), dtype=torch.bool)
        for mask in mask_functions:
            result = result | mask(batch_idx, head_idx, q_idx, kv_idx)
        return result
    return or_mask
```

## Public API 시그니처 및 사용 예시

### create_causal_mask()

```python
@deprecate_kwarg("input_embeds", version="5.6.0", new_name="inputs_embeds")
def create_causal_mask(
    config: PreTrainedConfig,              # 모델 설정
    inputs_embeds: torch.Tensor,           # [batch, q_length, hidden]
    attention_mask: torch.Tensor | None,   # 2D padding mask [batch, seq_len]
    past_key_values: Cache | None,         # 과거 KV 캐시
    position_ids: torch.Tensor | None = None,  # 위치 ID
    or_mask_function: Callable | None = None,  # OR 조합 함수
    and_mask_function: Callable | None = None, # AND 조합 함수
) -> torch.Tensor | BlockMask | None:
    """
    표준 causal mask 생성
    
    Returns:
        - torch.Tensor (SDPA/Eager): [batch, 1, q_length, kv_length]
        - BlockMask (Flex Attention): 블록 압축 마스크
        - None (Flash Attention): 마스크 불필요
    
    사용 예시 1: Training (no cache)
    >>> causal_mask = create_causal_mask(
    ...     config=model.config,
    ...     inputs_embeds=inputs_embeds,     # [8, 512, 4096]
    ...     attention_mask=attention_mask,   # [8, 512]
    ...     past_key_values=None,
    ... )
    >>> # 결과: [8, 1, 512, 512] boolean mask
    
    사용 예시 2: Generation (with cache)
    >>> causal_mask = create_causal_mask(
    ...     config=model.config,
    ...     inputs_embeds=new_embeds,        # [8, 5, 4096] (new tokens only)
    ...     attention_mask=attention_mask,   # [8, 105] (past + current)
    ...     past_key_values=past_kv,         # 100 past tokens
    ... )
    >>> # 결과: [8, 1, 5, 105] boolean mask
    ```
    
    사용 예시 3: Multimodal (with OR mask)
    >>> def image_token_mask(b, h, q, k):
    ...     return is_image_token(q) | is_image_token(k)
    >>> 
    >>> causal_mask = create_causal_mask(
    ...     config=model.config,
    ...     inputs_embeds=inputs_embeds,
    ...     attention_mask=attention_mask,
    ...     past_key_values=past_kv,
    ...     or_mask_function=image_token_mask,  # 이미지 토큰 attend 허용
    ... )
    """
```

### 실제 사용 예시 - LlamaModel.forward()

```python
@auto_docstring
class LlamaModel(LlamaPreTrainedModel):
    def forward(
        self,
        input_ids: torch.LongTensor | None = None,
        attention_mask: torch.Tensor | None = None,
        position_ids: torch.LongTensor | None = None,
        past_key_values: Cache | None = None,
        inputs_embeds: torch.FloatTensor | None = None,
        use_cache: bool | None = None,
        **kwargs,
    ) -> BaseModelOutputWithPast:
        # 1. 임베딩 변환
        if inputs_embeds is None:
            inputs_embeds = self.embed_tokens(input_ids)
        
        # 2. 캐시 초기화
        if use_cache and past_key_values is None:
            past_key_values = DynamicCache(config=self.config)
        
        # 3. 위치 ID 계산
        if position_ids is None:
            past_seen_tokens = past_key_values.get_seq_length() if past_key_values else 0
            position_ids = torch.arange(inputs_embeds.shape[1], device=inputs_embeds.device) \
                           + past_seen_tokens
            position_ids = position_ids.unsqueeze(0)
        
        # 4. Causal mask 생성 ⭐
        causal_mask = create_causal_mask(
            config=self.config,
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            past_key_values=past_key_values,
            position_ids=position_ids,
        )
        
        # 5. Decoder 레이어 순회
        hidden_states = inputs_embeds
        position_embeddings = self.rotary_emb(hidden_states, position_ids)
        
        for decoder_layer in self.layers:
            hidden_states = decoder_layer(
                hidden_states,
                attention_mask=causal_mask,  # 마스크 전달
                position_embeddings=position_embeddings,
                past_key_values=past_key_values,
                use_cache=use_cache,
                **kwargs,
            )
        
        # 6. 최종 LayerNorm
        hidden_states = self.norm(hidden_states)
        return BaseModelOutputWithPast(
            last_hidden_state=hidden_states,
            past_key_values=past_key_values,
        )
```

### 실제 사용 예시 - LlamaAttention.forward()

```python
class LlamaAttention(nn.Module):
    def forward(
        self,
        hidden_states: torch.Tensor,
        position_embeddings: tuple[torch.Tensor, torch.Tensor] | None = None,
        attention_mask: torch.Tensor | None = None,  # causal_mask 전달됨
        past_key_values: Cache | None = None,
        **kwargs,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # 1. Q, K, V 프로젝션
        input_shape = hidden_states.shape[:-1]
        hidden_shape = (*input_shape, -1, self.head_dim)
        
        query_states = self.q_proj(hidden_states).view(hidden_shape).transpose(1, 2)
        key_states = self.k_proj(hidden_states).view(hidden_shape).transpose(1, 2)
        value_states = self.v_proj(hidden_states).view(hidden_shape).transpose(1, 2)
        
        # 2. RoPE 적용
        cos, sin = position_embeddings
        query_states, key_states = apply_rotary_pos_emb(query_states, key_states, cos, sin)
        
        # 3. 캐시 업데이트
        if past_key_values is not None:
            key_states, value_states = past_key_values.update(
                key_states, value_states, self.layer_idx
            )
        
        # 4. Attention interface 선택
        attention_interface = ALL_ATTENTION_FUNCTIONS.get_interface(
            self.config._attn_implementation, eager_attention_forward
        )
        
        # 5. Attention 계산 (attention_mask = causal_mask 전달)
        attn_output, attn_weights = attention_interface(
            self,
            query_states,
            key_states,
            value_states,
            attention_mask,  # ⭐ causal_mask 여기에 전달됨
            dropout=0.0 if not self.training else self.attention_dropout,
            scaling=self.scaling,
            **kwargs,
        )
        
        # 6. 출력 프로젝션
        attn_output = attn_output.reshape(*input_shape, -1).contiguous()
        attn_output = self.o_proj(attn_output)
        return attn_output, attn_weights
```

### 실제 사용 예시 - eager_attention_forward()

```python
def eager_attention_forward(
    module: nn.Module,
    query: torch.Tensor,                      # [batch, heads, q_length, head_dim]
    key: torch.Tensor,                        # [batch, heads, kv_length, head_dim]
    value: torch.Tensor,                      # [batch, heads, kv_length, head_dim]
    attention_mask: torch.Tensor | None,      # ⭐ causal_mask (4D)
    scaling: float,
    dropout: float = 0.0,
    **kwargs,
):
    """
    Eager attention 계산
    
    마스크 적용 핵심 단계:
    attn_weights = attn_weights + attention_mask
    """
    # 1. GQA: Key, Value repeat
    key_states = repeat_kv(key, module.num_key_value_groups)
    value_states = repeat_kv(value, module.num_key_value_groups)
    
    # 2. QK^T 곱셈
    attn_weights = torch.matmul(query, key_states.transpose(2, 3)) * scaling
    # attn_weights: [batch, heads, q_length, kv_length]
    
    # 3. ⭐ 마스크 적용
    if attention_mask is not None:
        attn_weights = attn_weights + attention_mask
        # -inf가 추가된 위치는 softmax 후 0이 됨
        # 예: attn_weights[i, j] += -3.4e38 → softmax ≈ 0
    
    # 4. Softmax
    attn_weights = nn.functional.softmax(attn_weights, dim=-1, dtype=torch.float32)
    attn_weights = attn_weights.to(query.dtype)
    
    # 5. Dropout
    attn_weights = nn.functional.dropout(
        attn_weights, p=dropout, training=module.training
    )
    
    # 6. V와 곱셈
    attn_output = torch.matmul(attn_weights, value_states)
    attn_output = attn_output.transpose(1, 2).contiguous()
    
    return attn_output, attn_weights
```

## 확장 포인트 (Extension Points)

### 1. 새로운 Attention 구현 추가

```python
# masking_utils.py에서 AttentionMaskInterface에 등록
from transformers.masking_utils import ALL_MASK_ATTENTION_FUNCTIONS

def my_custom_mask(batch_size, q_length, kv_length, **kwargs):
    """Custom mask implementation"""
    # mask creation logic
    return custom_mask

# 등록
ALL_MASK_ATTENTION_FUNCTIONS.register("my_custom_attn", my_custom_mask)

# 모델 설정에서 사용
config._attn_implementation = "my_custom_attn"
```

### 2. 커스텀 마스크 함수 조합

```python
# 이미지 토큰 처리 예시 (멀티모달)
def image_token_mask(batch_idx, head_idx, q_idx, kv_idx):
    """이미지 토큰이 서로 attend할 수 있도록 허용"""
    # 이미지 토큰 인덱스 확인 (예: 100-200번 인덱스)
    q_is_image = (100 <= q_idx < 200)
    k_is_image = (100 <= kv_idx < 200)
    return q_is_image & k_is_image

causal_mask = create_causal_mask(
    config=config,
    inputs_embeds=inputs_embeds,
    attention_mask=attention_mask,
    past_key_values=past_kv,
    or_mask_function=image_token_mask,  # causal OR image_token
)
# 결과: causal mask + 이미지 토큰 간 attend 허용
```

### 3. 상속을 통한 모델 확장

```python
# Llama 모델 상속하여 마스크 로직 변경
from transformers import LlamaModel

class MyCustomLlamaModel(LlamaModel):
    def forward(self, input_ids, attention_mask, **kwargs):
        # 커스텀 마스크 로직
        inputs_embeds = self.embed_tokens(input_ids)
        
        # 추가 마스크 함수 정의
        def custom_mask(b, h, q, k):
            # custom logic
            return q >= k - 10  # 10-token look-back
        
        causal_mask = create_causal_mask(
            config=self.config,
            inputs_embeds=inputs_embeds,
            attention_mask=attention_mask,
            past_key_values=kwargs.get("past_key_values"),
            and_mask_function=custom_mask,  # causal AND custom
        )
        
        # 나머지 forward 로직
        return super().forward(input_ids, attention_mask=causal_mask, **kwargs)
```
