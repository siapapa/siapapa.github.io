---
title: 실습 자산
---

# 실습 자산 안내

<div class="lab-link" data-course="isaac-sim-robotics"></div>

## 자산의 형태 — 노트북이 아닌 이유

!!! danger "Isaac Sim 실습은 Jupyter 노트북으로 하지 않습니다"
    `SimulationApp` 은 **프로세스 시작 시점에** Kit 런타임을 띄웁니다.
    주피터 커널 안에서 만들면 커널 재시작·GPU 점유 문제로 사고가 납니다.

    **시뮬레이션은 스크립트, 결과 분석은 노트북** — 이것이 규칙입니다.

| 형태 | 쓰는 곳 |
|---|---|
| **`.py`** | Isaac Sim 시뮬레이션, Isaac Lab 학습 |
| **`.ipynb`** | 데이터 검수, 학습 곡선 진단, 모델 학습, DB, 자연어 질의 |
| **확장 폴더** | Kit 확장 (`extension.toml` + 파이썬 패키지) |

## 구조

```
labs/course_b/
├─ day1/                              Isaac Sim 로보틱스
│  ├─ _isaac_bootstrap.py             ★ API 경계면
│  ├─ 10_hello_isaacsim.py            시뮬레이션 루프
│  ├─ 11_robot_import.py              URDF 임포트 + 구조 진단
│  ├─ 12_robot_control.py             드라이브 게인 · 관절 제어
│  ├─ 13_sensors_camera.py            카메라 · 어노테이터
│  ├─ 14_sensors_lidar_imu.py         LiDAR · IMU · 정합 점검
│  ├─ 15_replicator.py                도메인 랜덤화
│  ├─ 16_dataset_build.py             데이터셋 생성
│  └─ 17_dataset_qc.ipynb             품질 검수  (GPU 불필요)
├─ day2/                              Isaac Lab 강화학습
│  ├─ _isaaclab_bootstrap.py          ★ API 경계면
│  ├─ 18_isaaclab_check.py            환경 점검
│  ├─ 19_sorting_env.py               환경 정의 (씬·관측·행동·보상·종료)
│  ├─ 20_train.py                     학습 실행
│  ├─ 21_training_monitor.ipynb       곡선 진단  (GPU 불필요)
│  ├─ 22_play_eval.py                 정책 재생·평가
│  └─ 23_eval_report.ipynb            비교 리포트  (GPU 불필요)
└─ day3/                              sim2real · AI 연계
   ├─ 24_sim2real.py                  노이즈·지연·물성 랜덤화
   ├─ 25_train_vision.ipynb           비전 모델 학습  (GPU 불필요)
   ├─ 26_measure_gap.ipynb            갭 측정·배포 판정  (GPU 불필요)
   ├─ 27_sim_to_db.ipynb              DB 적재  (GPU 불필요)
   ├─ 28_nl_query.ipynb               자연어 질의  (GPU 불필요)
   └─ 29_kit_extension/               Kit 확장 템플릿
```

!!! success "GPU 없이 되는 것이 7개 있습니다"
    `17` · `21` · `23` · `25` · `26` · `27` · `28` 은 GPU 가 필요 없습니다.
    학습이 백그라운드로 도는 동안 이 노트북들로 진도를 나갈 수 있고,
    사양 문제로 앞부분에서 고전한 경우에도 이 구간은 온전히 따라올 수 있습니다.

## 실행 방법

Isaac Sim 이 제공하는 파이썬으로 실행해야 합니다.

=== "Linux"

    ```bash
    ./python.sh 10_hello_isaacsim.py
    ./python.sh 10_hello_isaacsim.py --headless
    ```

=== "Windows"

    ```bat
    python.bat 10_hello_isaacsim.py
    ```

=== "Isaac Lab (Day 2)"

    ```bash
    ./isaaclab.sh -p 19_sorting_env.py --num-envs 16 --gui
    ```

=== "노트북 (GPU 불필요)"

    ```bash
    pip install jupyterlab
    jupyter lab
    ```

## API 변동에 대비한 구조

!!! info "Isaac Sim 은 import 경로가 자주 바뀝니다"
    4.5 에서 `omni.isaac.*` → `isaacsim.*` 로 전면 리네임되었고,
    5.0 에서 하위호환 레이어가 제거되었으며, 6.0 에서 다시 새 API 가 도입되었습니다.

실습 자산은 **모든 import 를 두 파일에 모아** 두었습니다.

```
day1/_isaac_bootstrap.py       Isaac Sim API
day2/_isaaclab_bootstrap.py    Isaac Lab API
```

버전이 달라 경로가 안 맞으면 **어떤 경로를 시도했는지 그대로 출력**됩니다.
새 경로를 찾아 후보 목록 맨 앞에 한 줄 추가하면 나머지 스크립트는 그대로 동작합니다.

```
[Camera] 를 찾지 못했습니다. Isaac Sim 버전이 바뀌었을 수 있습니다.
  시도한 경로:
    isaacsim.sensors.camera.Camera  →  ImportError
    omni.isaac.sensor.Camera        →  ImportError
  해결: 설치된 버전의 API 문서에서 새 경로를 찾아
        _isaac_bootstrap.py 의 후보 목록에 맨 앞에 추가하세요.
```

!!! quote "이 구조 자체가 수업 내용입니다"
    빠르게 변하는 SDK 를 다룰 때는 **경계면을 한 곳에 모읍니다.**
    소프트웨어 공학의 기본이고, 로보틱스에서 특히 절실합니다.

## 과제 난이도

| 표시 | 대상 |
|---|---|
| `TODO(basic)` | 전원 — 이것만 해도 진도가 나갑니다 |
| `TODO(advanced)` | 여유가 되면 |

## 배포

실습 자산은 개강 전 **GitHub 저장소로 공개**됩니다.
공개 시점에 이 페이지에 저장소 주소가 표시됩니다.
