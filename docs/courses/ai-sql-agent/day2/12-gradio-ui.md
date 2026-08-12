# 12H · Gradio in Colab -- 채팅 UI 만들기

## 학습목표

- Gradio `ChatInterface`로 대화형 UI를 만들 수 있다
- `share=True`로 공개 URL을 생성하여 다른 사람과 공유할 수 있다
- 세션별 상태를 관리하여 여러 사용자가 독립적으로 사용할 수 있게 한다

!!! tip "🧭 이 시간을 이렇게 읽으세요 (비개발자용)"
    - **한 줄 핵심**: 파이썬 코드 몇 줄로 **공개 URL 의 채팅 화면** 을 띄워, 본인 챗봇을 동료에게 시연합니다.
    - **꼭 이해**: `ChatInterface` + `share=True` 면 끝. 어렵게 생각할 것 없이, 화면이 뜨는 것 자체가 첫 목표입니다.
    - **지금은 몰라도 OK**: Gradio 5.x 와 4.x 의 파라미터 차이, 세션 메모리의 내부 구현. 강의는 4.44.1 핀으로 동작 보장.
    - **막히면**: 모르는 단어는 [용어 사전](../appendix/glossary.md) 으로 → 처음이라면 [비개발자 학습 가이드](../beginners-guide.md).

---

<div class="colab-link" data-notebook="09_gradio_chatbot"></div>

## 왜 Gradio인가? -- 프레임워크 비교

| 프레임워크 | 코드량 | Colab 지원 | 공유 URL | 학습 곡선 |
|---|---|---|---|---|
| **Gradio** | 5줄 | O | O (자동) | 매우 쉬움 |
| Streamlit | 20줄 | X (터널 필요) | X | 보통 |
| Flask/FastAPI | 100줄+ | X | X | 어려움 |
| React | 500줄+ | X | X | 매우 어려움 |

!!! tip "Gradio = AI 데모를 5줄로 만드는 도구"
    Gradio는 ML 데모에 최적화된 UI 프레임워크입니다. 웹 개발 지식 없이도 채팅 UI를 만들 수 있고, Colab에서 `share=True` 한 줄이면 72시간 유효한 공개 URL이 자동 생성됩니다.

---

## 실습 Step 1 -- 에코봇 (5줄)

!!! warning "Gradio 버전 고정 필수"
    이 실습의 `ChatInterface` 코드는 **Gradio 4.x 전용**입니다. 5.x에서는 `retry_btn` / `undo_btn` / `clear_btn` / `bubble_full_width` 등이 모두 제거돼 `TypeError` 로 실행이 멈춥니다. 아래 설치 셀의 `gradio==4.44.1` 핀을 임의로 풀지 마세요.

??? success "정답 보기"

    ```python
    # ============================================================
    # 📦 패키지 설치 (버전 핀 — Gradio 4.x 전용 실습)
    # ------------------------------------------------------------
    # NumPy 2.x ABI 충돌 방지를 위해 numpy / pandas 도 명시 핀.
    # (없으면 일부 Colab 에서 ValueError: numpy.dtype size changed.)
    # ============================================================
    !pip install -q --upgrade \
        "numpy>=2.0,<3" "pandas>=2.2.2,<3" \
        "gradio==4.44.1" \
        "sqlalchemy>=2.0" psycopg2-binary "openai>=1.30" sqlparse \
        "llama-index>=0.10.50,<0.12" llama-index-llms-openai llama-index-embeddings-openai

    # 위 설치가 numpy 메이저 버전을 갈아치웠다면, 메뉴 [Runtime] → [Restart runtime]
    # 후 이 셀부터 다시 실행하세요. (이미 import 된 옛 numpy 와 ABI 가 어긋남 방지)

    import os
    from google.colab import userdata
    os.environ["OPENAI_API_KEY"] = userdata.get("OPENAI_API_KEY")
    os.environ["NEON_DSN"]       = userdata.get("NEON_DSN")
    ```

