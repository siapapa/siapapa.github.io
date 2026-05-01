# Day 4 — 평가 · 모니터링 + 최종 발표 (21~24H)

> **수업 형식**: 각 시간 = 50분 강의 + 10분 휴식 | 이론 30% · 실습 70%
> **실행 환경**: Google Colab + Neon PostgreSQL + OpenAI API + LangSmith

---

## 학습 목표

Day 4에서는 AI 에이전트의 **품질을 측정하고 개선하는 방법**을 배웁니다.

- LangSmith로 에이전트 실행을 **모니터링**하고 토큰/비용/지연을 분석한다
- Ragas로 4대 메트릭을 **정량 평가**하고 낮은 점수의 원인을 진단한다
- Before/After 비교를 통해 **튜닝 효과를 시각화**한다
- 최종 발표에서 라이브 데모와 평가 결과를 공유한다

---

## 4시간 타임라인

| 시간 | 주제 | 핵심 활동 |
|---|---|---|
| **21H** | [LangSmith 트레이싱](21-langsmith.md) | 에이전트 모니터링, 토큰/비용 분석, Dataset 생성 |
| **22H** | [Ragas 정량 평가](22-ragas-eval.md) | 4대 메트릭 측정, 시각화, 원인 진단, 튜닝 |
| **23H** | [최종 튜닝 & 리허설](23-final-tuning.md) | 슬라이드 3장 완성, 라이브 데모 리허설 |
| **24H** | [최종 발표 & 수료](24-final-presentation.md) | 발표, 피드백, 동료 투표, 수료 |

---

## 키워드 표

| 키워드 | 설명 |
|---|---|
| **LangSmith** | AI 앱의 실행 과정을 기록하는 모니터링 플랫폼 |
| **Ragas** | RAG 파이프라인의 성능을 정량 평가하는 프레임워크 |
| **Faithfulness** | 주어진 컨텍스트만으로 답변했는가를 측정하는 메트릭 |
| **Answer Relevancy** | 질문에 관련된 답변을 했는가를 측정하는 메트릭 |
| **Context Precision** | 검색된 컨텍스트 중 유용한 비율을 측정하는 메트릭 |
| **Context Recall** | 필요한 정보를 빠뜨리지 않았는가를 측정하는 메트릭 |
| **Before/After** | 튜닝 전후 성능 비교를 시각화하는 발표 핵심 자료 |

---

## 용어 사전 (비IT 수강생을 위한)

| 용어 | 쉬운 설명 |
|---|---|
| **트레이싱(Tracing)** | AI의 작업 과정을 기록하는 것. 의사의 "진료 기록부"와 같음 |
| **메트릭(Metric)** | 성과를 숫자로 측정한 것. 시험 점수처럼 AI의 성적표 |
| **할루시네이션(Hallucination)** | AI가 없는 정보를 만들어내는 것. "거짓말"이 아니라 "착각" |
| **Ground Truth** | 정답. AI의 답변과 비교할 기준이 되는 올바른 답 |
| **Faithfulness (충실도)** | 주어진 자료만 보고 답했는가? (거짓 없이) |
| **Relevancy (관련성)** | 질문에 맞는 답을 했는가? |

---

## 공통 부트스트랩

!!! warning "주의"
    LangSmith API Key가 없다면 [smith.langchain.com](https://smith.langchain.com)에서 무료 가입 후 Settings > API Keys에서 생성하세요.

```python
# Day 4 실습 도구 설치 및 LangSmith 트레이싱 활성화
!pip install -q \
    langgraph langchain langchain-openai langsmith \
    ragas datasets \
    sqlalchemy psycopg2-binary pandas tabulate matplotlib \
    openai sqlparse

import os
from google.colab import userdata

# AI 및 DB 설정
os.environ["OPENAI_API_KEY"]       = userdata.get("OPENAI_API_KEY")
os.environ["NEON_DSN"]             = userdata.get("NEON_DSN")

# LangSmith 트레이싱 활성화
os.environ["LANGCHAIN_TRACING_V2"] = "true"                    # 트레이싱 ON
os.environ["LANGCHAIN_API_KEY"]    = userdata.get("LANGSMITH_KEY")  # LangSmith API 키
os.environ["LANGCHAIN_PROJECT"]    = "sql-agent-final"          # 프로젝트 이름

from sqlalchemy import create_engine, text
import pandas as pd
engine = create_engine(os.environ["NEON_DSN"])
print("연결 완료! LangSmith 트레이싱 활성화됨")
```

---

!!! note "핵심 정리"
    Day 4는 **만든 에이전트를 검증하고 발표하는 날**입니다. LangSmith로 모니터링하고, Ragas로 정량 평가한 뒤, Before/After 개선 과정을 발표에 담으세요.
