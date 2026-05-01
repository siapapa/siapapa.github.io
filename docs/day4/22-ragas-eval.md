# 22H · Ragas 정량 평가

## 학습목표

- RAG 시스템의 4대 평가 메트릭(Faithfulness, Answer Relevancy, Context Precision, Context Recall)을 설명할 수 있다
- Ragas로 본인 에이전트를 정량적으로 평가할 수 있다
- 낮은 점수의 원인을 진단하고 개선할 수 있다
- Before/After 비교로 개선 효과를 시각화할 수 있다

---

<div class="colab-link" data-notebook="19_ragas_eval"></div>

## 사전 준비 -- 패키지 & 판정 LLM

!!! warning "Ragas 버전 고정 필수"
    Ragas는 0.1 → 0.2 사이에 **필드 이름이 바뀌었습니다**. 본 강의는 **0.1 계열**을 기준으로 작성되어 있으므로 반드시 버전을 고정하세요.

    ```bash
    !pip install "ragas>=0.1.17,<0.2" "datasets>=2.16,<3"
    ```

    - 0.1: `contexts`, `ground_truth`, `report.to_pandas()` 사용
    - 0.2+: `retrieved_contexts`, `reference`로 필드명이 바뀌고 일부 메트릭 시그니처가 변경됨

    만약 Colab 기본 환경이 0.2+를 끌어온다면 위 핀으로 강제 다운그레이드하세요.

!!! danger "API 비용 주의 -- 판정 LLM 호출량 예측"
    Ragas의 각 메트릭은 내부적으로 **LLM 판정자**를 호출합니다. 4개 메트릭 × 10개 질문이면 **대략 40~80회** 호출이 발생하며, 기본값인 `gpt-4` 계열을 그대로 쓰면 **$1~$3**가 쉽게 나옵니다.

    비용을 1/10 수준으로 줄이려면 **판정 LLM을 명시적으로 주입**하세요:

    ```python
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_openai import OpenAIEmbeddings

    judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
    judge_emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))
    ```

    평가 실행 시 `evaluate(..., llm=judge_llm, embeddings=judge_emb)`로 주입하면 됩니다(본 페이지 실습 2 참고). 처음 실습할 때는 **5개 질문으로 축소**해서 파이프라인이 돌아가는지 확인한 후 전체로 확장하세요.

---

## "좋아 보여요"는 평가가 아니다

### 주관적 평가 vs 정량적 평가

| | 주관적 평가 | 정량적 평가 |
|---|---|---|
| 방법 | "잘 되는 것 같은데요?" | Faithfulness: 0.72 |
| 문제점 | 실제로는 10개 중 3개만 정답 | 정확한 수치로 측정 |
| 개선 | "좀 더 좋게 해보세요" | "질문 3, 7에서 실패 -- COMMENT 부족이 원인" |
| 추적 | 변화를 추적할 수 없음 | 0.72 → 0.85 (프롬프트 개선 후 향상) |

!!! warning "주의"
    "정확한 것 같아요"라는 주관적 판단은 할루시네이션(착각)을 놓칠 수 있습니다. 반드시 정량 평가를 수행하세요. "잘 되는 것 같다"는 느낌은 대부분 **확증 편향**입니다 -- 성공 사례만 기억하고 실패 사례는 무시하게 됩니다.

!!! tip "점수가 낮아도 괜찮다"
    점수가 낮아도 괜찮습니다. 중요한 것은 **"왜 낮은지 진단하고 어떻게 개선했는지"**입니다. 이것이 발표의 핵심이며, 엔지니어로서의 역량을 보여주는 부분입니다. 높은 점수보다 **개선 과정**이 더 가치 있습니다.

---

## 4대 메트릭 -- AI의 성적표

### 1. Faithfulness (충실도) -- "교과서에 있는 내용만 답했는가?"

!!! tip "비유"
    **오픈북 시험**에서 교재에 없는 내용을 적으면 감점됩니다. LLM이 컨텍스트(SQL 결과)에 없는 정보를 "지어내면" Faithfulness가 떨어집니다.

**측정 방법:**

