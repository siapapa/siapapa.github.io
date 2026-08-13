---
title: 사전 준비
---

# 사전 준비 — 등록 전에 사양부터 확인하세요

!!! danger "이 과정은 사양 미달이면 실습이 중간에 멈춥니다"
    [기초 과정](../omniverse-digital-twin/index.md)은 사양이 부족해도
    일부 구간을 따라올 수 있지만, **이 과정은 그렇지 않습니다.**
    Day 2 의 병렬 강화학습에서 VRAM 이 모자라면 진행이 불가능합니다.

---

## 1단계 · 사양 확인 (필수)

```bash
nvidia-smi
```

| 항목 | 최소 | 권장 |
|---|---|---|
| **GPU** | **GeForce RTX 4080 (16GB)** | RTX 5080 이상 |
| **VRAM** | **16GB** | 24GB 이상 |
| RAM | 32GB | 64GB |
| CPU | i7 7세대 / Ryzen 5, 4코어 | i7 9세대 / Ryzen 7, 8코어 |
| 저장장치 | 50GB SSD | 500GB SSD |
| 드라이버 | Linux 580.65.06+ / Windows 580.88+ | 최신 |
| **Python** | **3.11 고정** | — |
| OS | Windows 10/11 · Ubuntu 22.04/24.04 | — |

!!! failure "지원되지 않는 GPU"
    **A100 · H100 등 데이터센터 GPU 는 쓸 수 없습니다.**
    성능과 무관하게 RT Core 가 없어 Isaac Sim 이 동작하지 않습니다.

!!! warning "Python 3.11 이어야 합니다"
    Isaac Sim 5.x 는 Python 3.11 에 고정되어 있습니다.
    3.12 · 3.13 에서는 설치가 실패합니다.

**`nvidia-smi` 출력을 등록 시 제출**해 주세요. 미달인 경우
[기초 과정](../omniverse-digital-twin/index.md) 수강을 안내드립니다 —
중간에 멈추는 것보다 낫습니다.

---

## 2단계 · Isaac Sim 설치

Python 3.11 가상환경에서 진행합니다.

```bash
python3.11 -m venv .venv-isaac
source .venv-isaac/bin/activate     # Windows: .venv-isaac\Scripts\activate
pip install --upgrade pip
pip install "isaacsim[all]"
```

!!! info "설치 후 예제 씬을 반드시 한 번 실행하세요"
    첫 실행 시 셰이더 컴파일에 시간이 걸립니다.
    수업 당일에 처음 실행하면 그 시간을 수업에서 쓰게 됩니다.

- Linux 는 GLIBC 2.34 이상이어야 pip 설치가 됩니다. Ubuntu 20.04 는 바이너리 설치를 쓰세요.
- 컨테이너 설치는 Linux 에서만 가능합니다.

---

## 3단계 · Isaac Lab 설치 (Day 2 용)

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
./isaaclab.sh --install
```

설치 후 예제 학습이 도는지 확인하세요. **여기까지 성공해야 Day 2 가 가능합니다.**

```bash
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
    --task Isaac-Cartpole-v0 --headless --max_iterations 50
```

!!! warning "버전 조합에 주의하세요"
    Isaac Sim 과 Isaac Lab 은 **짝이 정해져 있습니다.** 섞으면 동작하지 않습니다.
    개강 시점의 권장 조합은 등록 안내와 함께 공지합니다.

    현재는 **둘 다 정식 출시(GA)된 안정 조합**을 기준으로 준비하고 있습니다.
    베타 버전은 수업 중 API 가 바뀔 위험이 있어 쓰지 않습니다.

---

## 4단계 · 분석용 패키지 (Day 3 용)

Day 3 의 18~21H 는 GPU 없이 진행됩니다. 별도로 설치해 두세요.

```bash
pip install torch numpy sqlalchemy pandas matplotlib
```

PostgreSQL 을 쓰려면 추가로:

```bash
pip install psycopg2-binary
```

!!! tip "DB 가 없어도 진행됩니다"
    Day 3 의 DB 실습은 PostgreSQL 이 없으면 **로컬 SQLite 로 자동 전환**됩니다.
    네트워크나 계정 문제로 수업이 멈추지 않도록 만들어 두었습니다.

---

## Day 0 체크리스트

- [ ] `nvidia-smi` — GPU · VRAM · 드라이버 확인
- [ ] `python --version` 이 **3.11** 인지 확인
- [ ] Isaac Sim 예제 씬 실행 화면
- [ ] 예제 씬에서 물리 시뮬레이션 재생 확인
- [ ] Isaac Lab 예제 학습 50회 반복 완료 로그
- [ ] `python -c "import torch; print(torch.cuda.is_available())"` → `True`

---

## 자주 나는 문제

| 증상 | 원인 | 조치 |
|---|---|---|
| `isaacsim` 모듈 없음 | 일반 python 으로 실행 | 가상환경 활성화 또는 `./python.sh` 사용 |
| 설치가 Python 버전에서 실패 | 3.12/3.13 사용 | 3.11 가상환경 생성 |
| `CUDA out of memory` | 병렬 환경 수 과다 | `--num_envs` 를 절반으로 |
| 첫 실행이 멈춘 것 같음 | 셰이더 컴파일 | 5~10분 대기 |
| 에셋 다운로드 실패 | 오프라인 / 회선 포화 | 로컬 사본 배포본 사용 |

## 강의실 네트워크 안내

Isaac Sim 과 로봇 에셋은 수 GB 입니다. 전원이 동시에 받으면 회선이 마비됩니다.
**Day 0 을 각자 집 회선에서** 미리 끝내 주시는 것이 가장 좋습니다.
