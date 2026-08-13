---
title: 9H · SimReady 에셋
---

# 9H · SimReady 에셋

## 학습 목표

- 에셋에 **물리·시맨틱 메타데이터**가 왜 필요한지 안다
- 보기용 3D 모델과 시뮬레이션용 에셋의 차이를 구분한다

---

## 보기용 모델 ≠ 시뮬용 에셋

!!! question "지금 가진 CAD 모델에 질량과 마찰이 들어 있습니까?"
    대부분 없습니다. **설계 도면과 시뮬레이션 모델은 다릅니다.**
    도면에는 질량중심과 관성텐서가 없습니다.

**SimReady** 는 "시뮬레이션에 바로 쓸 수 있게 준비된" 에셋 규격입니다.
겉모습은 같아도 다음이 들어 있습니다.

| 항목 | 없으면 생기는 일 |
|---|---|
| 물리 속성 (질량·마찰·충돌 형상) | 물건이 벨트를 뚫고 지나감 |
| **시맨틱 라벨** (`class: pallet`) | 다음 과정의 합성데이터에서 라벨을 못 붙임 |
| 정확한 축척·원점 | 배치할 때마다 손으로 보정 |
| 조인트·가동부 정의 | 로봇 팔이 안 움직임 |

## 충돌 형상은 단순할수록 좋습니다

CAD 메시를 그대로 충돌 형상으로 쓰면 **시뮬이 기어갑니다.**

| 방식 | 정확도 | 속도 |
|---|---|---|
| 원본 메시 | 높음 | **매우 느림** |
| 볼록 분해 (convex decomposition) | 중간 | 빠름 |
| 박스·실린더 근사 | 낮음 | **매우 빠름** |

컨베이어나 프레임처럼 단순한 것은 박스로 충분합니다.
로봇 그리퍼처럼 정밀한 접촉이 필요한 곳만 정확한 형상을 씁니다.

---

## 실습 · 시맨틱 라벨 붙이기

공용 씬의 프림에 라벨을 붙입니다.
다음 과정의 합성데이터가 이 라벨을 읽어 학습 데이터의 정답을 만듭니다.

```python
prim.CreateAttribute(
    "semantic:class", Sdf.ValueTypeNames.String, custom=True
).Set("conveyor")
```

라벨 체계를 먼저 정하세요.

| 프림 | 라벨 |
|---|---|
| `Conveyor_A` · `Conveyor_B` | `conveyor` |
| `InspectionStation` | `inspection_station` |
| `Buffer` | `buffer` |
| `Pallet_*` | `pallet` |

!!! note "정식 API 는 다음 과정에서"
    Isaac Sim 의 시맨틱 라벨은 전용 스키마를 씁니다.
    여기서는 **개념과 라벨 체계**만 잡고, 실제 합성데이터 생성은
    [로보틱스 과정](../../isaac-sim-robotics/index.md) Day 1 에서 다룹니다.

## 에셋을 구할 곳

| 출처 | 특징 |
|---|---|
| NVIDIA SimReady 에셋 라이브러리 | 물리·시맨틱이 준비된 산업 자산 |
| 사내 CAD | 단위·충돌 형상 보정 필요 |
| 무료 3D 모델 사이트 | 시뮬용으로는 대개 부적합 |

---

## 실습

1. 공용 씬의 각 설비에 `semantic:class` 를 붙이세요
2. 라벨별로 프림을 세어 출력하세요

```python
from collections import Counter

labels = Counter()
for prim in stage.Traverse():
    attr = prim.GetAttribute("semantic:class")
    if attr:
        labels[attr.Get()] += 1

for name, count in labels.most_common():
    print(f"{name:<20} {count}")
```

## 정리

| 항목 | 핵심 |
|---|---|
| **SimReady** | 물리·시맨틱이 준비된 에셋 규격 |
| **충돌 형상** | 단순할수록 빠름. 필요한 곳만 정밀하게 |
| **시맨틱 라벨** | 다음 과정 합성데이터의 정답이 됨 |

---

!!! tip "다음 시간"
    [10H · 물리 시뮬레이션](10-physics.md) — 물건이 벨트 위에 놓입니다.
