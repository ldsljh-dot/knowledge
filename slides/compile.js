const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'PPT Harness';
pres.title = 'Harness Engineering';

// Vibrant & Tech palette
const theme = {
  primary: "023047",    // deep navy
  secondary: "219ebc",  // teal
  accent: "ffb703",     // amber
  light: "8ecae6",      // light blue
  bg: "f2f5f7"          // off-white
};

// Load and compile all slides
const slideCount = 14;
for (let i = 1; i <= slideCount; i++) {
  const num = String(i).padStart(2, '0');
  try {
    const slideModule = require(`./slide-${num}.js`);
    slideModule.createSlide(pres, theme);
    console.log(`✅ slide-${num}.js loaded`);
  } catch (e) {
    console.error(`❌ Failed to load slide-${num}.js: ${e.message}`);
  }
}

pres.writeFile({ fileName: './output/presentation.pptx' });
console.log(`\n🎉 PPTX compilation complete: ./output/presentation.pptx (${slideCount} slides)`);
