"""BM25 + local dense embeddings + RRF + cross encoder + exact eligibility.
Lazy neural model loading is deliberate: health and browsing work without model downloads.
"""
import os,re,time,threading,json
from datetime import date, timedelta
import numpy as np
from rank_bm25 import BM25Okapi
from .catalogue import COURSES,FAQS
from .schemas import normalize_format

def tokens(text): return re.findall(r'[a-z0-9]+',text.lower())
# Lexical subject coverage is a retrieval precision guard, not a conversational
# fallback. Only explicit catalogue topic terms constrain semantic candidates;
# paraphrases without recognised subject terms keep normal neural retrieval.
TOPIC_STOP={'a','an','and','at','for','in','of','on','the','to','with','training','course','courses','team','teams','staff','employee','employees','business','workplace','work','practical','foundation','foundations','essential','essentials','beginner','intermediate','advanced','effective','applied','professional','online','classroom','blended','learn','learning','skill','skills','day','days','week','weeks'}
def subject_tokens(text):
    text=text.lower().replace('artificial intelligence','ai').replace('powerbi','power bi')
    return {t[:-1] if len(t)>4 and t.endswith('s') and not t.endswith('ss') else t for t in tokens(text)
            if len(t)>1 and not t.isdigit() and t not in TOPIC_STOP}

def eligible(course,r,as_of=None):
    reasons=[]
    if r.get('audience') and r['audience'] not in course['audiences']: reasons.append('audience')
    requested_format=normalize_format(r.get('format'))
    if requested_format not in (None,'','any') and requested_format not in [normalize_format(f) for f in course['formats']]: reasons.append('format')
    if r.get('team_size',1)>course['capacity']: reasons.append('cohort capacity')
    known=set(s.lower() for s in r.get('skills',[]))
    if not set(course['required_skills']).issubset(known): reasons.append('unconfirmed prerequisites')
    if r.get('experience')=='beginner' and course['level']!='beginner': reasons.append('difficulty')
    # Budget is total enquiry budget. Course rates are per learner.
    if r.get('budget_gbp') is not None and course['price_gbp'] is not None and course['price_gbp']*r.get('team_size',1)>r['budget_gbp']: reasons.append('total budget')
    today=as_of or date.today()
    future=[date.fromisoformat(d) for d in course['dates'] if date.fromisoformat(d)>=today]
    if not future: reasons.append('no future dates')
    if r.get('timeline_weeks') and not any(d<=today+timedelta(weeks=r['timeline_weeks']) for d in future): reasons.append('timeline')
    return not reasons,reasons

