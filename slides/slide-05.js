// slide-05.js — Content: 4-Stage Pipeline
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 5,
  title: '4단계 직렬 파이프라인',
  subtitle: '',
  key_points: ['Structure: 목차 추출', 'Copywriting: 제목+불릿', 'Vis+Script: 시각+원고'],
  visual_type: 'diagram',
  speaker_script: '하네스의 핵심은 4단계 직렬 파이프라인입니다. Structure 단계가 원문을 서론-본문-결론 구조로 분할하면, Copywriting이 후킹 제목과 간결한 불릿으로 변환합니다. Visualization은 각 슬라이드에 적합한 시각 자료를 기획하고, Scripting이 발표자 원고를 작성하죠. 각 단계의 출력이 다음 단계의 입력이 됩니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('4단계 직렬 파이프라인', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Pipeline diagram — 4 blocks horizontal
  const stages = [
    { num: '1', label: 'Structure', desc: '목차 추출', color: theme.accent, output: 'slide_outline' },
    { num: '2', label: 'Copywriting', desc: '제목+불릿', color: theme.secondary, output: 'enhanced_outline' },
    { num: '3', label: 'Visualization', desc: '시각 기획', color: theme.light, output: 'outline_w/_visuals' },
    { num: '4', label: 'Scripting', desc: '시각+원고', color: theme.accent, output: 'complete_slides' }
  ];

  const startX = 0.4;
  const boxW = 2.1;
  const boxH = 1.4;
  const gap = 0.2;

  stages.forEach((stage, i) => {
    const xPos = startX + i * (boxW + gap);
    const yPos = 1.5;

    // Main box
    slide.addShape("roundRect", {
      x: xPos, y: yPos, w: boxW, h: boxH,
      fill: { color: stage.color },
      rectRadius: 0.1
    });

    // Number
    slide.addText(stage.num, {
      x: xPos, y: yPos + 0.08, w: boxW, h: 0.35,
      fontSize: 14, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });

    // Label
    slide.addText(stage.label, {
      x: xPos, y: yPos + 0.4, w: boxW, h: 0.45,
      fontSize: 20, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });

    // Description
    slide.addText(stage.desc, {
      x: xPos, y: yPos + 0.85, w: boxW, h: 0.3,
      fontSize: 12, fontFace: 'Arial',
      color: 'FFFFFF', bold: false,
      align: 'center', valign: 'middle'
    });

    // Output label below
    slide.addShape("roundRect", {
      x: xPos + 0.2, y: yPos + boxH + 0.12, w: boxW - 0.4, h: 0.35,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.05,
      line: { color: stage.color, width: 0.5 }
    });
    slide.addText(stage.output, {
      x: xPos + 0.2, y: yPos + boxH + 0.12, w: boxW - 0.4, h: 0.35,
      fontSize: 9, fontFace: 'Arial',
      color: theme.primary, bold: false,
      align: 'center', valign: 'middle'
    });

    // Arrow between stages
    if (i < stages.length - 1) {
      const arrowX = xPos + boxW + 0.01;
      slide.addText('▶', {
        x: arrowX, y: yPos + 0.5, w: 0.18, h: 0.4,
        fontSize: 16, fontFace: 'Arial',
        color: theme.accent, bold: true,
        align: 'center', valign: 'middle'
      });
    }
  });

  // Bottom: key points cards
  const points = [
    { label: 'Structure:', detail: '목차 추출' },
    { label: 'Copywriting:', detail: '제목+불릿' },
    { label: 'Vis+Script:', detail: '시각+원고' }
  ];

  const cardY = 3.8;
  points.forEach((p, i) => {
    const xPos = 0.5 + i * 3.1;
    slide.addShape("roundRect", {
      x: xPos, y: cardY, w: 2.8, h: 0.7,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.1,
      line: { color: theme.light, width: 0.5 }
    });
    slide.addText(p.label, {
      x: xPos + 0.15, y: cardY + 0.05, w: 2.5, h: 0.3,
      fontSize: 13, fontFace: 'Arial',
      color: theme.accent, bold: true, align: 'left'
    });
    slide.addText(p.detail, {
      x: xPos + 0.15, y: cardY + 0.35, w: 2.5, h: 0.3,
      fontSize: 12, fontFace: 'Arial',
      color: theme.primary, bold: false, align: 'left'
    });
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('5', {
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
  pres.writeFile({ fileName: "slide-05-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
