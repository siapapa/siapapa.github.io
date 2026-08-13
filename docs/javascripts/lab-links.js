/* ============================================================
 * 실습 자산 저장소 링크 자동 삽입
 * ------------------------------------------------------------
 * Colab 기반 과정은 colab-links.js 를 씁니다. 하지만 Omniverse 계열
 * 과정은 실습 자산이 노트북이 아니라 USD 파일 · Python 스크립트 ·
 * Kit 확장이고, 로컬 RTX PC 에서 실행하므로 Colab 링크가 맞지 않습니다.
 *
 * 이 스크립트는 대신 **저장소 주소와 실행 방법**을 안내하는 박스를 넣습니다.
 *
 * 사용법:
 *   1) 아래 LAB_REPOS 에 과정별 저장소 정보를 채웁니다.
 *      저장소가 아직 없으면 url 을 빈 문자열로 두세요 — "준비 중"으로
 *      표시되고, 공개 후 url 만 채우면 됩니다.
 *
 *   2) 강의 페이지에 다음 한 줄을 두면 자동으로 렌더링됩니다.
 *        <div class="lab-link" data-course="omniverse-digital-twin"></div>
 * ============================================================ */

const LAB_REPOS = {
  "omniverse-digital-twin": {
    url: "",                       // 예: https://github.com/siapapa/omniverse-dt-labs
    subdir: "course_a",
    requirements: "requirements/usd.txt",
    note: "GPU 없이 되는 실습부터 시작할 수 있습니다.",
  },
  "isaac-sim-robotics": {
    url: "",
    subdir: "course_b",
    requirements: "requirements/isaac.txt",
    note: "Isaac Sim 이 제공하는 파이썬으로 실행해야 합니다.",
  },
};

function buildLabBox(courseKey, info) {
  const box = document.createElement("div");
  box.className = "lab-link-box";

  if (!info.url) {
    box.classList.add("lab-link-box--pending");
    box.innerHTML = `
      <div class="lab-link-box__title">🧪 실습 자산 — <code>${info.subdir}/</code></div>
      <div class="lab-link-box__body">
        <span class="lab-link-box__pending">⚙️ 저장소 공개 준비 중입니다.</span>
        <div class="lab-link-box__instructions">
          개강 전 GitHub 저장소로 공개되며, 이 자리에 주소가 표시됩니다.
          그 전까지는 강의실 공유폴더 또는 USB 로 배포합니다.
        </div>
      </div>`;
    return box;
  }

  box.innerHTML = `
    <div class="lab-link-box__title">🧪 실습 자산 — <code>${info.subdir}/</code></div>
    <div class="lab-link-box__body">
      <a class="lab-link-box__btn" href="${info.url}" target="_blank" rel="noopener">
        저장소 열기 ↗
      </a>
      <div class="lab-link-box__instructions">
        <ol>
          <li><code>git clone ${info.url}</code></li>
          <li><code>pip install -r ${info.requirements}</code></li>
          <li><code>cd ${info.subdir}/</code> 후 번호 순서대로 진행</li>
        </ol>
        <p>${info.note}</p>
      </div>
    </div>`;
  return box;
}

function renderLabLinks() {
  document.querySelectorAll("div.lab-link[data-course]").forEach((marker) => {
    const key = marker.getAttribute("data-course");
    if (!(key in LAB_REPOS)) {
      console.warn(`[lab-links] Unknown course key: ${key}`);
      return;
    }
    marker.replaceWith(buildLabBox(key, LAB_REPOS[key]));
  });
}

// MkDocs Material 의 instant navigation 호환
if (typeof document$ !== "undefined" && document$.subscribe) {
  document$.subscribe(renderLabLinks);
} else {
  document.addEventListener("DOMContentLoaded", renderLabLinks);
}
