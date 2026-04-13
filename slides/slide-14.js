// slide-14.js — Conclusion
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'conclusion',
  index: 14,
  title: '하네스 핵심 요약',
  subtitle: '',
  key_points: ['Rules = 제약과 가드레일', 'Skills = 콘텐츠 변환', 'Feedback = 검증과 개선'],
  visual_type: 'infographic',
  speaker_script: '하네스 엔지니어링의 핵심은 세 가지입니다. Rules는 제약과 가드레일을 정의하고, Skills는 원문을 고품질 콘텐츠로 변환하며, Feedback은 검증과 자기 개선을 수행합니다. 이 3계층이 결합하여 AI의 자의적 판단을 구조적으로 통제하죠. 결과적으로 누구나 일관된 고품질 PPT를 생성할 수 있습니다. 감사합니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('하네스 핵심 요약', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // 3 summary cards vertical
  const cards = [
    {
      icon: '🔒',
      keyword: 'Rules',
      desc: '제약과 가드레일',
      color: theme.accent
    },
    {
      icon: '⚙️',
      keyword: 'Skills',
      desc: '콘텐츠 변환',
      color: theme.secondary
    },
    {
      icon: '🔄',
      keyword: 'Feedback',
      desc: '검증과 개선',
      color: theme.light
    }
  ];

  cards.forEach((card, i) => {
    const yPos = 1.25 + i * 1.1;
    // Card background
    slide.addShape("roundRect", {
      x: 0.5, y: yPos, w: 9, h: 0.9,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.12,
      line: { color: card.color, width: 1.5 }
    });
    // Left accent bar
    slide.addShape("rect", {
      x: 0.5, y: yPos, w: 0.08, h: 0.9,
      fill: { color: card.color },
      rectRadius: 0.04
    });
    // Icon
    slide.addText(card.icon, {
      x: 0.8, y: yPos + 0.1, w: 0.6, h: 0.7,
      fontSize: 28, fontFace: 'Arial',
      color: theme.primary, align: 'center', valign: 'middle'
    });
    // Keyword
    slide.addText(card.keyword, {
      x: 1.6, y: yPos + 0.05, w: 2, h: 0.45,
      fontSize: 24, fontFace: 'Arial',
      color: card.color, bold: true, align: 'left'
    });
    // Description
    slide.addText(card.desc, {
      x: 1.6, y: yPos + 0.45, w: 3, h: 0.35,
      fontSize: 14, fontFace: 'Arial',
      color: theme.secondary, bold: false, align: 'left'
    });
    // Number badge on right
    slide.addShape("oval", {
      x: 8.7, y: yPos + 0.2, w: 0.5, h: 0.5,
      fill: { color: card.color }
    });
    slide.addText(String(i + 1), {
      x: 8.7, y: yPos + 0.2, w: 0.5, h: 0.5,
      fontSize: 16, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });
  });

  // Bottom message
  slide.addText('AI의 자의성을 구조로 통제한다', {
    x: 0.5, y: 4.7, w: 9, h: 0.5,
    fontSize: 18, fontFace: 'Arial',
    color: theme.primary, bold: true,
    align: 'center', valign: 'middle'
  });

  // Thank you
  slide.addText('감사합니다', {
    x: 0.5, y: 5.1, w: 9, h: 0.35,
    fontSize: 14, fontFace: 'Arial',
    color: theme.secondary, bold: false,
    align: 'center', valign: 'middle'
  });

  return slide;
}

if (require.main === module) {
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9';
  const theme = { primary: "023047", secondary: "219ebc", accent: "ffb703", light: "8ecae6", bg: "f2f5f7" };
  createSlide(pres, theme);
  pres.writeFile({ fileName: "slide-14-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
