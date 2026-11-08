// Один макет для пробы; смысловые данные и подписи читаются из Markdown.
export function makeSkeleton(spec,fontFamily) {
  if(spec.layout!=='loop-with-exit') throw new Error('Поддерживается только loop-with-exit');
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
