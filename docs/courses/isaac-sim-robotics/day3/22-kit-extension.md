---
title: 22H · Kit 확장 개발
---

# 22H · Kit 확장 — 내 도구 만들기

!!! warning "실행은 최종 검증 전입니다"
    문법과 `extension.toml` 유효성은 확인했으나
    Kit 안에서의 동작은 아직 확인 전입니다.

**실습 자산**: `course_b/day3/29_kit_extension/`

## 학습 목표

- 확장 생명주기 두 개를 안다
- 반복하는 점검을 버튼 하나로 만든다

---

## 왜 확장인가

[기초 과정](../../omniverse-digital-twin/day1/07-scripting.md) 7H 에서 만든
씬 검증기는 **스크립트**였습니다. 쓸 때마다 터미널로 나가야 합니다.

확장으로 만들면 **앱 안에서 버튼 하나**입니다.
현장에서 반복하는 점검일수록 이 차이가 큽니다.

## 구조

```
exts/company.digitaltwin.tools/
├─ config/extension.toml          ← 메타데이터·의존성
└─ company/digitaltwin/tools/
   ├─ __init__.py                 ← 확장 클래스를 노출
   └─ extension.py                ← on_startup / on_shutdown
```

!!! danger "폴더 이름과 파이썬 패키지 경로가 일치해야 합니다"
    `company.digitaltwin.tools` → `company/digitaltwin/tools/`

    어긋나면 Kit 이 모듈을 못 찾고 **조용히 로드에 실패합니다.**
    UI 가 안 뜨는 원인의 대부분이 이것입니다.

---

## 생명주기 두 개만 ★

```python
class DigitalTwinToolsExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._window = ui.Window("Digital Twin Tools", width=420, height=320)
        ...

    def on_shutdown(self):
        self._output = None
        if self._window is not None:
            self._window.destroy()      # ← 반드시 정리
            self._window = None
```

| 훅 | 시점 | 할 일 |
|---|---|---|
| `on_startup(ext_id)` | 확장이 켜질 때 | UI 생성, 구독 등록 |
| `on_shutdown()` | 확장이 꺼질 때 | **만든 것을 전부 정리** |

!!! danger "정리를 빠뜨리면"
    껐다 켤 때마다 **창이 하나씩 늘어나고**,
    남은 구독이 사라진 객체를 건드려 크래시가 납니다.

    Hot reload 때문에 개발 중 껐다 켜기를 수없이 반복하므로
    **바로 드러납니다.**

---

## 등록하고 켜기

1. Kit 앱 → `Window` → `Extensions`
2. 톱니바퀴(⚙) → `Extension Search Paths` → `29_kit_extension/exts` 경로 추가
3. 목록에서 `Digital Twin Tools` 토글 켜기

## 이 확장이 하는 일

| 버튼 | 무엇 |
|---|---|
| **규약 점검** | 단위·업축·명명 규칙 검사 (기초 과정 7H 의 검증기) |
| **텔레메트리 요약** | `telemetry:` 속성의 현재 값 표시 |

```python
# TraverseAll() 을 씁니다 — 기본 Traverse() 는 def 프림만 훑어
# over 로 된 물리·시각화 레이어가 통째로 빠집니다
for prim in stage.TraverseAll():
    ...
```

기초 과정 Day 2 10H 에서 만난 것과 같은 함정입니다.

---

## 개발 요령

| 항목 | 요령 |
|---|---|
| **Hot reload** | 파일을 저장하면 자동 재로드. 앱 재시작 불필요 |
| **로그 보기** | `Window` → `Console` |
| **UI 가 안 뜸** | `extension.toml` 의 `name` 과 폴더 경로 확인 |

## 실습 과제

**`TODO(basic)`** — "경고 임계치를 넘은 태그만 보기" 버튼을 추가하세요.
`tags.yaml` 을 읽어 `warn` 과 `warn_when` 을 적용합니다.

**`TODO(advanced)`**

1. 점검 결과를 **클릭하면 해당 프림이 선택되도록** 만드세요
2. 타임라인 재생 중 텔레메트리가 **실시간 갱신**되게 하세요
   (업데이트 구독 — `on_shutdown` 에서 반드시 해제)

## 정리

| 항목 | 핵심 |
|---|---|
| **경로 일치** | 폴더와 모듈 이름이 같아야 함 |
| **`on_shutdown`** | 정리 안 하면 창이 쌓이고 크래시 |
| **Hot reload** | 그래서 정리가 더 중요 |

---

!!! tip "다음 시간"
    [23H · 최종 튜닝](23-final-tuning.md)
