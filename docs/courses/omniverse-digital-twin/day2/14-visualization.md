---
title: 14H · 상태 시각화
---

# 14H · 상태 시각화 — 값을 색으로

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 스크립트**: `course_a/day2/07_status_visual.py`

## 학습 목표

- 값을 상태로 판정하고 색으로 표현한다
- **히스테리시스**로 알람 플러딩을 막는다
- 상태 전이 구간을 리포트로 뽑는다

---

## 색은 정보입니다

운전원이 화면을 3초 봤을 때 **"저기가 문제"** 를 알아채야 합니다.

3색 규칙: **정상(초록) · 경고(주황) · 이상(빨강)**. 그 이상 늘리지 마세요.
색이 많아지면 아무 색도 의미를 갖지 못합니다.

---

## 이 시간의 핵심 — 히스테리시스 ★

!!! danger "단순히 `value >= warn` 으로 판정하면 안 됩니다"
    값이 임계선 근처에서 흔들리면 **매 프레임 상태가 뒤집힙니다.**

    실제 현장에서는 경보등이 깜빡이는 **알람 플러딩**이 되고,
    운전원은 곧 경보를 무시하게 됩니다. **안전 문제로 이어집니다.**

### 실제로 겪은 일

이 교재를 만들 때 히스테리시스 없이 돌렸더니 이렇게 됐습니다.

```
프레임 3789  InspectionStation  normal → warning
프레임 3790  InspectionStation  warning → normal
프레임 3791  InspectionStation  normal → warning
프레임 3792  InspectionStation  warning → normal
...
```

전이가 **134건** 나왔고, 대부분이 이런 떨림이었습니다.

### 해법 두 가지

| 장치 | 역할 |
|---|---|
| **데드밴드** (range 의 5%) | 들어가는 문턱과 나오는 문턱을 다르게 |
| **최소 유지시간** (5프레임) | 잠깐 튀는 값으로 색이 바뀌지 않게 |

```python
def classify(value, spec, current="normal"):
    warn = spec["warn"]
    lo, hi = spec["range"]
    dead = (hi - lo) * 0.05                    # 데드밴드

    fault_enter, fault_exit = warn, warn - dead
    if current == "fault":
        return "fault" if value >= fault_exit else "warning"   # 나올 땐 더 내려가야
    if value >= fault_enter:
        return "fault"
    ...
```

**한 번 fault 로 들어가면, 단순히 임계 아래로 내려온 정도가 아니라
데드밴드만큼 더 회복해야 빠져나옵니다.**

### 적용 후

```
프레임 3646  Conveyor_A         normal → warning   conveyor_01.motor_temp
프레임 3691  Conveyor_A         warning → fault    conveyor_01.motor_temp
프레임 3793  InspectionStation  normal → warning   inspection.pass_rate
프레임 3841  InspectionStation  warning → fault    inspection.pass_rate
```

깨끗한 3단계 전이만 남았습니다.

!!! question "이 표에서 무엇이 보입니까?"
    **컨베이어가 먼저(3646), 검사 스테이션이 약 150초 뒤(3793).**

    이 시간차가 인과관계의 단서입니다.
    12H 의 이벤트 검출과 같은 결론에 다른 방법으로 도달했습니다.

---

## 별도 레이어에 씁니다

색상 바인딩은 `layers/visual.usda` 에만 씁니다.
시각화 규칙을 통째로 바꿔 끼우거나 꺼 버릴 수 있습니다.

!!! note "머티리얼 바인딩은 시간에 따라 바뀌지 않습니다"
    USD 의 관계(relationship)는 타임샘플을 갖지 않습니다.
    그래서 **대표 상태**로 머티리얼을 바인딩하고,
    프레임별 색 변화는 `displayColor` 타임샘플로 처리합니다.

    Kit 에서 타임라인을 재생하면 색이 실제로 변합니다.

---

## 실습 과제

**`TODO(basic)`** — 데드밴드 비율을 `0.01` 로 낮춰 다시 돌리고,
전이 건수가 얼마나 늘어나는지 확인하세요.
**너무 크게 잡으면** 어떤 문제가 생길지도 생각해 보세요.

**`TODO(advanced)`** — 설비별 상태를 라인 전체 상태로 집계하세요.

1. 한 설비라도 fault 면 라인은 fault
2. 라인 상태가 바뀐 구간과 그 원인 설비를 리포트로
3. 상태별 **누적 시간**을 계산해 가동률을 구하세요

## 정리

| 항목 | 핵심 |
|---|---|
| **3색 규칙** | 정상·경고·이상. 더 늘리지 않기 |
| **히스테리시스** | 들어가는 문턱과 나오는 문턱을 다르게 |
| **최소 유지시간** | 잠깐 튀는 값 무시 |
| **별도 레이어** | 시각화 규칙을 끄고 켤 수 있게 |

---

!!! tip "다음 시간"
    [15H · 운영 시나리오](15-scenarios.md) — **해 보기 전에 아는 것**,
    디지털트윈의 진짜 값어치.
