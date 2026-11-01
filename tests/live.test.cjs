const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto');
const L=require('../h5/live.js'),H=require('../h5/history.js'),S=require('../h5/scan.js');
const hexagrams=require('../data/hexagrams.json'),examples=require('../data/content-examples.json');
const id='a'.repeat(32),other='b'.repeat(32),token='aB0_-12345678901234567';
const content={title:'向前一步',meaning:'卦象启发',reflection:'先观察事实',action:'做一次小尝试'};
const fixture=(readingId=id)=>({id:readingId,hex:hexagrams[0],base:{title:'原纸签',message:'纸签上的原文',action:'先走一步'},web:content,deep:{},questions:[],selected:'',content_origin:'ai',scanned_at:'2026-01-01T00:00:00.000Z',day:'2026-01-01'});
const ready=record=>({reading_id:record.id,status:'ready',record});
const response=(body,status=200)=>({ok:status<400,status,json:async()=>body});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function settle(){for(let i=0;i<6;i++)await tick();}
function fakeClient(queue,options={}){
 const calls=[];return {calls,client:L.createClient({fetch:async(path,init)=>{calls.push({path,init});const next=queue.shift();assert.notEqual(next,undefined,'unexpected API request');if(next instanceof Error)throw next;return typeof next==='function'?next(path,init):response(next);},wait:async()=>{},...options})};
}
// Minimal DOM double exercises app state and storage, without asserting browser layout.
function app({path='/s/'+id+'/',hash='',fetch,stored=[]}={}){
 const nodes=new Map(),writes=[],urls=[],scrollEvents=[];
 function element(tag='div'){
  return {tag,children:[],scrolls:[],dataset:{},value:'',hidden:false,disabled:false,checked:false,open:false,textContent:'',className:'',classList:{add(){},remove(){}},setAttribute(k,v){this[k]=v;},append(...children){this.children.push(...children);},replaceChildren(...children){this.children=[...children];},querySelectorAll(tag){return this.children.filter(x=>x.tag===tag);},focus(){},scrollIntoView(options){this.scrolls.push(options);this.scrolledWhileLoading=!get('#loading').hidden;scrollEvents.push({questionId:this.dataset.questionId,options,askBusy:get('#ask')['aria-busy'],askLabel:get('#ask-label').textContent,dotsHidden:get('#ask-dots').hidden,question:get('#question').value,status:get('#ask-status').textContent});},addEventListener(){},showModal(){this.open=true;},close(){this.open=false;}};
 }
 const get=selector=>{if(!nodes.has(selector))nodes.set(selector,element());return nodes.get(selector);};get('#scenario').value='normal';
 const document={querySelector:get,querySelectorAll:selector=>selector==='.theme'?get('#themes').children:[],createElement:element};
 let storedValue=stored.length?JSON.stringify({version:1,active_id:stored[0].id,records:stored,quarantined:[]}):null;
 const storage={getItem:()=>storedValue,setItem:(key,value)=>{writes.push(value);storedValue=value;}};
 const location={pathname:path,hash,search:'',reload(){}};
 const history={replaceState(_state,_title,url){urls.push(url);location.pathname=url;location.hash='';}};
 const fakeHistory={...H,save:(store,record,active)=>H.save(store,record,active,{request:async(_name,_options,fn)=>fn()})};
 const window={TURTLE_DATA:{hexagrams,examples},TurtleHistory:fakeHistory,TurtleScan:S,TurtleLive:{...L,createClient:()=>L.createClient({fetch,wait:async()=>{},pollLimit:2})},localStorage:storage,addEventListener(){}};
 const context=vm.createContext({window,document,location,history,structuredClone,crypto,AbortController,setTimeout,clearTimeout,console,navigator:{},matchMedia:()=>({matches:true})});
 vm.runInContext(fs.readFileSync(require.resolve('../h5/app.js'),'utf8'),context);
 return {get,writes,urls,scrollEvents,context,run:code=>vm.runInContext(code,context),saved:()=>H.read(storage).records};
}
(async()=>{
 assert.equal(token.length,22);
 assert.deepEqual(L.entry('/r/'+token+'/'),{kind:'claim',token});
 assert.deepEqual(L.entry('/s/'+id+'/'),{kind:'reading',readingId:id});
 for(const path of ['/r','/r/short/','/r/'+token+'/extra','/s/ABC/','/s/'+id+'x/'])assert.equal(L.entry(path).kind,'invalid');
 for(const path of ['/','/index.html','/cyber-turtle-clawhunt/'])assert.equal(L.entry(path).kind,'none');
 const local=new Date('2026-10-31T16:23:45.678Z'),first=L.prepareRecord(fixture(),id,[],H,local);
 assert.equal(first.scanned_at,local.toISOString());assert.equal(first.day,H.dayKey(local));assert(H.valid(first));
 const rescanned=L.prepareRecord(fixture(),id,[first],H,new Date('2026-11-05T00:00:00.000Z'));
 assert.equal(rescanned.scanned_at,first.scanned_at);assert.equal(rescanned.day,first.day);assert.deepEqual(rescanned.base,fixture().base);
 assert.throws(()=>L.prepareRecord(fixture(other),id,[],H));assert.throws(()=>L.prepareRecord({...fixture(),content_origin:'demo'},id,[],H));
 assert.throws(()=>L.prepareRecord({...fixture(),web:{}},id,[],H));
 let uuid=0;const q1=L.questionRequest(null,'问题','today',()=>String(++uuid));
 assert.equal(L.questionRequest(q1,'问题','today',()=>String(++uuid)),q1);
 assert.notEqual(L.questionRequest(q1,'修改问题','today',()=>String(++uuid)).request_id,q1.request_id);
 assert.notEqual(L.questionRequest(q1,'问题','career',()=>String(++uuid)).request_id,q1.request_id);

 let mock=fakeClient([{reading_id:id,status:'pending'},ready(fixture())]);
 const claim=await mock.client.claim(token);await mock.client.waitReading(claim);
 assert.equal(mock.calls[0].path,'/api/claim');assert.equal(mock.calls[0].init.body,JSON.stringify({token}));
 assert.equal(mock.calls[1].path,'/api/readings/'+id);
 for(const call of mock.calls)assert.equal(call.init.credentials,'same-origin');
 mock=fakeClient([{reading_id:id,status:'failed',error:'生成失败'}]);
 const failed=await mock.client.read(id);assert.equal((await mock.client.waitReading(failed)).status,'failed');assert.equal(mock.calls.length,1);
 mock=fakeClient([{reading_id:id,status:'pending'}]);await mock.client.retry(id);assert.equal(mock.calls[0].path,'/api/readings/'+id+'/retry');assert.equal(mock.calls[0].init.body,'{}');
 mock=fakeClient([{reading_id:id,status:'pending'},{reading_id:id,status:'pending'}],{pollLimit:2});
 await assert.rejects(mock.client.waitReading({reading_id:id,status:'pending'}),error=>error.code==='timeout');assert.equal(mock.calls.length,2);
 mock=fakeClient([ready(fixture(other))]);await assert.rejects(mock.client.read(id),/不匹配/);
 mock=fakeClient([()=>response({error:'会话结束',code:'session'},401)]);await assert.rejects(mock.client.read(id),error=>error.code==='session');
 mock=fakeClient([()=>{throw new DOMException('Aborted','AbortError');}]);await assert.rejects(mock.client.read(id),error=>error.code==='network');
 mock=fakeClient([{task_id:'task-1',reading_id:id,theme:'today',status:'pending'},{task_id:'task-1',reading_id:id,theme:'today',status:'succeeded',content}]);
 assert.deepEqual(await mock.client.deep(id,'today'),content);assert.equal(mock.calls[1].path,'/api/readings/'+id+'/tasks/task-1');
 mock=fakeClient([{task_id:'task-1',reading_id:other,status:'succeeded',content}]);await assert.rejects(mock.client.deep(id,'today'),/归属/);
 mock=fakeClient([{task_id:'task-1',status:'pending'},{task_id:'task-2',status:'succeeded',content}]);await assert.rejects(mock.client.deep(id,'today'),/不匹配/);
 let current=true;mock=fakeClient([{task_id:'task-1',status:'pending'}],{wait:async()=>{current=false;}});
 await assert.rejects(mock.client.deep(id,'today',()=>current),error=>error.code==='stale');assert.equal(mock.calls.length,1);
 const answer={id:'question-1',question:'问题',answer:{meaning:'启发',reflection:'观察',action:'一步'},created_at:'2026-10-31T01:00:00.000Z',content_origin:'ai'};
 mock=fakeClient([{task_id:'task-q',question_id:answer.id,reading_id:id,status:'succeeded',content:answer}]);assert.deepEqual(await mock.client.question(id,{request_id:crypto.randomUUID(),question:'问题'}),answer);

 let finishClaim;const claimPromise=new Promise(resolve=>{finishClaim=resolve;});
 const page=app({path:'/r/'+token+'/',hash:'#d=64.0123456789abcdef.1',fetch:()=>claimPromise});
 assert.equal(page.get('#reading').hidden,true);assert.equal(page.get('#explore').hidden,true);assert.equal(page.get('.dev').hidden,true);assert.equal(page.writes.length,0);assert.equal(page.run('record'),null);
 finishClaim(response(ready(fixture())));await settle();
 assert.deepEqual(page.urls,['/s/'+id+'/']);assert.equal(page.get('#base-message').textContent,'纸签上的原文');assert.equal(page.get('#reading').hidden,false);
 assert.equal(page.saved().length,1);assert.equal(page.saved()[0].id,id);assert.equal(page.saved()[0].hex.hexagram_id,1,'untrusted #d never overrides server hexagram');
 assert.equal(page.get('#reading-source').textContent,'娱乐与自我探索 · AI 创作');assert(!page.writes.join('').includes(token));assert.equal(page.get('.brand').href,'/history/');
 assert(!page.get('#question-source').textContent.includes('模板'));
 page.get('#paper-preview').onclick();assert.equal(page.get('#print-area').children.at(-1).textContent,'娱乐与自我探索 · AI 创作');
 page.run('calendarDay=record.day;monthCursor=new Date(record.scanned_at);renderCalendar()');assert.match(page.get('#history-list').children[0].children[1].textContent,/AI 创作/);

 const failureCalls=[];const failedPage=app({fetch:async(path,init)=>{failureCalls.push({path,init});return response(failureCalls.length===1?{reading_id:id,status:'failed',error:'长解读生成失败'}:ready(fixture()));}});
 await settle();assert.equal(failedPage.writes.length,0);assert.equal(failureCalls.length,1);assert.equal(failedPage.get('#reading').hidden,true);
 await failedPage.get('#notice').children.at(-1).onclick();await settle();assert.equal(failureCalls[1].path,'/api/readings/'+id+'/retry');assert.equal(failedPage.saved().length,1);
 const invalid=app({path:'/r/bad/',fetch:()=>{throw Error('must not request');}});await settle();assert.equal(invalid.writes.length,0);assert.equal(invalid.get('#reading').hidden,true);
 const history=app({path:'/history/',fetch:()=>{throw Error('history must not request');}});await settle();assert.equal(history.writes.length,0);assert.equal(history.run('record'),null);assert.equal(history.get('#reading').hidden,true);assert.equal(history.get('#notice').children[0].textContent,'本机签文日历');
 const expired=app({stored:[fixture()],fetch:async()=>response({code:'session',error:'会话已过期'},401)});await settle();assert.equal(expired.writes.length,0);assert.equal(expired.get('#reading').hidden,true);assert.equal(expired.run('liveAuthorized'),false);
 expired.run('calendarDay=records[0].day;monthCursor=new Date(records[0].scanned_at);renderCalendar()');await expired.get('#history-list').children[0].onclick();assert.equal(expired.get('#reading').hidden,false);assert.equal(expired.get('#question').disabled,true);assert.equal(expired.writes.length,0);

 let finishDeep,deepPosts=0;const late=app({stored:[fixture(other)],fetch:async(path)=>{if(path.endsWith('/deep-reading')){deepPosts++;return new Promise(resolve=>{finishDeep=resolve;});}return response(ready(fixture()));}});await settle();
 late.run("selected='today';updateThemes()");const deepWork=late.get('#generate').onclick();await settle();
 late.run('epoch++;record=structuredClone(records.find(r=>r.id!==currentId));archived=true;scenario();renderReading()');
 finishDeep(response({task_id:'late-task',reading_id:id,theme:'today',status:'succeeded',content}));await deepWork;
 assert.equal(late.run('record.id'),other);assert.equal(Object.keys(late.run('record.deep')).length,0);assert.equal(late.saved().find(r=>r.id===id).deep.today,undefined);assert.equal(deepPosts,1);assert.equal(late.get('#result').scrolls.length,0);

 const questionCalls=[];const questions=app({fetch:async(path,init)=>{if(path.endsWith('/questions')){const body=JSON.parse(init.body);questionCalls.push(body);if(questionCalls.length===1)return response({task_id:'q-task',status:'failed',error:'稍后重试'});return response({task_id:'q-task',reading_id:id,question_id:answer.id,status:'succeeded',content:answer});}return response(ready(fixture()));}});await settle();
 questions.get('#question').value='问题';questions.get('#question').oninput();await questions.get('#ask').onclick();assert.equal(questions.get('#question').value,'问题');assert.equal(questions.get('#ask-label').textContent,'问问这一卦');assert.equal(questions.get('#ask-dots').hidden,true);assert.equal(questions.get('#ask').disabled,false);assert.equal(questions.scrollEvents.length,0,'a failed question keeps the input and never scrolls');
 await questions.get('#ask').onclick();assert.equal(questionCalls.length,2);assert.equal(questionCalls[0].request_id,questionCalls[1].request_id);assert.equal(questions.saved()[0].questions.length,1);assert.equal(questions.get('#question').value,'');
 const existingQuestion=fixture();existingQuestion.questions=[answer];let finishQuestion;const asking=app({fetch:async(path)=>path.endsWith('/questions')?new Promise(resolve=>{finishQuestion=resolve;}):response(ready(existingQuestion))});await settle();assert.equal(asking.scrollEvents.length,0,'restoring saved questions does not scroll');
 asking.get('#question').value='第二个问题';asking.get('#question').oninput();const questionWork=asking.get('#ask').onclick();
 assert.equal(asking.get('#ask-label').textContent,'正在解读');assert.equal(asking.get('#ask-dots').hidden,false);assert.equal(asking.get('#ask')['aria-busy'],'true');assert.equal(asking.get('#ask').disabled,true);assert.equal(asking.get('#question').disabled,true);assert.match(asking.get('#ask-status').textContent,/正在/);
 const secondAnswer={...answer,id:'question-2',question:'第二个问题',created_at:'2026-10-31T02:00:00.000Z'};
 finishQuestion(response({task_id:'q-second',reading_id:id,question_id:secondAnswer.id,status:'succeeded',content:secondAnswer}));await questionWork;
 assert.equal(asking.scrollEvents.length,1);assert.equal(asking.scrollEvents[0].questionId,secondAnswer.id,'scroll to the new answer, not the first saved question');assert.equal(asking.scrollEvents[0].options.behavior,'instant');
 assert.equal(asking.scrollEvents[0].askBusy,'false');assert.equal(asking.scrollEvents[0].askLabel,'问问这一卦');assert.equal(asking.scrollEvents[0].dotsHidden,true);assert.equal(asking.scrollEvents[0].question,'');assert.match(asking.scrollEvents[0].status,/回答已完成/);
 asking.run('renderQuestions();renderReading()');assert.equal(asking.scrollEvents.length,1,'passive rerenders keep the reader in place');
 asking.run("matchMedia=()=>({matches:false});let finishQuestionTransition;document.startViewTransition=fn=>({updateCallbackDone:new Promise(resolve=>{finishQuestionTransition=()=>{fn();resolve();};})})");
 asking.get('#question').value='第三个问题';asking.get('#question').oninput();const smoothQuestion=asking.get('#ask').onclick();const thirdAnswer={...answer,id:'question-3',question:'第三个问题',created_at:'2026-10-31T03:00:00.000Z'};
 finishQuestion(response({task_id:'q-third',reading_id:id,question_id:thirdAnswer.id,status:'succeeded',content:thirdAnswer}));await settle();assert.equal(asking.scrollEvents.length,1,'wait for the question DOM transition before scrolling');asking.run('finishQuestionTransition()');await smoothQuestion;assert.equal(asking.scrollEvents[1].questionId,thirdAnswer.id);assert.equal(asking.scrollEvents[1].options.behavior,'smooth');assert.equal(asking.scrollEvents[1].askBusy,'false');
 asking.get('#question').value='第四个问题';asking.get('#question').oninput();const staleQuestionTransition=asking.get('#ask').onclick();const fourthAnswer={...answer,id:'question-4',question:'第四个问题',created_at:'2026-10-31T04:00:00.000Z'};
 finishQuestion(response({task_id:'q-fourth',reading_id:id,question_id:fourthAnswer.id,status:'succeeded',content:fourthAnswer}));await settle();asking.run('epoch++;archived=true;finishQuestionTransition()');await staleQuestionTransition;assert.equal(asking.scrollEvents.length,2,'a late question animation cannot scroll after leaving the active reading');
 let finishLateQuestion;const lateQuestion=app({stored:[fixture(other)],fetch:async(path)=>path.endsWith('/questions')?new Promise(resolve=>{finishLateQuestion=resolve;}):response(ready(fixture()))});await settle();lateQuestion.get('#question').value='问题';lateQuestion.get('#question').oninput();const lateQuestionWork=lateQuestion.get('#ask').onclick();
 lateQuestion.run('epoch++;record=structuredClone(records.find(r=>r.id!==currentId));archived=true;scenario();renderReading()');finishLateQuestion(response({task_id:'q-late',reading_id:id,question_id:answer.id,status:'succeeded',content:answer}));await lateQuestionWork;assert.equal(lateQuestion.run('record.id'),other);assert.equal(lateQuestion.scrollEvents.length,0);assert.equal(lateQuestion.saved().find(r=>r.id===id).questions.length,0,'late answers cannot attach to or scroll another record');
 const cachedRecord=fixture();cachedRecord.deep.today=content;cachedRecord.selected='today';let cachedCalls=0;const cached=app({fetch:async()=>{cachedCalls++;return response(ready(cachedRecord));}});await settle();
 assert.equal(cached.get('#result').scrolls.length,0,'restoring a saved theme does not move the reader');
 await cached.get('#generate').onclick();assert.equal(cachedCalls,1);assert.equal(cached.get('#deep-title').textContent,content.title);
 assert.equal(cached.get('#result').scrolls.length,1,'explicit cached result click brings it into view');assert.equal(cached.get('#result').scrolls[0].behavior,'instant');
 cached.run("matchMedia=()=>({matches:false});let finishTransition;document.startViewTransition=fn=>({updateCallbackDone:new Promise(resolve=>{finishTransition=()=>{fn();resolve();};})})");
 const transitionWork=cached.get('#generate').onclick();assert.equal(cached.get('#result').scrolls.length,1,'wait until result DOM is revealed');cached.run('finishTransition()');await transitionWork;assert.equal(cached.get('#result').scrolls[1].behavior,'smooth');
 const staleTransition=cached.get('#generate').onclick();cached.run('epoch++;finishTransition()');await staleTransition;assert.equal(cached.get('#result').scrolls.length,2,'late transition must not scroll another reading');
 let resolveFresh;const fresh=app({fetch:async(path)=>path.endsWith('/deep-reading')?new Promise(resolve=>{resolveFresh=resolve;}):response(ready(fixture()))});await settle();fresh.run("selected='career';updateThemes()");const freshWork=fresh.get('#generate').onclick();await settle();assert.equal(fresh.get('#loading').hidden,false);assert.equal(fresh.get('#generate').disabled,true);
 resolveFresh(response({task_id:'fresh-task',reading_id:id,theme:'career',status:'succeeded',content}));await freshWork;assert.equal(fresh.get('#result').hidden,false);assert.equal(fresh.get('#result').scrolls.length,1);assert.equal(fresh.get('#result').scrolledWhileLoading,false,'remove loading before scrolling to avoid shifting the result above the viewport');assert.equal(fresh.get('#loading').hidden,true);assert.equal(fresh.get('#generate').disabled,false);
 const demo=app({path:'/',fetch:()=>{throw Error('demo must not request');}});await settle();assert.equal(demo.saved()[0].content_origin,'demo');assert.equal(demo.get('#reading').hidden,false);
 const device=app({path:'/',hash:'#d=32.0123456789abcdef.1',fetch:()=>{throw Error('device demo must not request');}});await settle();assert.equal(device.saved()[0].content_origin,'device_demo');assert.equal(device.saved()[0].hex.hexagram_id,32);
 console.log('PASS: authenticated routes, exact server snapshot, local scan dates, token cleanup, pending/error no writes, explicit retry, request id reuse, task ownership, stale response rejection, read-only history, source labels, cached themes, immediate question feedback, latest-answer scrolling after UI reset, passive render stability, legacy demos.');
})().catch(error=>{console.error(error);process.exitCode=1;});
