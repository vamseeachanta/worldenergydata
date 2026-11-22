function interval(c){
const top=Math.max(1,...c.q3.filter(x=>x!==null))*1.8;
const under=c.bands.map((b,i)=>({type:'scatter',mode:'markers',x:[c.median[i]],y:[b],showlegend:false,hoverinfo:'skip',marker:{size:1,opacity:0},
error_x:{type:'data',symmetric:false,array:[c.q3[i]-c.median[i]],arrayminus:[c.median[i]-c.q1[i]],thickness:7,width:0,color:c.edge}}));
const traces=under.concat(c.bands.map((b,i)=>({type:'scatter',mode:'markers',name:b,x:[c.median[i]],y:[b],showlegend:false,
error_x:{type:'data',symmetric:false,array:[c.q3[i]-c.median[i]],arrayminus:[c.median[i]-c.q1[i]],thickness:5,width:0,color:c.colours[i]},
marker:{color:c.colours[i],size:10,line:{color:'#0b3d5c',width:1}},
hovertemplate:b+'<br>Median '+c.shown[i][1]+' d<br>Quartiles '+c.shown[i][0]+' to '+c.shown[i][2]+' d<br>'+c.nlabel[i]+'<extra></extra>'})));
const ann=c.bands.map((b,i)=>({x:c.q3[i],y:b,text:c.label[i],xanchor:'left',xshift:6,showarrow:false,font:{size:11}}));
return [traces,{margin:{l:130,r:16,t:8,b:44},xaxis:{title:'Days (d)',range:[0,top],rangemode:'tozero'},yaxis:{categoryorder:'array',categoryarray:c.bands,autorange:'reversed',ticksuffix:'  '},annotations:ann}];
}
function grouped(c){
const traces=c.bands.map((b,i)=>{const r=c.stages.map(s=>c.rows.find(x=>x.stage===s&&x.band===b));
return {type:'bar',name:b,x:c.ticks,y:r.map(x=>x.median),text:r.map(x=>x.shown),textposition:'outside',cliponaxis:false,
customdata:r.map(x=>[x.stage,x.nlabel,x.shown]),marker:{color:c.colours[i],line:{color:c.edge,width:.6}},
hovertemplate:'%{customdata[0]}<br>'+b+'<br>Median %{customdata[2]} d<br>%{customdata[1]}<extra></extra>'};});
return [traces,{barmode:'group',bargap:.22,bargroupgap:.06,margin:{l:60,r:12,t:60,b:60},legend:{orientation:'h',x:0,y:1.02,yanchor:'bottom',title:{text:'Water depth '}},
xaxis:{type:'category'},yaxis:{title:'Median days (d)',range:[0,c.top],rangemode:'tozero'}}];
}
function byband(c){
const traces=c.bands.map((b,i)=>{const r=c.stages.map(s=>c.rows.find(x=>x.stage===s&&x.band===b));
return {type:'bar',orientation:'h',name:b,showlegend:false,y:[r.map(()=>b),c.stages],x:r.map(x=>x.median),text:r.map(x=>x.shown),textposition:'outside',cliponaxis:false,
customdata:r.map(x=>[x.stage,x.nlabel,x.shown]),marker:{color:c.colours[i],line:{color:c.edge,width:.6}},
hovertemplate:'%{customdata[0]}<br>'+b+'<br>Median %{customdata[2]} d<br>%{customdata[1]}<extra></extra>'};});
return [traces,{margin:{l:310,r:24,t:8,b:50},bargap:.18,xaxis:{title:'Median days (d)',range:[0,c.top],rangemode:'tozero'},
yaxis:{type:'multicategory',autorange:'reversed',ticksuffix:'  '}}];
}
