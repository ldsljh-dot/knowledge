// slide-06.js — Section Divider: Rules
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'section_divider',
  index: 6,
  title: '02 Rules',
  subtitle: 'AI가 벗어날 수 없는 가드레일',
  key_points: [],
  visual_type: 'infographic',
  speaker_script: '파트 2입니다. Rules 레이어에서 정의하는 절대 규칙을 살펴보겠습니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  // Guardrail accent lines on left
  for (let i = 0; i < 5; i++) {
    slide.addShape("rect", {
      x: 1.5 + i * 0.25, y: 0.3, w: 0.06, h: 1.8,
      fill: { color: theme.accent }
    });
  }

  // Large section number
  slide.addText('02', {
    x: 2, y: 0.8, w: 6, h: 2.5,
    fontSize: 96, fontFace: 'Arial',
    color: theme.accent, bold: true,
    align: 'center', valign: 'middle'
  });

  // Section title
  slide.addText('Rules', {
    x: 1, y: 3.2, w: 8, h: 0.8,
    fontSize: 36, fontFace: 'Arial',
    color: theme.light, bold: true,
    align: 'center'
  });

  // Subtitle
  slide.addText('AI가 벗어날 수 없는 가드레일', {
    x: 1, y: 4.0, w: 8, h: 0.5,
    fontSize: 16, fontFace: 'Arial',
    color: theme.secondary, bold: false,
    align: 'center'
  });

  // Accent line
  slide.addShape("rect", {
    x: 4.2, y: 4.6, w: 1.6, h: 0.04,
    fill: { color: theme.accent }
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('6', {
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
  pres.writeFile({ fileName: "slide-06-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
