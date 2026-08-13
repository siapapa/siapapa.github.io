---
title: 2H · 시뮬레이션 루프
---

# 2H · 시뮬레이션 루프

!!! warning "이 시간의 실습은 최종 검증 전입니다"

**실습 스크립트**: `course_b/day1/10_hello_isaacsim.py`

## 학습 목표

- `SimulationApp` · `World` · `reset()` 의 역할을 구분한다
- 물리 주기와 렌더 주기를 나누는 이유를 안다
- **왜 노트북이 아니라 스크립트인지** 안다

---

## 왜 노트북이 아닌가 ★

기초 과정에서는 노트북 위주였는데 여기서 규칙이 바뀝니다.

!!! danger "Isaac Sim 실습을 Jupyter 노트북으로 하지 마세요"
    `SimulationApp` 은 **프로세스 시작 시점에** Kit 런타임을 띄웁니다.
    주피터 커널 안에서 만들면 커널 재시작·GPU 점유 문제로 사고가 납니다.

    **시뮬레이션은 스크립트, 결과 분석은 노트북.**

이 규칙에 따라 오늘 실습은 대부분 `.py` 이고, 8H 의 데이터 검수만 노트북입니다.

## 순서를 지켜야 합니다

```python
from _isaac_bootstrap import launch, report

session = launch(headless=False)    # ① 먼저 앱을 띄운다
api = session.api                   # ② 그 다음에야 isaacsim.* 를 쓸 수 있다
```

!!! warning "거꾸로 하면 실패합니다"
    `SimulationApp` 을 만들기 **전에** `isaacsim.*` 를 import 하면
    Kit 런타임이 아직 없어 실패합니다.
    부트스트랩이 이 순서를 강제하고 있습니다.

---

## World — 씬 + 물리 + 시간

```python
world = api.World(
    stage_units_in_meters=1.0,
    physics_dt=1.0 / 60.0,       # 물리 1스텝의 시간
    rendering_dt=1.0 / 60.0,     # 화면 1프레임의 시간
)
world.scene.add_default_ground_plane()
```

### 물리 주기와 렌더 주기를 나누는 이유

| | 잘게 하면 | 크게 하면 |
|---|---|---|
| **물리** | 정확하고 안정적 | 빠르지만 물체가 뚫고 지나가거나 폭발 |
| **렌더** | 부드럽지만 느림 | 빠르지만 뚝뚝 끊김 |

물리는 1/120, 렌더는 1/60 처럼 나누면 **정확도를 지키면서 속도를 법니다.**
학습할 때는 렌더를 아예 끄기도 합니다 (`--headless`).

## `reset()` 을 빼먹지 마세요 ★

```python
cube = world.scene.add(api.DynamicCuboid(
    prim_path="/World/FallingCube",
    position=np.array([0.0, 0.0, 2.0]),
))

world.reset()        # ← 물리 핸들 초기화
```

!!! danger "이걸 안 부르고 값을 읽으면 엉뚱한 결과가 나옵니다"
    물리 엔진이 아직 프림을 인식하지 못한 상태입니다.
    큐브가 떨어지지 않거나, 위치가 초기값 그대로 나옵니다.

---

## 실습 · 낙하 시뮬레이션

```bash
./python.sh 10_hello_isaacsim.py
```

```
── 낙하 시뮬레이션 ──
    스텝    시간(s)    높이(m)
     0     0.000     2.000
    20     0.333     1.456
    40     0.667     0.323
    60     1.000     0.150
   119     1.983     0.150

최종 높이 0.150 m — 바닥 근처에서 멈췄으면 정상입니다.
```

| 결과 | 판정 |
|---|---|
| 높이가 0.15 근처에서 멈춤 | ✅ 정상 |
| 높이가 2.0 그대로 | `world.reset()` 누락 |
| 값이 `nan` | `physics_dt` 가 너무 큼 |

## 공용 씬 불러오기

```python
api.add_reference_to_stage(str(SCENE), "/World/Factory")
world.reset()
```

기초 과정에서 만든 `SmartFactory-01` 이 그대로 올라옵니다.
오늘 이 씬 위에 로봇을 얹습니다.

---

## 반드시 닫으세요

```python
finally:
    session.close()
```

!!! warning "안 닫으면 프로세스가 남습니다"
    다음 실행 때 GPU 를 못 잡아 "이미 사용 중" 오류가 납니다.
    실습 스크립트는 전부 `try/finally` 로 감싸 두었습니다.

## 정리

| 항목 | 핵심 |
|---|---|
| **순서** | SimulationApp → isaacsim.* import |
| **World** | 씬 + 물리 + 타임스텝 |
| **`reset()`** | 물리 핸들 초기화. 빼먹으면 값이 엉뚱함 |
| **dt 분리** | 물리는 잘게, 렌더는 성기게 |
| **`close()`** | 안 하면 프로세스가 남음 |

---

!!! tip "다음 시간"
    [3H · 로봇 임포트](03-robot-import.md) — URDF 가 담는 것과 **담지 않는 것**.
