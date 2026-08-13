---
title: 20H · 시뮬 결과 → DB
---

# 20H · 시뮬 결과를 DB 에 — 물어볼 수 있게

!!! success "이 시간은 실행 검증 완료 · GPU 불필요"
    PostgreSQL 이 없으면 **SQLite 로 자동 전환**됩니다.

**실습 노트북**: `course_b/day3/27_sim_to_db.ipynb`

## 학습 목표

- 시뮬 결과에 맞는 시계열 스키마를 설계한다
- 실행 이력을 재현 가능하게 남긴다
- 집계 질의로 실험을 비교한다

---

## 왜 DB 인가

지금까지 결과는 JSON 파일과 콘솔 출력에 흩어져 있습니다.

!!! question "지난주 학습들 중 성공률이 가장 높았던 건 뭐였지?"
    파일에 흩어져 있으면 답할 수 없습니다.
    **DB 에 넣으면 물어볼 수 있게 됩니다.**

    그리고 다음 시간에는 그 질문을 **자연어로** 하게 됩니다.

---

## 세 층으로 나눕니다 ★

시뮬레이션 결과는 **성격이 다른 세 가지**가 섞여 있습니다.

| 테이블 | 담는 것 | 한 행의 의미 |
|---|---|---|
| `sim_runs` | 실행 조건 | 학습·평가 1회 |
| `sim_metrics` | 시간에 따라 변하는 값 | 한 시점의 한 지표 |
| `sim_episodes` | 에피소드 결과 | 한 판의 성패 |

한 테이블에 넣으면 나중에 아무것도 못 합니다.

### `sim_metrics` 를 세로로 두는 이유

```sql
CREATE TABLE sim_metrics (
    run_id  TEXT,
    step    INTEGER,
    metric  TEXT,          -- 'mean_reward', 'value_loss', ...
    value   REAL,
    PRIMARY KEY (run_id, step, metric)
);
```

!!! tip "지표를 열로 두면 스키마를 계속 바꿔야 합니다"
    `mean_reward`, `value_loss` … 지표를 추가할 때마다 `ALTER TABLE`.

    세로(long format)로 두면 **행만 늘어납니다.**
    태그가 계속 늘어나는 디지털트윈에서 특히 중요합니다.

### 인덱스를 잊지 마세요

```sql
CREATE INDEX idx_metrics_lookup ON sim_metrics (metric, run_id);
```

없으면 데이터가 조금만 쌓여도 질의가 느려집니다.

---

## 질의로 실험 비교하기

```sql
SELECT r.preset,
       COUNT(DISTINCT r.run_id) AS runs,
       ROUND(AVG(e.success) * 100, 1) AS success_pct
FROM sim_runs r
JOIN sim_episodes e ON e.run_id = r.run_id
GROUP BY r.preset
ORDER BY success_pct DESC
```

```
preset  | runs | episodes | success_pct | avg_reward
--------+------+----------+-------------+-----------
robust  | 3    | 360      | 88.3        | 11.04
naive   | 2    | 240      | 44.6        | 4.81
extreme | 1    | 120      | 20.8        | 1.83
```

!!! success "이 표가 나오는 순간이 DB 를 쓰는 이유입니다"
    17H 의 sim2real 이야기가 **데이터로 확인**됩니다.
    파일에 흩어져 있으면 이 비교를 못 합니다.

---

## 재현 가능하게 남기세요

```python
runs.append({
    "run_id": run_id,
    "preset": preset,
    "num_envs": 1024,
    "seed": 42,              # ← 이게 없으면 재현 불가
    "started_at": ...,
    "elapsed_sec": ...,
})
```

**seed 와 조건을 남겨야** 나중에 "그때 그 결과"를 다시 만들 수 있습니다.

## 실습 과제

**`TODO(basic)`** — Day 2 에서 돌린 학습 로그를 `load_train_log()` 로 적재하고,
"내 실행들 중 최종 보상이 가장 높은 것"을 찾는 질의를 쓰세요.

**`TODO(advanced)`**

1. `sim_artifacts` 테이블 추가 — 체크포인트 경로·크기·해시.
   **어느 실행이 어느 모델 파일을 만들었는지** 추적할 수 있어야 합니다.
2. 18~19H 의 비전 모델 평가 결과도 넣으세요.
   로봇 학습과 비전 모델을 **한 DB 에서** 비교할 수 있게 됩니다.
3. `sim_metrics` 가 수백만 행이 되면 느려집니다.
   구간 집계를 미리 계산해 두는 테이블을 설계하세요.

## 정리

| 항목 | 핵심 |
|---|---|
| **세 층 분리** | 조건 / 시계열 / 에피소드 |
| **long format** | 지표 추가에 스키마 변경이 없게 |
| **인덱스** | 없으면 금방 느려짐 |
| **seed 기록** | 없으면 재현 불가 |

---

!!! tip "다음 시간"
    [21H · 자연어 질의](21-nl-query.md) — 진짜 주제는 **가드레일**입니다.
