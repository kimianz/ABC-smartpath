import {describe,it,expect,vi,afterEach} from 'vitest';
import {api,money} from './api';
afterEach(()=>vi.unstubAllGlobals());
describe('API boundary',()=>{
 it('sends the session credential without a staff credential',async()=>{const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({id:'saved'})});vi.stubGlobal('fetch',fetch);await api('/leads',{method:'POST',sessionToken:'private',body:{service_consent:true}});expect(fetch.mock.calls[0][1].headers['X-Session-Token']).toBe('private');expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()});
 it('surfaces an unavailable AI response instead of inventing content',async()=>{vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:'Ollama unavailable'})}));await expect(api('/sessions/x/messages')).rejects.toThrow('Ollama unavailable')});
 it('does not invent missing prices',()=>expect(money(null)).toBe('Ask for pricing'));
});
it('explains old-backend support rejection without blaming contact details',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:[{loc:['body','action'],type:'literal_error',msg:"Input should be 'quote', 'consultation', 'enrol' or 'email'"}]})}));
 await expect(api('/leads',{method:'POST',body:{action:'support'}})).rejects.toThrow('backend is running an older version');
});
it('identifies invalid email without echoing private input',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({detail:[{loc:['body','email'],type:'value_error',msg:'value is not a valid email address',input:'private-invalid-value'}]})}));
 await expect(api('/leads',{method:'POST',body:{}})).rejects.toThrow('Please enter a valid email address');
});
