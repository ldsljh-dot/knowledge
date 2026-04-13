// slide-10.js — Content: Structure + Copywriting
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 10,
  title: 'Structure + Copywriting',
  subtitle: '',
  key_points: ['서론 15% 본문 70%', '후킹 제목 자동 생성', '길이 자가 점검 루프'],
  visual_type: 'mixed',
  speaker_script: 'Structure 단계는 원문을 서론 15%, 본문 70%, 결론 15% 비율로 분할합니다. 이어 Copywriting이 제목을 후킹 카피로 변환하고 불릿을 요약하죠. 핵심은 길이 자가 점검 루프입니다. 생성 즉시 글자 수를 카운트하고, 초과 시 단어를 축약하고 구조를 단순화합니다. 3회 내에 제한을 반드시 준수하죠.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('Structure + Copywriting', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Pie chart representation (15/70/15)
  // Left side: 3 segments as colored bars
  const segments = [
    { label: '서론', pct: '15%', color: theme.accent, y: 1.3 },
    { label: '본문', pct: '70%', color: theme.secondary, y: 2.2 },
    { label: '결론', pct: '15%', color: theme.light, y: 3.1 }
  ];

  segments.forEach(s => {
    // Label
    slide.addText(s.label, {
      x: 0.6, y: s.y, w: 1, h: 0.65,
      fontSize: 14, fontFace: 'Arial',
      color: theme.primary, bold: true,
      align: 'right', valign: 'middle'
    });
    // Bar
    const barW = s.pct === '15%' ? 1.2 : (s.pct === '70%' ? 3.2 : 1.2);
    slide.addShape("roundRect", {
      x: 1.8, y: s.y + 0.1, w: barW, h: 0.45,
      fill: { color: s.color },
      rectRadius: 0.06
    });
    // Percentage
    slide.addText(s.pct, {
      x: 1.8 + barW + 0.1, y: s.y + 0.1, w: 0.6, h: 0.45,
      fontSize: 14, fontFace: 'Arial',
      color: theme.primary, bold: true,
      align: 'left', valign: 'middle'
    });
  });

  // Right side: Self-check loop flowchart
  slide.addText('자가 점검 루프', {
    x: 5.5, y: 1.3, w: 4, h: 0.4,
    fontSize: 16, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  const steps = [
    { text: '① 불릿 작성', color: theme.accent },
    { text: '② 글자 수 카운트', color: theme.secondary },
    { text: '③ 초과 시 축약', color: theme.light },
    { text: '④ 3회 내 제한 준수', color: theme.accent }
  ];

  steps.forEach((step, i) => {
    const yPos = 1.85 + i * 0.65;
    slide.addShape("roundRect", {
      x: 5.5, y: yPos, w: 3.5, h: 0.5,
      fill: { color: step.color },
      rectRadius: 0.08
    });
    slide.addText(step.text, {
      x: 5.5, y: yPos, w: 3.5, h: 0.5,
      fontSize: 13, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });

    if (i < steps.length - 1) {
      slide.addText('▼', {
        x: 6.9, y: yPos + 0.52, w: 0.6, h: 0.2,
        fontSize: 10, fontFace: 'Arial',
        color: theme.accent, align: 'center', valign: 'middle'
      });
    }
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('10', {
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
  pres.writeFile({ fileName: "slide-10-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
