from datetime import date
from app.catalogue import COURSES
from app.rag import eligible,Retriever

def test_exact_eligibility_prerequisites_budget_and_capacity():
    assert not eligible(COURSES[4],{'skills':[]},date(2026,10,24))[0]
    assert eligible(COURSES[4],{'skills':['python']},date(2026,10,24))[0]
    assert not eligible(COURSES[0],{'team_size':25},date(2026,10,24))[0]
    assert not eligible(COURSES[0],{'team_size':15,'budget_gbp':1000},date(2026,10,24))[0]

def test_timeline_and_expired_dates():
    assert not eligible(COURSES[0],{'timeline_weeks':1},date(2026,10,24))[0]
    assert not eligible(COURSES[0],{},date(2027,1,1))[0]
    assert eligible(COURSES[0],{'timeline_weeks':6},date(2026,10,24))[0]

def test_real_bm25_baseline_filters_and_records_trace():
    recs,trace=Retriever().search('Python data analysis',{'experience':'beginner','skills':[]},advanced=False)
    assert recs and all(x['course']['id'] not in ['PY201','ML301'] for x in recs)
    assert trace['pipeline']=='BM25 baseline' and trace['retrieval_ms']>=0

def test_invalid_neural_scores_fail_closed():
    import numpy as np
    import pytest
    class Encoder:
        def encode(self,docs,**kwargs):return np.ones((len(docs),3))
    class Ranker:
        def predict(self,pairs):return np.full(len(pairs),np.nan)
    with pytest.raises(RuntimeError,match='nonfinite'):
        Retriever(encoder=Encoder(),reranker=Ranker()).search('AI',{})
