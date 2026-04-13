// slide-09.js — Section Divider: Skills
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'section_divider',
  index: 9,
  title: '03 Skills',
  subtitle: '콘텐츠 변환 4단계 엔진',
  key_points: [],
  visual_type: 'infographic',
  speaker_script: '파트 3입니다. 4단계 Skills 변환 엔진의 각 단계를 심층 분석합니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  // Gear-like decorative elements
  slide.addShape("oval", {
    x: 7.5, y: 0.5, w: 1.2, h: 1.2,
    fill: { color: theme.accent }
  });
  slide.addShape("oval", {
    x: 8.2, y: 1.2, w: 0.8, h: 0.8,
    fill: { color: theme.secondary }
  });

  // Large section number
  slide.addText('03', {
    x: 2, y: 0.8, w: 6, h: 2.5,
    fontSize: 96, fontFace: 'Arial',
    color: theme.accent, bold: true,
    align: 'center', valign: 'middle'
  });

  // Section title
  slide.addText('Skills', {
    x: 1, y: 3.2, w: 8, h: 0.8,
    fontSize: 36, fontFace: 'Arial',
    color: theme.light, bold: true,
    align: 'center'
  });

  // Subtitle
  slide.addText('콘텐츠 변환 4단계 엔진', {
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
  slide.addText('9', {
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
  pres.writeFile({ fileName: "slide-09-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
