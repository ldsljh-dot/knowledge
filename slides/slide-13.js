// slide-13.js — Content: Validation + PPTX Generation
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 13,
  title: '검증 + PPTX 생성',
  subtitle: '',
  key_points: ['4가지 체크리스트', '2-gram 중복 검사', 'JS 모듈식 컴파일'],
  visual_type: 'mixed',
  speaker_script: 'Feedback은 4가지 체크리스트로 검증합니다. 텍스트 길이, 논리적 흐름, 2-gram 기반 중복 검사, 필수 필드 포함 여부죠. 위반 시 해당 슬라이드만 재작성하며 최대 3회 시도합니다. 검증 통과 후 PPTX Generator가 JS 모듈 파일들을 컴파일하여 최종 프레젠테이션을 생성합니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('검증 + PPTX 생성', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Left: 4 checklist items
  const checks = [
    { icon: '✓', label: '텍스트 길이', desc: '불릿 수/길이, 제목 길이' },
    { icon: '✓', label: '논리적 흐름', desc: '슬라이드 간 연결성' },
    { icon: '✓', label: '중복 검사', desc: '2-gram Jaccard ≥ 0.4' },
    { icon: '✓', label: '포맷 적합', desc: '필수 필드 포함' }
  ];

  checks.forEach((c, i) => {
    const yPos = 1.25 + i * 0.7;
    // Checkbox
    slide.addShape("roundRect", {
      x: 0.6, y: yPos, w: 0.4, h: 0.4,
      fill: { color: theme.accent },
      rectRadius: 0.06
    });
    slide.addText(c.icon, {
      x: 0.6, y: yPos, w: 0.4, h: 0.4,
      fontSize: 14, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });
    // Label
    slide.addText(c.label, {
      x: 1.15, y: yPos, w: 2, h: 0.3,
      fontSize: 14, fontFace: 'Arial',
      color: theme.primary, bold: true, align: 'left'
    });
    slide.addText(c.desc, {
      x: 1.15, y: yPos + 0.3, w: 2.5, h: 0.25,
      fontSize: 11, fontFace: 'Arial',
      color: theme.secondary, bold: false, align: 'left'
    });
  });

  // Right: Compilation flow
  slide.addText('컴파일 흐름', {
    x: 5, y: 1.25, w: 4, h: 0.4,
    fontSize: 16, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // JS files → compile.js → PPTX
  const compileSteps = [
    { text: 'slide-01.js ~ slide-14.js', color: theme.secondary },
    { text: '▶  compile.js', color: theme.accent },
    { text: '▶  presentation.pptx', color: theme.primary }
  ];

  compileSteps.forEach((step, i) => {
    const yPos = 1.85 + i * 0.75;
    slide.addShape("roundRect", {
      x: 5, y: yPos, w: 4.5, h: 0.55,
      fill: { color: step.color },
      rectRadius: 0.08
    });
    slide.addText(step.text, {
      x: 5, y: yPos, w: 4.5, h: 0.55,
      fontSize: 13, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });

    if (i < compileSteps.length - 1) {
      slide.addText('▼', {
        x: 6.9, y: yPos + 0.57, w: 0.6, h: 0.2,
        fontSize: 10, fontFace: 'Arial',
        color: theme.accent, align: 'center', valign: 'middle'
      });
    }
  });

  // Rewrite loop note at bottom
  slide.addShape("roundRect", {
    x: 0.5, y: 4.3, w: 9, h: 0.55,
    fill: { color: 'FFFFFF' },
    rectRadius: 0.1,
    line: { color: theme.light, width: 0.5 }
  });
  slide.addText('🔄 재작성 루프: 위반 시 해당 슬라이드만 수정 → 최대 3회 시도 → 통과 시 Phase 6 진행', {
    x: 0.7, y: 4.3, w: 8.6, h: 0.55,
    fontSize: 13, fontFace: 'Arial',
    color: theme.primary, bold: false,
    align: 'left', valign: 'middle'
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('13', {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fontSize: 11, fontFace: 'Arial',
    color: 'FFFFFF', bold: true,
    align: 'center', valign: 'middle'
  });

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { primary: "023047", secondary: "219ebc", accent: "ffb703", light: "8ecae6", bg: "f2f5f7" };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-13-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