1. 답변에서 개별 **주장(claim)**을 추출합니다
2. 각 주장이 컨텍스트(SQL 결과)에서 **뒷받침되는지** 검증합니다
3. 뒷받침되는 주장 수 / 전체 주장 수 = Faithfulness 점수

**예시:**

```
컨텍스트: "내과에는 김철수, 이영희, 신민아 의사가 있습니다."

답변: "내과에는 김철수, 이영희, 신민아, 박준혁 의사가 있습니다."
→ 3/4 = 0.75 (박준혁은 컨텍스트에 없음 = 할루시네이션!)

답변: "내과에는 김철수, 이영희, 신민아 3명의 의사가 있습니다."
→ 3/3 = 1.00 (모든 주장이 컨텍스트에 근거함)
```

**낮은 점수 원인:** 할루시네이션, 컨텍스트에 없는 정보 추가, LLM이 사전 학습 지식을 활용

**개선 방법:** 프롬프트에 "주어진 결과에 있는 정보**만** 사용하세요. 추측하지 마세요." 규칙을 명시적으로 추가

---

### 2. Answer Relevancy (답변 관련성) -- "질문에 제대로 답했는가?"

!!! tip "비유"
    시험 문제가 "내과 의사 수"를 물었는데 "전체 의사 수"를 답하면 감점됩니다. 질문의 **핵심 의도**에 정확히 답변해야 높은 점수를 받습니다.

**측정 방법:**

1. 답변에서 **역질문(reverse question)**을 생성합니다
2. 역질문과 원래 질문의 **유사도**를 측정합니다
3. 유사도가 높으면 답변이 질문에 잘 부합하는 것

**예시:**

```
질문: "내과 의사는 몇 명인가요?"

좋은 답변: "내과에는 김철수, 이영희, 신민아 3명의 의사가 있습니다."
  역질문: "내과에 있는 의사 수는?" → 원래 질문과 매우 유사 → 높은 점수

나쁜 답변: "병원에는 총 20명의 의사가 근무합니다."
  역질문: "병원의 전체 의사 수는?" → 원래 질문과 다름 → 낮은 점수
```

**낮은 점수 원인:** 질문과 관련 없는 답변, 너무 일반적인 답변, 질문의 범위를 벗어난 답변

**개선 방법:** 프롬프트에 "질문에 직접적으로 답변하세요. 질문하지 않은 정보는 포함하지 마세요." 지시 추가

---

### 3. Context Precision (컨텍스트 정밀도) -- "검색한 자료 중 쓸모있는 비율은?"

!!! tip "비유"
    시험 준비 자료 10장 중 실제 시험에 나온 게 2장이면 정밀도가 낮은 것입니다. 불필요한 정보가 많으면 LLM이 혼란을 겪을 수 있습니다.

**측정 방법:** 검색된 컨텍스트 각각이 답변에 실제로 기여했는지 평가

**예시:**

```
질문: "내과 의사 목록"
검색 결과:
  [1] "내과에는 김철수, 이영희, 신민아가 있습니다." ← 관련 O
  [2] "주차 요금은 3시간 무료입니다."              ← 무관 X
  [3] "내과 진료 시간은 9시~17시입니다."           ← 약간 관련
→ Precision = 1~2/3
```

**낮은 점수 원인:** 관련 없는 문서가 검색됨, 검색 범위가 너무 넓음

**개선 방법:** Re-ranking 적용, 메타데이터 필터 추가, 검색 범위 축소, 임베딩 모델 변경

---

### 4. Context Recall (컨텍스트 재현율) -- "필요한 자료를 빠뜨리지 않았는가?"

!!! tip "비유"
    정답이 3명의 의사인데 검색 결과에 2명만 포함되어 있으면 재현율이 낮은 것입니다. 빠진 정보가 있으면 완전한 답변이 불가능합니다.

**측정 방법:** Ground truth의 각 문장이 컨텍스트에서 뒷받침되는지 확인

**예시:**

