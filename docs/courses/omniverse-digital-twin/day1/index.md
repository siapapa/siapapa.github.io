---
title: Day 1 — OpenUSD 와 Kit 기반
---

# Day 1 · OpenUSD 와 Kit 기반 (1~8H)

오늘의 목표는 **파일을 열어볼 줄 아는 사람이 되는 것**입니다.

GUI 로만 배우면 씬이 이상해졌을 때 아무것도 못 합니다. 그래서 전반부는
일부러 3D 화면 없이 진행합니다. 파일을 직접 만들고, 읽고, 고칩니다.

## 오늘의 흐름

| H | 주제 | 실습 자산 | GPU |
|:--:|---|---|:--:|
| [1](01-ot-demo.md) | OT & 완성 데모 | — | 관람 |
| [2](02-architecture.md) | Omniverse 아키텍처 | — | 불필요 |
| [3](03-usd-basics.md) | OpenUSD I — 씬은 파일이다 | `00_usd_basics.ipynb` | **불필요** |
| [4](04-usd-composition.md) | OpenUSD II — Composition | `01_usd_composition.ipynb` | **불필요** |
| [5](05-kit-setup.md) | Kit 앱 셋업 | Script Editor | 필요 |
| [6](06-scene-assembly.md) | 씬 조립 | `02_asset_import.ipynb` | 일부 |
| [7](07-scripting.md) | Python 스크립팅 | `03_scene_scripting.ipynb` | 불필요 |
| [8](08-project-briefing.md) | 프로젝트 브리핑 | — | — |

!!! success "3~4H 는 GPU 가 없어도 됩니다"
    OpenUSD 파트는 `usd-core` 만 씁니다. 사양이 부족해도 이 구간은
    온전히 따라올 수 있습니다.

## 시작 전 확인

- [ ] [사전 준비](../setup.md)의 Day 0 체크리스트 완료
- [ ] `python -c "from pxr import Usd; print(Usd.GetVersion())"` 가 동작
- [ ] Kit 앱 빌드가 끝나 있음 (5H 에서 씁니다)

!!! danger "Kit 빌드를 아직 안 했다면 지금 시작하세요"
    빌드는 시간이 걸립니다. 수업 중에 시작하면 5H 까지 못 끝냅니다.
    지금 백그라운드로 걸어 두고 3H 로 진행하세요.

## 오늘 끝나면

`SmartFactory-01` 공장 레이아웃을 코드로 조립하고, 설비에 텔레메트리
속성을 붙이고, 씬이 규칙을 지키는지 자동으로 검사할 수 있게 됩니다.

내일은 여기에 **물리와 실시간 데이터**를 붙여 살아 움직이게 만듭니다.
