'use strict';
const $=s=>document.querySelector(s), data=window.TURTLE_DATA, H=window.TurtleHistory, L=window.TurtleLive;
const themes={today:'今日 / 自我',romance:'感情',career:'事业 / 学业',friendship:'友情'};
let storage;try{storage=window.localStorage;}catch{storage={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');}};}
let historyState=H.read(storage), records=historyState.records, currentId=historyState.active_id;
function makeRecord(){const now=new Date();return {id:'demo-'+(globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random()),scanned_at:now.toISOString(),day:H.dayKey(now),hex:structuredClone(data.hexagrams.find(x=>x.hexagram_id===data.examples.hexagram_fixture.hexagram_id)),base:structuredClone(data.examples.base_reading),web:structuredClone(data.examples.web_reading),deep:{},questions:[],selected:'',content_origin:'demo'};}
const entryOpenedAt=new Date();
const historyOnly=/^\/history\/?$/.test(location.pathname),liveMode=L.entry(location.pathname).kind!=='none',liveClient=L.createClient();
const scanEntry=liveMode?{kind:'none'}:window.TurtleScan.resolve(location.hash,data.hexagrams,records);
let invalidEntry=liveMode?L.entry(location.pathname).kind==='invalid':scanEntry.kind==='invalid';
let liveReadingId=L.entry(location.pathname).readingId||null,liveState='pending',liveAuthorized=false,liveError=null,currentLiveRecord=null,questionDraft=null;
let record=liveMode||historyOnly?null:scanEntry.record||records.find(r=>r.id===currentId&&['demo','device_demo',undefined].includes(r.content_origin))||makeRecord();currentId=record?.id||liveReadingId;
const deviceDemo=()=>record?.content_origin==='device_demo';
let base=record?.base,selected=record?.selected||'',busy=false,askBusy=false,results=record?.deep||{},active=null,epoch=0,exportText='',archived=false;
let monthCursor=new Date(),calendarDay=H.dayKey(new Date());
const put=(id,text)=>{$(id).textContent=text;};
let saveSequence=0;
async function persist(){
 if(invalidEntry||historyOnly||!record||archived||liveMode&&(!liveAuthorized||record.id!==liveReadingId))return;
 record.selected=selected;record.deep=results;
 const savingId=record.id,sequence=++saveSequence;put('#storage-status','正在保存到本机…');
 const saved=await H.save(storage,record,currentId);
 if(sequence!==saveSequence)return;
 if(saved.error){put('#storage-status',saved.error);return;}
 records=saved.records;
 if(record.id===savingId&&!archived){
  const merged=records.find(r=>r.id===savingId);
  if(merged){record=structuredClone(merged);results=record.deep;if(liveMode)currentLiveRecord=record;renderQuestions();}
 }
 put('#storage-status',saved.warning||'已保存在本机 · 可在签文日历回看');
}
function glyph(el,lines){el.replaceChildren();for(const value of [...lines].reverse()){const line=document.createElement('div');line.className='line'+(value?'':' yin');el.append(line);}}
function animateChange(fn){if(document.startViewTransition&&!matchMedia('(prefers-reduced-motion: reduce)').matches)return document.startViewTransition(fn);else fn();}
function appendSections(el,content){el.replaceChildren();for(const [key,label] of [['meaning','卦象启发'],['reflection','对你的启发'],['action','一个小行动']]){if(!content[key])continue;const h=document.createElement('h3'),p=document.createElement('p');h.textContent=label;p.textContent=content[key];el.append(h,p);}}
function updateThemes(){const readOnly=archived||liveMode&&!liveAuthorized;document.querySelectorAll('.theme').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.theme===selected));b.disabled=busy||askBusy||deviceDemo();});$('#generate').disabled=deviceDemo()||!selected||busy||askBusy||(readOnly&&!results[selected]);put('#generate',deviceDemo()?'设备卦象解读待接入':busy?'正在展开':readOnly?(results[selected]?'查看已保存解读':'此主题没有保存的解读'):selected?'深入解读':'先选择一个主题');const text=$('#question').value.trim();$('#ask').disabled=deviceDemo()||!text||[...text].length>200||askBusy||busy||readOnly;$('#ask').setAttribute('aria-busy',String(askBusy));put('#ask-label',askBusy?'正在解读':'问问这一卦');$('#ask-dots').hidden=!askBusy;$('#question').disabled=askBusy||readOnly||deviceDemo();put('#question-count',[...$('#question').value].length+' / 200');}
for(const [id,label] of Object.entries(themes)){const b=document.createElement('button');b.className='theme';b.dataset.theme=id;b.textContent=label;b.onclick=()=>{selected=id;if(!archived)persist();updateThemes();};$('#themes').append(b);}
function renderQuestions(){const el=$('#question-answers');el.replaceChildren();$('#questions-panel').hidden=!record||record.questions.length===0||liveMode&&!archived&&liveState!=='ready';for(const q of record?.questions||[]){const item=document.createElement('article');item.className='qa-item';item.dataset.questionId=q.id;const origin=document.createElement('small');origin.textContent=L.sourceLabel(q.content_origin||record.content_origin);const title=document.createElement('h3');title.textContent=q.question;const content=document.createElement('div');appendSections(content,q.answer);item.append(origin,title,content);el.append(item);}}
async function revealQuestion(questionId,isCurrent){const transition=animateChange(()=>{if(isCurrent())renderQuestions();});await transition?.updateCallbackDone;if(!isCurrent()||$('#questions-panel').hidden)return;const item=[...$('#question-answers').children].find(node=>node.dataset.questionId===questionId);item?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}
function renderReading(){if(!record)return;base=record.base;results=record.deep;selected=record.selected||'';glyph($('#hexagram'),record.hex.lines_bottom_to_top);$('#hexagram').setAttribute('aria-label',record.hex.name_zh+'卦');put('.identity h2',record.hex.name_zh);put('.identity p','上卦 '+record.hex.upper_trigram+' · 下卦 '+record.hex.lower_trigram);put('.paper-top span:last-child','NO. '+String(record.hex.hexagram_id).padStart(2,'0'));put('.demo-label',deviceDemo()?'设备扫码演示 · 同一卦象 · 解读未接入':record.content_origin==='ai'?'AI 创作 · 与纸签同一卦象':record.content_origin==='fallback'?'备用内容 · 与纸签同一卦象':'演示模式 · 固定样例 · 未调用 AI');put('#base-title',base.title);put('#base-message',base.message);put('#base-action',base.action);put('#reading-source','娱乐与自我探索 · '+L.sourceLabel(record.content_origin));put('#question-source',archived?'历史签文只读 · 已保存问答可回看':deviceDemo()?'设备卦象已同步 · 真实 AI 问答尚未接入':liveMode?'AI 回答沿用当前卦象与原签，不重新起卦':'当前为问卦交互演示，回复使用模板，未连接真实 AI');put('#loading-text',liveMode?'正在展开这张签的解读…':'正在展示模拟解读…');appendSections($('#web-reading'),record.web);$('#archive-banner').hidden=!archived;$('#question').value='';questionDraft=null;put('#ask-status',deviceDemo()?'已同步设备卦象，真实 AI 问答尚未接入':archived?'历史签文只读，已保存的问答可在下方回看':'');$('#result').hidden=true;active=null;renderQuestions();updateThemes();if(selected&&results[selected])revealResult(selected,results[selected]);}
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function revealResult(theme,content,scroll=false){const mine=epoch,readingId=record.id;active={theme,content};const transition=animateChange(()=>{if(mine!==epoch||record?.id!==readingId)return;put('#result-theme',themes[theme]+' · '+L.sourceLabel(record.content_origin));put('#deep-title',content.title);appendSections($('#deep-content'),content);$('#result').hidden=false;});if(scroll){await transition?.updateCallbackDone;if(mine===epoch&&record?.id===readingId&&!$('#result').hidden)$('#result').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}}
function sessionFailure(error){if(liveMode&&['session','expired','claimed','invalid'].includes(error.code)){liveAuthorized=false;liveState='error';liveError=error;scenario();return true;}return false;}
async function generate(){
 if(!record||deviceDemo()||busy||askBusy||!selected||(!liveMode&&!archived&&$('#scenario').value!=='normal'))return;
 if(results[selected])return revealResult(selected,results[selected],true);if(archived||liveMode&&!liveAuthorized)return;
 const mine=++epoch,theme=selected,readingId=record.id,isCurrent=()=>mine===epoch&&record?.id===readingId&&!archived;busy=true;$('#error').hidden=true;$('#loading').hidden=false;updateThemes();
 try{
  let content;
  if(liveMode)content=await liveClient.deep(readingId,theme,isCurrent);
  else{const fail=$('#fail-next').checked;$('#fail-next').checked=false;await delay(650);if(fail)throw Error('这次解读没有完成，你的基础签还在，可以重试');content=structuredClone(data.examples.deep_readings.find(x=>x.theme===theme).content);}
  if(!isCurrent())return;results[theme]=content;await persist();if(isCurrent()){$('#loading').hidden=true;await revealResult(theme,content,true);}
 }catch(error){if(!isCurrent()||error.code==='stale')return;if(!sessionFailure(error)){put('#error p',error.message);$('#error').hidden=false;}}
 finally{if(isCurrent()){busy=false;$('#loading').hidden=true;updateThemes();}}
}
$('#generate').onclick=generate;$('#retry').onclick=generate;$('#question').oninput=()=>{questionDraft=null;updateThemes();};
$('#ask').onclick=async()=>{const question=$('#question').value.trim();if(!record||deviceDemo()||archived||busy||askBusy||!question||[...question].length>200||(liveMode?!liveAuthorized:$('#scenario').value!=='normal'))return;
 const mine=++epoch,readingId=record.id,isCurrent=()=>mine===epoch&&record?.id===readingId&&!archived;askBusy=true;updateThemes();put('#ask-status',liveMode?'正在结合当前卦象与原签回答…':'正在展示基于当前卦象的问卦模板…');
 if(liveMode){try{
  questionDraft=L.questionRequest(questionDraft,question,selected,()=>crypto.randomUUID());
  const response=await liveClient.question(readingId,questionDraft,isCurrent);if(!isCurrent())return;
  if(!record.questions.some(q=>q.id===response.id))record.questions.push(response);await persist();if(!isCurrent())return;
  askBusy=false;put('#ask-status','回答已完成，问题与回答随本签保存。实际保存状态见页面上方。');$('#question').value='';questionDraft=null;updateThemes();await revealQuestion(response.id,isCurrent);
 }catch(error){if(!isCurrent()||error.code==='stale')return;if(!sessionFailure(error))put('#ask-status',error.message+'；问题已保留，可重试本次问卦');}
 finally{if(isCurrent()){askBusy=false;updateThemes();}}return;}
 const fail=$('#fail-next').checked;$('#fail-next').checked=false;await delay(650);if(!isCurrent())return;if(fail){askBusy=false;put('#ask-status','这次问卦没有完成，问题已保留，可以重新提交');updateThemes();return;}
// Explicit demo template, not an AI inference. B must replace this block with authenticated model service.
const answer={meaning:'这条问答沿用当前的'+record.hex.name_zh+'卦，不重新起卦。演示模板把“先开始、再观察、留有余力”作为思考角度，并不判断问题的结果或推测他人的想法。',reflection:'关于你写下的“'+question+'”，可以先拆开三件事：你已经知道的事实、仍需要了解的信息，以及你真正希望得到的变化。暂时不把愿望当成证据，也不急于用一个答案替代观察。\n\n这是通用演示模板，并未使用 AI 分析你的具体处境。正式接入后，将由服务端把这次问题、当前卦象与原签文一起交给模型，给出更贴合问题的释义。',action:'写下一个你能亲自确认的小问题，选择一次成本较低、可以调整的尝试。根据实际反馈再决定下一步。'};
const response={id:'question-'+(globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random()),question,answer,created_at:new Date().toISOString(),content_origin:'demo_template'};record.questions.push(response);await persist();if(!isCurrent())return;askBusy=false;put('#ask-status','演示回复已展示；问题与回答随本签保存。实际保存状态见页面上方。');$('#question').value='';updateThemes();await revealQuestion(response.id,isCurrent);};
$('#change-theme').onclick=()=>{$('#themes').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});document.querySelector('.theme').focus();};
const notices={history:['本机签文日历','从右上方打开日历，回看此浏览器已保存的签文；尚无记录时，请先扫描设备二维码'],expired:['本次扫码已结束','已经保存在本机的签文，仍可从签文日历回看'],claimed:['这张签已被领取','请在最初领取的浏览器中继续查看'],session:['本次网页会话已结束','已经保存的内容仍可回看，新的问卦需要有效会话'],network:['暂时连接不上','请检查网络后重试，或查看本机历史'],invalid:['没有找到这张签','请确认扫描了设备上本次显示的二维码'],pending:['正在读取这张签','网页解读准备好后会自动显示，请稍候'],generation:['这张签的网页解读尚未完成','可以重试生成，纸签和卦象保持不变'],timeout:['内容仍在生成','稍后重试可继续读取本次任务'],busy:['服务正在忙碌','请稍后重试读取，或查看本机历史']};
async function startLive(retryGeneration=false){
 liveAuthorized=false;liveState='pending';liveError=null;archived=false;scenario();const mine=epoch,isCurrent=()=>mine===epoch&&!archived;
 try{
  let value;
  if(liveReadingId)value=await (retryGeneration?liveClient.retry(liveReadingId):liveClient.read(liveReadingId));
  else{
   let token=L.entry(location.pathname).token;if(!token){const error=Error('请确认扫描了设备上本次显示的二维码');error.code='invalid';throw error;}
   try{value=await liveClient.claim(token);}finally{token=null;}
   liveReadingId=value.reading_id;currentId=liveReadingId;history.replaceState(null,'','/s/'+liveReadingId+'/');
  }
  if(!isCurrent())return;value=await liveClient.waitReading(value,isCurrent);if(!isCurrent())return;
  if(value.status==='failed'){const error=Error(value.error||'网页解读生成失败，可手动重试');error.code='generation';throw error;}
  const known=currentLiveRecord&&!records.some(r=>r.id===currentLiveRecord.id)?[...records,currentLiveRecord]:records;
  record=L.prepareRecord(value.record,liveReadingId,known,H,entryOpenedAt);currentLiveRecord=record;currentId=record.id;selected=record.selected||'';results=record.deep;liveAuthorized=true;liveState='ready';
  scenario();renderReading();await persist();
 }catch(error){if(!isCurrent()||error.code==='stale')return;liveError=error;liveState='error';scenario();put('#storage-status','本次尚未保存新的签文；已有本机历史仍可回看');}
}
function scenario(){epoch++;busy=false;askBusy=false;active=null;$('#loading').hidden=true;$('#error').hidden=true;$('#result').hidden=true;$('#archive-banner').hidden=!archived;updateThemes();const state=historyOnly&&!archived?'history':liveMode&&!archived?(liveState==='ready'?'normal':liveState==='pending'?'pending':liveError?.code||'network'):$('#scenario').value;const mine=epoch;animateChange(()=>{if(mine!==epoch)return;$('#reading').hidden=state!=='normal';$('#explore').hidden=state!=='normal';$('#questions-panel').hidden=state!=='normal'||!record?.questions.length;$('#notice').hidden=state==='normal';$('#notice').replaceChildren();if(liveMode&&!archived&&state!=='normal')put('.demo-label','同一卦象 · 同一张纸签');if(notices[state]){const h=document.createElement('h2'),p=document.createElement('p');h.textContent=notices[state][0];p.textContent=liveMode&&liveError?liveError.message+'。'+notices[state][1]:notices[state][1];$('#notice').append(h,p);if(liveMode&&['network','timeout','busy','generation'].includes(state)){const b=document.createElement('button');b.className='secondary';b.textContent=state==='generation'?'重试生成网页解读':'重试读取';b.onclick=()=>startLive(state==='generation');$('#notice').append(b);}else if(!liveMode&&state==='network'){const b=document.createElement('button');b.className='secondary';b.textContent='重试连接（模拟）';b.onclick=()=>{$('#scenario').value='normal';scenario();};$('#notice').append(b);}}});}
$('#scenario').onchange=scenario;$('#reset').onclick=()=>{$('#scenario').value=invalidEntry?'invalid':'normal';$('#fail-next').checked=false;scenario();renderReading();};
$('#new-reading').onclick=()=>{if(liveMode||historyOnly)return;epoch++;invalidEntry=false;history.replaceState(null,'',location.pathname+location.search);record=makeRecord();currentId=record.id;archived=false;selected='';results={};$('#scenario').value='normal';scenario();persist();renderReading();};
function openDialog(id){$(id).showModal();}
async function closeDialog(d){d.classList.add('leaving');await delay(matchMedia('(prefers-reduced-motion: reduce)').matches?0:180);d.close();d.classList.remove('leaving');}
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>closeDialog(b.closest('dialog')));document.querySelectorAll('dialog').forEach(d=>d.addEventListener('cancel',e=>{e.preventDefault();closeDialog(d);}));
function renderCalendar(restoreDay=null){const year=monthCursor.getFullYear(),month=monthCursor.getMonth(),info=H.monthDays(year,month);put('#month-label',year+' 年 '+(month+1)+' 月');const grid=$('#calendar');grid.replaceChildren();for(let i=0;i<info.offset;i++){const gap=document.createElement('span');gap.setAttribute('aria-hidden','true');grid.append(gap);}for(let day=1;day<=info.count;day++){const key=H.dayKey(new Date(year,month,day)),n=records.filter(r=>r.day===key).length,b=document.createElement('button');b.className='calendar-day';b.textContent=day;b.dataset.day=key;b.setAttribute('aria-label',key+'，'+n+' 条记录');b.setAttribute('aria-pressed',String(key===calendarDay));if(key===H.dayKey(new Date()))b.setAttribute('aria-current','date');if(n){const dot=document.createElement('small');dot.textContent=n;b.append(dot);}b.onclick=()=>{calendarDay=key;renderCalendar(key);};grid.append(b);}put('#history-date',calendarDay+' 的签文');const list=$('#history-list');list.replaceChildren();const matches=records.filter(r=>r.day===calendarDay).sort((a,b)=>b.scanned_at.localeCompare(a.scanned_at));if(!matches.length){const p=document.createElement('p');p.textContent='这一天还没有保存的签文';list.append(p);}for(const r of matches){const b=document.createElement('button');b.className='history-item';const title=document.createElement('strong'),sub=document.createElement('small');title.textContent=r.hex.name_zh+' · '+r.base.title;sub.textContent=new Date(r.scanned_at).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'})+' · '+Object.keys(r.deep).length+' 个主题 · '+r.questions.length+' 条问答 · '+L.sourceLabel(r.content_origin);b.append(title,sub);b.onclick=async()=>{epoch++;record=structuredClone(r);archived=true;$('#scenario').value='normal';scenario();renderReading();await closeDialog($('#history-dialog'));$('#archive-banner').scrollIntoView({block:'start'});};list.append(b);}if(restoreDay){[...grid.querySelectorAll('button')].find(b=>b.dataset.day===restoreDay)?.focus({preventScroll:true});}}
$('#history-open').onclick=()=>{const loaded=H.read(storage);if(!loaded.error)records=loaded.records;if(loaded.error||loaded.warning)put('#storage-status',loaded.error||loaded.warning);renderCalendar();openDialog('#history-dialog');};
$('#month-prev').onclick=()=>{monthCursor=new Date(monthCursor.getFullYear(),monthCursor.getMonth()-1,1);calendarDay=H.dayKey(monthCursor);renderCalendar();};$('#month-next').onclick=()=>{monthCursor=new Date(monthCursor.getFullYear(),monthCursor.getMonth()+1,1);calendarDay=H.dayKey(monthCursor);renderCalendar();};$('#calendar-today').onclick=()=>{monthCursor=new Date();calendarDay=H.dayKey(monthCursor);renderCalendar();};
$('#return-current').onclick=()=>{if(historyOnly){archived=false;record=null;selected='';results={};scenario();$('#history-open').onclick();return;}if(liveMode){startLive();return;}const saved=records.find(r=>r.id===currentId);if(!saved)return;record=structuredClone(saved);archived=false;$('#scenario').value='normal';scenario();renderReading();};

function blocks(kind){return kind==='deep'&&active?{title:active.content.title,label:themes[active.theme],rows:[['卦象启发',active.content.meaning],['对你的启发',active.content.reflection],['一个小行动',active.content.action]]}:{title:base.title,label:'今日签',rows:[['纸签',base.message],['卦象启发',record.web.meaning],['对你的启发',record.web.reflection],['一个小行动',record.web.action]]};}
async function exportCard(kind){const b=blocks(kind);try{await document.fonts.ready;const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');canvas.width=900;canvas.height=2600;ctx.font='30px sans-serif';function wrap(text){const lines=[];let line='';for(const char of text){if(char==='\n'){lines.push(line);line='';continue;}if(ctx.measureText(line+char).width>720){lines.push(line);line=char;}else line+=char;}if(line)lines.push(line);return lines;}
const rows=b.rows.map(([label,text])=>({label,lines:wrap(text)}));const height=520+rows.reduce((n,x)=>n+70+x.lines.length*49,0)+130;canvas.height=height;ctx.fillStyle='#ffffff';ctx.fillRect(0,0,900,height);ctx.fillStyle='#242623';ctx.font='24px sans-serif';ctx.fillText('赛博龟壳 / CYBER TURTLE',90,75);ctx.fillStyle='#355d8e';ctx.font='24px sans-serif';ctx.fillText(b.label+' · '+L.sourceLabel(record.content_origin),90,123);ctx.fillStyle='#242623';for(let i=0;i<6;i++){if(record.hex.lines_bottom_to_top[5-i])ctx.fillRect(90,172+i*20,110,10);else{ctx.fillRect(90,172+i*20,47,10);ctx.fillRect(153,172+i*20,47,10);}}ctx.font='48px serif';ctx.fillText(record.hex.name_zh,238,239);ctx.font='21px sans-serif';ctx.fillText('上卦 '+record.hex.upper_trigram+' · 下卦 '+record.hex.lower_trigram,238,282);ctx.font='42px serif';ctx.fillText(b.title,90,390);let y=460;for(const row of rows){ctx.fillStyle='#355d8e';ctx.font='23px sans-serif';ctx.fillText(row.label,90,y);y+=48;ctx.fillStyle='#242623';ctx.font='30px sans-serif';for(const line of row.lines){ctx.fillText(line,90,y);y+=49;}y+=30;}ctx.font='20px sans-serif';ctx.fillStyle='#73766f';ctx.fillText('娱乐与自我探索 · '+L.sourceLabel(record.content_origin),90,height-70);const url=canvas.toDataURL('image/png');$('#export-image').src=url;$('#download').href=url;$('#download').download='赛博龟壳-'+L.sourceLabel(record.content_origin)+'.png';exportText='赛博龟壳 · '+record.hex.name_zh+' · '+b.label+'\n'+b.title+'\n'+b.rows.map(x=>x.join('\n')).join('\n\n')+'\n娱乐与自我探索 · '+L.sourceLabel(record.content_origin);put('#export-status','');openDialog('#export-dialog');}catch(e){exportText=[b.title,...b.rows.map(x=>x.join('\n'))].join('\n');alert('图片暂时无法生成，可直接复制以下文字：\n'+exportText);}}
$('#save-base').onclick=()=>exportCard('base');$('#save-deep').onclick=()=>exportCard('deep');$('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(exportText);put('#export-status','签文已复制');}catch{put('#export-status','未能自动复制，请长按下方文字手动复制：\n'+exportText);}};
$('#paper-preview').onclick=()=>{const p=$('#print-area');p.replaceChildren();const title=document.createElement('h3');title.textContent='赛博龟壳 · 今日签';const g=document.createElement('div');g.className='hexagram';glyph(g,record.hex.lines_bottom_to_top);const identity=document.createElement('section');identity.className='print-identity';const name=document.createElement('h2'),tags=document.createElement('p');name.textContent=record.hex.name_zh;tags.textContent='上卦 '+record.hex.upper_trigram+' · 下卦 '+record.hex.lower_trigram;identity.append(g,name,tags);p.append(title,identity);for(const text of [base.title,base.message,'今日小行动',base.action,'遇事不决，摇壳问问','娱乐与自我探索 · '+L.sourceLabel(record.content_origin)]){const node=document.createElement('p');node.textContent=text;p.append(node);}openDialog('#paper-dialog');};$('#print').onclick=()=>window.print();
for(const x of data.hexagrams){const opt=document.createElement('option');opt.value=x.hexagram_id;opt.textContent=x.hexagram_id+' · '+x.name_zh;$('#library-select').append(opt);}
function showHex(){const x=data.hexagrams.find(x=>x.hexagram_id===Number($('#library-select').value));const el=$('#library-content');el.replaceChildren();const g=document.createElement('div');g.className='hexagram';glyph(g,x.lines_bottom_to_top);const title=document.createElement('h2');title.textContent=x.name_zh;const p=document.createElement('p');p.textContent='上卦 '+x.upper_trigram+' · 下卦 '+x.lower_trigram+'\n自下而上编码 '+x.lines_bottom_to_top.join('');el.append(g,title,p);}
$('#library-select').onchange=showHex;$('#library-open').onclick=()=>{showHex();openDialog('#library-dialog');};

if(liveMode||historyOnly)$('.brand').href='/history/';
if(historyOnly){$('.dev').hidden=true;put('.demo-label','本机历史 · 只读回看');put('#return-current','返回签文日历');scenario();}
else if(liveMode){$('.dev').hidden=true;if(invalidEntry){liveState='error';liveError={code:'invalid',message:'扫码链接格式不正确'};scenario();}else startLive();}
else{renderReading();if(invalidEntry){$('#scenario').value='invalid';scenario();put('#storage-status','链接无效，未写入本机历史');}else{scenario();persist();}}
window.addEventListener('hashchange',()=>location.reload());

window.addEventListener('storage',event=>{
 if(event.key!==H.KEY)return;
 const loaded=H.read(storage);
 if(loaded.error){put('#storage-status',loaded.error);return;}
 records=loaded.records;
 if(loaded.warning)put('#storage-status',loaded.warning);
 const remote=record&&records.find(r=>r.id===record.id);
 if(remote){record=H.merge(remote,record);results=record.deep;renderQuestions();}
 if($('#history-dialog').open){const focusDay=document.activeElement?.dataset?.day;renderCalendar(focusDay||null);}
});
