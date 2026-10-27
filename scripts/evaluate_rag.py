"""Small expert-authored relevance fixture, not external benchmark or uplift evidence."""
import json,time,math,statistics
from pathlib import Path
from app.rag import Retriever
CASES=[
('AI workplace productivity training for HR team',{'experience':'beginner','audience':'team','team_size':15},['AI101','AI102','AI103']),
('learn python programming from scratch',{'experience':'beginner','audience':'individual'},['PY101']),
('Excel spreadsheet formulas for beginners',{'experience':'beginner','audience':'individual'},['XL101']),
('Power BI dashboard reports',{'experience':'intermediate','skills':['excel'],'audience':'individual'},['BI101']),
('protect employees from phishing and security threats',{'experience':'beginner','audience':'team','team_size':15},['CY101']),
('coaching line managers leadership teams',{'experience':'beginner','audience':'team','team_size':10},['LD101']),
('project scope risk planning dependencies',{'experience':'beginner','audience':'individual'},['PM101']),
('pandas clean analyse data in Python',{'experience':'intermediate','skills':['python'],'audience':'individual'},['PY201'])]
def run():
    r=Retriever();rows=[]
    for query,req,relevant in CASES:
        for advanced in [False,True]:
            start=time.perf_counter();recs,trace=r.search(query,req,advanced)
            ids=[x['course']['id'] for x in recs];hits=[int(x in relevant) for x in ids]
            dcg=sum(v/math.log2(i+2) for i,v in enumerate(hits));ideal=sum(1/math.log2(i+2) for i in range(min(3,len(relevant))))
            rows.append({'query':query,'method':'advanced' if advanced else 'bm25','ranked':ids,'relevant':relevant,
                'recall_at_3':sum(hits)/len(relevant),'mrr':next((1/(i+1) for i,h in enumerate(hits) if h),0),'ndcg_at_3':dcg/ideal,
                'seconds':time.perf_counter()-start,'trace':trace})
    summary={m:{k:statistics.mean(x[k] for x in rows if x['method']==m) for k in ['recall_at_3','mrr','ndcg_at_3','seconds']} for m in ['bm25','advanced']}
    out={'dataset':'8 hand-authored synthetic catalogue queries; author-labelled relevance; no held-out external benchmark','limitations':'Small exploratory fixture. First advanced query includes model load. Answer correctness requires separate live grounded-response review. Does not establish generalisation or business uplift.','summary':summary,'cases':rows}
    Path('evidence/rag-evaluation.json').write_text(json.dumps(out,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