```
Ground truth: "내과에는 김철수(심장), 이영희(호흡기), 신민아(소화기)가 있다"
검색된 컨텍스트에 김철수, 이영희만 포함
→ Recall = 2/3 (신민아 정보가 누락됨)

검색된 컨텍스트에 김철수, 이영희, 신민아 모두 포함
→ Recall = 3/3 = 1.00
```

**낮은 점수 원인:** 관련 문서를 검색하지 못함, Top-K가 너무 작음, 청킹이 부적절

**개선 방법:** Top-K 증가, 하이브리드 검색(BM25 + 벡터) 적용, 청킹 전략 변경, 스키마 COMMENT 보강

---

### 4대 메트릭 요약

| 메트릭 | 측정 대상 | 핵심 질문 | 낮을 때 원인 |
|---|---|---|---|
| **Faithfulness** | 답변 vs 컨텍스트 | 지어낸 정보가 있나? | 할루시네이션 |
| **Answer Relevancy** | 답변 vs 질문 | 질문에 제대로 답했나? | 관련 없는 답변 |
| **Context Precision** | 컨텍스트 품질 | 쓸모없는 정보가 많나? | 부정확한 검색 |
| **Context Recall** | 컨텍스트 완전성 | 필요한 정보를 빠뜨렸나? | 검색 누락 |

---

## 실습 1 -- 평가 데이터 준비

21H에서 실행한 결과 + 정답(ground truth)을 Ragas에 넣어 4개 메트릭을 측정합니다.

!!! warning "변수 이름 주의 -- Day 4 21H와 충돌 방지"
    21H에서는 `ground_truths`를 **리스트**(질문 순서대로 정답 문자열만)로 썼습니다. 여기서는 **질문→정답 매핑 딕셔너리**를 쓰기 때문에 같은 이름을 덮어쓰면 `create_feedback` 루프가 깨집니다. 이 페이지에서는 일관되게 **`ground_truths_dict`**로 부르겠습니다.

```python
# ============================================================
# 1. 에이전트 실행 결과 수집
# ============================================================

# 21H에서 실행한 results를 사용하거나, 다시 실행
# results 리스트에는 question, answer, sql, sql_result 등이 있음

# Ragas 입력 데이터 구성 (Ragas 0.1 필드명)
eval_data = {
    "question": [],
    "answer": [],
    "contexts": [],       # 0.2+ 에서는 "retrieved_contexts"
    "ground_truth": [],   # 0.2+ 에서는 "reference"
}

ground_truths_dict = {
    "전체 환자 수는?": "전체 환자 수는 30명입니다.",
    "남성 환자 중 40세 이상은 몇 명?": "남성 환자 중 40세 이상은 약 7명입니다.",
    "진료과별 의사 수를 보여줘": "내과 3명, 외과 3명, 소아과 3명, 정형외과 2명, 피부과 2명, 신경과 3명, 산부인과 2명, 안과 2명입니다.",
    "지난달 완료 진료 건수는?": "지난달 완료된 진료 건수를 보여줍니다.",
    "응급 진료 평균 비용은?": "응급 진료의 평균 비용은 약 300,000원입니다.",
    "가장 많이 방문한 환자 Top 3는?": "홍길동, 이준석, 강현우 등이 가장 많이 방문한 환자입니다.",
    "중증 진단을 받은 환자 이름은?": "급성 충수염, 담낭결석, 뇌진탕 등 중증 진단을 받은 환자 목록입니다.",
    "2026년 월별 방문 수 추이는?": "2026년 1월부터 4월까지 월별 방문 수 추이를 보여줍니다.",
    "내과 의사 중 급여 최고는?": "내과 의사 중 김철수가 월 8,500,000원으로 가장 높습니다.",
    "혈액형별 환자 분포는?": "A형, B형, O형, AB형 각각의 환자 수 분포입니다.",
}

for res in results:
    q = res["question"]
    eval_data["question"].append(q)
    eval_data["answer"].append(res.get("answer", ""))
    # contexts는 SQL 결과 + 스키마 정보 (에이전트가 참조한 컨텍스트)
    context = f"SQL: {res.get('sql', '')}\n결과: {res.get('sql_result', '')}"
    eval_data["contexts"].append([context])
    eval_data["ground_truth"].append(ground_truths_dict.get(q, ""))

print(f"평가 데이터 준비: {len(eval_data['question'])}개 질문")
```

