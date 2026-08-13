---
title: 사전 준비
---

# 사전 준비 — 개강 전에 끝내 두세요

이 과정은 클라우드가 아니라 **로컬 RTX PC** 에서 돌아갑니다.
설치가 무거워서, 수업 시간에 시작하면 하루가 날아갑니다.

!!! danger "Day 0 세션에서 함께 진행합니다"
    정규 시수와 별도로 **2시간짜리 사전 셋업 세션**이 있습니다.
    그 전에 아래 1단계(사양 확인)만이라도 미리 해 두세요.

---

## 1단계 · 내 PC 가 되는지 확인

터미널(Windows 는 PowerShell)에서:

```bash
nvidia-smi
```

출력의 GPU 이름·드라이버 버전·VRAM 을 아래와 대조합니다.

| 항목 | 기준 |
|---|---|
| **GPU** | RTX 3070 이상 권장 |
| VRAM | 8GB 이상 |
| RAM | 16GB 이상 (32GB 권장) |
| 여유 디스크 | 30GB 이상 |
| OS | Windows 10/11 또는 Ubuntu 22.04/24.04 |
| Python | 3.10 이상 |

!!! failure "지원되지 않는 GPU"
    **A100 · H100 등 데이터센터 GPU 는 쓸 수 없습니다.**
    성능과 무관하게 RT Core 가 없어 Omniverse 렌더러가 동작하지 않습니다.

!!! success "사양이 안 되어도 참여할 수 있는 구간이 있습니다"
    Day 1 의 OpenUSD 파트(3~4H)는 **GPU 없이** 실습합니다.
    사양 미달인 경우 미리 알려 주시면 강의실 PC 배정 또는
    2인 1조 페어 실습으로 배정합니다.

**`nvidia-smi` 출력을 스크린샷으로 제출**해 주세요.

---

## 2단계 · 공통 도구 설치

=== "모든 OS"

    - **Git** — <https://git-scm.com/downloads>
    - **Git LFS** — 설치 후 `git lfs install` 실행
    - **Python 3.10+**

=== "Windows 추가"

    - **Visual Studio 2019 또는 2022**
    - Visual Studio Installer 에서 **`C++를 사용한 데스크톱 개발`** 워크로드 선택
    - **Windows SDK** 포함

=== "Linux 추가"

    ```bash
    sudo apt-get update && sudo apt-get install -y build-essential
    ```

---

## 3단계 · Omniverse Kit 앱 빌드

!!! warning "예전 자료의 설치 방법은 동작하지 않습니다"
    **Omniverse Launcher 는 2025년 10월 1일자로 폐지되었습니다.**
    인터넷에서 찾을 수 있는 "Launcher 에서 USD Composer 설치" 절차는
    더 이상 쓸 수 없습니다. 지금은 GitHub 템플릿을 받아 직접 빌드합니다.

```bash
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
cd kit-app-template

# 템플릿에서 앱 생성 (Windows: .\repo.bat template new)
./repo.sh template new
#   → Application 선택
#   → USD Composer (또는 Kit Base Editor) 선택
#   → 앱 이름은 소문자·영숫자로

# 빌드 — "BUILD (RELEASE) SUCCEEDED" 가 나와야 합니다
./repo.sh build

# 실행
./repo.sh launch
```

!!! info "첫 실행은 5~8분 걸립니다"
    셰이더 컴파일 때문입니다. 멈춘 것이 아니니 기다리세요.
    두 번째부터는 훨씬 빠릅니다. **수업 당일 아침에 미리 한 번 띄워 두면 좋습니다.**

### 자주 나는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| 빌드가 컴파일러를 못 찾음 | VS C++ 워크로드 누락 | Visual Studio Installer 에서 추가 |
| LFS 파일이 텍스트로 받아짐 | `git lfs install` 미실행 | 실행 후 `git lfs pull` |
| 실행 직후 검은 화면 | 셰이더 컴파일 중 | 5~8분 대기 |
| 드라이버 관련 크래시 | 드라이버 구버전 | 최신 스튜디오/게임레디 드라이버 |

---

## 4단계 · USD 실습 환경 (전원)

Day 1 의 OpenUSD 파트는 GPU 없이 됩니다. **사양과 무관하게 전원 설치**하세요.

```bash
pip install usd-core pyyaml

# 확인
python -c "from pxr import Usd; print(Usd.GetVersion())"
```

---

## Day 0 체크리스트

각 항목 스크린샷 1장씩 제출합니다.

- [ ] `nvidia-smi` 출력 (GPU · 드라이버 · VRAM)
- [ ] `git --version` · `git lfs version` · `python --version`
- [ ] `python -c "from pxr import Usd; print(Usd.GetVersion())"` 출력
- [ ] `./repo.sh build` 의 `BUILD (RELEASE) SUCCEEDED`
- [ ] Kit 앱 실행 화면 (뷰포트가 보이는 상태)

---

## 강의실 네트워크 안내

전원이 동시에 수 GB 를 내려받으면 회선이 마비됩니다.
가능하면 **Day 0 을 각자 집 회선에서** 미리 끝내 주세요.
강의실에서 진행할 경우 USB 또는 공유폴더로 사전 배포합니다.
