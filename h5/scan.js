(function(root){
'use strict';
// Public device demo links, not authentication or one-time claim tokens.
function resolve(hash,hexagrams,records,now=new Date()){
 if(!hash.startsWith('#d='))return {kind:'none'};
 const match=/^#d=([1-9]|[1-5]\d|6[0-4])\.([0-9a-f]{16})\.([1-9]\d{0,9})$/.exec(hash);
 if(!match||Number(match[3])>4294967295)return {kind:'invalid'};
 const hex=hexagrams.find(h=>h.hexagram_id===Number(match[1]));
 if(!hex)return {kind:'invalid'};
 const id='device-'+match[2]+'-'+match[3],existing=records.find(r=>r.id===id);
 if(existing){
  if(existing.content_origin!=='device_demo'||existing.hex.hexagram_id!==hex.hexagram_id||JSON.stringify(existing.hex.lines_bottom_to_top)!==JSON.stringify(hex.lines_bottom_to_top))return {kind:'invalid'};
  return {kind:'device',record:structuredClone(existing)};
 }
 const title='第 '+hex.hexagram_id+' 卦 · '+hex.name_zh;
 return {kind:'device',record:{id,scanned_at:now.toISOString(),day:[now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-'),hex:structuredClone(hex),
  base:{title,message:'本次设备卦象：上卦'+hex.upper_trigram+'，下卦'+hex.lower_trigram+'。',action:'先记录此刻的问题，解读功能将在服务接入后开放。'},
  web:{title,meaning:'此页展示设备本次确定的上下卦，与屏幕使用同一组卦象数据。',reflection:'当前为扫码联调，尚未生成纸签或 AI 解读，也没有进行一次性领取认证。',action:'本次记录可在当前浏览器的签文日历中回看；重新摇动设备会产生新记录。'},
  deep:{},questions:[],selected:'',content_origin:'device_demo'}};
}
const api={resolve};if(typeof module==='object')module.exports=api;else root.TurtleScan=api;
})(typeof window==='undefined'?{}:window);
