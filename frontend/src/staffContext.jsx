import React from 'react';
const types={support:'Support enquiry',consultation:'Consultation request',quote:'Quote request',enrol:'Enrolment enquiry',email:'Course recommendations request'};
export function enquiryText(lead){return lead?.message||lead?.requirements?.goal||(lead?.summary_source!=='latest_assistant_response'?lead?.summary:'')||'No message collected; open the enquiry for its recorded requirements.'}
export function EnquiryContext({record,leads,onOpen,recipient}){
 const lead=leads.find(l=>l.id===record.lead_id);const text=enquiryText(lead);
 return <div className="enquiry-context"><p><strong>{lead?.name||'Customer details unavailable'}</strong><br/><span>To: {recipient||record.recipient||lead?.email||'Recipient unavailable'}</span></p><p>{types[lead?.action]||'Original enquiry'}{lead?.company?' · '+lead.company:''}</p><p className="prewrap">{text.length>220?text.slice(0,217)+'…':text}</p><p className="fine enquiry-reference">Enquiry reference: {record.lead_id}</p><button className="text-button" disabled={!lead} onClick={()=>onOpen(lead)}>View original enquiry</button></div>
}
export function EmailDeliveryActions({message,lead,onNotice}){
 const allowed=Boolean(lead?.service_consent)&&lead?.status!=='opted_out';
 if(!allowed)return <p className="fine">Email actions unavailable: the enquiry is missing or service contact permission is inactive.</p>;
 const href='mailto:'+encodeURIComponent(message.to)+'?subject='+encodeURIComponent(message.subject)+'&body='+encodeURIComponent(message.body);
 async function copy(){try{await navigator.clipboard.writeText('To: '+message.to+'\nSubject: '+message.subject+'\n\n'+message.body);onNotice('Email copied. Review and send it using your email app; SmartPath has not sent it.')}catch{onNotice('Copy is unavailable here. Select the displayed message text to copy it.')}}
 return <><p className="fine">Approved and saved locally. SmartPath has not sent this email. Your email app may need to be configured.</p><div className="actions"><a className="button secondary" href={href}>Open in email app</a><button className="button secondary" onClick={copy}>Copy email</button></div><p className="fine">Review the recipient and message before sending. Opening or copying does not confirm delivery. Record the contacted status yourself after sending.</p></>
}