class Retriever:
    def __init__(self,courses=None,encoder=None,reranker=None,faqs=None):
        self.courses=courses if courses is not None else COURSES
        self.docs=[c['title']+'. Category: '+c['category']+'. Skills: '+', '.join(c['skills'])+'. '+c['description'] for c in self.courses]
        self.rerank_docs=[c['title']+'. Category: '+c['category']+'. Skills: '+', '.join(c['skills'])+'. '+
            ' '.join(re.split(r'(?<=[.!?])\s+',c['description'])[:3]) for c in self.courses]
        self.subjects=[subject_tokens(c['title']+' '+c['category']+' '+' '.join(c['skills'])) for c in self.courses]
        self.bm25=BM25Okapi([tokens(d) for d in self.docs])
        self.faqs=faqs if faqs is not None else FAQS
        self.faq_bm25=BM25Okapi([tokens(x['text']) for x in self.faqs])
        self.knowledge=[{**f,'source_type':'faq'} for f in self.faqs]
        for c in self.courses:
            facts={k:c[k] for k in ['title','description','level','duration','price_gbp','formats','prerequisites','required_skills','capacity','dates','availability','audiences']}
            self.knowledge.append({'id':c['id'],'source_type':'course','facts':facts,'text':c['id']+' '+c['title']+'. Published per-learner price GBP '+str(c['price_gbp'])+'. Duration '+c['duration']+'. Formats '+', '.join(c['formats'])+'. Prerequisites '+', '.join(c['prerequisites'])+'. '+c['description']+' Exact facts: '+json.dumps(facts)})
        self.knowledge_bm25=BM25Okapi([tokens(x['text']) for x in self.knowledge])
        self.encoder=encoder; self.reranker=reranker; self.embeddings=None; self.faq_embeddings=None
        self.lock=threading.Lock()
    def _load(self):
        with self.lock:
            if self.encoder is None or self.reranker is None:
                from sentence_transformers import SentenceTransformer,CrossEncoder
                import torch
                # CPU avoids simultaneous Metal contention with Ollama on 18GB unified memory.
                self.encoder=self.encoder or SentenceTransformer(os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2'),device='cpu')
                self.reranker=self.reranker or CrossEncoder(os.getenv('RERANK_MODEL','cross-encoder/ms-marco-MiniLM-L6-v2'),device='cpu',max_length=384,model_kwargs={'torch_dtype':torch.float64,'attn_implementation':'eager'})
            if self.embeddings is None:
                self.embeddings=self.encoder.encode(self.docs,normalize_embeddings=True,convert_to_numpy=True)
                if not np.isfinite(self.embeddings).all():
                    raise RuntimeError('Embedding model produced nonfinite vectors')
    def search(self,query,requirements,advanced=True):
        start=time.perf_counter()
        lexical=np.asarray(self.bm25.get_scores(tokens(query)))
        lex_order=np.argsort(-lexical,kind='stable').tolist()
        trace={'pipeline':'advanced' if advanced else 'BM25 baseline','eligible_exclusions':{},'sources':[]}
        vocabulary=set().union(*self.subjects)
        requested_subjects=subject_tokens(requirements.get('goal','')+' '+query)&vocabulary
        trace['explicit_subject_terms']=sorted(requested_subjects)
        trace['subject_exclusions']={}
        if advanced:
            self._load()
            vector=self.encoder.encode([query],normalize_embeddings=True,convert_to_numpy=True)[0]
            dense=np.asarray(self.embeddings)@vector
            dense_order=np.argsort(-dense,kind='stable').tolist()
            rrf={i:0. for i in range(len(self.courses))}
            for order in (lex_order,dense_order):
                for rank,i in enumerate(order): rrf[i]+=1/(60+rank+1)
            candidates=sorted(rrf,key=rrf.get,reverse=True)[:12]
            cross=np.asarray(self.reranker.predict([(query,self.rerank_docs[i]) for i in candidates])).reshape(-1)
            if not np.isfinite(cross).all():
                raise RuntimeError('Reranker produced nonfinite scores; inspect model compatibility')
            # Cross encoder raw logits govern relevance. RRF is recorded for traceability.
            ranked=sorted(zip(candidates,cross),key=lambda x:float(x[1]),reverse=True)
            trace.update({'lexical_ranking':[self.courses[i]['id'] for i in lex_order], 'dense_ranking':[self.courses[i]['id'] for i in dense_order],
                'rrf':{self.courses[i]['id']:round(v,6) for i,v in rrf.items()},'reranker':os.getenv('RERANK_MODEL','cross-encoder/ms-marco-MiniLM-L6-v2'),
                'reranked_scores':{self.courses[i]['id']:round(float(v),4) for i,v in ranked},'embedding_model':os.getenv('EMBEDDING_MODEL','sentence-transformers/all-MiniLM-L6-v2')})
        else: ranked=[(i,float(lexical[i])) for i in lex_order]
        recs=[]
        for i,score in ranked:
            c=self.courses[i]
            if requested_subjects and not requested_subjects.intersection(self.subjects[i]):
                trace['subject_exclusions'][c['id']]='No coverage of explicitly requested catalogue subject terms'
                continue
            ok,why=eligible(c,requirements)
            if not ok: trace['eligible_exclusions'][c['id']]=why; continue
            # A weak/negative semantic match should not fill a third slot for appearance.
            if (advanced and float(score)<float(os.getenv('MIN_RERANK_SCORE','-5'))) or (not advanced and float(score)<=0): continue
            reason=f"Relevant to {requirements.get('goal','your goal')}. {c['level'].capitalize()} level; {requirements.get('format','available delivery')} delivery; prerequisites and cohort limits checked."
            recs.append({'course':dict(c),'reason':reason,'score':round(float(score),4),'sources':[c['id']]})
            if len(recs)==3: break
        trace['approved_faqs']=[]
        trace['sources']=[r['course']['id'] for r in recs]
        trace['retrieval_ms']=round((time.perf_counter()-start)*1000,2)
        trace['score_meaning']='cross-encoder relevance logit; not a conversion probability' if advanced else 'BM25 relevance'
        return recs,trace

    def search_faq(self,query,original_query=None):
        """Independent approved-knowledge hybrid retrieval, never course filters."""
        start=time.perf_counter()
        if not self.knowledge: return [],{'pipeline':'FAQ hybrid','sources':[]}
        self._load()
        with self.lock:
            if self.faq_embeddings is None:
                self.faq_embeddings=self.encoder.encode([f['text'] for f in self.knowledge],normalize_embeddings=True,convert_to_numpy=True)
        q=self.encoder.encode([query],normalize_embeddings=True,convert_to_numpy=True)[0]
        dense=np.asarray(self.faq_embeddings)@q
        lexical=np.asarray(self.knowledge_bm25.get_scores(tokens(query)))
        if not np.isfinite(dense).all(): raise RuntimeError('FAQ embeddings produced nonfinite scores')
        orders=[np.argsort(-lexical,kind='stable').tolist(),np.argsort(-dense,kind='stable').tolist()]
        fusion={i:0. for i in range(len(self.knowledge))}
        for order in orders:
            for rank,i in enumerate(order): fusion[i]+=1/(61+rank)
        candidates=sorted(fusion,key=fusion.get,reverse=True)[:12]
        scores=np.asarray(self.reranker.predict([(query,self.knowledge[i]['text']) for i in candidates])).reshape(-1)
        if not np.isfinite(scores).all(): raise RuntimeError('FAQ reranker produced nonfinite scores')
        ranked=sorted(zip(candidates,scores),key=lambda x:float(x[1]),reverse=True)
        threshold=float(os.getenv('MIN_FAQ_RERANK_SCORE','0'))
        # An explicitly named approved course is an authoritative entity lookup,
        # not a semantic relevance guess. Exact facts must remain available even
        # when a cross-encoder dislikes a price/equipment phrasing.
        normalized=' '.join(tokens(query))
        padded=' '+normalized+' '+' '.join(tokens(original_query or ''))+' '
        exact=[i for i,record in enumerate(self.knowledge) if record.get('source_type')=='course' and
            (' '+record['id'].lower()+' ' in padded or
             ' '+' '.join(tokens(record['facts']['title']))+' ' in padded)]
        score_by_index={i:float(score) for i,score in ranked}
        wording=(original_query or query).lower()
        comparison=bool(re.search(r'\b(compare|comparison|versus|vs|difference|alternatives?)\b',wording))
        policy=bool(re.search(r'\b(cancel|cancellation|refund|accessibility|accessible|payment|pay|booking|certificate|discount|policy|policies)\b',wording))
        if exact and not comparison:
            # A named-course fact question does not need unrelated course facts.
            extra=[i for i,score in ranked if score>=threshold and self.knowledge[i]['source_type']=='faq'] if policy else []
        else: extra=[i for i,score in ranked if score>=threshold and i not in exact]
        selected=exact+extra
        hits=[{**self.knowledge[i],'score':round(score_by_index[i],4) if i in score_by_index else None,
            'exact_entity_lookup':i in exact} for i in selected[:3]]
        return hits,{'pipeline':'approved FAQ/course knowledge BM25 + local dense + RRF + cross-encoder','sources':[f['id'] for f in hits],
            'faq_lexical_ranking':[self.knowledge[i]['id'] for i in orders[0]],'faq_dense_ranking':[self.knowledge[i]['id'] for i in orders[1]],
            'faq_reranked_scores':{self.knowledge[i]['id']:round(float(v),4) for i,v in ranked},'faq_min_score':threshold,'exact_course_lookups':[self.knowledge[i]['id'] for i in exact],
            'retrieval_ms':round((time.perf_counter()-start)*1000,2)}
