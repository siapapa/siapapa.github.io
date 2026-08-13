---
title: 12H · 실시간 데이터 II — 바인딩
---

# 12H · 실시간 데이터 바인딩 — 트윈이 움직인다

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day2/06_live_binding.ipynb` · **GPU 불필요**

!!! success "오늘의 정점입니다"
    씬이 처음으로 살아 움직입니다.

## 학습 목표

- 외부 데이터를 USD 속성에 바인딩한다
- **어느 레이어에 쓸지** 통제한다
- 갱신 주기와 성능의 관계를 안다
- 임계치 이벤트를 검출한다

---

## 1. 데이터 만들기

실제 현장이라면 이 자리에 **OPC UA 클라이언트나 MQTT 구독자**가 들어갑니다.
수업에서는 모의 생성기를 씁니다.

```python
from generator import LineState
import random

state = LineState(rng=random.Random(42))
records = []
t = 0.0
while t < 7200:                      # 2시간
    records.append(state.step(t, 1.0, fault_at=3600))   # 1시간 뒤 고장
    t += 1.0
```

## 2. EditTarget — 어느 레이어에 쓸 것인가 ★

어제 4H 에서 배운 것의 실전 적용입니다.

```python
live_layer = Sdf.Layer.FindOrOpen("layers/live.usda")
stage.SetEditTarget(Usd.EditTarget(live_layer))
```

!!! danger "안 정하면 루트에 기록됩니다"
    그러면 배치·물리와 실시간 데이터가 한 파일에 섞여
    레이어를 나눈 의미가 사라집니다.

## 3. 속성 손잡이를 미리 만들어 둡니다

매 샘플마다 경로를 다시 조회하면 느립니다. **한 번만** 찾아 재사용하세요.

```python
bindings = {}
for name, spec in tags.items():
    prim = stage.OverridePrim(spec["prim"])
    attr = prim.CreateAttribute(spec["attr"], USD_TYPE[spec["type"]], custom=True)
    bindings[name] = (attr, CAST[spec["type"]])
```

## 4. 데이터 흘려 넣기

`Sdf.ChangeBlock` 으로 감싸면 USD 가 변경 알림을 **한 번에 모아** 처리합니다.
샘플이 수천 개일 때 차이가 큽니다.

```python
with Sdf.ChangeBlock():
    for frame, record in enumerate(records):
        for name, (attr, cast) in bindings.items():
            if name in record:
                attr.Set(cast(record[name]), Usd.TimeCode(frame))
```

## 5. 시간 메타데이터 — 함정 두 개 ★

### 함정 ① 스테이지 메타데이터는 아무 레이어에나 못 씁니다

EditTarget 이 데이터 레이어로 가 있는 상태에서 이걸 부르면 **에러가 납니다.**

```python
stage.SetStartTimeCode(0)     # ❌ 여기서 죽습니다
```

`startTimeCode` 같은 스테이지 메타데이터는 **루트(또는 세션) 레이어 전용**입니다.
레이어에 직접 쓰거나 EditTarget 을 되돌린 뒤 호출하세요.

```python
for layer in (live_layer, stage.GetRootLayer()):
    layer.startTimeCode = 0
    layer.endTimeCode = len(records) - 1
    layer.timeCodesPerSecond = 1.0

stage.SetEditTarget(Usd.EditTarget(stage.GetRootLayer()))   # 되돌리기
```

### 함정 ② `timeCodesPerSecond` 불일치

레이어마다 TCPS 가 다르면 USD 가 그 비율로 타임샘플을 스케일해
**에러 없이 엉뚱한 값**이 조회됩니다.

**원본과 대조해서 확인하세요.**

```
 프레임       USD        원본  일치
     0     25.47     25.47   ✅
  1800     48.11     48.11   ✅
  3600     48.28     48.28   ✅
  3700     72.52     72.52   ✅
  4000     95.00     95.00   ✅
```

## 6. 이벤트 검출 — 값 기록이 아니라 "언제 무엇이"

값을 넣는 것으로 끝이 아닙니다. 운전원에게 쓸모 있으려면
**언제 무엇이 넘었는지** 뽑아내야 합니다.

```python
def detect_events(records, tags):
    events, active = [], {}
    for frame, rec in enumerate(records):
        for name, spec in tags.items():
            warn = spec.get("warn")
            if warn is None or name not in rec:
                continue
            below = spec.get("warn_when", "above") == "below"
            bad = rec[name] <= warn if below else rec[name] >= warn
            if bad and name not in active:
                active[name] = frame
            elif not bad and name in active:
                events.append((active.pop(name), frame, name))
    return sorted(events)
```

### 결과를 읽는 법 ★

```
   시작     종료     지속  태그
  3513     7199    3686  conveyor_01.motor_temp
  3849     7199    3350  inspection.pass_rate
```

!!! question "무엇이 먼저 일어났습니까?"
    **모터 온도가 먼저 넘고, 통과율이 뒤이어 떨어졌습니다.**

    이 순서가 곧 원인과 결과입니다.
    1H 데모에서 던진 질문의 답이 여기서 나옵니다.

## 7. 실제 현장에 붙일 때 — MQTT

```bash
pip install paho-mqtt
python sim_data/generator.py --mqtt localhost --duration 0 --realtime
```

구독 쪽은 위 §3~4 의 바인딩 코드를 그대로 쓰고,
`records` 순회 대신 콜백에서 `attr.Set(value)` 를 부르면 됩니다.
실시간이면 타임샘플 대신 **기본값**을 갱신합니다.

---

## 실습 과제

**`TODO(basic)`** — 고장 시점을 `1200`(20분)으로 바꿔 다시 돌리세요.
고장이 빨라지면 버퍼 이벤트는 늘어날까요, 줄어들까요?
**먼저 예상하고** 확인하세요.

**`TODO(advanced)`** — 이벤트 요약 리포트를 만드세요.

1. 태그별 총 이상 시간과 발생 횟수
2. 가장 먼저 이상이 시작된 태그 (= 원인 후보)
3. **태그 쌍의 시작 시각 차이** — A 뒤 B 가 몇 초 뒤 따라왔는지

3번이 인과관계 추적의 출발점입니다.
상관이 인과는 아니지만, **순서는 단서**입니다.

## 정리

| 항목 | 핵심 |
|---|---|
| **EditTarget** | 안 정하면 루트에 기록됨 |
| **손잡이 재사용** | 매번 경로 조회하면 느림 |
| **ChangeBlock** | 대량 기록 시 알림을 묶어 처리 |
| **TCPS 일치** | 안 맞으면 에러 없이 엉뚱한 값 |
| **이벤트 검출** | "언제 무엇이" 가 쓸모 |

---

!!! tip "다음 시간"
    [13H · OmniGraph](13-omnigraph.md) — 코드 없이 반응 로직을 만듭니다.
