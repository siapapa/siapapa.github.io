---
title: 실습 자산
---

# 실습 자산 안내

<div class="lab-link" data-course="omniverse-digital-twin"></div>

## 자산의 형태

이 과정의 실습은 **노트북과 스크립트를 나눠** 씁니다. 목적이 다릅니다.

| 형태 | 쓰는 곳 | 이유 |
|---|---|---|
| **`.ipynb`** | OpenUSD 기초, 데이터 연동, 시나리오 분석 | 설명과 코드가 섞이고 셀 단위로 진도 확인이 쉬움 |
| **`.py`** | 물리 저작, 상태 시각화 | 결과물(USD 레이어)을 만들어 내는 도구 |
| **`.usda`** | 공용 씬 | 텍스트라 **열어서 읽을 수 있음** |

!!! tip "`.usda` 는 열어 보라고 만든 것입니다"
    USD 는 텍스트로 저장할 수 있습니다. 씬이 이상해졌을 때
    GUI 만 쳐다보는 사람과 파일을 열어보는 사람의 차이가 큽니다.
    Day 1 3H 에서 직접 손으로 써 봅니다.

## 구조

```
labs/
├─ requirements/
│  └─ usd.txt                     GPU 없이 되는 것들
├─ assets/
│  └─ smartfactory01/             ★ 공용 실습 씬
│     ├─ build_scene.py           씬 생성 (레이어 3장 + 루트)
│     ├─ apply_telemetry.py       데이터 → USD 타임샘플 바인딩
│     ├─ sim_data/
│     │  ├─ generator.py          모의 텔레메트리 생성기
│     │  └─ tags.yaml             태그 ↔ USD 속성 매핑
│     └─ layers/
│        ├─ layout.usda           배치·형상
│        ├─ physics.usda          물리 (over)
│        └─ live.usda             텔레메트리 기록 대상
└─ course_a/
   ├─ day1/
   │  ├─ 00_usd_basics.ipynb            Stage · Prim · Attribute
   │  ├─ 01_usd_composition.ipynb       레이어 · 참조 · variant
   │  ├─ 02_asset_import.ipynb          단위 · 머티리얼 · 조명 · 카메라
   │  └─ 03_scene_scripting.ipynb       순회 · 자동 배치 · 검증기
   └─ day2/
      ├─ 04_physics.py                  PhysX 스키마 저작
      ├─ 05_data_schema.ipynb           태그 스키마 설계·검증
      ├─ 06_live_binding.ipynb          실시간 바인딩
      ├─ 07_status_visual.py            상태 → 색상 (히스테리시스)
      └─ 08_scenarios.ipynb             what-if · 병목 분석
```

## 실행 방법

### GPU 없이 되는 것부터

```bash
pip install -r requirements/usd.txt

cd assets/smartfactory01
python build_scene.py                                            # 씬 생성
python sim_data/generator.py --duration 7200 --fault 3600 > /tmp/tele.jsonl
python apply_telemetry.py /tmp/tele.jsonl                        # USD 에 바인딩
```

노트북은 Jupyter 로 엽니다.

```bash
pip install jupyterlab
jupyter lab
```

### Kit 안에서 실행하는 코드

Day 1 5H 이후 일부 코드는 **Kit 앱의 Script Editor** 에서 실행합니다.
앱 메뉴 `Window` → `Script Editor` 를 열고 붙여 넣으면 됩니다.

## 과제 난이도

모든 실습에 두 단계가 있습니다.

| 표시 | 대상 | 설명 |
|---|---|---|
| `TODO(basic)` | 전원 | **이것만 해도 진도가 나갑니다** |
| `TODO(advanced)` | 여유가 되면 | 구조를 바꾸거나 기능을 추가 |

!!! note "완성 코드를 먼저 실행합니다"
    빈칸 채우기부터 시작하지 않습니다. 동작하는 코드를 먼저 돌려 결과를 본 뒤,
    일부를 고쳐 가며 이해하는 순서입니다.

## 배포

실습 자산은 개강 전 **GitHub 저장소로 공개**됩니다.
공개 시점에 이 페이지에 저장소 주소가 표시됩니다.

그 전까지는 강의실 공유폴더 또는 USB 로 배포합니다.
