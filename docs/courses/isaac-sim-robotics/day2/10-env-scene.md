---
title: 10H · 환경 정의 I — 씬
---

# 10H · 환경 정의 I — 씬과 로봇

!!! warning "이 시간의 실습은 최종 검증 전입니다"

**실습 스크립트**: `course_b/day2/19_sorting_env.py`

## 학습 목표

- 병렬 환경이 무엇인지 안다
- 씬 설정을 작성한다
- **스크립트이면서 모듈이기도 한 파일**을 쓰는 법을 안다

---

## 과제 정의

`SmartFactory-01` 의 검사 스테이션에서, 로봇 팔이 벨트 위 부품을
**정상은 오른쪽 버퍼, 불량은 왼쪽 반출구**로 옮기는 것이 최종 목표입니다.

오늘은 그 축소판으로 **"엔드이펙터를 목표 지점으로 가져가기"** 를 학습시킵니다.
전체 분류 동작은 16H 의 커스텀 태스크에서 확장합니다.

---

## 병렬 환경 ★

Isaac Lab 은 GPU 에서 **수천 개 환경을 동시에** 돌립니다.

```python
scene: SortingSceneCfg = SortingSceneCfg(num_envs=16, env_spacing=3.0)
```

`num_envs` 개가 격자로 복제되어 각자 독립적으로 진행됩니다.

```bash
./isaaclab.sh -p 19_sorting_env.py --num-envs 16 --gui
```

!!! success "16개 로봇이 격자로 늘어선 것을 눈으로 보세요"
    강화학습이 왜 GPU 시뮬레이터를 쓰는지 이 장면 하나로 설명됩니다.
    경험을 16배 빠르게 모으는 것입니다.

| 항목 | 주의 |
|---|---|
| `env_spacing` | 좁으면 옆 환경 물체와 충돌 |
| `{ENV_REGEX_NS}` | 환경마다 복제되는 프림에 붙이는 네임스페이스 |
| 조명·바닥 | 복제 대상이 아닌 것은 `/World` 아래 |

## 씬 설정

```python
@configclass
class SortingSceneCfg(L.InteractiveSceneCfg):
    ground = L.AssetBaseCfg(
        prim_path="/World/ground",
        spawn=L.sim_utils.GroundPlaneCfg(),
    )
    dome_light = L.AssetBaseCfg(
        prim_path="/World/DomeLight",
        spawn=L.sim_utils.DomeLightCfg(intensity=2000.0),
    )
    robot: L.ArticulationCfg = None      # __post_init__ 에서 채웁니다
```

!!! note "조명이 없으면 렌더가 검게 나옵니다"
    학습 자체에는 영향이 없지만(관측이 이미지가 아니므로)
    `--gui` 로 확인할 때 아무것도 안 보입니다.

---

## 스크립트이면서 모듈이기도 한 파일 ★

이 파일은 **13H 의 `20_train.py` 가 import 해서 재사용**합니다.

```python
_IS_MAIN = __name__ == "__main__"

if _IS_MAIN:
    args = parser.parse_args()
    app = launch_app(headless=not args.gui)
else:
    args = None
    app = None

L = lab()        # 이건 항상 필요합니다 (@configclass 선언이 심볼을 씀)
```

!!! danger "이 가드가 없으면"
    import 하는 순간 **남의 인자를 파싱하려다 죽고, 앱이 두 번 뜹니다.**

    Isaac Lab 스크립트는 관례상 모듈 최상위에서 앱을 띄우기 때문에
    재사용하려면 반드시 갈라 줘야 합니다.

!!! tip "실무에서 자주 필요한 패턴입니다"
    "직접 실행하면 도구, import 하면 라이브러리" — 파이썬에서 흔한 구조인데
    Isaac Lab 처럼 초기화 순서가 까다로운 환경에서는 특히 중요합니다.

## 시간 설정

```python
def __post_init__(self):
    self.episode_length_s = 5.0     # 한 판의 길이
    self.decimation = 2             # 물리 몇 스텝마다 정책이 한 번 행동?
    self.sim.dt = 1.0 / 120.0
```

물리 dt 1/120 에 decimation 2 면 정책은 **60Hz 로 행동**합니다.

| | 짧으면 | 길면 |
|---|---|---|
| `episode_length_s` | 목표에 못 닿음 | 학습이 느림 |
| `decimation` | 정책 호출이 잦아 느림 | 반응이 둔함 |

## 실습 과제

**`TODO(basic)`** — `--num-envs` 를 4 · 16 · 64 로 바꿔 화면을 보세요.
`env_spacing` 을 1.0 으로 줄이면 어떻게 됩니까?

**`TODO(advanced)`** — 씬에 컨베이어와 목표 지점을 추가하세요.
`{ENV_REGEX_NS}` 를 붙여 환경마다 복제되게 하세요.

---

!!! tip "다음 시간"
    [11H · 관측과 행동](11-env-obs-action.md) — 로봇이 무엇을 보고 무엇을 할 수 있나.
