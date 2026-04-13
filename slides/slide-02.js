// slide-02.js — TOC
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'toc',
  index: 2,
  title: 'Agenda',
  subtitle: '',
  key_points: ['하네스 아키텍처', 'Rules: 절대 규칙', 'Skills + Feedback'],
  visual_type: 'infographic',
  speaker_script: '발표는 네 부분으로 진행됩니다. 첫째, 하네스 아키텍처의 전체 구조를 overview하고, 둘째, Rules 레이어의 절대적 제약 조건을 살펴보겠습니다. 셋째, 4단계 Skills 변환 엔진을 분석하고, 마지막으로 Feedback 검증 루프와 PPTX Generation 과정을 설명드리겠습니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText('Agenda', {
    x: 0.5, y: 0.4, w: 4, h: 0.7,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line under title
  slide.addShape("rect", {
    x: 0.5, y: 1.15, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  const items = [
    { num: '01', label: '하네스 아키텍처', desc: 'Rule-Skill-Feedback 개요' },
    { num: '02', label: 'Rules: 절대 규칙', desc: '텍스트 제약 · 톤 앤 매너' },
    { num: '03', label: 'Skills + Feedback', desc: '변환 엔진 · 검증 루프' }
  ];

  let yPos = 1.6;
  items.forEach((item, i) => {
    // Number circle
    slide.addShape("oval", {
      x: 0.7, y: yPos, w: 0.55, h: 0.55,
      fill: { color: theme.accent }
    });
    slide.addText(item.num, {
      x: 0.7, y: yPos, w: 0.55, h: 0.55,
      fontSize: 16, fontFace: 'Arial',
      color: theme.primary, bold: true,
      align: 'center', valign: 'middle'
    });

    // Label
    slide.addText(item.label, {
      x: 1.5, y: yPos + 0.02, w: 6, h: 0.4,
      fontSize: 20, fontFace: 'Arial',
      color: theme.primary, bold: true, align: 'left'
    });

    // Description
    slide.addText(item.desc, {
      x: 1.5, y: yPos + 0.38, w: 6, h: 0.3,
      fontSize: 13, fontFace: 'Arial',
      color: theme.secondary, bold: false, align: 'left'
    });

    // Divider line
    if (i < items.length - 1) {
      slide.addShape("rect", {
        x: 1.5, y: yPos + 0.72, w: 7.5, h: 0.01,
        fill: { color: theme.light }
      });
    }

    yPos += 0.95;
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('2', {
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
  pres.writeFile({ fileName: "slide-02-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
