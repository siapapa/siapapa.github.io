---
title: 7H · Python 스크립팅
---

# 7H · Python 스크립팅 — 자동화와 검증

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day1/03_scene_scripting.ipynb` · **GPU 불필요**

## 학습 목표

- 씬을 순회하며 원하는 프림을 조건으로 찾는다
- 설비를 반복 배치하는 코드를 쓴다
- 씬이 규칙을 지키는지 **자동으로 검증**한다

---

## 1. 순회와 검색

`Traverse()` 는 씬 전체를 훑습니다. 여기에 조건을 걸어 원하는 것만 고릅니다.

```python
# 타입으로 찾기
cubes = [p for p in stage.Traverse() if p.IsA(UsdGeom.Cube)]

# 속성 네임스페이스로 찾기 — 3H 에서 붙인 telemetry: 규칙이 여기서 쓰입니다
def telemetry_tags(prim):
    return [a.GetName() for a in prim.GetAttributes()
            if a.GetName().startswith("telemetry:")]

for prim in stage.Traverse():
    tags = telemetry_tags(prim)
    if tags:
        print(prim.GetPath())
        for t in tags:
            print(f"    {t} = {prim.GetAttribute(t).Get()}")
```

!!! warning "`Traverse()` 는 정의된 프림만 훑습니다"
    `over` 로만 이루어진 레이어(물리·시각화)를 열면 **아무것도 안 나옵니다.**
    그럴 때는 `TraverseAll()` 을 쓰세요. 내일 물리 레이어에서 바로 만나게 됩니다.

## 2. 반복 배치 자동화

버퍼 구역에 파레트를 격자로 깝니다. 손으로는 못 할 일입니다.

```python
ROWS, COLS = 4, 6
PITCH_X, PITCH_Y = 1.2, 1.0
ORIGIN = Gf.Vec3d(6.0, -2.5, 0.075)

for r in range(ROWS):
    for c in range(COLS):
        idx = r * COLS + c
        pallet = UsdGeom.Cube.Define(stage, f"/World/Buffer/Pallet_{idx:03d}")
        pallet.CreateSizeAttr(1.0)
        xf = UsdGeom.Xformable(pallet)
        xf.AddTranslateOp().Set(ORIGIN + Gf.Vec3d(c * PITCH_X, r * PITCH_Y, 0))
        xf.AddScaleOp().Set(Gf.Vec3f(1.1, 0.9, 0.15))
        pallet.GetPrim().CreateAttribute(
            "inventory:occupied", Sdf.ValueTypeNames.Bool, custom=True
        ).Set(idx % 3 != 0)
```

파레트 24개가 코드 10줄로 배치됩니다. 간격을 바꾸려면 숫자 하나만 고치면 됩니다.

## 3. 씬 검증기 ★

**사람이 만든 씬에는 반드시 실수가 있습니다.**
디지털트윈이 커지면 규칙을 코드로 박아 두고 자동으로 검사해야 합니다.

여기서는 네 가지를 봅니다.

1. 단위·업축이 우리 규약(m, Z-up)인가
2. 명명 규칙을 지키는가
3. `tags.yaml` 에 선언한 태그가 씬에 실제로 있는가
4. 형상 프림에 부모 Xform 이 있는가 (배치 변경이 가능한 구조인가)

```python
def validate(stage, tags_path):
    issues = []

    mpu = UsdGeom.GetStageMetersPerUnit(stage)
    if abs(mpu - 1.0) > 1e-9:
        issues.append(f"[단위] metersPerUnit={mpu} — 1.0(m) 이어야 함")

    if UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z:
        issues.append("[업축] Z 이어야 함")

    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Cube) and prim.GetName() != "Body":
            issues.append(f"[명명] {prim.GetPath()} — 형상은 'Body' 로 통일")
        if " " in prim.GetName():
            issues.append(f"[명명] {prim.GetPath()} — 이름에 공백 금지")

    tags = yaml.safe_load(open(tags_path, encoding="utf-8"))["tags"]
    for tag, spec in tags.items():
        prim = stage.GetPrimAtPath(spec["prim"])
        if not prim or not prim.IsValid():
            issues.append(f"[태그] {tag} — 프림 없음: {spec['prim']}")
        elif not prim.GetAttribute(spec["attr"]):
            issues.append(f"[태그] {tag} — 속성 없음: {spec['attr']}")

    return issues
```

## 4. 검증기를 검증하세요 ★

**검증기가 실제로 잡는지 확인해야 믿을 수 있습니다.**
공용 씬은 건드리지 말고 **사본에 일부러 문제를 심습니다.**

```python
broken = new_stage("broken.usda", meters_per_unit=0.01,   # 잘못된 단위 (cm)
                   up_axis=UsdGeom.Tokens.y)              # 잘못된 업축
bad = UsdGeom.Cube.Define(broken, "/World/Machine")       # 이름이 'Body' 가 아님

for issue in validate(broken, tags_path):
    print(issue)
```

```
[단위] metersPerUnit=0.01 — 1.0(m) 이어야 함
[업축] Z 이어야 함
[명명] /World/Machine — 형상은 'Body' 로 통일
[태그] conveyor_01.speed — 프림 없음: /World/Line01/Conveyor_A
```

!!! quote "이 감각을 가져가세요"
    **검증기를 믿으려면 검증기를 검증해야 합니다.**
    통과만 확인하고 넘어가면, 정작 문제가 생겼을 때 검증기가 조용히
    아무것도 못 잡고 있었다는 걸 나중에 알게 됩니다.

---

## 실습 과제

**`TODO(basic)`** — 파레트 적재율 리포트를 출력하세요.
전체 수 · 적재된 수 · 적재율(%), 그리고 행(row)별 적재 수.

**`TODO(advanced)`** — `validate()` 에 규칙 두 개를 더하세요.

1. **원점 이탈** — 모든 형상이 `x∈[-20,20], y∈[-15,15], z≥0` 안에 있을 것.
   바닥 아래로 내려간 설비를 잡는 규칙입니다.
2. **태그 범위** — `tags.yaml` 의 `range` 를 벗어난 현재 값 보고

그리고 결과를 **심각도(error/warning)** 로 나눠 출력하세요.

!!! tip "엔지니어 수강생에게"
    코드를 짜는 것보다 **어떤 규칙이 현장에서 필요한지** 생각해 보세요.
    "이 설비는 반드시 저 설비보다 상류에 있어야 한다" 같은 도메인 규칙이
    개발자는 떠올리지 못하는 것들입니다.

## 정리

| 항목 | 핵심 |
|---|---|
| **Traverse** | 타입·속성·이름으로 필터. `over` 는 `TraverseAll()` |
| **네임스페이스** | `telemetry:` 접두어로 관련 속성을 한 번에 수집 |
| **반복 배치** | 격자·배열은 코드로. 손으로 하면 반드시 틀림 |
| **검증기** | 규칙을 코드로 박아 두면 사람 실수를 자동으로 잡음 |
| **검증기 검증** | 일부러 망가뜨려 잡히는지 확인 |

---

!!! tip "다음 시간"
    [8H · 프로젝트 브리핑](08-project-briefing.md) — 과제 #1 을 받습니다.
