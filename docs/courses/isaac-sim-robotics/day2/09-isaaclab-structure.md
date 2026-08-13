---
title: 9H · Isaac Lab 구조
---

# 9H · Isaac Lab 구조

!!! warning "이 시간의 실습은 최종 검증 전입니다"

**실습 스크립트**: `course_b/day2/18_isaaclab_check.py`

## 학습 목표

- 우리가 손댈 것과 라이브러리가 해 주는 것을 구분한다
- Manager-based 와 Direct 방식의 차이를 안다

---

## 우리가 쓰는 건 환경 파일 하나뿐입니다 ★

```
환경(Env) ──관측──▶ 정책(Policy) ──행동──▶ 환경
    │                                      │
    └──────── 보상 · 종료 ──────────────────┘
                    │
                러너(Runner) — 경험을 모아 정책 갱신
```

| 무엇 | 누가 |
|---|---|
| **환경** | **우리가 정의합니다** (10~12H) |
| 정책·러너 | RSL-RL 이 제공 (13H 에서 호출만) |

!!! success "강화학습을 다 만들어야 하나요?"
    아닙니다. **환경 파일 하나**만 쓰면 됩니다.
    PPO 알고리즘도, 신경망도, 학습 루프도 라이브러리가 해 줍니다.

## 두 가지 워크플로

| | **Manager-based** | Direct |
|---|---|---|
| 구성 | 관측·행동·보상·종료를 **항(term)** 으로 선언 | 클래스 안에서 메서드로 구현 |
| 장점 | **항 단위로 꺼 보며 진단** | 자유도·성능 |
| 단점 | 프레임워크 규칙을 익혀야 함 | 구조가 없어 처음엔 헤맴 |
| 수업 | **이걸 씁니다** | 16H 에서 언급만 |

!!! tip "Manager-based 를 쓰는 이유는 디버깅입니다"
    보상이 항으로 쪼개져 있으면 **"이 항을 빼면 어떻게 되나"** 를
    실험할 수 있습니다. 12H 에서 실제로 씁니다.

---

## 실습 · 환경 점검

```bash
./isaaclab.sh -p 18_isaaclab_check.py
```

```
── 필요한 패키지 ──
  ✅ isaaclab           Isaac Lab 본체
  ✅ isaaclab_assets    사전 정의 로봇 자산
  ✅ rsl_rl             학습 러너 (PPO)
  ✅ torch              딥러닝 프레임워크
  ✅ tensorboard        학습 곡선 시각화

── GPU ──
  ✅ NVIDIA GeForce RTX 4080
     VRAM 16.0 GB

── 등록된 예제 태스크 (일부) ──
  총 N개
    Isaac-Cartpole-v0
    Isaac-Lift-Cube-Franka-v0
    ...
```

## 남의 것이 먼저 도는지 보세요 ★

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless --max_iterations 50
```

!!! success "자기 환경을 만들기 전에 예제를 돌려 보세요"
    나중에 안 될 때 **"Isaac Lab 자체가 문제인가?"** 를 배제할 수 있습니다.

    이 배제 하나가 디버깅 시간을 크게 줄입니다.

## 버전 조합

!!! danger "Isaac Sim 과 Isaac Lab 은 짝이 정해져 있습니다"
    섞으면 동작하지 않습니다. 수업은 **둘 다 정식 출시(GA)된 안정 조합**을
    기준으로 합니다. 베타는 수업 중 API 가 바뀔 위험이 있어 쓰지 않습니다.

    실습 스크립트는 여러 버전에서 동작하도록 import 후보를 여러 개
    두었습니다 → [실습 자산 안내](../labs.md#api)

## 정리

| 항목 | 핵심 |
|---|---|
| **우리 몫** | 환경 정의뿐 |
| **Manager-based** | 항 단위 진단이 되므로 학습용으로 적합 |
| **예제 먼저** | 라이브러리 문제를 배제하는 값싼 방법 |

---

!!! tip "다음 시간"
    [10H · 환경 정의 I](10-env-scene.md) — 로봇 수백 대가 동시에 학습합니다.
