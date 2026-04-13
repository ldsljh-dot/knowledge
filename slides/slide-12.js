// slide-12.js — Section Divider: Feedback
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'section_divider',
  index: 12,
  title: '04 Feedback',
  subtitle: '자가 검증과 재작성 루프',
  key_points: [],
  visual_type: 'infographic',
  speaker_script: '파트 4입니다. 생성된 슬라이드를 검증하고 개선하는 Feedback 루프를 살펴보겠습니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  // Circular arrow decoration (simplified)
  slide.addShape("oval", {
    x: 7.8, y: 0.3, w: 1.5, h: 1.5,
    fill: { color: theme.accent }
  });
  slide.addShape("oval", {
    x: 8.05, y: 0.55, w: 1, h: 1,
    fill: { color: theme.primary }
  });

  // Large section number
  slide.addText('04', {
    x: 2, y: 0.8, w: 6, h: 2.5,
    fontSize: 96, fontFace: 'Arial',
    color: theme.accent, bold: true,
    align: 'center', valign: 'middle'
  });

  // Section title
  slide.addText('Feedback', {
    x: 1, y: 3.2, w: 8, h: 0.8,
    fontSize: 36, fontFace: 'Arial',
    color: theme.light, bold: true,
    align: 'center'
  });

  // Subtitle
  slide.addText('자가 검증과 재작성 루프', {
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
  slide.addText('12', {
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
  pres.writeFile({ fileName: "slide-12-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
