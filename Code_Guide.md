# Code Guide — 강의 사이트 실행 & GitHub Pages 배포

이 문서는 `mkdocs.yml` 기반의 강의 사이트를 **로컬에서 실행**하고 **GitHub Pages로 배포**하기 위한 모든 스크립트·설정 파일을 모아둔 가이드다. 복사-붙여넣기로 바로 사용할 수 있도록 구성했다.

- 플랫폼: MkDocs Material 9.x (한국어)
- 대상 저장소: `/home/totorokr/Assist 강의/` (WSL/Linux/macOS 공통, Windows는 cmd 아닌 PowerShell/Git Bash 권장)
- Python: 3.10 이상

---

## 1. 파이썬 환경 & 의존성

### 1-1. `requirements.txt` 생성

저장소 루트에 다음 파일을 만든다.

```txt
# requirements.txt
mkdocs==1.6.1
mkdocs-material==9.5.49
pymdown-extensions==10.12
mkdocs-material-extensions==1.3.1
```

### 1-2. 가상환경 + 설치 (bash)

```bash
cd "/home/totorokr/Assist 강의"
python3 -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 1-3. 설치 검증

```bash
mkdocs --version                   # mkdocs, version 1.6.1 출력 예상
python -c "import material; print('material OK')"
```

---

## 2. 로컬 실행 스크립트

### 2-1. 개발 서버 (실시간 리로드)

```bash
# scripts/serve.sh  (권한: chmod +x scripts/serve.sh)
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdocs serve --dev-addr 0.0.0.0:8000 --strict
```

- 실행: `bash scripts/serve.sh` → 브라우저에서 `http://localhost:8000`
- `--strict`: 깨진 링크/빠진 파일을 빌드 실패로 처리 (수업 전 품질 게이트로 권장)
- WSL에서 Windows 브라우저로 접속하려면 `--dev-addr 0.0.0.0:8000` 유지

### 2-2. 정적 빌드

```bash
# scripts/build.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
rm -rf site
mkdocs build --strict
echo "빌드 완료 → $(pwd)/site/index.html"
```

- 산출물은 `site/` 디렉토리
- 로컬에서 빌드 결과 미리보기:
  ```bash
  cd site && python3 -m http.server 8080
  # http://localhost:8080
  ```

### 2-3. 하나의 진입점 (Makefile, 선택)

```make
# Makefile
.PHONY: install serve build clean deploy

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

serve:
	. .venv/bin/activate && mkdocs serve --dev-addr 0.0.0.0:8000 --strict

build:
	. .venv/bin/activate && mkdocs build --strict

clean:
	rm -rf site/ .cache/

deploy:
	. .venv/bin/activate && mkdocs gh-deploy --force --clean --verbose
```

사용: `make install` → `make serve` → (배포) `make deploy`

---

## 3. Git 저장소 초기화 (최초 1회)

현재 저장소는 git 미초기화 상태. 다음 순서로 GitHub에 올린다.

### 3-1. `.gitignore` 생성

```gitignore
# .gitignore
# Python
.venv/
__pycache__/
*.pyc

# MkDocs 빌드 산출물
site/

# OS / 에디터
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp

# 환경 변수·비밀키
.env
.env.local
*.key

# Claude Code 내부
.claude/
memory/

# 검토 산출물 (공개 불필요 시)
# review_output/
```

### 3-2. 최초 커밋 & GitHub 푸시

GitHub에서 빈 저장소를 먼저 만든다(예: `jaeyoo1981/assist-sql-agent-lecture`). 그 후:

```bash
cd "/home/totorokr/Assist 강의"
git init -b main
git add .
git commit -m "초기 커밋: 강의자료 + MkDocs 사이트"
git remote add origin git@github.com:<YOUR_GH_USER>/<REPO_NAME>.git
git push -u origin main
```

> SSH 키가 없으면 HTTPS 원격 주소(`https://github.com/...`)를 쓰고 Personal Access Token으로 인증.

---

## 4. GitHub Pages 배포 — 방식 A (간편)

`mkdocs gh-deploy` 명령이 `gh-pages` 브랜치에 빌드 산출물을 강제 푸시한다.

```bash
# 최초 1회
source .venv/bin/activate
mkdocs gh-deploy --force --clean --verbose
```

- 실행 후 GitHub 저장소 **Settings → Pages** 에서
  - Source: `Deploy from a branch`
  - Branch: `gh-pages` / `/ (root)` 선택 → Save
- 약 1분 뒤 `https://<YOUR_GH_USER>.github.io/<REPO_NAME>/`에서 접속 가능.

장점: 설정이 거의 없고 즉시 배포.
단점: 로컬 브랜치 상태를 강제 덮어씀. CI가 아니라 개인 머신에서 수동 배포.

---

## 5. GitHub Pages 배포 — 방식 B (GitHub Actions, 권장)

`main` 브랜치에 푸시될 때마다 자동으로 빌드·배포한다. 팀원 여러 명이 기여할 때 권장.

