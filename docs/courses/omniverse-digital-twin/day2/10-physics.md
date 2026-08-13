---
title: 10H · 물리 시뮬레이션
---

# 10H · 물리 시뮬레이션

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 스크립트**: `course_a/day2/04_physics.py`

## 학습 목표

- PhysX 의 세 요소를 구분해 쓴다
- 물리 속성을 **별도 레이어**에 저작한다
- 물리가 터졌을 때 어디를 보는지 안다

---

## PhysX 세 요소만 잡으면 됩니다

| 스키마 | 의미 | 안 붙이면 |
|---|---|---|
| **CollisionAPI** | 부딪히는 형상 | 서로 통과함 |
| **RigidBodyAPI** | 중력·힘을 받는 물체 | 공중에 떠 있음 |
| **MassAPI** | 질량 | 밀도로 자동 계산 (엉뚱할 수 있음) |

!!! danger "벨트에 RigidBodyAPI 를 붙이지 마세요"
    **벨트는 CollisionAPI 만, 박스는 둘 다.**

    벨트에 RigidBodyAPI 를 붙이면 벨트가 중력을 받아 **바닥으로 떨어집니다.**
    가장 흔한 실수입니다.

```python
# 벨트 — 움직이지 않는 벽
body = stage.OverridePrim("/World/Line01/Conveyor_A/Body")
UsdPhysics.CollisionAPI.Apply(body)

# 적재물 — 중력을 받는 물체
UsdPhysics.CollisionAPI.Apply(box.GetPrim())
UsdPhysics.RigidBodyAPI.Apply(box.GetPrim())
UsdPhysics.MassAPI.Apply(box.GetPrim()).CreateMassAttr(12.0)
```

## 물리 재질 — 미끄러짐과 튐

```python
material = UsdPhysics.MaterialAPI.Apply(prim)
material.CreateStaticFrictionAttr(0.9)     # 정지 마찰
material.CreateDynamicFrictionAttr(0.8)    # 운동 마찰
material.CreateRestitutionAttr(0.0)        # 반발 — 0 이면 안 튐
```

| 증상 | 조치 |
|---|---|
| 벨트 위 물건이 미끄러짐 | 마찰 ↑ |
| 물건이 통통 튐 | 반발(restitution) ↓ |

!!! warning "재질은 '바인딩' 만 합니다"
    `MaterialAPI` 는 **재질 프림 쪽**에 적용합니다.
    충돌체에는 관계로 연결만 하세요.

    ```python
    body.CreateRelationship("material:binding:physics").SetTargets([material_path])
    ```

## 조인트 — 회전하는 부품

```python
joint = UsdPhysics.RevoluteJoint.Define(stage, ".../DriveRoller/Hinge")
joint.CreateBody0Rel().SetTargets([Sdf.Path(".../Conveyor_A/Body")])
joint.CreateBody1Rel().SetTargets([roller.GetPath()])
joint.CreateAxisAttr(UsdGeom.Tokens.y)     # y 축 중심 회전
```

---

## 별도 레이어에 저작합니다

물리는 `layers/physics_lab.usda` 에만 씁니다.
**배치 레이어는 건드리지 않습니다** — 실습 중 망가뜨려도 복구가 쉽습니다.

```python
body = stage.OverridePrim("/World/Line01/Conveyor_A/Body")   # def 가 아니라 over
UsdPhysics.CollisionAPI.Apply(body)
```

!!! danger "결과가 비어 있으면 `TraverseAll()` 을 쓰세요"
    물리 레이어는 대부분 `over` 로 되어 있습니다.
    `Traverse()` 는 **정의된(def) 프림만** 훑기 때문에 아무것도 안 나옵니다.

    ```python
    for prim in stage.TraverseAll():        # ← Traverse() 가 아니라
        applied = [s for s in prim.GetAppliedSchemas() if "Physics" in s]
        if applied:
            print(prim.GetPath(), applied)
    ```

    "왜 빈 결과가 나오죠?" 로 가장 자주 막히는 지점입니다.

실행하면 이런 결과가 나옵니다.

```
/World/PhysicsMaterials/Belt          <Scope>     PhysicsMaterialAPI
/World/Line01/Conveyor_A/Body         <over>      PhysicsCollisionAPI
/World/Line01/Conveyor_A/DriveRoller  <Cylinder>  PhysicsCollisionAPI, PhysicsRigidBodyAPI
/World/Line01/Cargo/Box_00            <Cube>      PhysicsCollisionAPI, PhysicsRigidBodyAPI, PhysicsMassAPI
```

---

## Kit 에서 확인

1. `smartfactory01.usda` 를 열고 `physics_lab.usda` 를 subLayer 로 추가
2. 재생(Play)

| 결과 | 판정 |
|---|---|
| 박스가 벨트 위로 떨어져 **멈춤** | ✅ 성공 |
| 벨트를 **뚫고 지나감** | 충돌체 누락 또는 스케일 문제 |
| **통통 튐** | restitution 을 낮출 것 |
| **벨트가 바닥으로 떨어짐** | 벨트에 RigidBodyAPI 를 잘못 붙임 |

!!! note "컨베이어가 물건을 실어 나르는 동작은 여기까지가 아닙니다"
    표준 USD 스키마에는 벨트 이송이 없습니다. PhysX 전용 표면 속도나
    별도 익스텐션이 필요하며 Kit 안에서만 설정됩니다.

    오늘은 **"벨트 위에 놓이고 안 미끄러지는"** 데까지가 목표입니다.

---

## 실습 과제

**`TODO(basic)`** — 박스를 3개 더 추가하고 질량을 다르게 주세요.
무거운 것과 가벼운 것이 어떻게 다르게 움직이는지 관찰하세요.

**`TODO(advanced)`** — 버퍼에 파레트를 쌓고, 아래 것을 빼면
위 것이 무너지도록 만드세요. 안정성이 무너지면 `physics_dt` 를 줄여 보세요.

## 정리

| 항목 | 핵심 |
|---|---|
| **벨트** | CollisionAPI 만 |
| **적재물** | Collision + RigidBody + Mass |
| **재질** | 재질 프림에 API, 충돌체에는 바인딩 |
| **별도 레이어** | 배치를 건드리지 않는다 |
| **`TraverseAll()`** | `over` 프림을 보려면 필수 |

---

!!! tip "다음 시간"
    [11H · 실시간 데이터 I](11-data-schema.md) — 데이터와 씬을 잇는 계약서.
