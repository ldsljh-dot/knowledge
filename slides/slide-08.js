// slide-08.js — Content: Tone & Manner
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 8,
  title: '톤 앤 매너 규칙',
  subtitle: '',
  key_points: ['전문적 친근 구어체', '~습니다 종결어미', '전문 용어 괄호 비유'],
  visual_type: 'mixed',
  speaker_script: '톤 앤 매너도 규칙으로 정의됩니다. 스크립트 스타일은 전문적이되 친근한 구어체, 문장 종결은 ~습니다/~하죠를 사용합니다. 전문 용어는 반드시 괄호 안에 짧은 비유를 추가하죠. 이로써 청중 누구나 내용을 이해할 수 있습니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('톤 앤 매너 규칙', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Left: 3 rules
  const rules = [
    { label: '전문적 친근 구어체', desc: 'professional_conversational' },
    { label: '~습니다 종결어미', desc: '문장 종결 규칙' },
    { label: '전문 용어 괄호 비유', desc: 'jargon_handling' }
  ];

  rules.forEach((r, i) => {
    const yPos = 1.25 + i * 0.85;
    // Number badge
    slide.addShape("oval", {
      x: 0.6, y: yPos, w: 0.4, h: 0.4,
      fill: { color: theme.accent }
    });
    slide.addText(String(i + 1), {
      x: 0.6, y: yPos, w: 0.4, h: 0.4,
      fontSize: 13, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });
    // Rule text
    slide.addText(r.label, {
      x: 1.15, y: yPos, w: 3.2, h: 0.3,
      fontSize: 15, fontFace: 'Arial',
      color: theme.primary, bold: true, align: 'left'
    });
    slide.addText(r.desc, {
      x: 1.15, y: yPos + 0.32, w: 3.2, h: 0.25,
      fontSize: 11, fontFace: 'Arial',
      color: theme.secondary, bold: false, align: 'left'
    });
  });

  // Right: Example box
  slide.addShape("roundRect", {
    x: 5, y: 1.25, w: 4.5, h: 3.2,
    fill: { color: 'FFFFFF' },
    rectRadius: 0.1,
    line: { color: theme.light, width: 0.5 }
  });

  // Example header
  slide.addShape("rect", {
    x: 5, y: 1.25, w: 4.5, h: 0.45,
    fill: { color: theme.primary },
    rectRadius: 0.1
  });
  slide.addText('📌 적용 예시', {
    x: 5.1, y: 1.25, w: 4.3, h: 0.45,
    fontSize: 14, fontFace: 'Arial',
    color: 'FFFFFF', bold: true,
    align: 'left', valign: 'middle'
  });

  // Example content
  slide.addText('"LLM(대규모 언어 모델,', {
    x: 5.2, y: 1.9, w: 4.1, h: 0.35,
    fontSize: 13, fontFace: 'Arial',
    color: theme.primary, bold: false,
    align: 'left', valign: 'middle'
  });
  slide.addText('사람 언어 패턴 학습)은', {
    x: 5.2, y: 2.3, w: 4.1, h: 0.35,
    fontSize: 13, fontFace: 'Arial',
    color: theme.primary, bold: false,
    align: 'left', valign: 'middle'
  });
  slide.addText('맥락 이해에 강합니다."', {
    x: 5.2, y: 2.7, w: 4.1, h: 0.35,
    fontSize: 13, fontFace: 'Arial',
    color: theme.primary, bold: false,
    align: 'left', valign: 'middle'
  });

  // Highlight annotation
  slide.addText('← 괄호 내 비유 추가', {
    x: 5.2, y: 3.2, w: 4, h: 0.3,
    fontSize: 11, fontFace: 'Arial',
    color: theme.accent, bold: false,
    align: 'left', valign: 'middle'
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('8', {
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
  pres.writeFile({ fileName: "slide-08-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
