// slide-07.js — Content: Text Constraints
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 7,
  title: '텍스트 제약의 미학',
  subtitle: '',
  key_points: ['불릿 ≤ 3개', '불릿 ≤ 20자', '제목 ≤ 30자'],
  visual_type: 'infographic',
  speaker_script: '하네스에서 가장 엄격한 규칙이 텍스트 제약입니다. 슬라이드당 불릿은 최대 3개, 불릿당 글자 수는 20자, 제목은 30자를 넘을 수 없죠. 예를 들어 55자 불릿은 실패지만, 13자는 통과합니다. 이 제약이 발표 집중도를 보장하죠.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('텍스트 제약의 미학', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // 3 constraint cards horizontal
  const constraints = [
    { icon: '📋', value: '≤ 3개', label: '불릿 수' },
    { icon: '✏️', value: '≤ 20자', label: '불릿 길이' },
    { icon: '📝', value: '≤ 30자', label: '제목 길이' }
  ];

  constraints.forEach((c, i) => {
    const xPos = 0.5 + i * 3.1;
    // Card
    slide.addShape("roundRect", {
      x: xPos, y: 1.3, w: 2.8, h: 1.8,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.12,
      line: { color: theme.accent, width: 1 }
    });
    // Icon
    slide.addText(c.icon, {
      x: xPos, y: 1.4, w: 2.8, h: 0.5,
      fontSize: 24, fontFace: 'Arial',
      color: theme.primary, align: 'center', valign: 'middle'
    });
    // Value
    slide.addText(c.value, {
      x: xPos, y: 1.9, w: 2.8, h: 0.6,
      fontSize: 36, fontFace: 'Arial',
      color: theme.accent, bold: true, align: 'center', valign: 'middle'
    });
    // Label
    slide.addText(c.label, {
      x: xPos, y: 2.55, w: 2.8, h: 0.35,
      fontSize: 14, fontFace: 'Arial',
      color: theme.secondary, bold: false, align: 'center', valign: 'middle'
    });
  });

  // Pass/Fail examples
  slide.addText('통과 / 실패 예시', {
    x: 0.5, y: 3.4, w: 4, h: 0.4,
    fontSize: 16, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Pass example
  slide.addShape("roundRect", {
    x: 0.5, y: 3.85, w: 4.2, h: 0.55,
    fill: { color: 'E8F5E9' },
    rectRadius: 0.08
  });
  slide.addText('✅ "AI 통제의 구조적 비계" (13자)', {
    x: 0.6, y: 3.85, w: 4, h: 0.55,
    fontSize: 12, fontFace: 'Arial',
    color: '#2E7D32', bold: false, align: 'left', valign: 'middle'
  });

  // Fail example
  slide.addShape("roundRect", {
    x: 5.3, y: 3.85, w: 4.2, h: 0.55,
    fill: { color: 'FFEBEE' },
    rectRadius: 0.08
  });
  slide.addText('❌ "인공지능은 인간의 지능을 모방하는 시스템" (55자)', {
    x: 5.4, y: 3.85, w: 4, h: 0.55,
    fontSize: 12, fontFace: 'Arial',
    color: '#C62828', bold: false, align: 'left', valign: 'middle'
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('7', {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fontSize: 12, fontFace: 'Arial',
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
  pres.writeFile({ fileName: "slide-07-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
