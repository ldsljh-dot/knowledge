### 📄 [타임라인 및 생태계 통합 분석] Meta-AMD Helios 기반 2026 하반기 인프라 구축 전략

- **배경 및 개요 (Context)**:
  - Meta의 AI 인프라 구축 타임라인과 구체적인 생태계 스택이 확인됨. 하드웨어(Custom MI450, EPYC CPU)부터 소프트웨어(ROCm), 그리고 아키텍처(Helios Rack-Scale)까지 AMD 생태계의 전방위적 도입이 2026년 하반기에 본격화될 예정임.

- **핵심 분석 내용 (Deep Dive)**:
  - **1. 도입 타임라인 (2026년 하반기)**:
    - **일정**: 2026년 하반기를 목표로 Meta의 데이터센터에 해당 시스템이 실제로 구축(Deployment) 및 가동(Go-live)됨.
    - **시사점**: 2026년 하반기는 당사의 차세대 메모리 솔루션(HBF, CXL Appliance)의 초기 시장 진입 및 PoC 검증 타이밍과 맞물림. 하이퍼스케일러들의 주력 인프라가 NVIDIA 일변도에서 AMD 연합군으로 분산되는 시점임.
  - **2. Full AMD Stack 채택 (Hardware + Software)**:
    - **컴퓨팅 노드 구성**: EPYC CPU (6세대, 코드명 Venice/Turin 기반)와 Custom MI450 가속기의 조합. 이는 타팀 보고에서 확인된 Meta의 "Grace/Very(ARM) CPU 도입" 투트랙(Two-track) 전략의 또 다른 축인 **x86 기반 고성능 컴퓨팅 노드** 구성을 의미함.
    - **소프트웨어 생태계**: AMD의 **ROCm (Radeon Open Compute) 소프트웨어**를 적극 활용. CUDA 의존성을 탈피하고 ROCm 생태계에 PyTorch 등 주요 프레임워크를 최적화하려는 Meta의 전략적 결정.
  - **3. Helios Rack-Scale Architecture 완성**:
    - **아키텍처 통합**: 개별 서버 섀시(Chassis) 단위를 넘어, 전력 분배, 네트워킹(Infinity Fabric / Ethernet), 쿨링이 하나로 통합된 랙 스케일(Helios)로 클러스터를 구성.

- **흐름 및 시사점 (Tracking & Insights)**:
  - EPYC CPU - MI450 GPU - ROCm SW로 이어지는 **Full AMD Stack**의 대규모 상용화는 AI 가속기 생태계에 큰 지각 변동임.
  - **대응 전략 (Action Item)**:
    - **호환성 검증 방향 선회**: 당사에서 개발 중인 CXL Memory Appliance 및 HBF 기반 가속 카드의 성능 검증(PoC) 대상을 기존 NVIDIA(CUDA) 환경 중심에서 **AMD(ROCm) 및 EPYC/MI450 환경**으로 조기 확장해야 할 필요성이 매우 높음.
    - 특히, CXL 생태계 내에서 AMD EPYC CPU(호스트)와 MI450 가속기 간의 CXL/Infinity Fabric 프로토콜 호환성 및 대역폭 병목을 사전 검증하는 워크스트림 편성이 요구됨.