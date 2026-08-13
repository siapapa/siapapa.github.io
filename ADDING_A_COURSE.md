# 새 강의 추가하기

이 저장소(`siapapa.github.io`)는 **강의 포털**입니다. 강의 하나하나가 독립된 폴더로 들어가고,
홈(`docs/index.md`)이 그 목록을 카드로 보여 줍니다. 새 강의를 열 때 아래 순서만 따르면 됩니다.

## 구조

```
docs/
├─ index.md                      ← 포털 홈 (강의 카탈로그)
├─ courses/
│   ├─ ai-sql-agent/             ← 강의 1 (24H AI SQL 에이전트)
│   │   ├─ index.md              ← 강의 개요 = 이 강의의 첫 페이지
│   │   ├─ setup.md
│   │   ├─ day1/ … day4/
│   │   └─ appendix/
│   └─ <새-강의-slug>/            ← 강의 2 … 같은 모양으로 추가
├─ stylesheets/extra.css         ← 전 강의 공용 CSS
└─ javascripts/colab-links.js    ← 전 강의 공용 Colab 링크 스크립트
```

강의별 자료는 **반드시 `docs/courses/<slug>/` 안에서만** 상대경로로 서로를 링크합니다.
그래야 나중에 폴더를 통째로 옮기거나 다른 저장소로 떼어내도 링크가 깨지지 않습니다.

`<slug>`는 영문 소문자 + 하이픈 (예: `ai-sql-agent`, `rdb-sql-basics`). URL에 그대로 노출됩니다.

## 절차

### 1. 폴더 만들기

```bash
mkdir -p docs/courses/<slug>
```

`docs/courses/<slug>/index.md` 에 강의 개요를 작성합니다. 첫 줄에 포털로 돌아가는 링크를 둡니다:

```markdown
[:material-arrow-left: 전체 강의 목록](../../index.md){ .course-backlink }

# 강의 제목
```

### 2. `mkdocs.yml` 의 `nav` 에 탭 추가

최상위 항목 하나 = 상단 탭 하나입니다. 기존 `"AI SQL 에이전트 (24H)"` 블록을 복사해
제목과 경로만 바꾸는 게 가장 빠릅니다.

```yaml
nav:
  - "강의 목록": index.md
  - "AI SQL 에이전트 (24H)":
    - courses/ai-sql-agent/index.md
    - ...
  - "새 강의 이름":            # ← 추가
    - courses/<slug>/index.md
    - "1강. …": courses/<slug>/01-....md
```

### 3. 홈에 강의 카드 추가

`docs/index.md` 의 `<div class="grid cards" markdown>` 안에 카드를 추가합니다.
"다음 강의 준비 중" 카드는 맨 뒤에 두거나, 대기 중인 강의가 없으면 지웁니다.

```markdown
-   :material-database-outline:{ .lg .middle } **강의 제목**

    ---

    <span class="course-badge course-badge--live">진행 중</span>
    <span class="course-badge">16시간 · 4주</span>

    한 문단 소개.

    **핵심 기술 1** · **핵심 기술 2**

    [:octicons-arrow-right-24: 강의 자료 보기](courses/<slug>/index.md)
```

상태 뱃지는 `docs/stylesheets/extra.css` 에 정의되어 있습니다.

| 클래스 | 표시 | 용도 |
|---|---|---|
| `course-badge--live` | 초록 | 진행 중 |
| `course-badge--done` | 남색 | 진행 종료 (자료는 계속 열람 가능) |
| `course-badge--soon` | 주황 | 준비 중 / 개설 예정 |
| `course-badge--req` | 빨강 | **필수 요건** (사양 미달 시 수강 불가) |
| (클래스 없음) | 회색 | 시수·기간 등 메타 정보 |

### 4. 빌드 확인

```bash
.venv/bin/mkdocs build --strict     # 링크 오류가 하나라도 있으면 실패합니다
.venv/bin/mkdocs serve              # http://127.0.0.1:8000 에서 미리보기
```

`main` 에 푸시하면 `.github/workflows/deploy.yml` 이 자동으로 GitHub Pages 에 배포합니다.

## 공용 자산 사용법

### 실습 자산 링크 — 두 가지 방식

강의 성격에 맞는 쪽을 고르세요.

| 방식 | 쓰는 곳 | 스크립트 |
|---|---|---|
| **Colab 링크** | 브라우저에서 노트북을 여는 과정 | `colab-links.js` |
| **저장소 링크** | 로컬 PC 에서 스크립트를 실행하는 과정 | `lab-links.js` |

저장소 방식은 페이지에 아래 한 줄을 두고, `lab-links.js` 의 `LAB_REPOS` 에
과정 정보를 채웁니다. `url` 을 빈 문자열로 두면 "준비 중" 으로 표시됩니다.

```html
<div class="lab-link" data-course="omniverse-digital-twin"></div>
```

### Colab 노트북 링크

강의 페이지 아무 곳에나 아래 한 줄을 두면 Colab 뱃지 박스로 렌더링됩니다.

```html
<div class="colab-link" data-notebook="01_postgres_basics"></div>
```

노트북 키 → Google Drive file ID 매핑은 `docs/javascripts/colab-links.js` 의 `NOTEBOOK_IDS` 에 있습니다.
**강의가 여러 개가 되면 키 충돌에 주의하세요.** 새 강의의 노트북은 `<slug>/01_xxx` 처럼
접두사를 붙이거나, 강의별 키 그룹을 나눠 관리하는 편이 안전합니다.

### 예전 URL 리다이렉트

`mkdocs.yml` 의 `redirects` 플러그인 블록은 **`ai-sql-agent` 강의를 루트에서 `courses/` 아래로
옮기면서 생긴 과거 URL 전용**입니다. 새 강의는 처음부터 `courses/<slug>/` 로 만들기 때문에
여기에 추가할 것이 없습니다.

## 강의가 많아지면

강의가 10개를 넘어 `mkdocs.yml` 의 `nav` 가 관리하기 버거워지면 다음 단계는
**강의별 독립 MkDocs 사이트를 서브경로로 조립**하는 방식입니다
(`courses/<slug>/mkdocs.yml` + monorepo 플러그인, 또는 개별 빌드 후 `site/courses/<slug>/` 로 배치).
지금 구조는 그 방향으로 그대로 승격할 수 있게 폴더가 이미 강의 단위로 나뉘어 있습니다.