??? success "정답 보기"

    ```python
    # ============================================================
    # 1. 최소 Gradio ChatInterface (Echo Bot)
    # ============================================================
    import gradio as gr

    def echo_chat(message, history):
        """입력을 그대로 반환하는 에코 봇"""
        return f"당신이 말한 것: {message}"

    demo = gr.ChatInterface(
        fn=echo_chat,
        title="🤖 에코 봇",
        description="입력한 메시지를 그대로 반환합니다.",
    )
    demo.launch(share=True)
    # share=True → 72시간 유효한 공개 URL 생성
    ```

!!! tip "Gradio 공개 URL"
    실행하면 `Running on public URL: https://xxxxx.gradio.live` 형태의 URL이 나옵니다. 이 URL을 브라우저에서 열면 채팅 UI가 보입니다! 72시간 동안 유효하며, Colab 런타임이 종료되면 URL도 만료됩니다.

!!! warning "`share=True` 는 공개 URL — 본인 Neon DB 에 누구나 접근 가능"
    - URL 을 아는 사람은 누구나 UI 에 접속해 **본인 에이전트를 통해 본인 Neon DB 로 쿼리를 실행**할 수 있습니다.
    - 과제·실습 제출 시에는 URL 을 SNS/오픈 채팅방에 공유하지 마세요. 강사·동료 리뷰어에게만 개인적으로 전달.
    - 민감한 데이터(실제 환자정보·고객정보)가 들어간 DB 는 절대로 `share=True` 와 함께 띄우지 마세요. **에이전트는 read-only 세션**으로 연결하고(공통 부트스트랩의 `agent_engine` 참고), 가능하면 기본 파라미터 `auth=("id","pw")` 로 잠가 둡니다.

---

## 실습 Step 2 -- 병원 상담사 Gradio 통합

### 가드레일 + SQL 함수 전체 코드

??? success "정답 보기"

    ```python
    # ============================================================
    # 2. 병원 DB 상담사 + Gradio 통합
    # ============================================================
    import re
    import pandas as pd
    from sqlalchemy import create_engine, text
    from openai import OpenAI as OpenAIClient
    import sqlparse

    engine = create_engine(os.environ["NEON_DSN"])
    oai = OpenAIClient()

    # 스키마 정보 (간소화)
    from llama_index.core import SQLDatabase, Settings
    from llama_index.llms.openai import OpenAI
    from llama_index.embeddings.openai import OpenAIEmbedding

    Settings.llm = OpenAI(model="gpt-4o-mini", temperature=0)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-3-small")

    sql_db = SQLDatabase(
        engine,
        include_tables=["patients", "doctors", "visits", "diagnoses", "departments"],
    )
    schema_parts = []
    for t in sql_db.get_usable_table_names():
        schema_parts.append(sql_db.get_single_table_info(t))
    SCHEMA_INFO = "\n\n".join(schema_parts)

    # 가드레일
    BLOCKED = re.compile(
        r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
        re.IGNORECASE,
    )
    ALLOWED_TABLES = {"patients", "doctors", "visits", "diagnoses", "departments", "vw_visit_details"}
    ```

### safe_execute 함수

??? success "정답 보기"

    ```python
    def safe_execute(sql: str) -> str:
        """가드레일 적용 후 SQL 실행"""
        if BLOCKED.search(sql):
            return "🚫 위험한 명령어가 포함되어 있어 실행할 수 없습니다."
        if "LIMIT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + "\nLIMIT 1000;"
        try:
            df = pd.read_sql(sql, engine)
            if df.empty:
                return "(결과 없음)"
            if len(df) > 20:
                return df.head(20).to_markdown(index=False) + f"\n\n... 외 {len(df)-20}행"
            return df.to_markdown(index=False)
        except Exception as e:
            return f"❌ SQL 오류: {str(e)}"
    ```

### generate_sql 함수

