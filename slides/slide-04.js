// slide-04.js — Content: What is Harness
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 4,
  title: '하네스란 무엇인가',
  subtitle: '',
  key_points: ['AI 자의성 통제 가드레일', '구조적 비계(Scaffold)', 'RSF 순환 구조'],
  visual_type: 'diagram',
  speaker_script: '하네스는 AI의 자의적 판단을 통제하는 구조적 비계입니다. 말 그대로 AI가 작업을 수행할 때 벗어날 수 없는 가드레일을 설정하죠. 원문 데이터가 입력되면 Rules 레이어가 제약 조건을 정의하고, Skills 레이어가 단계별 변환을 수행하며, Feedback 레이어가 결과를 검증합니다. 이 3계층이 하나의 엔진으로 작동하죠.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('하네스란 무엇인가', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Left: 3 bullet cards
  const bullets = [
    { icon: '🔒', text: 'AI 자의성 통제 가드레일' },
    { icon: '🏗', text: '구조적 비계(Scaffold)' },
    { icon: '🔄', text: 'RSF 순환 구조' }
  ];

  bullets.forEach((b, i) => {
    const yPos = 1.2 + i * 1.0;
    // Card background
    slide.addShape("roundRect", {
      x: 0.5, y: yPos, w: 3.8, h: 0.75,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.1,
      line: { color: theme.light, width: 0.5 }
    });
    // Icon
    slide.addText(b.icon, {
      x: 0.6, y: yPos + 0.08, w: 0.5, h: 0.55,
      fontSize: 22, fontFace: 'Arial',
      color: theme.primary, align: 'center', valign: 'middle'
    });
    // Text
    slide.addText(b.text, {
      x: 1.2, y: yPos + 0.1, w: 2.9, h: 0.5,
      fontSize: 15, fontFace: 'Arial',
      color: theme.primary, bold: false, align: 'left', valign: 'middle'
    });
  });

  // Right: Architecture diagram
  // Background box
  slide.addShape("roundRect", {
    x: 4.8, y: 1.2, w: 4.7, h: 3.5,
    fill: { color: theme.primary },
    rectRadius: 0.1
  });

  // Layer boxes
  const layers = [
    { label: 'RULES', color: theme.accent, y: 1.5 },
    { label: 'SKILLS', color: theme.secondary, y: 2.45 },
    { label: 'FEEDBACK', color: theme.light, y: 3.4 }
  ];

  layers.forEach((layer, i) => {
    slide.addShape("roundRect", {
      x: 5.2, y: layer.y, w: 3.8, h: 0.7,
      fill: { color: layer.color },
      rectRadius: 0.08
    });
    slide.addText(layer.label, {
      x: 5.2, y: layer.y, w: 3.8, h: 0.7,
      fontSize: 18, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });

    // Arrow between layers
    if (i < layers.length - 1) {
      slide.addText('▼', {
        x: 6.8, y: layer.y + 0.72, w: 0.6, h: 0.25,
        fontSize: 12, fontFace: 'Arial',
        color: theme.light, align: 'center', valign: 'middle'
      });
    }
  });

  // Input/Output labels
  slide.addText('입력 →', {
    x: 4.9, y: 1.65, w: 1, h: 0.3,
    fontSize: 10, fontFace: 'Arial',
    color: theme.light, align: 'left', valign: 'middle'
  });
  slide.addText('→ 출력', {
    x: 8.2, y: 3.55, w: 1.2, h: 0.3,
    fontSize: 10, fontFace: 'Arial',
    color: theme.light, align: 'left', valign: 'middle'
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('4', {
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
  pres.writeFile({ fileName: "slide-04-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
