export async function api(path, {method='GET',body,token,sessionToken}={}) {
 const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{}),...(sessionToken?{'X-Session-Token':sessionToken}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
 let data; try{data=await response.json()}catch{throw new Error('The server returned an unreadable response. Please check the backend.')}
 if(!response.ok) {
  if(typeof data.detail==='string')throw new Error(data.detail);
  if(Array.isArray(data.detail)) {
   const issues=data.detail.map(issue=>{
    const field=issue.loc?.filter(p=>p!=='body').join('.')||'details';
    if(field==='action'&&body?.action==='support'&&issue.type==='literal_error')return 'The backend is running an older version. Restart SmartPath in Terminal, then refresh this page.';
    if(field==='email')return 'Please enter a valid email address, for example name@example.com.';
    const labels={name:'Name',company:'Company',message:'Your question',service_consent:'Service contact permission','requirements.audience':'Who the training is for'};
    return (labels[field]||field)+': '+(issue.msg||'Please check this field.');
   });
   throw new Error([...new Set(issues)].join(' '));
  }
  throw new Error('The request could not be saved. Please try again.');
 }
 return data;
}
export const money=n=>n==null?'Ask for pricing':new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:0}).format(n);
