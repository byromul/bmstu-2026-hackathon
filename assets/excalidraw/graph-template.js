// Один макет для пробы; смысловые данные и подписи читаются из Markdown.
export function makeSkeleton(spec,fontFamily) {
  if(spec.layout!=='loop-with-exit') return makeOverview(spec,fontFamily);
  const positions={context:[60,60],model:[600,60],answer:[1140,60],result:[60,390],tool:[600,390]};
  const expected=['context:model','model:tool','tool:result','result:context','model:answer'];
  if(Object.keys(spec.nodes).sort().join()!==Object.keys(positions).sort().join()) throw new Error('Неверный набор узлов');
  if(spec.connections.map(e=>`${e.from}:${e.to}`).sort().join()!==expected.sort().join()) throw new Error('Неверные связи цикла');
  const hash=id=>[...id].reduce((n,c)=>(Math.imul(n,31)+c.charCodeAt(0))>>>0,7)&0x7fffffff;
  const base=id=>({id,seed:hash(id),versionNonce:hash(id),strokeWidth:1.8,roughness:.55,
    strokeColor:'#4e6666',backgroundColor:'transparent',fillStyle:'solid',opacity:100});
  const width=330,height=170,elements=[];
  for(const [id,[x,y]] of Object.entries(positions)) {
    const node=spec.nodes[id],groupIds=[`group-${id}`];
    elements.push({...base(id),type:'rectangle',x,y,width,height,roundness:{type:3},groupIds,
      backgroundColor:id==='answer'?'#e9f1df':id==='model'?'#dfeeea':'#f1f5f2',strokeColor:id==='model'?'#17615f':'#617470'});
    elements.push({...base(`${id}-title`),type:'text',x:x+20,y:y+26,text:node.title,fontSize:32,fontFamily,
      textAlign:'center',strokeColor:'#17252b',groupIds,customData:{boxWidth:width-40}});
    elements.push({...base(`${id}-detail`),type:'text',x:x+20,y:y+85,text:node.detail,fontSize:25,fontFamily,
      textAlign:'center',strokeColor:'#536460',groupIds,customData:{boxWidth:width-40}});
  }
  const routes={
    'context:model':{x:398,y:145,points:[[0,0],[194,0]],label:[405,101,185]},
    'model:answer':{x:938,y:145,points:[[0,0],[194,0]],label:[950,101,180]},
    'model:tool':{x:765,y:238,points:[[0,0],[0,144]],label:[795,292,230]},
    'tool:result':{x:592,y:475,points:[[0,0],[-194,0]],label:[400,413,190]},
    'result:context':{x:225,y:382,points:[[0,0],[0,-144]],label:[-10,284,215]}
  };
  const wrap=(text,limit)=>{const lines=[''];for(const word of text.split(' ')){const i=lines.length-1;if(lines[i]&&lines[i].length+word.length+1>limit)lines.push(word);else lines[i]+=(lines[i]?' ':'')+word;}return lines.join('\n');};
  for(const edge of spec.connections) {
    const key=`${edge.from}:${edge.to}`,route=routes[key],id=`edge-${edge.from}-${edge.to}`,groupIds=[`group-${id}`];
    elements.push({...base(id),type:'arrow',x:route.x,y:route.y,points:route.points,
      endArrowhead:'arrow',startArrowhead:null,strokeWidth:2.3,strokeColor:'#17615f',roughness:.45,
      start:{id:edge.from},end:{id:edge.to},groupIds});
    elements.push({...base(`${id}-label`),type:'text',x:route.label[0],y:route.label[1],
      text:wrap(edge.label,key==='result:context'||key==='tool:result'?14:25),fontSize:23,fontFamily,
      textAlign:'center',strokeColor:'#17615f',groupIds,customData:{boxWidth:route.label[2]}});
  }
  return elements;
}

