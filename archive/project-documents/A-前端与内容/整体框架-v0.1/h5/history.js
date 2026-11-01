(function(root){
'use strict';
const KEY='cyber-turtle-history-v1';
const THEMES=['today','romance','career','friendship'];
const clone=x=>JSON.parse(JSON.stringify(x));
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const text=x=>typeof x==='string'&&x.trim().length>0;
function dayKey(date){return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-');}
function monthDays(year,month){return {offset:(new Date(year,month,1).getDay()+6)%7,count:new Date(year,month+1,0).getDate()};}
function validDay(value){if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const date=new Date(value+'T00:00:00.000Z');return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===value;}
function validTime(value){if(typeof value!=='string')return false;const date=new Date(value);return Number.isFinite(date.getTime())&&date.toISOString()===value;}
function fields(value,keys){return object(value)&&keys.every(k=>text(value[k]));}
function valid(r){
 if(!object(r)||!text(r.id)||!validTime(r.scanned_at)||!validDay(r.day))return false;
 if(!fields(r.base,['title','message','action'])||!fields(r.web,['title','meaning','reflection','action']))return false;
 if(!fields(r.hex,['name_zh','upper_trigram','lower_trigram'])||!Number.isInteger(r.hex.hexagram_id)||r.hex.hexagram_id<1||r.hex.hexagram_id>64)return false;
 if(!Array.isArray(r.hex.lines_bottom_to_top)||r.hex.lines_bottom_to_top.length!==6||!r.hex.lines_bottom_to_top.every(x=>x===0||x===1))return false;
 if(!object(r.deep)||!Object.entries(r.deep).every(([key,value])=>THEMES.includes(key)&&fields(value,['title','meaning','reflection','action'])))return false;
 if(r.selected!==undefined&&r.selected!==''&&!THEMES.includes(r.selected))return false;
 if(!Array.isArray(r.questions)||!r.questions.every(q=>object(q)&&text(q.id)&&text(q.question)&&validTime(q.created_at)&&fields(q.answer,['meaning','reflection','action'])))return false;
 return new Set(r.questions.map(q=>q.id)).size===r.questions.length;
}
function read(storage){
 try{
  const raw=storage.getItem(KEY);if(!raw)return {version:1,records:[],active_id:null,quarantined:[]};
  const x=JSON.parse(raw);
  if(!object(x)||x.version!==1||!Array.isArray(x.records)||(x.quarantined!==undefined&&!Array.isArray(x.quarantined)))throw Error('invalid envelope');
  const records=[],quarantined=[...(x.quarantined||[])],seen=new Set();
  for(const record of x.records){if(valid(record)&&!seen.has(record.id)){records.push(record);seen.add(record.id);}else quarantined.push(record);}
  const result={version:1,records,quarantined,active_id:records.some(r=>r.id===x.active_id)?x.active_id:null};
  if(quarantined.length)result.warning=quarantined.length+' 条历史数据暂时无法显示，原始内容已保留；其余记录可正常使用。';
  return result;
 }catch{return {records:[],active_id:null,error:'本机历史暂时无法读取。原有数据未被覆盖，本次内容仍可查看和导出。'};}
}
function merge(existing,incoming){
 if(!existing)return clone(incoming);
 const questions=new Map(existing.questions.map(q=>[q.id,q]));
 for(const q of incoming.questions)if(!questions.has(q.id))questions.set(q.id,q);
 // Printed and web snapshots are immutable; completed theme results are also retained.
 return {...existing,selected:incoming.selected||'',deep:{...incoming.deep,...existing.deep},questions:[...questions.values()].sort((a,b)=>a.created_at.localeCompare(b.created_at)||a.id.localeCompare(b.id))};
}
async function save(storage,record,activeId,locks=root.navigator?.locks){
 if(!valid(record))return {...read(storage),error:'本次记录格式不完整，未写入历史；已有记录保持不变。'};
 const incoming=clone(record);
 if(!locks||typeof locks.request!=='function')return {...read(storage),error:'当前浏览器无法安全协调多页面保存，历史暂未写入。请使用支持 Web Locks 的 HTTPS 页面或本机预览，并先导出内容。'};
 try{return await locks.request(KEY+'-write',{mode:'exclusive'},()=>{
  // Read only after obtaining the same-origin cross-tab lock.
  const latest=read(storage);if(latest.error)return latest;
  const existing=latest.records.find(r=>r.id===incoming.id),merged=merge(existing,incoming);
  const records=latest.records.filter(r=>r.id!==incoming.id);records.push(merged);
  const result={version:1,active_id:activeId,records,quarantined:latest.quarantined};
  storage.setItem(KEY,JSON.stringify(result));
  return {...result,...(latest.warning?{warning:latest.warning}:{})};
 });}catch{return {...read(storage),error:'浏览器未能保存本次内容，请先导出图片或复制文字。'};}
}
const api={KEY,dayKey,monthDays,read,save,valid,merge};if(typeof module==='object')module.exports=api;else root.TurtleHistory=api;
})(typeof window==='undefined'?{}:window);
