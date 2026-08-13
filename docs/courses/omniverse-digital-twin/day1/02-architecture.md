---
title: 2H · Omniverse 아키텍처
---

# 2H · Omniverse 아키텍처

## 학습 목표

- Kit · OpenUSD · RTX · PhysX 가 각각 무엇을 하는지 말할 수 있다
- 왜 "Omniverse 를 설치한다"가 아니라 "Kit 앱을 빌드한다"인지 안다

---

## 층 구조

```
   ┌─────────────────────────────────────────┐
   │  Kit 앱  (USD Composer, Isaac Sim, …)   │  ← 우리가 쓰는 프로그램
   ├─────────────────────────────────────────┤
   │  Kit SDK — 익스텐션 · UI · 파이썬        │  ← 앱을 만드는 틀
   ├──────────────┬──────────────┬───────────┤
   │  OpenUSD     │  PhysX       │  RTX      │  ← 씬 · 물리 · 렌더
   └──────────────┴──────────────┴───────────┘
```

| 층 | 하는 일 |
|---|---|
| **OpenUSD** | 씬을 기술하는 형식. 파일이자 데이터 모델 |
| **PhysX** | 충돌·중력·조인트 — 물리 시뮬레이션 |
| **RTX** | 레이트레이싱 렌더러 |
| **Kit SDK** | 위 셋을 묶어 앱을 만드는 프레임워크 |
| **Kit 앱** | USD Composer, Isaac Sim 등 — 전부 Kit 으로 만든 것 |

## 알아 둘 세 가지

**① Omniverse 는 하나의 프로그램이 아닙니다.**
Kit SDK 로 만든 앱들의 묶음입니다. 그래서 "USD Composer 를 설치"하는 게
아니라 템플릿에서 **빌드**합니다.

**② 모든 데이터는 USD 입니다.**
앱이 달라도 파일은 같습니다. USD Composer 에서 만든 씬을 Isaac Sim 이
그대로 엽니다. 다음 과정에서 실제로 그렇게 합니다.

**③ Launcher 는 폐지되었습니다.**

!!! warning "인터넷 자료를 볼 때 주의하세요"
    **Omniverse Launcher 는 2025년 10월 1일자로 폐지되었습니다.**
    검색해서 나오는 설치 안내가 Launcher 를 언급하면 오래된 자료입니다.
    지금은 GitHub `kit-app-template` 을 받아 직접 빌드합니다.

---

## 실습 · 공용 씬 구조 보기

Kit 을 열지 않고, 파이썬으로 씬 구조만 확인합니다.

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.Open("assets/smartfactory01/smartfactory01.usda")

print("단위:", UsdGeom.GetStageMetersPerUnit(stage), "m/unit")
print("업축:", UsdGeom.GetStageUpAxis(stage))
print()

for prim in stage.Traverse():
    print(f"{prim.GetPath()}  <{prim.GetTypeName()}>")
```

출력은 이렇게 나옵니다.

```
단위: 1.0 m/unit
업축: Z

/World  <Xform>
/World/Environment/Ground  <Plane>
/World/Line01  <Xform>
/World/Line01/Conveyor_A  <Xform>
/World/Line01/Conveyor_A/Body  <Cube>
/World/Line01/Conveyor_B  <Xform>
...
```

!!! question "3D 프로그램인데 왜 코드부터 하나요?"
    **설비 100대를 마우스로 클릭해 배치하실 겁니까?**

    현장 규모의 트윈은 손으로 못 만듭니다. 그리고 문제가 생겼을 때
    파일을 열어볼 수 있어야 원인을 찾습니다. 7H 에서 이 감각이 왜
    중요한지 실감하게 됩니다.

---

## 생태계 — 참고

| 이름 | 무엇 |
|---|---|
| **Connector** | CAD·BIM 도구와 USD 사이의 다리 |
| **SimReady 에셋** | 물리·시맨틱 정보가 포함된 에셋 규격 (9H) |
| **DSX Blueprint** | NVIDIA 가 공개한 AI 팩토리 디지털트윈 레퍼런스 |

---

!!! tip "다음 시간"
    [3H · OpenUSD I](03-usd-basics.md) — 이제 직접 파일을 만듭니다.
    **여기부터 GPU 가 필요 없습니다.**