!!! note "핵심 정리"
    Ragas가 요구하는 데이터 형식은 4개 필드입니다:

    - `question`: 사용자 질문 (문자열)
    - `answer`: 에이전트의 답변 (문자열)
    - `contexts`: 에이전트가 참조한 컨텍스트 (문자열 리스트의 리스트)
    - `ground_truth`: 기대 정답 (문자열)

    SQL 에이전트의 경우 `contexts`에는 **실행된 SQL 쿼리 + 쿼리 결과**를 넣습니다. 이것이 에이전트가 답변을 생성할 때 참조한 "컨텍스트"이기 때문입니다.

---

## 실습 2 -- Ragas 평가 실행

```python
# ============================================================
# 2. Ragas 평가 실행
# ============================================================
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from datasets import Dataset

# HuggingFace Dataset 형식으로 변환
eval_dataset = Dataset.from_dict(eval_data)

# 판정자(Judge) LLM -- gpt-4o-mini 사용으로 비용 1/10 절감
judge_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-4o-mini", temperature=0))
judge_emb = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model="text-embedding-3-small"))

# 평가 실행 (약 2~5분 소요)
print("Ragas 평가 실행 중... (약 2~5분)")
report = evaluate(
    eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=judge_llm,
    embeddings=judge_emb,
)

# 메트릭별 평균 점수를 DataFrame 집계로 구함 (Ragas 0.1/0.2 공통 안전 경로)
df_report = report.to_pandas()
metric_cols = [c for c in ["faithfulness", "answer_relevancy",
                            "context_precision", "context_recall"]
               if c in df_report.columns]
metric_means = df_report[metric_cols].mean(numeric_only=True)

print(f"\n{'='*50}")
print(f"Ragas 평가 결과 (메트릭별 평균)")
print(f"{'='*50}")
for metric, score in metric_means.items():
    bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"  {metric:<25} {bar} {score:.4f}")
```

!!! warning "처음엔 5개로 축소 실행"
    Ragas는 내부적으로 판정 LLM을 여러 번 호출하므로 10개 질문 기준 **2~5분 + 수 달러**가 소요됩니다. 파이프라인이 올바른지 먼저 **`eval_dataset.select(range(5))`**로 축소 실행해 확인한 뒤 전체로 확장하세요.

!!! note "SQL 에이전트에서 Context 메트릭의 한계"
    Context Precision / Context Recall은 **여러 문서를 검색하는 순수 RAG**를 전제로 설계되었습니다. 우리 SQL 에이전트는 컨텍스트가 "SQL + 결과" 한 덩어리로 들어가기 때문에:

    - **Context Precision**: 항상 1에 가깝게 나오기 쉽습니다(검색된 문서가 1개뿐).
    - **Context Recall**: `ground_truth`에 포함된 사실이 SQL 결과에 있는지를 봅니다. SQL이 틀리면 Recall이 떨어지므로 **"SQL 생성 품질"의 간접 지표**로 해석하세요.

    SQL 에이전트에는 `answer_correctness`(Ragas 0.1+ 제공)가 보완으로 유용합니다. 본 실습에서는 4대 메트릭을 그대로 쓰되, **해석 시 이 한계를 발표에서 언급**하면 평가자가 좋아합니다.

---

## 실습 3 -- 질문별 상세 분석

```python
# ============================================================
# 3. 질문별 상세 분석
# ============================================================

# Ragas 결과를 DataFrame으로 변환
df_eval = report.to_pandas()

print("\n질문별 상세 점수:")
display_cols = ["question", "faithfulness", "answer_relevancy", "context_precision", "context_recall"]
available_cols = [c for c in display_cols if c in df_eval.columns]

if available_cols:
    print(df_eval[available_cols].to_string(index=False))
else:
    print(df_eval.head(10).to_string())
```

---

## 실습 4 -- 시각화

### 4-패널 barh 차트

