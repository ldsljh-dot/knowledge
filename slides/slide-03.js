// slide-03.js — Section Divider: Architecture
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'section_divider',
  index: 3,
  title: '01 아키텍처',
  subtitle: 'Rule-Skill-Feedback 프레임워크',
  key_points: [],
  visual_type: 'infographic',
  speaker_script: '파트 1입니다. 하네스 아키텍처의 전체 구조를 살펴보겠습니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };

  // Large section number
  slide.addText('01', {
    x: 2, y: 0.8, w: 6, h: 2.5,
    fontSize: 96, fontFace: 'Arial',
    color: theme.accent, bold: true,
    align: 'center', valign: 'middle'
  });

  // Section title
  slide.addText('아키텍처', {
    x: 1, y: 3.2, w: 8, h: 0.8,
    fontSize: 36, fontFace: 'Arial',
    color: theme.light, bold: true,
    align: 'center'
  });

  // Subtitle
  slide.addText('Rule-Skill-Feedback 프레임워크', {
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
  slide.addText('3', {
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
  pres.writeFile({ fileName: "slide-03-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
