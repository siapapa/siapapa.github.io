---
title: 1H · OT · 데모 · USD 복습
---

# 1H · OT · 데모 · USD 압축 복습

!!! warning "이 시간의 실습은 최종 검증 전입니다"
    Isaac Sim 실행이 필요한 부분은 아직 확인이 끝나지 않았습니다.
    화면이 안내와 다르면 강사에게 알려 주세요.

## 학습 목표

- Isaac Sim 이 Kit 위에 무엇을 얹은 것인지 안다
- 3일 뒤 자기가 무엇을 만들게 되는지 본다
- OpenUSD 핵심 개념을 되짚는다

---

## Isaac Sim 은 Kit 앱입니다

[기초 과정](../../omniverse-digital-twin/index.md)에서 만진 USD·Kit 위에
**물리와 로보틱스 도구**가 얹힌 것입니다. 씬 파일도 그대로 `.usd` 입니다.

```
   ┌─────────────────────────────────────────┐
   │  Isaac Sim  (로봇 · 센서 · Replicator)   │  ← 오늘 배울 것
   ├─────────────────────────────────────────┤
   │  Kit SDK                                │  ← 기초 과정에서 본 것
   ├──────────────┬──────────────┬───────────┤
   │  OpenUSD     │  PhysX       │  RTX      │
   └──────────────┴──────────────┴───────────┘
```

!!! tip "기초 과정에서 만든 씬을 그대로 씁니다"
    `SmartFactory-01` 의 로봇 마운트 자리에 실제 로봇을 올립니다.
    기초 과정을 안 들으셨어도 완성본 씬이 제공됩니다.

---

## 완성본 데모

3일 뒤 만들 것을 먼저 봅니다.

1. 공장 씬에서 **로봇이 부품을 집어 옮깁니다** — 사람이 프로그래밍한 것이 아니라 학습된 것
2. 검사 스테이션 카메라가 이미지를 찍고, **불량을 판정**합니다
3. 결과가 DB 에 쌓이고, **자연어로 물어보면** 답이 나옵니다

```
"지난 학습들 중 성공률이 가장 높았던 조건은?"
→ preset=robust, 성공률 88.3%
```

## 3일 로드맵

| Day | 무엇 |
|---|---|
| **1** | 로봇을 올리고 센서를 달고 데이터를 만든다 |
| **2** | 로봇에게 **스스로 움직이는 법을 학습**시킨다 |
| **3** | 시뮬과 현실의 격차를 재고, AI 와 잇고, 발표한다 |

---

## USD 압축 복습

기초 과정을 안 들으신 분을 위해 핵심만 되짚습니다.

| 개념 | 한 줄 |
|---|---|
| **Stage** | 열려 있는 씬. 파일 하나 |
| **Prim** | 씬 안의 물건. 경로가 곧 주소 (`/World/Robot`) |
| **Attribute** | 프림에 붙는 값 |
| **Reference** | 다른 파일을 가리켜 재사용 |
| **Layer** | 여러 파일을 겹쳐 합성. 앞이 강함 |

로봇을 씬에 올리는 것도 결국 **reference** 입니다.

```python
api.add_reference_to_stage(robot_usd_path, "/World/Robot")
```

!!! note "단위와 업축"
    Isaac Sim 은 **미터 · Z-up** 을 씁니다.
    기초 과정의 공용 씬도 같은 규약으로 만들어져 있어 그대로 이어집니다.

---

## 실습 · 환경 확인

```bash
./python.sh 10_hello_isaacsim.py        # Linux
python.bat 10_hello_isaacsim.py         # Windows
```

가장 먼저 **API 점검표**가 나옵니다.

```
── Isaac Sim API 점검 ──
  ✅ World                    isaacsim.core.api
  ✅ DynamicCuboid            isaacsim.core.api.objects
  ✅ add_reference_to_stage   isaacsim.core.utils.stage
  ✅ Articulation             isaacsim.core.prims
  ✅ Camera                   isaacsim.sensors.camera
  ✅ omni.replicator.core     로드됨

  파이썬: 3.11.x
  공용 씬: .../smartfactory01.usda  ✅
```

!!! danger "문제가 생기면 항상 여기부터 보세요"
    ⚠️ 표시가 있으면 그 항목을 쓰는 시간에 막힙니다.
    미리 알고 대응할 수 있습니다.

    ```
    [Camera] 를 찾지 못했습니다. Isaac Sim 버전이 바뀌었을 수 있습니다.
      시도한 경로:
        isaacsim.sensors.camera.Camera  →  ImportError
        omni.isaac.sensor.Camera        →  ImportError
      해결: 새 경로를 찾아 _isaac_bootstrap.py 의 후보 목록 맨 앞에 추가하세요.
    ```

---

!!! tip "다음 시간"
    [2H · 시뮬레이션 루프](02-simulation-loop.md)