```python
# ============================================================
# 4. 시각화 — 4-패널 차트
# ============================================================
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0"]
titles = ["Faithfulness", "Answer Relevancy", "Context Precision", "Context Recall"]

for ax, metric, color, title in zip(axes.flat, metrics, colors, titles):
    if metric in df_eval.columns:
        values = df_eval[metric].fillna(0)
        short_labels = [q[:15] + "..." for q in df_eval["question"]]

        bars = ax.barh(range(len(values)), values, color=color, alpha=0.8)
        ax.set_yticks(range(len(values)))
        ax.set_yticklabels(short_labels, fontsize=8)
        ax.set_xlim(0, 1)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axvline(x=0.7, color="red", linestyle="--", alpha=0.5, label="Target (0.7)")
        ax.invert_yaxis()

        # 점수 표시
        for bar, val in zip(bars, values):
            ax.text(val + 0.02, bar.get_y() + bar.get_height()/2,
                   f"{val:.2f}", va="center", fontsize=8)

plt.suptitle("Ragas Evaluation Report", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("ragas_report.png", dpi=150, bbox_inches="tight")
plt.show()
print("리포트 저장: ragas_report.png")
```

!!! note "핵심 정리"
    차트에서 **빨간 점선(0.7)**은 일반적인 목표 기준선입니다. 이 기준선 아래에 있는 질문이 개선이 필요한 대상입니다. 4개 메트릭을 한눈에 비교하면 에이전트의 강점과 약점을 빠르게 파악할 수 있습니다.

### 레이더 차트 (polar plot)

```python
# ============================================================
# 5. 레이더 차트 — 전체 요약
# ============================================================
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

metric_names = titles
metric_values = [float(metric_means.get(m, 0)) for m in metrics]
metric_values.append(metric_values[0])  # 원형으로 닫기

angles = np.linspace(0, 2 * np.pi, len(metric_names), endpoint=False).tolist()
angles.append(angles[0])

ax.plot(angles, metric_values, "o-", linewidth=2, color="#2196F3")
ax.fill(angles, metric_values, alpha=0.25, color="#2196F3")
ax.set_thetagrids(np.degrees(angles[:-1]), metric_names)
ax.set_ylim(0, 1)
ax.set_title("Agent Performance Radar", fontsize=12, fontweight="bold", pad=20)

# 점수 표시
for angle, value, name in zip(angles[:-1], metric_values[:-1], metric_names):
    ax.annotate(f"{value:.2f}", xy=(angle, value), fontsize=10, ha="center")

plt.tight_layout()
plt.savefig("ragas_radar.png", dpi=150, bbox_inches="tight")
plt.show()
```

!!! tip "레이더 차트 읽는 법"
    레이더 차트에서 **면적이 넓을수록** 전체적으로 좋은 성능입니다. 특정 축이 안쪽으로 들어가 있으면 그 메트릭이 약점입니다. 이상적인 에이전트는 **정사각형에 가까운** 레이더를 가집니다. 이 차트를 발표 슬라이드에 넣으면 에이전트의 전체 성능을 한눈에 전달할 수 있습니다.

---

## 실습 5 -- 낮은 점수 원인 진단

```python
# ============================================================
# 6. 낮은 점수 원인 진단
# ============================================================

print("낮은 점수 케이스 분석:\n")

for _, row in df_eval.iterrows():
    low_metrics = []
    for m in metrics:
        if m in row and row[m] is not None and row[m] < 0.7:
            low_metrics.append(f"{m}={row[m]:.2f}")

    if low_metrics:
        print(f"  Q: {row['question'][:40]}...")
        print(f"   낮은 메트릭: {', '.join(low_metrics)}")

        # 원인 추정 + 처방
        for m in metrics:
            if m in row and row[m] is not None and row[m] < 0.7:
                if m == "faithfulness":
                    print(f"   -> 진단: 답변에 컨텍스트에 없는 정보가 포함됨 (할루시네이션)")
                    print(f"   -> 처방: 프롬프트에 '주어진 결과만 사용' 강조")
                elif m == "answer_relevancy":
                    print(f"   -> 진단: 답변이 질문과 직접 관련 없음")
                    print(f"   -> 처방: 프롬프트에 '질문에 직접 답변' 지시")
                elif m == "context_precision":
                    print(f"   -> 진단: 검색된 컨텍스트에 불필요한 정보가 많음")
                    print(f"   -> 처방: Re-ranking 적용 또는 검색 범위 축소")
                elif m == "context_recall":
                    print(f"   -> 진단: 정답에 필요한 정보가 검색되지 않음")
                    print(f"   -> 처방: 스키마 COMMENT 보강 또는 검색 범위 확대")
        print()
```

