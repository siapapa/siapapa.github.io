# 트러블슈팅

실습 중 자주 발생하는 문제와 해결 방법을 정리합니다.

---

## 문제 해결 요약표

| 문제 | 원인 | 해결 |
|---|---|---|
| Neon 연결 실패 | DSN에 `?sslmode=require` 누락 | DSN 끝에 추가 |
| OpenAI 토큰 초과 | 프롬프트가 너무 길음 | 스키마 축소, gpt-4o-mini 사용 |
| Ragas 실행 느림 | LLM 호출 횟수 많음 | 질문 5개로 줄여서 먼저 테스트 |
| ChromaDB 데이터 소실 | Colab 런타임 재시작 | 재학습 필요 |
| LangSmith 트레이스 안 보임 | API Key 미설정 | LANGCHAIN_API_KEY 확인 |
| Gradio URL 안 열림 | 런타임 종료 | Colab 다시 실행 |
| SQL 생성 반복 실패 | 스키마 COMMENT 부족 | COMMENT ON 추가 |

---

## 상세 해결 가이드

### 1. Neon 연결 실패

!!! warning "주의"
    Neon PostgreSQL은 SSL 연결이 필수입니다. `sslmode=require`가 없으면 연결이 거부됩니다.

**증상**: `connection refused` 또는 `SSL connection required` 오류

**원인**: DSN(접속 문자열)에 SSL 모드가 지정되지 않음

**해결**:

```python
# 잘못된 DSN
dsn = "postgresql://user:pass@host/db"

# 올바른 DSN — sslmode=require 추가
dsn = "postgresql://user:pass@host/db?sslmode=require"
```

추가 확인사항:

- Neon 대시보드에서 프로젝트가 활성 상태인지 확인
- 비밀번호에 특수문자(`@`, `#` 등)가 있으면 URL 인코딩 필요
- 무료 티어는 일정 시간 미사용 시 슬립 모드에 진입 — Neon 대시보드에서 깨우기

---

### 2. OpenAI 토큰 초과

**증상**: `context_length_exceeded` 또는 `Rate limit reached` 오류

**원인**: 프롬프트에 포함된 스키마 정보가 너무 길거나, 짧은 시간에 너무 많은 요청

**해결**:

```python
# 방법 1: 필요한 테이블만 포함하여 프롬프트 길이 줄이기
TABLES = ["patients", "visits"]  # 전체 대신 필요한 테이블만

# 방법 2: gpt-4o-mini 사용 (128K 컨텍스트, 더 저렴)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 방법 3: SQL 결과를 잘라서 전달
result_text = df.head(50).to_markdown(index=False)[:1500]
```

!!! tip "팁"
    Rate limit 오류가 발생하면 잠시 기다린 후 재실행하세요. gpt-4o-mini는 분당 요청 한도가 높아 실습에 적합합니다.

---

### 3. Ragas 실행 느림

**증상**: 평가 실행이 10분 이상 소요

**원인**: Ragas는 내부적으로 LLM을 여러 번 호출하므로, 질문 수가 많으면 오래 걸림

**해결**:

```python
# 방법 1: 질문 수를 줄여서 테스트 (5개로 시작)
eval_data_small = {k: v[:5] for k, v in eval_data.items()}
eval_dataset = Dataset.from_dict(eval_data_small)

# 방법 2: 일부 메트릭만 먼저 실행
from ragas.metrics import faithfulness, answer_relevancy
report = evaluate(eval_dataset, metrics=[faithfulness, answer_relevancy])

# 방법 3: 전체 10개는 최종 평가 시에만 실행
```

---

### 4. ChromaDB 데이터 소실

**증상**: 이전에 저장한 임베딩 데이터가 사라짐

**원인**: Google Colab은 런타임 재시작 시 메모리와 로컬 저장소가 초기화됨

**해결**:

