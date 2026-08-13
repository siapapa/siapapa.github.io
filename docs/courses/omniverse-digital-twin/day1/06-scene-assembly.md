---
title: 6H · 씬 조립
---

# 6H · 씬 조립 — 에셋 · 머티리얼 · 조명 · 카메라

<div class="lab-link" data-course="omniverse-digital-twin"></div>

**실습 노트북**: `course_a/day1/02_asset_import.ipynb`

## 학습 목표

- 외부 3D/CAD 파일을 붙이는 방법과 **단위 함정**을 안다
- 머티리얼로 상태를 색으로 구분한다
- 조명과 카메라를 배치한다
- 경계상자로 배치가 겹치는지 검증한다

---

## 1. 단위 함정 — 가장 많이 터집니다 ★

CAD 는 대개 **밀리미터**, 우리 씬은 **미터**입니다.
그대로 붙이면 설비가 **1000배**로 커집니다.

!!! danger "화면에 아무것도 안 보이거나 회색 벽만 보이면"
    거의 항상 이 문제입니다. 설비가 너무 커서 카메라가 그 안에 들어가 있는 것입니다.

```python
src_mpu = UsdGeom.GetStageMetersPerUnit(cad_stage)   # 0.001 (mm)
dst_mpu = 1.0                                        # 우리 씬 (m)
factor = src_mpu / dst_mpu                           # 0.001

slot = UsdGeom.Xform.Define(scene, "/World/ImportedPart")
slot.GetPrim().GetReferences().AddReference("./cad_part_mm.usda", "/Part")

UsdGeom.Xformable(slot).AddScaleOp().Set(Gf.Vec3f(factor, factor, factor))
UsdGeom.Xformable(slot).AddTranslateOp().Set(Gf.Vec3d(0, 3, 0.4))
```

!!! warning "xformOp 순서에 주의"
    위에서 **scale 을 먼저, translate 를 나중에** 추가했습니다.
    USD 는 추가한 순서대로 적용하므로 이동량까지 배율이 곱해지지 않습니다.

    순서를 바꾸면 부품이 엉뚱한 곳으로 날아갑니다. 직접 바꿔서 확인해 보세요.

### 보정이 맞았는지 숫자로 확인

```python
bound = UsdGeom.Imageable(slot.GetPrim()).ComputeWorldBound(
    Usd.TimeCode.Default(), UsdGeom.Tokens.default_
)
print(tuple(round(v, 3) for v in bound.ComputeAlignedBox().GetSize()))
# (0.8, 0.8, 0.8)  ← 800mm 부품이 0.8m 로 들어왔다
```

## 2. 머티리얼 — 색은 정보입니다

디지털트윈에서 색은 장식이 아닙니다. **운전원이 화면을 3초 봤을 때
"저기가 문제"를 알아채야** 합니다.

```python
def make_material(stage, path, rgb):
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgb))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material

STATUS_COLORS = {
    "normal":  (0.20, 0.65, 0.30),   # 초록
    "warning": (0.95, 0.65, 0.10),   # 주황
    "fault":   (0.85, 0.20, 0.20),   # 빨강
}
```

3색이면 충분합니다. 더 늘리지 마세요.

!!! warning "바인딩 전에 API 를 적용하세요"
    ```python
    binding = UsdShade.MaterialBindingAPI.Apply(prim)   # ← 이걸 빼먹으면
    binding.Bind(material)
    ```

    `Apply()` 없이 `Bind()` 만 하면 바인딩은 되지만 USD 가 경고를 냅니다.

    ```
    Found material bindings on prim ... but MaterialBindingAPI is not applied
    ```

## 3. 조명

**조명이 없으면 RTX 렌더러에서 새까맣게 나옵니다.**
실내 설비 씬은 **돔 라이트(전역) + 사각 라이트(국부)** 조합으로 시작합니다.

```python
dome = UsdLux.DomeLight.Define(scene, "/World/Lights/Dome")
dome.CreateIntensityAttr(500.0)

panel = UsdLux.RectLight.Define(scene, "/World/Lights/Panel")
panel.CreateIntensityAttr(3000.0)
panel.CreateWidthAttr(4.0)
panel.CreateHeightAttr(2.0)
UsdGeom.Xformable(panel).AddTranslateOp().Set(Gf.Vec3d(0, 0, 4.0))
```

## 4. 카메라

검사 스테이션 카메라는 **다음 과정에서 합성 데이터를 찍는 자리**가 됩니다.
지금 제대로 배치해 두면 그대로 이어집니다.

```python
cam = UsdGeom.Camera.Define(scene, "/World/Cameras/Inspection")
cam.CreateFocalLengthAttr(24.0)
cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 100.0))

xf = UsdGeom.Xformable(cam)
xf.AddTranslateOp().Set(Gf.Vec3d(0.0, -2.5, 2.0))
xf.AddRotateXYZOp().Set(Gf.Vec3f(60.0, 0.0, 0.0))
```

## 5. 배치 검증 — 겹치면 물리가 터집니다

눈으로는 괜찮아 보여도 설비가 서로 파고들어 있으면,
내일 물리 시뮬레이션에서 물체가 튕겨 날아갑니다. **숫자로 확인**하세요.

```python
bodies = [p for p in stage.Traverse() if p.GetName() == "Body"]

for a in bodies:
    box = world_box(a)
    lo, hi = box.GetMin(), box.GetMax()
    print(f"{a.GetParent().GetName():<20} "
          f"x[{lo[0]:6.2f},{hi[0]:6.2f}] z[{lo[2]:6.2f},{hi[2]:6.2f}]")
```

공용 씬에서는 겹침이 없어야 정상입니다.

---

## 실습 과제

**`TODO(basic)`** — 검사 스테이션용 사각 라이트를 추가하세요.
위치 `(0, 0, 2.5)`, 크기 `1.5 × 1.5`, 밝기 `5000`.

**`TODO(advanced)`** — 각 컨베이어의 `telemetry:motorTemp` 를 읽어
임계치에 따라 머티리얼을 **자동 바인딩**하는 함수를 쓰세요.
임계값은 `sim_data/tags.yaml` 에서 읽고 하드코딩하지 마세요.
편집은 **반드시 별도 레이어**에 하세요.

## 정리

| 항목 | 핵심 |
|---|---|
| **단위 보정** | CAD 는 mm, 씬은 m. `metersPerUnit` 비율을 스케일로 |
| **xformOp 순서** | scale → translate 순서 주의 |
| **머티리얼** | 색은 장식이 아니라 상태 정보 |
| **조명** | 없으면 새까맣게 나옴 |
| **경계상자** | 겹치면 물리가 터짐. 숫자로 검증 |

---

!!! tip "다음 시간"
    [7H · Python 스크립팅](07-scripting.md) — 설비 100대를 코드로 배치하고,
    사람 실수를 자동으로 잡습니다. **GPU 없이 진행합니다.**