!!! question "생각해보기"
    위 진단 결과를 보고 다음 질문에 답해보세요:

    - **가장 낮은 점수의 질문**은 무엇인가요? 왜 그 질문이 어려운가요?
    - 그 질문의 **SQL 쿼리**를 확인해보세요. 쿼리 자체가 잘못되었나요, 아니면 답변 생성 과정에서 문제가 발생했나요?
    - **스키마 COMMENT**가 부족해서 실패한 질문이 있나요? 어떤 COMMENT를 추가하면 개선될까요?
    - 동일한 질문을 다른 표현으로 물어보면 결과가 달라질까요? (예: "환자 몇 명?" vs "전체 환자 수는?")

---

## 실습 6 -- 튜닝: 개선된 답변 프롬프트

Faithfulness를 향상시키기 위해 answer 노드의 프롬프트를 개선합니다.

### answer_v2 개선 프롬프트

```python
# ============================================================
# 7. 튜닝 → 재평가 → Before/After 비교
# ============================================================

# 예시: answer 노드의 프롬프트를 개선
def answer_v2(state: AgentState) -> dict:
    """개선된 답변 프롬프트 — Faithfulness 향상 목적"""
    if state.get("error") and state.get("attempts", 0) >= 3:
        return {"answer": f"죄송합니다. 답변 실패.\n오류: {state['error']}"}

    prompt = ChatPromptTemplate.from_template(
        """아래 SQL 쿼리 결과를 바탕으로 질문에 답변하세요.

## 중요 규칙
- 반드시 아래 결과에 있는 정보만 사용하세요.
- 결과에 없는 정보를 추가하거나 추측하지 마세요.
- 숫자는 천 단위 구분자를 사용하세요.
- 질문에 직접적으로 답변하세요.

## 질문
{q}

## 실행된 SQL
{sql}

## 쿼리 결과
{r}

## 답변"""
    )
    chain = prompt | llm | StrOutputParser()
    ans = chain.invoke({"q": state["question"], "sql": state["sql"], "r": state["sql_result"][:1500]})
    return {"answer": ans}
```

!!! tip "v1 vs v2 프롬프트 차이점"
    **v1 프롬프트** (기존):
    `"결과를 한국어로 요약. 숫자 천 단위 구분."`
    -- 간단하지만 모호합니다. LLM이 결과 외의 정보를 추가할 여지가 있습니다.

    **v2 프롬프트** (개선):
    `"반드시 아래 결과에 있는 정보만 사용하세요. 결과에 없는 정보를 추가하거나 추측하지 마세요."`
    -- 명시적 규칙으로 할루시네이션을 억제합니다. 또한 "질문에 직접적으로 답변하세요"로 Answer Relevancy도 함께 개선합니다.

