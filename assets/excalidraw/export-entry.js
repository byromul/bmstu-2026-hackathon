import {convertToExcalidrawElements, exportToSvg, FONT_FAMILY} from '@excalidraw/excalidraw';
import {makeSkeleton} from './graph-template.js';
window.renderLectureDiagram = async (spec) => {
  const skeleton = makeSkeleton(spec, FONT_FAMILY.Helvetica);
  const positions = new Map(skeleton.map(element => [element.id, element]));
  const elements = convertToExcalidrawElements(skeleton, {regenerateIds:false});
  for (const element of elements) {
    element.updated=0; element.version=1; element.versionNonce=element.seed;
    if(element.type==='text' && element.customData?.boxWidth) {
      const original = positions.get(element.id);
      element.x = original.x + (element.customData.boxWidth-element.width)/2;
      element.y = original.y;
    }
  }
  const appState={viewBackgroundColor:'#fafaf7',exportBackground:false,exportWithDarkMode:false,
    exportEmbedScene:false,currentItemFontFamily:FONT_FAMILY.Helvetica};
  const svg=await exportToSvg({elements,appState,files:{},exportPadding:24});
  const external=[...svg.querySelectorAll('[href], [src]')].map(el=>el.getAttribute('href')||el.getAttribute('src'))
    .filter(url=>url&&!url.startsWith('#')&&!url.startsWith('data:'));
  if(external.length) throw new Error('Внешние ресурсы SVG: '+external.join(', '));
  return {svg:new XMLSerializer().serializeToString(svg),
    scene:{type:'excalidraw',version:2,source:'lecture-excalidraw-trial',elements,appState,files:{}},
    summary:{elements:elements.length,arrows:elements.filter(el=>el.type==='arrow').length,
      nodes:elements.filter(el=>el.type==='rectangle').length,fontFamily:FONT_FAMILY.Helvetica}};
};
