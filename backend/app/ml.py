"""Synthetic-only experimental scoring, NEVER an operational priority model."""
import json,os
from pathlib import Path
import numpy as np

LABEL='EXPERIMENTAL'
LIMIT='Synthetic labels only. This score is not a validated probability of ABC conversion.'
FEATURES=['team_size','timeline_weeks','intent','has_goal','has_format']
def features(r,action):
    return [min(r.get('team_size',1),100),r.get('timeline_weeks',12),int(action in ['quote','enrol','consultation']),int(bool(r.get('goal'))),int(bool(r.get('format')))]
def train(output_dir):
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.calibration import CalibratedClassifierCV,calibration_curve
    from sklearn.metrics import roc_auc_score,brier_score_loss,average_precision_score,confusion_matrix
    import joblib
    rng=np.random.default_rng(42); n=1600
    X=np.column_stack([rng.integers(1,51,n),rng.integers(1,25,n),rng.binomial(1,.5,n),rng.binomial(1,.85,n),rng.binomial(1,.65,n)])
    probabilities=1/(1+np.exp(-(-3.6+.02*X[:,0]-.06*X[:,1]+1.1*X[:,2]+.6*X[:,3]+.4*X[:,4])))
    y=rng.binomial(1,probabilities)
    a,b,c,d=train_test_split(X,y,test_size=.25,stratify=y,random_state=42)
    base=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000))
    model=CalibratedClassifierCV(base,method='sigmoid',cv=5); model.fit(a,c)
    p=model.predict_proba(b)[:,1]; frac,pred=calibration_curve(d,p,n_bins=5,strategy='quantile')
    metrics={'label':LABEL,'data':'1600 independent synthetic rows; stochastic invented label mechanism','limitations':LIMIT,'features':FEATURES,
        'split':'stratified 75/25 holdout, seed42; calibration CV inside training only','n_train':len(a),'n_holdout':len(b),
        'positive_rate_train':float(c.mean()),'positive_rate_holdout':float(d.mean()),'roc_auc':float(roc_auc_score(d,p)),
        'average_precision':float(average_precision_score(d,p)),'brier_score':float(brier_score_loss(d,p)),
        'constant_prevalence_brier':float(brier_score_loss(d,np.full(len(d),c.mean()))),'confusion_at_0_5':confusion_matrix(d,p>=.5).tolist(),
        'calibration_bins':[{'predicted':float(x),'observed':float(y)} for x,y in zip(pred,frac)],
        'production_data_needed':'Timestamped consented enquiry features available at scoring time, booking outcomes, exposure/channel, cancellations and revenue. Group/time split, leakage audit, subgroup checks, calibration drift and external validation before use.'}
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,out/'synthetic_model.joblib')
    (out/'ml_metrics.json').write_text(json.dumps(metrics,indent=2))
    return metrics

def score(requirements,action):
    p=Path(os.getenv('ML_MODEL_PATH','data/ml/synthetic_model.joblib'))
    result={'label':LABEL,'score':None,'limitations':LIMIT}
    if p.is_file():
        try:
            # Only load locally trained/trusted artifacts. joblib is not safe for untrusted uploads.
            import joblib
            model=joblib.load(p); result['score']=round(float(model.predict_proba([features(requirements,action)])[0,1]),4)
        except Exception: result['limitations']+=' Trained artifact unavailable or incompatible.'
    return result
if __name__=='__main__':
    print(json.dumps(train(os.getenv('ML_OUTPUT_DIR','data/ml')),indent=2))
