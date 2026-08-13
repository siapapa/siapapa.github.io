---
title: 5H · Kit 앱 셋업
---

# 5H · Kit 앱 셋업

!!! danger "이 시간부터 GPU 가 필요합니다"
    사양이 부족하면 페어의 화면을 함께 보며 진행하세요.
    7H 에서 다시 GPU 없이 실습할 수 있습니다.

## 학습 목표

- Kit 앱을 실행하고 4개 패널의 역할을 안다
- 3~4H 에서 코드로 만든 것이 **화면의 어디에 대응하는지** 연결한다
- 앱 안에서 파이썬을 실행한다

---

## 1. 앱 실행

[사전 준비](../setup.md)에서 빌드를 끝냈다면:

```bash
cd kit-app-template
./repo.sh launch          # Windows: .\repo.bat launch
```

!!! warning "첫 실행은 5~8분 걸립니다"
    셰이더 컴파일입니다. 검은 화면이 떠도 멈춘 게 아닙니다.
    Day 0 을 제대로 했다면 이미 한 번 컴파일되어 있어 빠르게 뜹니다.

## 2. 4개 패널만 익히면 됩니다

UI 를 다 배우려 하지 마세요. 이것만 확실히 하면 됩니다.

| 패널 | 무엇 | 3~4H 와의 연결 |
|---|---|---|
| **Viewport** | 3D 화면 | 렌더된 결과 |
| **Stage** | 프림 트리 | `stage.Traverse()` 로 본 그 계층 |
| **Property** | 선택한 프림의 속성 | `prim.GetAttributes()` 로 본 그 값들 |
| **Layer** | 레이어 목록과 강약 | 4H 의 `subLayers` 구조 그대로 |

!!! quote "이 시간의 목적"
    UI 숙달이 아니라 **"코드로 만든 것이 눈에 보인다"는 연결**입니다.

### Stage 트리 = 프림 경로

3H 에서 출력했던 것과 같은 계층이 트리로 보입니다.

```
World
└─ Line01
   ├─ Conveyor_A
   │  └─ Body
   └─ Conveyor_B
```

`/World/Line01/Conveyor_A/Body` — 코드에서 쓴 그 경로입니다.

### Layer 창 = subLayers

4H 에서 코드로 본 레이어 구조가 UI 에 그대로 나타납니다.
위에 있는 레이어가 강한 레이어입니다.

```
live.usda        ← 강함
physics.usda
layout.usda      ← 약함
```

!!! tip "여기서 '아, 그게 이거였구나' 가 나옵니다"
    레이어 하나를 눈으로 껐다 켜 보세요. 물리 레이어를 끄면
    충돌 설정이 사라지는 것을 확인할 수 있습니다.

## 3. Script Editor — 같은 코드가 앱 안에서도 돕니다

메뉴 `Window` → `Script Editor` 를 엽니다.

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
for prim in stage.Traverse():
    print(prim.GetPath())
```

3H 에서 쓴 코드와 **거의 같습니다.** 차이는 스테이지를 얻는 방법뿐입니다.

| 상황 | 스테이지 얻는 법 |
|---|---|
| 노트북·스크립트 | `Usd.Stage.Open(경로)` |
| Kit 앱 안 | `omni.usd.get_context().get_stage()` |

### 공용 씬 열기

`File` → `Open` 으로 `smartfactory01.usda` 를 엽니다.
Stage 트리에 컨베이어·검사 스테이션·버퍼가 나타납니다.

`Conveyor_A` 를 선택하고 Property 패널을 보세요.
3H 에서 만든 `telemetry:speed` 가 거기 있습니다.

---

## 실습

1. 공용 씬을 열고 Stage 트리에서 `Conveyor_A/Body` 를 찾으세요
2. Property 패널에서 `xformOp:translate` 값을 확인하세요 — 코드에서 준 그 값입니다
3. Layer 창에서 `physics.usda` 를 껐다 켜 보세요
4. Script Editor 에서 `telemetry:` 속성을 가진 프림을 전부 출력하세요

```python
import omni.usd

stage = omni.usd.get_context().get_stage()
for prim in stage.Traverse():
    tags = [a.GetName() for a in prim.GetAttributes()
            if a.GetName().startswith("telemetry:")]
    if tags:
        print(prim.GetPath(), tags)
```

## 흔한 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| 실행 직후 검은 화면 | 셰이더 컴파일 중 | 5~8분 대기 |
| 씬이 안 보임 | 카메라가 엉뚱한 곳 | Viewport 에서 `F` (선택 항목에 초점) |
| 회색 벽만 보임 | 단위 미보정으로 1000배 | 6H 에서 다룹니다 |
| 화면이 새까맣게 렌더됨 | 조명 없음 | 6H 에서 다룹니다 |

---

!!! tip "다음 시간"
    [6H · 씬 조립](06-scene-assembly.md) — 회색 박스를 **보기에 쓸 만한 씬**으로.