// Компоновки для учебных схем. Подписи и смысл связей находятся в Markdown.
function makeOverview(spec,fontFamily) {
  const elements=[];
  const hash=id=>[...id].reduce((n,c)=>(Math.imul(n,31)+c.charCodeAt(0))>>>0,7)&0x7fffffff;
  const base=id=>({id,seed:hash(id),versionNonce:hash(id),strokeWidth:1.8,roughness:.55,
    strokeColor:'#617470',backgroundColor:'transparent',fillStyle:'solid',opacity:100});
  const text=(id,value,x,y,width,size=29,color='#17252b')=>elements.push({...base(id),type:'text',x,y,text:value,fontSize:size,fontFamily,textAlign:'center',strokeColor:color,customData:{boxWidth:width}});
  const rect=(id,x,y,width,height,fill='#f1f5f2')=>elements.push({...base(id),type:'rectangle',x,y,width,height,roundness:{type:3},backgroundColor:fill});
  const node=(id,x,y,width=360,height=140)=>{
    const n=spec.nodes[id];if(!n)throw new Error('Нет узла '+id);
    rect(id,x,y,width,height,n.accent?'#dfeeea':'#f1f5f2');
    text(id+'-title',n.title,x+12,y+25,width-24,31);
    text(id+'-detail',n.detail,x+12,y+(height<120?64:83),width-24,24,'#536460');
  };
  const arrow=(edge,x,y,points,both=false)=>{
    elements.push({...base('edge-'+edge.from+'-'+edge.to),type:'arrow',x,y,points,
      strokeColor:'#17615f',strokeWidth:2.3,roughness:.45,startArrowhead:both?'arrow':null,endArrowhead:'arrow',
      start:{id:edge.from},end:{id:edge.to}});
  };
  if(spec.layout==='six-stage-cycle') {
    const pos={requirements:[40,30],design:[540,30],code:[1040,30],check:[1040,310],release:[540,310],operate:[40,310]};
    for(const [id,[x,y]]of Object.entries(pos))node(id,x,y);
    for(const e of spec.connections){
      const [x,y]=pos[e.from],[tx,ty]=pos[e.to];
      if(y===ty){const right=tx>x;arrow(e,x+(right?368:-8),y+70,[[0,0],[(right?132:-132),0]]);}
      else{const down=ty>y;arrow(e,x+180,y+(down?148:-8),[[0,0],[0,down?132:-132]]);}
    }
  }else if(spec.layout==='training-and-generation') {
    text('training-label',spec.lanes[0],40,0,1360,27,'#536460');
    text('generation-label',spec.lanes[1],40,240,1360,27,'#536460');
    const pos={examples:[40,55],learning:[540,55],trained:[1040,55],context:[40,295],model:[540,295],token:[1040,295]};
    for(const [id,[x,y]]of Object.entries(pos))node(id,x,y);
    for(const e of spec.connections){
      const [x,y]=pos[e.from];
      if(e.from==='token')arrow(e,1220,443,[[0,0],[0,65],[-1000,65],[-1000,0]]);
      else arrow(e,x+368,y+70,[[0,0],[132,0]]);
    }
    text('repeat-label',spec.return_label,400,463,640,24,'#17615f');
  }else if(spec.layout==='harness-components') {
    // Граница — группировка компонентов, стрелки не задают последовательность внутри неё.
    rect('harness-boundary',480,0,560,440,'#f5f7f2');
    text('boundary-label',spec.boundary,490,18,540,26,'#17615f');
    node('model',0,60,360,140);
    node('session',510,70,500,100);node('context',510,190,500,100);node('tools',510,310,500,100);
    node('environment',1160,300,360,140);
    for(const e of spec.connections){
      if(e.from==='session') {arrow(e,502,125,[[0,0],[-134,0]],true);text('model-link',e.label,0,220,360,24,'#17615f');}
      else {arrow(e,1018,365,[[0,0],[134,0]],true);text('environment-link',e.label,1160,250,360,24,'#17615f');}
    }
  }else throw new Error('Неизвестная компоновка: '+spec.layout);
  return elements;
}