??? success "정답 보기"

    ```python
    def generate_sql(question: str, history_text: str, last_sql: str = "") -> str:
        """LLM으로 SQL 생성"""
        last_ctx = f"\n직전 SQL:\n{last_sql}" if last_sql else ""
        prompt = f"""PostgreSQL 전문가입니다. 병원 DB에 대한 질문에 SQL을 작성하세요.

    {SCHEMA_INFO}

    규칙:
    - SELECT만 사용. completed 상태만 유효.
    - "그 중" = 직전 SQL 조건 유지 + 추가 필터
    - SQL만 반환 (설명 없이).
    {last_ctx}

    대화:
    {history_text}

    질문: {question}
    SQL:"""

        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        sql = resp.choices[0].message.content.strip()
        sql = re.sub(r"```sql\s*", "", sql)
        sql = re.sub(r"```\s*", "", sql)
        return sql
    ```

### summarize_result 함수

??? success "정답 보기"

    ```python
    def summarize_result(question: str, sql: str, result: str) -> str:
        """결과를 자연어로 요약"""
        prompt = f"""질문: {question}
    SQL: {sql}
    결과:
    {result[:800]}

    한국어로 간결하게 요약하세요. 숫자에 천 단위 구분자 사용."""

        resp = oai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    ```

### hospital_chat 핸들러

??? success "정답 보기"

    ````python
    def hospital_chat(message: str, history: list) -> str:
        """Gradio ChatInterface용 핸들러.

        11H 에서 설계한 멀티턴 컨텍스트(`ChatState.last_sql`)를 Gradio 의 history 에서
        복원해야 "그럼 작년에는?" 같은 후속 질문이 동작합니다. history 는 Gradio 가
        유지하는 유일한 세션 저장소이므로, 이전 bot 응답에 포함된 ```sql 코드블록을
        파싱해 `last_sql` 로 되돌립니다.
        """

        history_text = ""
        last_sql = ""
        for turn in history[-5:]:  # 최근 5턴만
            if isinstance(turn, dict):
                history_text += f"{turn.get('role','user')}: {turn.get('content', '')[:200]}\n"
                if turn.get("role") == "assistant":
                    m = re.search(r"```sql\s*\n(.*?)\n```", turn.get("content", "") or "", re.DOTALL)
                    if m:
                        last_sql = m.group(1).strip()
            elif isinstance(turn, (list, tuple)) and len(turn) == 2:
                user_msg, bot_msg = turn
                history_text += f"사용자: {user_msg}\n시스템: {(bot_msg or '')[:200]}\n"
                m = re.search(r"```sql\s*\n(.*?)\n```", bot_msg or "", re.DOTALL)
                if m:
                    last_sql = m.group(1).strip()

        try:
            # SQL 생성
            sql = generate_sql(message, history_text, last_sql)

            # SQL 실행
            result = safe_execute(sql)

            if result.startswith("🚫") or result.startswith("❌"):
                return result

            # 자연어 답변
            answer = summarize_result(message, sql, result)

            return f"{answer}\n\n---\n📝 **실행된 SQL:**\n```sql\n{sql}\n```\n\n📊 **원본 결과:**\n{result}"

        except Exception as e:
            return f"⚠️ 처리 중 오류가 발생했습니다: {str(e)}"
    ````

---

## 실습 Step 3 -- ChatInterface 생성

??? success "정답 보기"

    ```python
    # ============================================================
    # 3. Gradio ChatInterface + 세션 상태 관리
    # ============================================================

    # Gradio UI 구성 — 4.44.1 기준. 5.x 로 올리면 retry_btn/undo_btn/clear_btn 제거됨
    demo = gr.ChatInterface(
        fn=hospital_chat,
        title="🏥 병원 DB AI 상담사",
        description="자연어로 병원 데이터베이스에 질문하세요. 환자, 의사, 진료 기록을 분석합니다.",
        examples=[
            "현재 등록된 환자 수는?",
            "진료과별 의사 수를 보여줘",
            "지난 3개월간 가장 많이 방문한 환자 Top 5는?",
            "응급 진료 건수와 평균 비용은?",
        ],
        theme=gr.themes.Soft(),
        # Gradio 4.x 전용 파라미터 (5.x 에서는 제거됨)
        retry_btn="🔄 다시 시도",
        undo_btn="↩️ 실행 취소",
        clear_btn="🗑️ 대화 초기화",
    )

    demo.launch(share=True)
    ```

!!! warning "Gradio 5.x 로 업그레이드할 때"
    `retry_btn` / `undo_btn` / `clear_btn` / `Chatbot(bubble_full_width=...)` 는 모두 5.x 에서 제거됐습니다.
    5.x 로 올리려면 위 파라미터를 삭제하고, 기본 재시도·되돌리기·삭제 버튼이 UI 우상단에 자동으로 표시되는 동작으로 대체됩니다. 이번 강의는 4.44.1 기준이므로 버전을 유지하세요.

---

## 실습 Step 4 -- 고급 UI (gr.Blocks + 커스텀 CSS)

??? success "정답 보기"

    ```python
    # ============================================================
    # 4. 고급: 커스텀 CSS + 부가 기능
    # ============================================================

    custom_css = """
    .gradio-container {
        max-width: 900px !important;
        margin: auto !important;
    }
    .message-bubble-border {
        border-radius: 12px !important;
    }
    """

    with gr.Blocks(css=custom_css, theme=gr.themes.Soft(), title="병원 DB 상담사") as advanced_demo:
        gr.Markdown("# 🏥 병원 DB AI 상담사")
        gr.Markdown("자연어로 병원 데이터를 분석하세요. SQL을 자동으로 생성/실행합니다.")

        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    height=500,
                    bubble_full_width=False,  # Gradio 4.x 전용 (5.x 에서 제거)
                    show_label=False,
                )
                msg = gr.Textbox(
                    placeholder="질문을 입력하세요... (예: 남성 환자 수는?)",
                    show_label=False,
                    scale=4,
                )
                with gr.Row():
                    submit_btn = gr.Button("📤 전송", variant="primary")
                    clear_btn = gr.Button("🗑️ 초기화")

            with gr.Column(scale=1):
                gr.Markdown("### 📋 예시 질문")
                gr.Markdown("""
                - 환자 수는 몇 명?
                - 진료과별 의사 수
                - 월별 방문 추이
                - 가장 비싼 진료 5건
                - 중증 진단 환자 목록
                """)
                gr.Markdown("### ⚠️ 주의사항")
                gr.Markdown("""
                - SELECT 쿼리만 가능
                - 데이터 수정/삭제 불가
                - 결과는 최대 1000행
                """)

        def respond(message, chat_history):
            response = hospital_chat(message, chat_history)
            chat_history.append((message, response))
            return "", chat_history

        msg.submit(respond, [msg, chatbot], [msg, chatbot])
        submit_btn.click(respond, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: None, None, chatbot, queue=False)

    advanced_demo.launch(share=True)
    ```

---

## 수강생 간 교차 체험 가이드

```python
# ============================================================
# 5. 교차 체험 — URL 교환
# ============================================================

# 실행 후 출력되는 공개 URL:
# Running on public URL: https://xxxxx.gradio.live

# 교차 체험 진행:
# 1. 각자의 Gradio URL을 채팅/슬랙에 공유
# 2. 다른 학생의 URL에 접속하여 질문 테스트
# 3. 실패하는 질문을 발견하면 피드백
# 4. 5분 후 다른 학생의 앱으로 이동

print("""
🔄 교차 체험 진행 방법:

