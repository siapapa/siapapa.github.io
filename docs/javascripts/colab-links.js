/* ============================================================
 * Colab 실습 노트북 링크 자동 삽입
 * ------------------------------------------------------------
 * 사용법:
 *   1) 강사가 Google Drive 의 각 노트북 파일을 다음과 같이 공유합니다.
 *        - 우클릭 → 공유 → "링크가 있는 모든 사용자" + 권한 "뷰어"
 *        - 또는 'Colab Notebooks/notebooks_student' 폴더 자체를 동일 권한으로 공유
 *      → 학생이 링크로 접속하면 자동으로 "보기 전용"으로 열리고,
 *        Colab 상단의 [드라이브에 사본 저장] 버튼으로 본인 사본을 만들어
 *        자유롭게 수정·실행할 수 있습니다 (원본은 변경되지 않음).
 *
 *   2) 아래 NOTEBOOK_IDS 객체에 각 노트북의 Drive file ID 를 채워 넣습니다.
 *      (Drive 공유 링크 'https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing'
 *       에서 <FILE_ID> 부분만 복사)
 *
 *   3) 각 강의 페이지의 실습 시작 위치에 다음 한 줄을 두면
 *      자동으로 "📓 Colab 실습 노트북" 뱃지로 렌더링됩니다.
 *        <div class="colab-link" data-notebook="01_postgres_basics"></div>
 * ============================================================ */

// 공유 폴더: https://drive.google.com/drive/folders/1qFvTWW8_jv-CqrDBYOepB80ZCwE6JhLo
// 폴더 권한: "링크가 있는 모든 사용자 — 뷰어" (각 파일 권한은 자동 상속)
const NOTEBOOK_IDS = {
  "00_demo_agent":             "1KBT2esRp2FA6jWt-LqDfCqSL5TY_gsw_",
  "01_postgres_basics":        "1WuVIGxKnaQi6nJCu-A20duxZ-d2e_8MT",
  "02_sql_aggregation_join":   "1vkREzHTqr03c8ZqDzlvnZ2BJILMlsE6i",
  "03_schema_intelligence":    "1NAo6_rYtmaEYYodvyTo1qaEOXKfnHESE",
  "04_llamaindex_intro":       "1Wx9JydGwKqAw5FKpGmlcL33PPor2RlUS",
  "05_embedding_chromadb":     "16NSgb1MFMGcQMrH2o3stZ_pkskEPlRrC",
  "06_text_to_sql":            "14S3AG4hkzk2kla5017enrc9gecSL89t8",
  "07_project_briefing":       "1jIRsvweLvAz14DZjBru9Qwu8cBbkEuvd",
  "08_text_to_sql_advanced":   "1P4JJXxOHxD-n-_mUNxC44879vklhiVEi",
  "09_gradio_chatbot":         "1BWIAYsHizEcmOlHMIznSmAquZcDMDrcT",
  "10_vanna_intro":            "1xgyRnmP8C6VtTB9Kj-qfDGUPoRzDYdU2",
  "11_vanna_training":         "1-J22zJf5UGx1M24R92lYi3FZCn0qkQqQ",
  "12_langchain_lcel":         "1V4dTid3X-1NCj0s4T8u8VVvYN8j6IDyl",
  "13_lcel_rag_chain":         "1zIdl2PbMKub2zagcmzrKMG3VuO8uhq5T",
  "14_advanced_rag_query":     "1uhZklAGKmrSUpzcigMxkqXC3bdMwRtQH",
  "15_advanced_rag_retrieval": "1y8GCrrdSgsdRz_amZkw1QViPlPFHC9x4",
  "16_langgraph_concept":      "1O-7WHcVEqQAOyMFeadVfBEkYhAQnBqEa",
  "17_my_sql_agent":           "1Y8Gzt_Y0PQzFrpUJJgch3X2oz07hre4_",
  "18_langsmith_tracing":      "1vJrKnAOt_W3bjeBVQ7szzLVNT6Ska-UX",
  "19_ragas_eval":             "11BM1ns1cxdkVGoIlPtzz_qZFQBESNYUh"
};

const COLAB_BADGE = "https://colab.research.google.com/assets/colab-badge.svg";

function buildLinkBox(notebookKey, fileId) {
  const filename = `${notebookKey}.ipynb`;
  const colabUrl = `https://colab.research.google.com/drive/${fileId}`;

  const box = document.createElement("div");
  box.className = "colab-link-box";

  if (!fileId) {
    box.classList.add("colab-link-box--pending");
    box.innerHTML = `
      <div class="colab-link-box__title">📓 Colab 실습 노트북 — <code>${filename}</code></div>
      <div class="colab-link-box__body">
        <span class="colab-link-box__pending">⚙️ 아직 강사가 Drive 링크를 등록하지 않았습니다.</span>
      </div>`;
    return box;
  }

  box.innerHTML = `
    <div class="colab-link-box__title">📓 Colab 실습 노트북 — <code>${filename}</code></div>
    <div class="colab-link-box__body">
      <a class="colab-link-box__btn" href="${colabUrl}" target="_blank" rel="noopener">
        <img src="${COLAB_BADGE}" alt="Open In Colab" />
      </a>
      <div class="colab-link-box__instructions">
        <strong>📌 실습 전 반드시 사본을 만드세요.</strong>
        <ol>
          <li>위 뱃지를 눌러 노트북을 엽니다 <em>(보기 전용으로 열립니다)</em>.</li>
          <li>상단 메뉴 <code>파일 → 드라이브에 사본 저장</code> 클릭.</li>
          <li>본인 Drive 의 <em>"Colab Notebooks"</em> 폴더에 사본이 생성됩니다.</li>
          <li>그 사본에서 자유롭게 수정·실행하세요 (원본·다른 학생에 영향 없음).</li>
        </ol>
      </div>
    </div>`;
  return box;
}

function renderColabLinks() {
  const markers = document.querySelectorAll("div.colab-link[data-notebook]");
  markers.forEach((marker) => {
    const key = marker.getAttribute("data-notebook");
    if (!(key in NOTEBOOK_IDS)) {
      console.warn(`[colab-links] Unknown notebook key: ${key}`);
      return;
    }
    const box = buildLinkBox(key, NOTEBOOK_IDS[key]);
    marker.replaceWith(box);
  });
}

// MkDocs Material 의 instant navigation 호환 — 페이지 전환 시마다 재실행
if (typeof document$ !== "undefined" && document$.subscribe) {
  document$.subscribe(renderColabLinks);
} else {
  document.addEventListener("DOMContentLoaded", renderColabLinks);
}