### 5-1. 워크플로 파일

```yaml
# .github/workflows/deploy.yml
name: Deploy MkDocs to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # 변경 이력이 필요한 플러그인 대비

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Build site
        run: mkdocs build --strict

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### 5-2. GitHub Pages 소스 전환

저장소 **Settings → Pages → Build and deployment → Source**를 **`GitHub Actions`** 로 변경.

### 5-3. 배포 확인

- 워크플로 성공 후 Actions 탭의 Deploy 스텝에 공개 URL이 출력된다.
- 수동 재배포: Actions 탭 → Deploy MkDocs to GitHub Pages → **Run workflow**

---

## 6. `mkdocs.yml` 보강 (선택)

GitHub Pages 배포 후 아이콘 링크·편집 버튼을 위해 상단에 다음을 추가하면 편리하다.

```yaml
site_url: https://<YOUR_GH_USER>.github.io/<REPO_NAME>/
repo_url: https://github.com/<YOUR_GH_USER>/<REPO_NAME>
repo_name: <YOUR_GH_USER>/<REPO_NAME>
edit_uri: edit/main/docs/
```

- `site_url`이 설정되면 sitemap·canonical URL이 생성됨
- `edit_uri`를 두면 각 페이지 우상단에 "이 페이지 수정" 링크가 뜸

`extra.social.link`도 `https://github.com/<YOUR_GH_USER>`로 교체 권장.

---

## 7. 커스텀 도메인 (선택)

도메인이 있다면:

```bash
# docs/CNAME 파일 1줄
lecture.example.com
```

DNS에서 `lecture.example.com` → `<YOUR_GH_USER>.github.io` CNAME 레코드 추가. GitHub **Settings → Pages → Custom domain**에 같은 값을 입력하고 "Enforce HTTPS"를 체크.

---

## 8. 일상 운영 명령 치트시트

| 목적 | 명령 |
|---|---|
| 개발 서버 띄우기 | `make serve` 또는 `mkdocs serve --strict` |
| 강의 직전 빌드 검증 | `make build` (오류 나면 수업 개시 금지) |
| 변경 사항 푸시 → 자동 배포 | `git add . && git commit -m "..." && git push` |
| 방식 A 수동 배포 | `make deploy` |
| 방식 B 강제 재배포 | GitHub Actions 탭에서 `Run workflow` |
| 로컬 site/ 청소 | `make clean` |

---

## 9. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `mkdocs: command not found` | venv 미활성화. `source .venv/bin/activate` 후 재시도 |
| 빌드 시 `WARNING  -  Doc file '...' contains an absolute link ...` | 문서 내부 링크는 상대 경로(`../day2/09-peer-review.md`)로 |
| GitHub Actions 에서 `Pages site failed` | Settings → Pages Source가 `GitHub Actions`로 되어 있는지, workflow의 `permissions: pages: write`가 있는지 확인 |
| 한글 폰트 깨짐 | `mkdocs.yml`의 `theme.font.text`가 **Google Fonts에 존재하는 이름**인지 확인 (현재 `Noto Sans KR` OK). 오프라인 환경이면 `font: false` 후 `extra_css`로 로컬 폰트 지정 |
| Mermaid 다이어그램 렌더 안 됨 | `pymdownx.superfences`의 `custom_fences.mermaid` 블록이 `mkdocs.yml`에 존재하는지 확인 (현재 OK) |
| `mkdocs gh-deploy` 권한 오류 | SSH/PAT 인증 실패. `git remote -v`로 원격 URL 확인 후 자격증명 재설정 |
| Pages URL이 404 | 배포 직후 1~2분 대기. 그래도 404면 Source 설정·브랜치 이름(`gh-pages` vs `main`)을 Settings → Pages에서 재확인 |

---

## 10. 최초 1회 전체 시퀀스 (요약)

```bash
# 1) 의존성 파일 준비
cd "/home/totorokr/Assist 강의"
# requirements.txt, .gitignore, scripts/*.sh, Makefile, .github/workflows/deploy.yml 생성 (위 내용 사용)

# 2) 로컬 환경
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve --strict     # 브라우저로 확인

# 3) 저장소 초기화 & 푸시
git init -b main
git add .
git commit -m "초기 커밋"
git remote add origin git@github.com:<YOUR_GH_USER>/<REPO_NAME>.git
git push -u origin main

# 4) 배포 (방식 A로 빠르게)
mkdocs gh-deploy --force --clean --verbose
# GitHub Settings → Pages에서 gh-pages 브랜치 선택

# 4') 또는 방식 B (Actions)
# Settings → Pages → Source를 GitHub Actions로 변경 → push 시 자동 배포
```

---

## 11. 참고

- MkDocs Material 공식: https://squidfunk.github.io/mkdocs-material/
- GitHub Pages: https://docs.github.com/pages
- GitHub Actions Pages artifact: https://github.com/actions/upload-pages-artifact