```python
# 방법 1: 매 세션마다 재학습 코드를 실행
# (ChromaDB에 데이터를 다시 넣는 셀을 노트북 상단에 배치)

# 방법 2: Google Drive에 영속 저장
from google.colab import drive
drive.mount('/content/drive')
persist_dir = "/content/drive/MyDrive/chromadb_data"
```

!!! tip "팁"
    노트북 상단에 "부트스트랩" 셀을 만들어 환경 설정 + ChromaDB 재학습을 한 번에 실행할 수 있도록 구성하세요.

---

### 5. LangSmith 트레이스 안 보임

**증상**: 에이전트를 실행했지만 LangSmith 대시보드에 트레이스가 나타나지 않음

**원인**: 환경변수가 올바르게 설정되지 않음

**해결**:

```python
import os

# 3개 환경변수가 모두 설정되었는지 확인
print("TRACING:", os.environ.get("LANGCHAIN_TRACING_V2"))
print("API_KEY:", os.environ.get("LANGCHAIN_API_KEY", "")[:10] + "...")
print("PROJECT:", os.environ.get("LANGCHAIN_PROJECT"))

# 올바른 설정 — 3개 모두 필요
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"]    = "ls-..."  # LangSmith에서 발급받은 키
os.environ["LANGCHAIN_PROJECT"]    = "sql-agent-final"
```

!!! tip "팁"
    LangSmith API Key는 [smith.langchain.com](https://smith.langchain.com) > Settings > API Keys에서 생성할 수 있습니다. 무료 플랜으로 충분합니다.

추가 확인사항:

- `LANGCHAIN_TRACING_V2`의 값이 문자열 `"true"`인지 확인 (불리언 `True`가 아님)
- API Key가 `ls-`로 시작하는지 확인
- 에이전트 실행 **전에** 환경변수를 설정해야 함

---

### 6. Gradio URL 안 열림

**증상**: `share=True`로 실행했지만 공개 URL이 작동하지 않음

**원인**: Colab 런타임이 종료되었거나, 네트워크 문제

**해결**:

```python
# 방법 1: Colab 런타임을 다시 시작하고 전체 셀을 다시 실행
# Runtime > Restart and run all

# 방법 2: share=True 확인
demo.launch(share=True)  # share=True가 있어야 공개 URL 생성

# 방법 3: Gradio 버전 확인 및 업그레이드
!pip install --upgrade gradio
```

---

### 7. SQL 생성 반복 실패

**증상**: 에이전트가 같은 질문에 대해 3번 모두 잘못된 SQL을 생성

**원인**: LLM이 테이블/컬럼의 의미를 정확히 이해하지 못함

**해결**:

```sql
-- COMMENT ON으로 컬럼에 자연어 설명 추가
COMMENT ON COLUMN visits.status IS
  '방문 상태: scheduled(예약됨) | completed(완료) | cancelled(취소) | no_show(미방문)';

COMMENT ON COLUMN visits.visit_type IS
  '진료 유형: regular(일반) | emergency(응급) | follow_up(재진)';

COMMENT ON COLUMN patients.blood_type IS
  '혈액형: A, B, O, AB 중 하나';
```

!!! warning "주의"
    `COMMENT ON`은 AI 에이전트 성능에 **가장 큰 영향**을 미치는 요소입니다. 모든 컬럼에 반드시 추가하세요. 특히 상태값, 코드값, 약어가 있는 컬럼은 가능한 값 목록까지 기재해야 합니다.

추가 대처법:

- 에러 메시지를 확인하여 누락된 테이블/컬럼이 있는지 확인
- 프롬프트에 "SELECT만 사용" 규칙이 포함되어 있는지 확인
- 스키마 정보가 프롬프트에 올바르게 주입되고 있는지 확인

---

!!! note "핵심 정리"
    - 대부분의 문제는 **환경변수 설정**이나 **Colab 런타임 상태**에서 발생합니다
    - Neon 연결은 `sslmode=require` 필수
    - LangSmith는 환경변수 3개(`TRACING_V2`, `API_KEY`, `PROJECT`)가 모두 필요
    - SQL 생성 실패는 `COMMENT ON`으로 해결하세요
