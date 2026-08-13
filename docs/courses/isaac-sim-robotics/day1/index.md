---
title: Day 1 — Isaac Sim 로보틱스 기초
---

# Day 1 · Isaac Sim 로보틱스 기초 (1~8H)

로봇을 시뮬레이션에 올리고, 센서를 달고, **합성 데이터를 만드는** 날입니다.

## 오늘의 흐름

| H | 주제 | 실습 자산 | 검증 |
|:--:|---|---|:--:|
| [1](01-ot-usd-review.md) | OT · 데모 · USD 압축 복습 | `10_hello_isaacsim.py` | ⬜ |
| [2](02-simulation-loop.md) | 시뮬레이션 루프 | `10_hello_isaacsim.py` | ⬜ |
| [3](03-robot-import.md) | 로봇 임포트 | `11_robot_import.py` | ⬜ |
| [4](04-robot-control.md) | 로봇 제어 | `12_robot_control.py` | ⬜ |
| [5](05-camera.md) | 카메라 센서 | `13_sensors_camera.py` | ⬜ |
| [6](06-lidar-imu.md) | LiDAR · IMU | `14_sensors_lidar_imu.py` | ⬜ |
| [7](07-replicator.md) | Replicator 도메인 랜덤화 | `15_replicator.py` | ⬜ |
| [8](08-dataset.md) | 데이터셋 생성·검수 | `16` · `17_dataset_qc.ipynb` | 🟩 부분 |

!!! warning "⬜ 표시된 시간은 최종 검증 전입니다"
    Isaac Sim 이 필요한 실습은 아직 실행 확인이 끝나지 않았습니다.
    코드는 공식 문서 기준으로 작성되었고 문법 검사는 통과했으나,
    **버전에 따라 API 이름이 다를 수 있습니다.**

    막히면 [실습 자산 안내](../labs.md#api)의 부트스트랩 구조를 보세요 —
    경로 하나만 고치면 나머지가 그대로 동작하도록 만들어 두었습니다.

!!! success "8H 의 데이터 검수는 GPU 없이 검증 완료"
    `17_dataset_qc.ipynb` 는 실행 검증이 끝났고, Isaac Sim 이 없어도
    모의 데이터셋으로 진행할 수 있습니다.

## 시작 전

- [ ] [사전 준비](../setup.md)의 Day 0 체크리스트 완료
- [ ] `python 10_hello_isaacsim.py` 가 **API 점검표까지** 출력되는지 확인
- [ ] 에셋 서버 접속 확인 (첫 실행 시 수백 MB 다운로드)

!!! danger "오프라인 강의실이라면"
    로봇 에셋은 NVIDIA 서버에서 받습니다. 전원이 동시에 받으면 회선이 마비됩니다.
    Day 0 에 미리 받아 두셨는지 확인하세요.

## 오늘 끝나면

로봇이 씬에서 움직이고, 카메라와 LiDAR 가 데이터를 내고,
도메인 랜덤화가 적용된 합성 데이터셋 1,000장을 만들 수 있게 됩니다.

내일은 그 로봇에게 **스스로 움직이는 법을 학습**시킵니다.
