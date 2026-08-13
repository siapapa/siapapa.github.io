---
title: 4H · 로봇 제어
---

# 4H · 로봇 제어 — 드라이브 게인

!!! warning "이 시간의 실습은 최종 검증 전입니다"

**실습 스크립트**: `course_b/day1/12_robot_control.py`

## 학습 목표

- 드라이브 게인이 무엇을 결정하는지 안다
- 관절 목표값을 주고 로봇을 움직인다
- 증상을 보고 게인을 조정한다

---

## 드라이브 게인 — 이것만은 이해하고 가세요 ★

관절에 "여기로 가라"고 목표 각도를 줘도, 실제로 가게 만드는 것은 **드라이브**입니다.

```
토크 = stiffness × (목표각 − 현재각) − damping × 현재각속도
       └── 끌어당기는 힘 ──┘         └── 브레이크 ──┘
```

| 증상 | 원인 | 조치 |
|---|---|---|
| 로봇이 **흐물흐물 주저앉음** | stiffness 너무 낮음 | 올린다 |
| 목표 근처에서 **진동** | damping 너무 낮음 | 올린다 |
| 반응이 **굼뜸** | damping 너무 높음 | 내린다 |
| 값이 **NaN 으로 폭발** | stiffness 과다 / dt 과다 | stiffness↓, physics_dt↓ |

!!! note "URDF 에는 이 값이 없습니다"
    3H 에서 로봇이 무너진 것이 이 때문입니다. 임포트 후 직접 넣어야 합니다.

```python
from pxr import UsdPhysics

for prim in Usd.PrimRange(root):
    if prim.IsA(UsdPhysics.RevoluteJoint):
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        drive.CreateTypeAttr("force")
        drive.CreateStiffnessAttr(1e5)
        drive.CreateDampingAttr(1e4)
```

!!! warning "`world.reset()` 전에 넣어야 합니다"
    물리 핸들이 초기화되는 시점에 반영되기 때문입니다.

---

## 비교 실행 ★

**숫자를 설명하지 말고 망가진 것을 보세요.**

```bash
./python.sh 12_robot_control.py                      # 기본 게인
./python.sh 12_robot_control.py --stiffness 1e3      # 낮은 게인
```

기본 게인:

```
   스텝    목표idx     오차(rad)
    100        0        0.0031
    200        1        0.0089
    300        2        0.0142
```

낮은 게인:

```
   스텝    목표idx     오차(rad)
    100        0        0.4820
   ⚠️  오차가 큽니다 — stiffness 를 올리거나 유지 스텝을 늘리세요.
```

!!! success "한 번 보면 평생 기억합니다"
    로봇이 목표 자세를 못 따라가고 처지는 것을 눈으로 보세요.
    게인이 무엇인지에 대한 설명 열 문장보다 낫습니다.

---

## 관절 제어

```python
robot = api.Articulation(prim_path="/World/Robot", name="robot")
world.scene.add(robot)
world.reset()                          # ← 초기화 후에야 관절 정보를 읽을 수 있습니다

print(robot.dof_names)                 # ['panda_joint1', ...]
print(robot.num_dof)                   # 9

target = robot.get_joint_positions().copy()
target[1] += 0.5
robot.set_joint_position_targets(target)
```

| 방식 | 무엇을 주나 | 언제 |
|---|---|---|
| **위치 제어** | 목표 각도 | 대부분의 경우 |
| 속도 제어 | 목표 각속도 | 연속 회전 (컨베이어 롤러) |
| 토크 제어 | 힘 | 접촉·순응 제어 |

수업에서는 **위치 제어**만 씁니다.

---

## 범위를 분명히 합니다

여기서는 **관절 목표를 직접** 줍니다.

!!! note "역기구학(손끝 위치 → 관절각)은 다루지 않습니다"
    "손끝을 저 좌표로 가져가라" 는 별도의 계산이 필요합니다.
    Day 2 의 커스텀 태스크에서 필요하면 다시 다룹니다.

    4H 로는 픽앤플레이스를 "제대로" 만들 수 없습니다.
    개념을 잡는 것이 목표입니다.

## 실습 과제

**`TODO(basic)`** — `--stiffness` 를 `1e3` · `1e4` · `1e5` · `1e6` 으로 바꿔
오차가 어떻게 변하는지 표로 정리하세요. **너무 크면 어떻게 되는지도** 확인하세요.

**`TODO(advanced)`** — 관절별로 게인을 다르게 주세요.
어깨처럼 큰 하중을 받는 관절과 손목은 필요한 게인이 다릅니다.

## 정리

| 항목 | 핵심 |
|---|---|
| **stiffness** | 목표로 끌어당기는 힘 |
| **damping** | 브레이크. 진동을 잡음 |
| **URDF 에 없음** | 임포트 후 직접 넣어야 함 |
| **`reset()` 전에** | 물리 초기화 시점에 반영 |

---

!!! tip "다음 시간"
    [5H · 카메라 센서](05-camera.md) — 로봇에게 눈을 답니다.
