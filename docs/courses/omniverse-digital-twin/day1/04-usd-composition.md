---
title: 4H · OpenUSD II — Composition
---

# 4H · OpenUSD II — 파일을 여러 장으로 나누기

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day1/01_usd_composition.ipynb` · **GPU 불필요**

## 학습 목표

- subLayer 로 파일을 겹치고, 어느 쪽이 이기는지 판단한다
- reference 로 같은 설비를 여러 번 재사용한다
- payload 로 무거운 설비를 필요할 때만 불러온다
- variantSet 으로 배치안을 전환한다

---

## 왜 나누는가

!!! question "배치를 바꾸는 사람, 물리를 튜닝하는 사람, 실시간 데이터를 쓰는 시스템이 전부 다릅니다. 한 파일을 같이 쓰면 어떻게 됩니까?"
    서로 덮어씁니다. 그리고 데이터가 잘못 들어오면 배치까지 망가집니다.

`SmartFactory-01` 은 3장으로 나뉘어 있습니다.

```
smartfactory01.usda          루트 — subLayers 로 아래 3장을 합성
└─ layers/
   ├─ live.usda     (강함)   실시간 데이터가 기록되는 곳
   ├─ physics.usda           물리 속성을 over 로 덧씌움
   └─ layout.usda   (약함)   배치·형상
```

**`subLayers` 는 앞이 강합니다.** 데이터가 잘못 들어와도 배치·물리 레이어는
그대로이므로 씬 자체가 망가지지 않습니다.

!!! tip "설비 담당자를 위한 비유"
    **subLayer** = 도면 위에 올리는 트레이싱지
    **reference** = 표준 부품 도면 불러쓰기
    **variant** = 같은 라인의 배치 대안

---

## 1. 누가 이겼는지 추적하기

같은 속성을 여러 레이어가 정의하면 강한 쪽이 이깁니다.
**어느 파일의 의견이 채택됐는지** 볼 수 있어야 디버깅이 됩니다.

```python
prim = stage.GetPrimAtPath("/World/Line01/Conveyor_A")

for spec in prim.GetPrimStack():
    print(Path(spec.layer.identifier).name, spec.path)

attr = prim.GetAttribute("telemetry:motorTemp")
for spec in attr.GetPropertyStack(Usd.TimeCode.Default()):
    print(Path(spec.layer.identifier).name, "=", spec.default)
```

!!! question "값을 바꿨는데 반영이 안 돼요"
    **더 강한 레이어가 이기고 있는 것**입니다.
    위 코드로 누가 이겼는지 확인하세요. Day 2 에서 가장 많이 나오는 질문입니다.

## 2. EditTarget — 어느 레이어에 쓸 것인가 ★

정하지 않으면 **루트 레이어**에 기록됩니다. 그러면 레이어를 나눈 의미가 없어집니다.

```python
live_layer = Sdf.Layer.FindOrOpen("layers/live.usda")

stage.SetEditTarget(Usd.EditTarget(live_layer))   # 이제 live 에 기록됩니다
prim.GetAttribute("telemetry:motorTemp").Set(51.5)

stage.SetEditTarget(Usd.EditTarget(stage.GetRootLayer()))   # 되돌리기
```

!!! warning "Day 2 에서 가장 많이 틀리는 지점입니다"
    EditTarget 을 되돌리지 않으면 이후 작업이 계속 데이터 레이어에 기록되어,
    배치 수정이 엉뚱한 파일에 들어갑니다.

## 3. reference — 표준 부품 불러쓰기

같은 설비를 여러 대 놓을 때 형상을 복사하면, 나중에 고칠 때 전부 고쳐야 합니다.
**reference 는 원본 파일을 가리키기만** 합니다.

```python
for i in range(3):
    slot = UsdGeom.Xform.Define(line, f"/Line/Roller_{i:02d}")
    slot.GetPrim().GetReferences().AddReference("./roller_unit.usda", "/RollerUnit")
    UsdGeom.Xformable(slot).AddTranslateOp().Set(Gf.Vec3d(i * 1.0, 0, 0.5))
```

원본의 반지름을 바꾸면 **세 개가 동시에** 바뀝니다.

!!! note "참조할 프림 경로를 명시하세요"
    두 번째 인자(`"/RollerUnit"`)를 생략하면 대상 파일의 `defaultPrim` 을 씁니다.
    파일에 최상위 프림이 여러 개면 명시가 필수이고, 명시해 두면 원본 구조가
    바뀌어도 덜 깨집니다.

## 4. payload — 무거운 것은 나중에

reference 는 열 때 **항상** 읽습니다. 설비 하나가 수백 MB 라면 씬을 여는 것조차 느려집니다.
**payload 는 필요할 때만** 읽습니다.

```python
slot.GetPrim().GetPayloads().AddPayload("./heavy_machine.usda", "/Machine")

light = Usd.Stage.Open(path, load=Usd.Stage.LoadNone)   # 껍데기만
full  = Usd.Stage.Open(path, load=Usd.Stage.LoadAll)    # 전부
```

!!! quote "실무 규칙"
    씬 구조는 **reference**, 무거운 형상은 **payload**.
    레이아웃 검토 회의에서는 payload 를 꺼 두고 배치만 봅니다.

## 5. variantSet — 배치안 전환

같은 라인의 대안을 하나의 파일에 담고 스위치로 전환합니다.
공용 씬의 버퍼에 이미 들어 있습니다.

```python
vset = buffer.GetVariantSets().GetVariantSet("capacity")
print(vset.GetVariantNames())        # ['large', 'small']
vset.SetVariantSelection("large")
```

---

## 실습 과제

**`TODO(basic)`** — 롤러를 6개로 늘리고 간격을 `0.8m` 로 바꾸세요.
그리고 원본의 `radius` 를 바꾼 뒤, **라인 파일은 건드리지 않고**
6개가 모두 굵어지는지 확인하세요.

**`TODO(advanced)`** — `/Line` 에 `layout` variantSet 을 만들고
`straight` / `L_shape` 두 배치안을 담으세요.
각 variant 선택 시 월드 좌표가 실제로 달라지는지 확인하세요.

## 정리

| 장치 | 언제 | 한 줄 |
|---|---|---|
| **subLayer** | 역할이 다른 사람들이 같은 씬을 다룰 때 | 트레이싱지 겹치기. **앞이 강함** |
| **reference** | 같은 부품을 여러 번 놓을 때 | 원본을 고치면 전부 반영 |
| **payload** | 형상이 무거울 때 | 필요할 때만 로드 |
| **variantSet** | 대안을 비교할 때 | 스위치로 전환 |
| **EditTarget** | 어느 레이어에 쓸지 | **안 정하면 루트에 기록됨** |

---

!!! tip "다음 시간"
    [5H · Kit 앱 셋업](05-kit-setup.md) — 지금까지 만든 것을 **눈으로** 봅니다.
