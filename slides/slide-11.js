// slide-11.js — Content: Visualization + Scripting
const pptxgen = require("pptxgenjs");

const slideConfig = {
  type: 'content',
  index: 11,
  title: 'Visualization + Scripting',
  subtitle: '',
  key_points: ['6가지 시각 자료 타입', '슬라이드당 150자 원고', '불릿 수별 레이아웃'],
  visual_type: 'table',
  speaker_script: 'Visualization은 6가지 시각 자료 타입 중 최적의 것을 선택합니다. 그래프, 다이어그램, 이미지, 아이콘, 테이블, 인포그래픽이죠. 불릿이 1개면 인포그래픽, 2개면 분할 레이아웃, 3개면 3칸 카드를 추천합니다. Scripting은 슬라이드당 약 150~200자 분량의 발표 원고를 작성합니다.'
};

function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Title
  slide.addText('Visualization + Scripting', {
    x: 0.5, y: 0.35, w: 8, h: 0.6,
    fontSize: 36, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  // Accent line
  slide.addShape("rect", {
    x: 0.5, y: 0.95, w: 2, h: 0.04,
    fill: { color: theme.accent }
  });

  // Left: 6 visual types in 2x3 grid
  const vizTypes = [
    { icon: '📊', label: 'Graph' },
    { icon: '🔷', label: 'Diagram' },
    { icon: '🖼', label: 'Image' },
    { icon: '⭐', label: 'Icon' },
    { icon: '📋', label: 'Table' },
    { icon: '💡', label: 'Infographic' }
  ];

  vizTypes.forEach((v, i) => {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const xPos = 0.5 + col * 2.2;
    const yPos = 1.25 + row * 0.8;

    slide.addShape("roundRect", {
      x: xPos, y: yPos, w: 2, h: 0.65,
      fill: { color: i % 2 === 0 ? theme.accent : theme.secondary },
      rectRadius: 0.08
    });
    slide.addText(v.icon + '  ' + v.label, {
      x: xPos, y: yPos, w: 2, h: 0.65,
      fontSize: 14, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });
  });

  // Right: Script structure
  slide.addText('스크립트 구조', {
    x: 5.2, y: 1.25, w: 4, h: 0.4,
    fontSize: 16, fontFace: 'Arial',
    color: theme.primary, bold: true, align: 'left'
  });

  const scriptParts = [
    { label: '서문', text: '"먼저 이 슬라이드에서는~"', color: theme.accent },
    { label: '본문', text: '"(불릿 1) ...입니다."', color: theme.secondary },
    { label: '연결', text: '"다음 슬라이드에서는~"', color: theme.light }
  ];

  scriptParts.forEach((s, i) => {
    const yPos = 1.8 + i * 0.9;
    // Label
    slide.addShape("roundRect", {
      x: 5.2, y: yPos, w: 0.8, h: 0.55,
      fill: { color: s.color },
      rectRadius: 0.06
    });
    slide.addText(s.label, {
      x: 5.2, y: yPos, w: 0.8, h: 0.55,
      fontSize: 13, fontFace: 'Arial',
      color: 'FFFFFF', bold: true,
      align: 'center', valign: 'middle'
    });
    // Content
    slide.addShape("roundRect", {
      x: 6.15, y: yPos, w: 3.3, h: 0.55,
      fill: { color: 'FFFFFF' },
      rectRadius: 0.06,
      line: { color: theme.light, width: 0.5 }
    });
    slide.addText(s.text, {
      x: 6.25, y: yPos, w: 3.1, h: 0.55,
      fontSize: 12, fontFace: 'Arial',
      color: theme.primary, bold: false,
      align: 'left', valign: 'middle'
    });
  });

  // Bullet-to-layout rule at bottom
  slide.addText('불릿 수 → 레이아웃: 1개=인포그래픽  |  2개=분할  |  3개=3칸 카드', {
    x: 0.5, y: 4.2, w: 9, h: 0.4,
    fontSize: 13, fontFace: 'Arial',
    color: theme.secondary, bold: false,
    align: 'left', valign: 'middle'
  });

  // Page number badge
  slide.addShape("oval", {
    x: 9.3, y: 5.1, w: 0.4, h: 0.4,
    fill: { color: theme.accent }
  });
  slide.addText('11', {
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
  pres.writeFile({ fileName: "slide-11-preview.pptx" });
}

module.exports = { createSlide, slideConfig };