!!! note "어떤 메트릭이 낮을 때 어떻게 튜닝할까? (본인 프로젝트 적용 가이드)"
    v2 프롬프트는 "Faithfulness 낮음"에 대한 한 가지 대응일 뿐입니다. Ragas 리포트를 보고 **낮은 메트릭에 맞춰** 튜닝 방향을 골라야 합니다.

    | 낮은 메트릭 | 의심되는 원인 | 튜닝 후보 |
    |---|---|---|
    | **Faithfulness** (답변이 결과를 벗어남) | 프롬프트가 느슨, LLM 이 추측 | v2 예시처럼 "결과에 없는 내용 금지" 규칙 추가, temperature=0, 결과 길이 제한 |
    | **Answer Relevancy** (질문과 답변이 따로 놈) | 요약이 질문을 되받지 않음 | 프롬프트에 "질문에 직접 답하세요 · 관련 없는 배경 설명 생략" 추가 |
    | **Context Precision** (검색 문서가 질문과 무관) | 스키마/문서 검색이 부정확 | Day 3 17H HyDE/Multi-Query 적용, 테이블 선택 프롬프트 강화, Few-shot 추가 |
    | **Context Recall** (정답에 필요한 문서 누락) | 청크가 너무 작거나 TopK 부족 | Day 1 6H chunk_size 확대, TopK↑, BM25+벡터 하이브리드(18H) |
    | **SQL 실패 자체** (generate 오류, empty result) | SQL 프롬프트 문제, 스키마 설명 부실 | Day 2 10H 커스텀 프롬프트+Few-shot, Day 3 14H Vanna DDL/문서 재학습 |

    **튜닝 절차**:

    1. Ragas 리포트에서 가장 낮은 메트릭 1개를 고릅니다 (한 번에 2개 이상 동시에 바꾸면 원인 분석이 어렵습니다).
    2. 위 표에서 대응하는 튜닝 1개만 적용합니다.
    3. 같은 평가셋으로 재평가 → Before/After 비교.
    4. 개선된 메트릭이 확인되면 다음 낮은 메트릭으로 이동. 악화되면 되돌리고 다른 후보 시도.

### v2 에이전트 재구성 + 재실행

```python
# 개선된 에이전트로 재실행
os.environ["LANGCHAIN_PROJECT"] = "sql-agent-final-v2"

graph_v2 = StateGraph(AgentState)
graph_v2.add_node("generate_sql", generate_sql)
graph_v2.add_node("run_sql", run_sql)
graph_v2.add_node("validate", validate)
graph_v2.add_node("answer", answer_v2)  # ← 개선된 답변 노드
graph_v2.set_entry_point("generate_sql")
graph_v2.add_edge("generate_sql", "run_sql")
graph_v2.add_edge("run_sql", "validate")
graph_v2.add_conditional_edges("validate", should_retry)
graph_v2.add_edge("answer", END)
agent_v2 = graph_v2.compile()

# v2 실행 + Ragas 재평가
results_v2 = []
for q in questions:
    result = agent_v2.invoke({"question": q, "attempts": 0})
    results_v2.append(result)
```

### v2 Ragas 재평가

```python
# v2 평가 데이터 준비
eval_data_v2 = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
for q, res in zip(questions, results_v2):
    eval_data_v2["question"].append(q)
    eval_data_v2["answer"].append(res.get("answer", ""))
    eval_data_v2["contexts"].append([f"SQL: {res.get('sql','')}\n결과: {res.get('sql_result','')}"])
    eval_data_v2["ground_truth"].append(ground_truths_dict.get(q, ""))

report_v2 = evaluate(
    Dataset.from_dict(eval_data_v2),
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    llm=judge_llm,
    embeddings=judge_emb,
)

# v2 메트릭별 평균
df_report_v2 = report_v2.to_pandas()
metric_means_v2 = df_report_v2[[c for c in metric_cols if c in df_report_v2.columns]].mean(numeric_only=True)
```

---

## 실습 7 -- Before/After 비교

### 비교 출력

```python
# Before/After 비교
print(f"\n{'='*60}")
print(f"Before/After 비교")
print(f"{'='*60}")
print(f"{'메트릭':<25} {'v1':>8} {'v2':>8} {'변화':>8}")
print("-" * 49)
for m in metrics:
    v1 = float(metric_means.get(m, 0))
    v2 = float(metric_means_v2.get(m, 0))
    diff = v2 - v1
    arrow = "UP" if diff > 0 else "DOWN" if diff < 0 else "SAME"
    print(f"  {m:<23} {v1:>7.4f} {v2:>7.4f} {arrow} {diff:>+.4f}")
```

### 비교 bar 차트 (발표 슬라이드용)

