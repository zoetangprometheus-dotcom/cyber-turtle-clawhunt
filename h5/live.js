(function(root){
'use strict';
const READING=/^[0-9a-f]{32}$/;
function entry(path){
 let match=/^\/r\/([A-Za-z0-9_-]{22})\/?$/.exec(path);
 if(match)return {kind:'claim',token:match[1]};
 match=/^\/s\/([0-9a-f]{32})\/?$/.exec(path);
 if(match)return {kind:'reading',readingId:match[1]};
 return {kind:/^\/[rs](?:\/|$)/.test(path)?'invalid':'none'};
}
function failure(message,code='network'){const error=new Error(message);error.code=code;return error;}
function sourceLabel(origin){return {ai:'AI 创作',fallback:'备用内容',device_demo:'设备扫码演示',demo:'编辑样例',demo_template:'模板演示'}[origin]||'编辑样例';}
function prepareRecord(value,id,records,history,now=new Date()){
 if(!value||value.id!==id||!['ai','fallback'].includes(value.content_origin))throw failure('签文数据不完整，请重试读取');
 const existing=records.find(r=>r.id===id),record=structuredClone(value);
 record.scanned_at=existing?.scanned_at||now.toISOString();record.day=existing?.day||history.dayKey(now);
 if(!history.valid(record))throw failure('签文数据不完整，未写入本机历史');
 return record;
}
function questionRequest(previous,question,theme,uuid){
 if(previous&&previous.question===question&&previous.theme===(theme||undefined))return previous;
 return {request_id:uuid(),question,...(theme?{theme}:{})};
}
function createClient({fetch:fetcher=root.fetch?.bind(root),wait=ms=>new Promise(resolve=>setTimeout(resolve,ms)),now=Date.now,pollLimit=60,interval=1000}={}){
 function current(check){if(check&&!check())throw failure('已切换签文','stale');}
 async function request(path,body,timeout=15000){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
  try{
   const response=await fetcher(path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',headers:body===undefined?{Accept:'application/json'}:{Accept:'application/json','Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)}),signal:controller.signal});
   let payload;try{payload=await response.json();}catch{throw failure('暂时无法读取服务响应，请重试');}
   if(!response.ok){const code=['expired','claimed','session','invalid','busy','network'].includes(payload?.code)?payload.code:({401:'session',403:'session',404:'invalid',410:'expired',429:'busy'}[response.status]||'network');throw failure(typeof payload?.error==='string'?payload.error:'暂时连接不上，请稍后重试',code);}
   if(!payload||typeof payload!=='object')throw failure('服务响应不完整，请重试');
   return payload;
  }catch(error){if(typeof error.code==='string'&&['expired','claimed','session','invalid','busy','network'].includes(error.code))throw error;throw failure('暂时连接不上，请检查网络后重试');}finally{clearTimeout(timer);}
 }
 function readingEnvelope(value,id){
  if(!READING.test(value.reading_id)||id&&value.reading_id!==id||!['pending','ready','failed'].includes(value.status))throw failure('签文响应不匹配，请重试读取');
  if(value.status==='ready'&&value.record?.id!==value.reading_id)throw failure('签文响应不匹配，请重试读取');
  return value;
 }
 async function read(id,timeout){if(!READING.test(id))throw failure('没有找到这张签','invalid');return readingEnvelope(await request('/api/readings/'+id,undefined,timeout),id);}
 async function poll(value,fetchNext,check,validate){
  const deadline=now()+60000;
  for(let count=0;value.status==='pending';count++){
   current(check);
   if(count>=pollLimit||now()>=deadline)throw failure('内容仍在生成，稍后重试可继续读取本次任务','timeout');
   await wait(Math.min(interval,deadline-now()));current(check);
   const remaining=deadline-now();if(remaining<=0)throw failure('内容仍在生成，稍后重试可继续读取本次任务','timeout');
   value=validate(await fetchNext(Math.min(15000,remaining)));current(check);
  }
  return value;
 }
 function taskEnvelope(value,taskId){
  if(typeof value.task_id!=='string'||!/^[-_A-Za-z0-9]{1,128}$/.test(value.task_id)||taskId&&value.task_id!==taskId||!['pending','succeeded','failed'].includes(value.status))throw failure('解读任务响应不匹配，请重试');
  return value;
 }
 async function task(id,type,body,check){
  if(!READING.test(id))throw failure('没有找到这张签','invalid');current(check);
  function belongs(value,taskId,questionId){taskEnvelope(value,taskId);if(value.reading_id!==undefined&&value.reading_id!==id||type==='deep-reading'&&value.theme!==undefined&&value.theme!==body.theme||questionId&&value.question_id!==questionId)throw failure('解读任务归属不匹配，请重试');return value;}
  let value=belongs(await request('/api/readings/'+id+'/'+type,body));current(check);
  const taskId=value.task_id,questionId=value.question_id;
  value=await poll(value,timeout=>request('/api/readings/'+id+'/tasks/'+encodeURIComponent(taskId),undefined,timeout),check,next=>belongs(next,taskId,questionId));
  if(value.status==='failed')throw failure(value.error||'这次解读没有完成，可以重试','generation');
  const content=value.content,fields=type==='questions'?content?.answer:content;
  if(!fields||!(type==='questions'?['meaning','reflection','action']:['title','meaning','reflection','action']).every(key=>typeof fields[key]==='string'&&fields[key].trim()))throw failure('解读内容不完整，请重试');
  if(type==='questions'&&(!content.id||value.question_id&&content.id!==value.question_id||content.question!==body.question||content.content_origin!=='ai'||typeof content.created_at!=='string'||!Number.isFinite(Date.parse(content.created_at))||new Date(content.created_at).toISOString()!==content.created_at))throw failure('问卦响应不匹配，请重试');
  return content;
 }
 return {
  claim:async token=>{if(!/^[A-Za-z0-9_-]{22}$/.test(token))throw failure('没有找到这张签','invalid');return readingEnvelope(await request('/api/claim',{token}));},
  read,
  retry:async id=>{if(!READING.test(id))throw failure('没有找到这张签','invalid');return readingEnvelope(await request('/api/readings/'+id+'/retry',{}),id);},
  waitReading:(value,check)=>poll(readingEnvelope(value),timeout=>read(value.reading_id,timeout),check,next=>readingEnvelope(next,value.reading_id)),
  deep:(id,theme,check)=>task(id,'deep-reading',{theme},check),
  question:(id,body,check)=>task(id,'questions',body,check)
 };
}
const api={entry,sourceLabel,prepareRecord,questionRequest,createClient};if(typeof module==='object')module.exports=api;else root.TurtleLive=api;
})(typeof window==='undefined'?{}:window);
