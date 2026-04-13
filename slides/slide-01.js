// slide-01.js — Cover
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'title',
  index: 1,
  title: 'Harness Engineering',
  subtitle: 'Rule-Skill-Feedback 아키텍처 심층 분석',
  key_points: [],
  visual_type: 'infographic',
  speaker_script: '안녕하세요. 오늘 발표할 주제는 Harness Engineering입니다. AI가 고품질 PPT를 스스로 생성할 수 있도록 구조화한 Rule-Skill-Feedback 프레임워크를 심층 분석해 보겠습니다. 이 하네스는 AI의 자의적 판단에 제약과 검증의 비계를 제공하는 엔지니어링입니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Left accent bar
  slide.addShape("rect", {
    x: 0, y: 0, w: 0.15, h: 5.625,
    fill: { color: theme.accent }
  });

  // Decorative top-right block
  slide.addShape("rect", {
    x: 8.5, y: 0, w: 1.5, h: 0.8,
    fill: { color: theme.accent }
  });

  // Title text
  slide.addText('Harness Engineering', {
    x: 1, y: 1.5, w: 8, h: 1.5,
    fontSize: 52, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Subtitle
  slide.addText('Rule-Skill-Feedback 아키텍처 심층 분석', {
    x: 1, y: 3.2, w: 7, h: 0.8,
    fontSize: 22, fontFace: 'Arial',
    color: theme.secondary, bold: false, align: 'left'
  });

  // Bottom accent line
  slide.addShape("rect", {
    x: 1, y: 4.5, w: 3, h: 0.05,
    fill: { color: theme.accent }
  });

  // Section label
  slide.addText('AI PPT Generation Pipeline', {
    x: 1, y: 4.7, w: 5, h: 0.4,
    fontSize: 14, fontFace: 'Arial',
    color: theme.secondary, bold: false, align: 'left'
  });

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { primary: "023047", secondary: "219ebc", accent: "ffb703", light: "8ecae6", bg: "f2f5f7" };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-01-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
