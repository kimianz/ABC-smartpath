import React from 'react';
import {render,screen,fireEvent,within,waitFor,cleanup} from '@testing-library/react';
import {it,expect,vi,afterEach} from 'vitest';
import {App} from './main';
import {EnquiryContext,EmailDeliveryActions} from './staffContext';
afterEach(()=>{cleanup();vi.unstubAllGlobals();delete navigator.clipboard});
it('follows up the selected enquiry through manual approval and an addressed outbox message',async()=>{
 window.scrollTo=vi.fn();const calls=[];const copied=vi.fn().mockResolvedValue();Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:copied}});
 const sara={id:'enquiry-sara-1',name:'Sara Demo',email:'sara@example.com',action:'consultation',message:'Please discuss AI training for five colleagues.',status:'new',service_consent:true,requirements:{},recommendations:[],priority:'medium',created_at:'2026-10-26T09:00:00Z',activity:[]};
 const omar={...sara,id:'enquiry-omar-1',name:'Omar Demo',email:'omar@example.com',message:'I need Python training.'};let approvals=[];let outbox=[{id:'other-outbox',lead_id:omar.id,to:omar.email,subject:'Omar response',body:'Other customer message.',created_at:sara.created_at}];
 vi.stubGlobal('fetch',vi.fn(async(url,o={})=>{
  calls.push([url,o]);let value={};
  if(url.endsWith('/draft/manual')){const p=JSON.parse(o.body);value={id:'manual-1',lead_id:sara.id,recipient:sara.email,...p,status:'pending',source:'staff'};approvals.push(value)}
  else if(url==='/api/staff/approvals/manual-1'&&o.method==='PATCH'){Object.assign(approvals[0],{status:'approved'});outbox.push({id:'sara-message',lead_id:sara.id,to:sara.email,subject:approvals[0].subject,body:approvals[0].body,created_at:sara.created_at});value=approvals[0]}
  else if(url==='/api/courses')value=[];else if(url==='/api/health')value={status:'ok'};else if(url==='/api/staff/leads')value=[sara,omar];else if(url==='/api/staff/leads/'+sara.id)value={...sara,drafts:approvals};else if(url==='/api/staff/approvals')value=approvals;else if(url==='/api/staff/outbox')value=outbox;
  return {ok:true,json:async()=>value};
 }));
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:/Staff workspace/}));fireEvent.change(screen.getByLabelText('Staff access token'),{target:{value:'test-only'}});fireEvent.click(screen.getByRole('button',{name:'Open workspace →'}));await screen.findByRole('button',{name:'Sara Demo'});
 const row=screen.getByRole('button',{name:'Sara Demo'}).closest('tr');fireEvent.click(within(row).getByRole('button',{name:'Follow up →'}));await screen.findByLabelText('Reply subject');fireEvent.change(screen.getByLabelText('Reply subject'),{target:{value:'Following up on your AI training'}});fireEvent.change(screen.getByLabelText('Reply message'),{target:{value:'Hello Sara, can we discuss your preferred training dates?'}});fireEvent.click(screen.getByRole('button',{name:'Save reply for approval'}));await screen.findByText('Written by staff',{exact:false});
 expect(calls.some(([u])=>u==='/api/staff/leads/'+sara.id+'/draft/manual')).toBe(true);expect(calls.some(([u])=>u.includes('/draft')&&!u.endsWith('/manual'))).toBe(false);
 const card=screen.getByRole('article');expect(within(card).getByText('To: sara@example.com')).toBeInTheDocument();expect(card).toHaveTextContent(sara.message);expect(card).toHaveTextContent(sara.id);expect(card).not.toHaveTextContent(omar.message);
 fireEvent.click(screen.getByRole('button',{name:'Approve to outbox'}));await screen.findByRole('button',{name:'View messages for this enquiry in Outbox →'});fireEvent.click(screen.getByRole('button',{name:'View messages for this enquiry in Outbox →'}));expect(screen.queryByText('Omar response')).not.toBeInTheDocument();fireEvent.click(screen.getByText('Following up on your AI training').closest('summary'));
 const link=screen.getByRole('link',{name:'Open in email app'});expect(link.getAttribute('href')).toContain('mailto:sara%40example.com?');expect(decodeURIComponent(link.getAttribute('href'))).toContain('Hello Sara, can we discuss your preferred training dates?');fireEvent.click(screen.getByRole('button',{name:'Copy email'}));await waitFor(()=>expect(copied).toHaveBeenCalledWith(expect.stringContaining('To: sara@example.com')));
 expect(screen.getByText(/SmartPath has not sent it/)).toBeInTheDocument();fireEvent.click(screen.getByRole('button',{name:'Show all enquiries'}));expect(screen.getByText('Omar response')).toBeInTheDocument();
});
it('uses enquiry ID to distinguish two enquiries from the same contact',()=>{
 const leads=[{id:'one',name:'Sara',email:'sara@example.com',action:'quote',message:'Python enquiry.'},{id:'two',name:'Sara',email:'sara@example.com',action:'consultation',message:'AI enquiry.'}];
 render(<EnquiryContext record={{lead_id:'two'}} leads={leads} onOpen={vi.fn()}/>);expect(screen.getByText('AI enquiry.')).toBeInTheDocument();expect(screen.queryByText('Python enquiry.')).not.toBeInTheDocument();expect(screen.getByText('Enquiry reference: two')).toBeInTheDocument();
});
it('does not offer email export after contact permission is withdrawn',()=>{
 render(<EmailDeliveryActions message={{to:'sara@example.com',subject:'Example',body:'Saved message'}} lead={{service_consent:false,status:'opted_out'}} onNotice={vi.fn()}/>);expect(screen.queryByRole('link',{name:'Open in email app'})).not.toBeInTheDocument();expect(screen.queryByRole('button',{name:'Copy email'})).not.toBeInTheDocument();expect(screen.getByText(/permission is inactive/)).toBeInTheDocument();
});
