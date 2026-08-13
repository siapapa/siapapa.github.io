---
title: 11H · 실시간 데이터 I — 스키마
---

# 11H · 태그 스키마 — 데이터와 씬을 잇는 계약

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day2/05_data_schema.ipynb` · **GPU 불필요**

## 학습 목표

- 태그 ↔ USD 속성 매핑을 설계하고 문서화한다
- 매핑이 실제 씬과 맞는지 자동으로 검증한다
- 임계치에 **방향**과 **범위**가 왜 필요한지 안다

---

## 계약서가 없으면 아무것도 못 합니다

씬은 있고 데이터도 있는데, 둘을 잇는 표가 없으면
현장 태그 `LINE1_CV01_TEMP` 가 씬의 어느 속성인지 아무도 모릅니다.

이 표가 **데이터 담당자와 씬 담당자 사이의 계약**입니다.
계약이 있으면 서로를 기다리지 않고 각자 일할 수 있습니다.

```yaml
tags:
  conveyor_01.motor_temp:
    prim: /World/Line01/Conveyor_A
    attr: telemetry:motorTemp
    type: float
    unit: "°C"
    range: [20.0, 90.0]
    warn: 70.0

  inspection.pass_rate:
    prim: /World/Line01/InspectionStation
    attr: telemetry:passRate
    type: float
    unit: "%"
    range: [80.0, 100.0]
    warn: 92.0
    warn_when: below     # ← 통과율은 떨어지는 쪽이 이상
```

## 필드마다 이유가 있습니다

| 필드 | 없으면 생기는 일 |
|---|---|
| `prim` / `attr` | 데이터가 어디에 꽂히는지 아무도 모름 |
| `type` | 정수 태그에 실수가 들어가 조용히 잘림 |
| `range` | 색상 매핑이 한쪽에 붙어 변화가 안 보임 |
| `warn` | 이상을 자동으로 못 잡음 |
| **`warn_when`** | **정상 운전이 전부 경고로 잡힘** |

### `warn_when` — 태그마다 나쁜 방향이 다릅니다 ★

- 모터 온도 — **높으면** 이상
- 통과율 — **낮으면** 이상

!!! danger "이걸 빠뜨리면 어떻게 되나"
    전부 `value >= warn` 으로 판정하면, 정상 운전 중인 통과율 **99% 가
    전부 경고로 잡힙니다.**

    이 교재를 만들 때 처음에 실제로 그렇게 됐습니다.
    경고 3,849건 중 대부분이 정상 데이터였습니다.

### `range` — 색상 매핑의 기준

| 범위를 | 결과 |
|---|---|
| 너무 좁게 | 값이 항상 최댓값에 붙어 색이 안 변함 |
| 너무 넓게 | 변화가 눈에 안 보임 |

**실제 운전 데이터의 최소·최대를 보고 정해야 합니다.**
공용 씬의 `line.cycle_time` 은 고장 시 26초까지 오르므로 상한을 30 으로 잡았습니다.

---

## 검증 1 — 계약이 씬과 맞는가

사람이 손으로 쓴 표는 **반드시** 틀립니다.

```python
def validate_mapping(stage, tags):
    problems = []
    for name, spec in tags.items():
        prim = stage.GetPrimAtPath(spec["prim"])
        if not prim or not prim.IsValid():
            problems.append(f"[프림없음] {name} → {spec['prim']}")
            continue
        attr = prim.GetAttribute(spec["attr"])
        if not attr:
            problems.append(f"[속성없음] {name} → {spec['attr']}")
        elif attr.GetTypeName() != USD_TYPE[spec["type"]]:
            problems.append(f"[타입불일치] {name}")
    return problems
```

## 검증 2 — 계약 자체가 말이 되는가

```python
def validate_schema(tags):
    problems, seen = [], {}
    for name, spec in tags.items():
        lo, hi = spec["range"]
        if lo >= hi:
            problems.append(f"[범위역전] {name}")

        warn = spec.get("warn")
        if warn is not None and not (lo <= warn <= hi):
            problems.append(f"[임계범위밖] {name} — 있으나 마나 한 임계")

        # 비율성 태그인데 방향이 없으면 의심
        if warn is not None and "warn_when" not in spec:
            if any(k in name for k in ("rate", "ratio", "yield")):
                problems.append(f"[방향의심] {name}")

        key = (spec["prim"], spec["attr"])
        if key in seen:
            problems.append(f"[중복매핑] {name} 과 {seen[key]}")
        seen[key] = name
    return problems
```

## 검증기를 검증하세요

일부러 망가뜨린 표로 시험합니다. 어제 7H 와 같은 원칙입니다.

```
[방향의심]   line.ok_ratio — 비율성 태그인데 warn_when 이 없음
[범위역전]   conveyor_01.speed — range=[1.0, 0.0]
[중복매핑]   conveyor_01.spd 과 conveyor_01.speed 가 같은 속성을 가리킴
[임계범위밖] buffer.level — warn=80, range=[0, 50]
```

---

## 실습 과제

**`TODO(basic)`** — 과제 #1 에서 정한 태그 5개를 `tags.yaml` 형식으로 쓰고
`validate_schema()` 를 통과시키세요.
**낮을수록 나쁜 태그를 하나 이상** 포함해야 합니다.

**`TODO(advanced)`** — 검증 규칙 3개를 추가하세요.

1. **단위 누락** — `unit` 이 없는 태그 경고
2. **경고 여유** — `warn` 이 `range` 양 끝 5% 이내에 붙어 있으면
   "경보가 거의 안 뜨거나 항상 뜬다" 고 보고
3. **명명 규칙** — `설비.항목` 형태인지 검사

결과를 **error / warning** 두 단계로 나눠 출력하세요.

!!! tip "이 과제가 오늘 오후를 좌우합니다"
    여기서 만든 태그 표를 15H 개인 작업에서 그대로 씁니다.
    지금 제대로 해 두면 훨씬 수월합니다.

---

!!! tip "다음 시간"
    [12H · 실시간 데이터 II](12-live-binding.md) — **트윈이 움직입니다.**