1. 본인 Gradio URL을 복사하여 전체 채팅에 공유
2. 다른 학생 2명의 URL에 접속
3. 각 앱에서 질문 3개씩 테스트
4. 발견한 문제점을 정리하여 해당 학생에게 피드백

⏱ 소요 시간: 약 10분
""")
```

!!! tip "교차 체험이 이 시간의 하이라이트"
    다른 학생의 앱을 써보면서 "이 질문이 왜 실패하지?"를 발견하는 경험이 학습에 매우 효과적입니다. 경쟁심과 동기부여도 자극됩니다.

---

## 과제 #2 안내

```python
# ============================================================
# 📋 과제 #2 — 스키마 + 시드 데이터 배포
# ============================================================

print("""
╔════════════════════════════════════════════╗
║           과제 #2 — 스키마 + 시드 데이터        ║
╠════════════════════════════════════════════╣
║                                            ║
║  제출 기한: Day 3 시작 (13H)                ║
║                                            ║
║  제출물:                                    ║
║  1. Neon PostgreSQL에 스키마 생성 완료       ║
║  2. 테이블당 최소 50행 시드 데이터           ║
║  3. 모든 컬럼에 COMMENT ON 적용             ║
║  4. FK 관계 정상 동작 확인                   ║
║  5. (선택) read-only DSN을 강사에게 공유      ║
║                                            ║
║  체크리스트:                                 ║
║  □ 제안서 스키마가 Neon에 반영되었는가?       ║
║  □ 시드 데이터가 10개 질문을 답할 수 있는가?  ║
║  □ COMMENT ON이 누락된 컬럼이 없는가?        ║
║  □ FK 제약 조건이 정상 작동하는가?            ║
║                                            ║
║  💡 Faker 라이브러리로 가상 데이터 생성 추천   ║
║                                            ║
╚════════════════════════════════════════════╝
""")
```

!!! warning "DSN 공유는 read-only 전용으로"
    **원본 DSN(read-write 권한)을 강사/동료에게 그대로 공유하지 마세요.** 실수로 누가 `DROP TABLE` 을 날리면 복구 불가능합니다. 공유가 필요하면:

    1. Neon 대시보드에서 `GRANT SELECT ON ALL TABLES IN SCHEMA public TO reviewer_ro;` 로 read-only 롤 생성
    2. 해당 롤 전용 Connection String 을 별도 발급해 공유
    3. 과제 제출이 끝나면 `DROP ROLE reviewer_ro;` 로 회수

    "스키마·시드 확인"이 목적이면 read-only로 충분합니다. 또 강사 공유는 **필수가 아닙니다** -- 스크린샷(`\dt` + `SELECT COUNT(*) FROM ...`)으로 제출해도 인정됩니다.

### 시드 데이터 생성 (Faker)

```python
# 시드 데이터 생성 도우미
!pip install -q faker

from faker import Faker
fake = Faker('ko_KR')

# 예: 고객 데이터 생성
customers = []
for i in range(50):
    customers.append({
        'name': fake.name(),
        'email': fake.email(),
        'phone': fake.phone_number(),
        'address': fake.address(),
        'created_at': fake.date_between('-1y', 'today'),
    })

import pandas as pd
df = pd.DataFrame(customers)
print(df.head(10))

# DB에 삽입하려면:
# df.to_sql('customers', engine, if_exists='append', index=False)
```

!!! tip "Faker 사용 팁"
    - `Faker('ko_KR')`로 한국어 데이터를 생성할 수 있습니다
    - `fake.date_between('-1y', 'today')`로 최근 1년 내 날짜를 생성합니다
    - FK 관계가 있는 테이블은 부모 테이블을 먼저 생성하고, 자식 테이블에서 부모의 ID를 참조하세요
    - `df.to_sql()`로 pandas DataFrame을 바로 DB에 삽입할 수 있습니다

---

!!! example "실습"
    **인사 감지 기능을 추가하세요.**

    "감사합니다", "안녕", "고마워요" 같은 인사가 오면 SQL을 생성하지 않고 인사로 응답하는 기능을 `hospital_chat`에 추가합니다.

    구현 가이드:

    1. 인사 키워드(감사합니다 / 고마워 / 안녕 / 수고 / 반갑 / 잘 부탁 / 좋은 하루 / 화이팅 등)를 잡는 정규식 `GREETING_PATTERNS` 를 만드세요
    2. 응답 후보 문자열 리스트 `GREETING_RESPONSES` 를 정의하세요 (3~5개 권장)
    3. `hospital_chat` 을 복사해 `hospital_chat_v2` 를 만들고, 함수 가장 첫 줄에서 인사가 매칭되면 `random.choice(GREETING_RESPONSES)` 를 즉시 return 하도록 분기하세요
    4. 매칭되지 않을 때만 기존 SQL 생성/실행 로직으로 흘러가야 합니다
    5. 새 핸들러를 `gr.ChatInterface` 로 감싸 `examples=["안녕하세요!", "환자 수는?", "감사합니다!"]` 로 동작을 확인하세요

    *힌트: 위쪽 "hospital_chat 핸들러" 셀을 베이스로 두고, **함수 본문 시작 부분에 if 분기 한 줄만** 추가하면 됩니다. 정답 코드는 숨겨져 있으니, 먼저 본인이 짠 정규식이 "안녕하세요" / "감사해요" / "환자 수는?" 세 문장을 어떻게 구분하는지 직접 테스트해 보세요.*

!!! tip "Gradio 앱을 Google Drive에 저장하는 방법"
    Colab 노트북 자체가 Gradio 앱의 소스코드입니다. Google Drive에 저장하면 언제든 다시 실행할 수 있습니다.

    ```python
    # 1. Colab 노트북을 Google Drive에 마운트
    from google.colab import drive
    drive.mount('/content/drive')

    # 2. 노트북은 자동으로 Drive에 저장됩니다
    #    File > Save a copy in Drive

    # 3. 나중에 다시 실행하려면:
    #    - Google Drive에서 .ipynb 파일을 열기
    #    - "Open in Colab" 클릭
    #    - 모든 셀 실행 (Runtime > Run all)

    # 💡 팁: Colab Secrets에 저장한 API 키는
    #         같은 Google 계정이면 자동으로 불러옵니다
    ```

    **주의사항:**

    - Gradio 공개 URL은 72시간 후 만료됩니다
    - Colab 런타임이 종료되면 URL도 사용 불가
    - 영구 배포가 필요하면 Hugging Face Spaces를 사용하세요

---

## 실습 과제

1. `hospital_chat` 함수에 인사 감지 기능을 추가하세요 ("감사합니다" -> SQL 없이 인사 응답)
2. Gradio `examples`에 본인이 만든 흥미로운 질문 3개를 추가하세요
3. 다른 학생 2명의 Gradio URL에 접속하여 질문 3개씩 테스트하고 피드백을 공유하세요

---

!!! note "12H 핵심 정리"
    - **Gradio** = 5줄로 채팅 UI 완성. `share=True`로 공개 URL 자동 생성
    - `ChatInterface`는 대화 히스토리를 자동 관리해줌
    - 고급 UI는 `gr.Blocks` + 커스텀 CSS로 구성
    - 교차 체험으로 다른 학생의 앱을 테스트하고 피드백
    - **과제 #2**: 내일까지 Neon에 본인 스키마 + 시드 데이터 배포!

---

!!! note "Day 2 전체 정리"

    | 시간 | 주제 | 핵심 키워드 |
    |---|---|---|
    | 9H | 제안서 피어리뷰 | 스키마 검증기, 피어리뷰 |
    | 10H | Text-to-SQL 심화 | 커스텀 프롬프트, Few-shot, ObjectIndex |
    | 11H | 멀티턴 상담사 | ChatState, SQLGuardrail, 맥락 유지 |
    | 12H | Gradio UI | ChatInterface, share=True, 교차 체험 |

    **내일(Day 3) 예고**: Vanna 자가학습 -> LangChain/LCEL -> Advanced RAG -> LangGraph SQL 에이전트 빌드!
