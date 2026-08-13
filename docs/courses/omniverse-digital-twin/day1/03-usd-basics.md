---
title: 3H · OpenUSD I — 씬은 파일이다
---

# 3H · OpenUSD I — 씬은 파일이다

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day1/00_usd_basics.ipynb` · **GPU 불필요**

## 학습 목표

- Stage · Prim · Attribute 가 각각 무엇인지 말할 수 있다
- Python 으로 프림을 만들고 위치·크기를 줄 수 있다
- `.usda` 텍스트를 읽고 무엇이 적혀 있는지 이해한다
- 단위와 업축을 **왜 먼저** 정해야 하는지 안다

!!! tip "설비 담당자를 위한 비유"
    **Stage** = 도면 한 벌 · **Prim** = 도면에 있는 개별 설비 · **Attribute** = 설비의 사양란

---

## 1. Stage — 열려 있는 씬

Stage 는 파일 하나로 저장됩니다. **가장 먼저 할 일은 단위와 업축을 정하는 것**입니다.
나중에 바꾸면 이미 배치한 모든 것의 위치가 어긋납니다.

우리는 **미터 · Z-up** 을 씁니다. Isaac Sim 이 그렇게 쓰기 때문에,
다음 과정으로 넘어갈 때 그대로 이어집니다.

```python
from pxr import Usd, UsdGeom, Gf, Sdf

stage = Usd.Stage.CreateNew("my_first.usda")
UsdGeom.SetStageMetersPerUnit(stage, 1.0)          # 1 단위 = 1 미터
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)    # 위쪽은 +Z
stage.GetRootLayer().Save()
```

!!! danger "셀을 다시 실행하면 죽습니다"
    `Usd.Stage.CreateNew` 를 **같은 커널에서 두 번** 호출하면 이렇게 됩니다.

    ```
    Tf.ErrorException: A layer already exists with identifier '...'
    ```

    파일이 아니라 **메모리에 열려 있는 레이어**와 충돌하는 것이라
    **파일을 지워도 해결되지 않습니다.** 커널을 재시작하면 사라지기 때문에
    원인을 찾기가 특히 어렵습니다.

    노트북에는 재실행해도 안전한 `new_stage()` 헬퍼가 준비되어 있습니다.

## 2. Prim — 씬 안의 물건

Prim 은 계층 경로를 가집니다. **경로가 곧 이름이자 주소**입니다.

```python
world = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(world.GetPrim())

UsdGeom.Xform.Define(stage, "/World/Line01")          # 자리만 차지하는 그룹

belt = UsdGeom.Cube.Define(stage, "/World/Line01/Conveyor_A")
belt.CreateSizeAttr(1.0)                              # 한 변 1m 단위 큐브
```

| 타입 | 무엇 |
|---|---|
| `Xform` | 형상이 없는 그룹. 위치만 가짐 |
| `Cube` · `Cylinder` · `Plane` | 실제로 보이는 형상 |

## 3. 위치와 크기 — xformOp

USD 는 이동·회전·크기를 **연산 목록**으로 관리합니다.
**추가한 순서대로 적용**되므로 순서가 바뀌면 결과가 달라집니다.

```python
xform = UsdGeom.Xformable(belt.GetPrim())
xform.AddTranslateOp().Set(Gf.Vec3d(-4.0, 0.0, 0.5))   # x=-4m, 높이 0.5m
xform.AddScaleOp().Set(Gf.Vec3f(6.0, 0.8, 0.1))        # 6m × 0.8m × 0.1m
```

## 4. Attribute — 설비의 사양란

형상만으로는 디지털트윈이 되지 않습니다. **속성**이 붙어야 합니다.
USD 에 없는 우리만의 속성은 `custom=True` 로 만듭니다.

```python
speed = belt.GetPrim().CreateAttribute(
    "telemetry:speed", Sdf.ValueTypeNames.Float, custom=True
)
speed.Set(0.6)
```

!!! note "`telemetry:` 접두어를 붙이는 이유"
    네임스페이스를 붙여 두면 나중에 **한 번에 찾아낼 수** 있습니다.

    ```python
    tags = [a for a in prim.GetAttributes()
            if a.GetName().startswith("telemetry:")]
    ```

    7H 의 자동화와 Day 2 의 데이터 연동이 이 규칙 위에서 돌아갑니다.

## 5. 만든 파일을 직접 열어보기 ★

**이 시간의 핵심입니다.** `.usda` 는 텍스트입니다. 열어서 읽으세요.

```python
print(open("my_first.usda", encoding="utf-8").read())
```

```usda
#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "World"
{
    def Xform "Line01"
    {
        def Cube "Conveyor_A"
        {
            float3 xformOp:translate = (-4, 0, 0.5)
            float3 xformOp:scale = (6, 0.8, 0.1)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            custom float telemetry:speed = 0.6
        }
    }
}
```

읽는 법:

- `(...)` 안 = **메타데이터** (단위 · 업축 · 기본 프림)
- `def Xform "World"` — `def` 는 "여기서 정의한다", `Xform` 은 타입, `"World"` 는 이름
- `uniform token[] xformOpOrder = [...]` — **연산 적용 순서**

!!! quote "문제가 생겼을 때"
    GUI 만 쳐다보는 사람과 파일을 열어보는 사람의 차이가 여기서 갈립니다.

## 6. 시간에 따라 변하는 값

디지털트윈의 값은 시간에 따라 변합니다. USD 는 이를 **타임샘플**로 저장합니다.

```python
for frame in range(6):
    temp.Set(48.0 + frame * 4.5, Usd.TimeCode(frame))

stage.SetStartTimeCode(0)
stage.SetEndTimeCode(5)
stage.SetTimeCodesPerSecond(1.0)     # 1프레임 = 1초
```

!!! danger "`timeCodesPerSecond` 를 반드시 명시하세요"
    기본값은 **24** 입니다. 레이어마다 이 값이 다르면 USD 가 그 비율만큼
    타임샘플을 자동으로 늘리거나 줄여서, **에러 없이 엉뚱한 값**이 나옵니다.

    루트가 24 이고 데이터 레이어가 1 이면, 프레임 3700 을 물었을 때
    실제로는 154초 지점이 읽힙니다. 그럴듯한 값이 나오기 때문에
    가장 잡기 어려운 종류의 버그입니다.

---

## 실습 과제

**`TODO(basic)`** — 내 씬에 `Conveyor_B` 를 추가하세요.
위치 `x=+4`, 크기 `6 × 0.8 × 0.1`, `telemetry:speed = 0.6`.
저장한 뒤 `.usda` 를 다시 출력해 두 대가 보이는지 확인하세요.

**`TODO(advanced)`** — 검사 스테이션을 두 컨베이어 사이에 배치하고,
`ComputeWorldBound()` 로 월드 경계상자를 구해 **겹치지 않는지 숫자로** 확인하세요.
업축을 Y-up 으로 바꾸면 무엇이 깨지는지도 예상하고 확인해 보세요.

## 정리

| 개념 | 한 줄 |
|---|---|
| **Stage** | 열려 있는 씬. 파일 하나 |
| **Prim** | 씬 안의 물건. 경로가 곧 주소 |
| **Attribute** | 프림에 붙는 값. `custom=True` 로 우리만의 속성 |
| **xformOp** | 이동·회전·크기. **추가한 순서대로** 적용 |
| **TimeSample** | 시간에 따라 변하는 값. TCPS 를 꼭 명시 |

---

!!! tip "다음 시간"
    [4H · Composition](04-usd-composition.md) — 파일을 여러 장으로 나눕니다.
    **오늘의 승부처입니다.**