```python
# ============================================================
# 8. Before/After 비교 차트 (발표 슬라이드용)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 5))

x = np.arange(len(metrics))
width = 0.35

v1_scores = [float(metric_means.get(m, 0)) for m in metrics]
v2_scores = [float(metric_means_v2.get(m, 0)) for m in metrics]

bars1 = ax.bar(x - width/2, v1_scores, width, label="v1 (Before)", color="#90CAF9", edgecolor="white")
bars2 = ax.bar(x + width/2, v2_scores, width, label="v2 (After)", color="#2196F3", edgecolor="white")

ax.set_ylabel("Score")
ax.set_title("Ragas Evaluation: Before vs After Tuning")
ax.set_xticks(x)
ax.set_xticklabels(titles)
ax.legend()
ax.set_ylim(0, 1)
ax.axhline(y=0.7, color="red", linestyle="--", alpha=0.5, label="Target")

for bar in bars1:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
           f"{bar.get_height():.2f}", ha="center", fontsize=9)
for bar in bars2:
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
           f"{bar.get_height():.2f}", ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("ragas_before_after.png", dpi=150, bbox_inches="tight")
plt.show()
print("발표 슬라이드용 Before/After 차트 저장: ragas_before_after.png")
```

!!! tip "발표 슬라이드 활용"
    **이 Before/After 차트가 발표 슬라이드 3장째의 핵심 시각 자료입니다.** 발표에서 다음과 같이 설명하세요:

    - "v1에서 Faithfulness가 0.72였는데, 프롬프트에 '결과만 사용하세요' 규칙을 추가한 후 v2에서 0.85로 개선되었습니다."
    - "개선의 핵심은 프롬프트 엔지니어링이었습니다."
    - 점수가 개선되지 않았더라도 괜찮습니다 -- **왜 개선되지 않았는지 분석하는 것** 자체가 가치 있습니다.

---

## 실습 과제

!!! example "실습"
    1. **본인 에이전트의 10개 질문에 대해 Ragas 평가를 실행**하세요.
    2. **가장 낮은 점수의 질문을 찾아 원인을 진단**하세요:
        - 검색 실패인가요? (Context Recall 낮음)
        - 할루시네이션인가요? (Faithfulness 낮음)
        - 질문과 관련 없는 답변인가요? (Answer Relevancy 낮음)
    3. **하나 이상의 개선을 적용**하고 Before/After 비교를 기록하세요 (발표에 사용).
    4. (도전) 프롬프트 외에 다른 개선도 시도해보세요:
        - 스키마 COMMENT 추가
        - 검색 범위 조정
        - generate_sql 프롬프트 개선

!!! question "생각해보기"
    - 4대 메트릭 중 **가장 개선하기 쉬운 것**은 무엇일까요? 가장 어려운 것은?
    - Faithfulness와 Answer Relevancy는 **프롬프트 튜닝**으로 개선할 수 있습니다. Context Precision과 Context Recall은 어떻게 개선할까요?
    - Ragas 점수가 1.0이면 완벽한 에이전트일까요? 점수가 높아도 실제 사용에서 문제가 될 수 있는 상황은?
    - 만약 10개 질문 중 2개만 점수가 낮다면, 전체 평균을 보는 것보다 **질문별 점수**를 보는 것이 더 유용한 이유는 무엇일까요?

---

!!! note "핵심 정리"
    - **4대 메트릭**: Faithfulness(충실도), Answer Relevancy(관련성), Context Precision(정밀도), Context Recall(재현율)
    - 각 메트릭은 **다른 원인**에 대응 -- 진단을 통해 정확한 개선 포인트를 찾을 수 있음
    - **Ragas evaluate()** 한 줄로 4개 메트릭을 동시에 측정
    - **질문별 상세 분석**으로 어떤 질문이 약한지 파악
    - **레이더 차트**로 전체 성능을 한눈에 시각화
    - **낮은 점수 → 진단 → 처방 → 재평가** 사이클이 핵심
    - **Before/After 비교 차트**가 발표의 핵심 시각 자료
    - 점수가 낮아도 OK -- **"왜 낮은지 진단하고 어떻게 개선했는지"가 중요**
