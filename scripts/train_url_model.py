"""Select and evaluate the leakage-controlled URL-string baseline."""
from __future__ import annotations
import argparse,json,platform,sys
from datetime import datetime,timezone
from pathlib import Path
import joblib,numpy as np,pandas as pd,scipy,sklearn
from sklearn.dummy import DummyClassifier

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from scamlens.runtime import sha256,source_version_identifier
from scamlens.url_analysis import parse_url,url_properties
from scamlens.url_inference import URL_TASK
from scamlens.url_model import URL_LABELS,build_url_pipeline,classification_metrics

CANDIDATES=[
 {"ngram_range":(3,5),"min_df":2,"c_value":1.0,"class_weight":None},
 {"ngram_range":(3,5),"min_df":3,"c_value":2.0,"class_weight":"balanced"},
 {"ngram_range":(4,6),"min_df":2,"c_value":1.0,"class_weight":"balanced"},
 {"ngram_range":(4,6),"min_df":5,"c_value":2.0,"class_weight":"balanced"},
]

def jsonable_config(config): return {**config,"ngram_range":list(config["ngram_range"])}
def diagnostic(y,pred,mask): return classification_metrics(y[mask],pred[mask]) if int(mask.sum()) else {"rows":0}

def main():
 p=argparse.ArgumentParser(); p.add_argument('--data',type=Path,required=True); p.add_argument('--manifest',type=Path,required=True); p.add_argument('--config',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
 data=pd.read_parquet(a.data); manifest=pd.read_parquet(a.manifest)[['sha256','assignment']]; data=data.merge(manifest,on='sha256',validate='one_to_one')
 parts={name:data[data.assignment.eq(name)].copy() for name in ['train','validation','test']}
 xtrain,ytrain=parts['train'].url,parts['train'].label; xval,yval=parts['validation'].url,parts['validation'].label; xtest,ytest=parts['test'].url,parts['test'].label
 dummy=DummyClassifier(strategy='prior').fit(np.zeros((len(ytrain),1)),ytrain)
 dummy_metrics=classification_metrics(yval,dummy.predict(np.zeros((len(yval),1))))
 results=[]; best=None
 for config in CANDIDATES:
  model=build_url_pipeline(**config); model.fit(xtrain,ytrain); pred=model.predict(xval); metrics=classification_metrics(yval,pred)
  item={"parameters":jsonable_config(config),"validation":metrics}; results.append(item)
  rank=(metrics['macro_f1'],metrics['per_class']['phish']['f1'],metrics['per_class']['phish']['recall'],-config['c_value'])
  if best is None or rank>best[0]: best=(rank,config,model,metrics)
 _,selected,model,validation_metrics=best
 test_pred=model.predict(xtest); test_metrics=classification_metrics(ytest,test_pred)
 props=pd.DataFrame([url_properties(parse_url(value,enforce_length=False)) for value in xtest],index=xtest.index)
 bands=pd.cut(props.url_length,bins=[0,50,100,200,np.inf],labels=['1-50','51-100','101-200','201+'])
 diagnostics={"url_length_bands":{str(band):diagnostic(ytest,test_pred,bands.eq(band)) for band in bands.cat.categories},"ip_literal":diagnostic(ytest,test_pred,props.ip_literal),"has_query":diagnostic(ytest,test_pred,props.has_query),"no_query":diagnostic(ytest,test_pred,~props.has_query)}
 seen_domains=set(parts['train'].registered_domain); diagnostics['registered_domain_seen_in_subset']=diagnostic(ytest,test_pred,parts['test'].registered_domain.isin(seen_domains)); diagnostics['registered_domain_unseen_in_subset']=diagnostic(ytest,test_pred,~parts['test'].registered_domain.isin(seen_domains))
 errors=parts['test'].loc[ytest.ne(test_pred),['sha256','label','date','registered_domain']].copy(); error_props=props.loc[errors.index].drop(columns=['has_query']); errors=pd.concat([errors.reset_index(drop=True),error_props.reset_index(drop=True)],axis=1); errors['predicted']=test_pred[ytest.ne(test_pred)]; errors=errors.drop(columns=['registered_domain']); errors['domain_seen_in_training_subset']=parts['test'].loc[ytest.ne(test_pred),'registered_domain'].isin(seen_domains).to_numpy()
 a.output.mkdir(parents=True,exist_ok=True)
 bundle={"pipeline":model,"labels":URL_LABELS,"task":URL_TASK,"feature_scope":"raw_url_string_only","evaluation_scope":"official_temporal_test_with_documented_eligibility_filters","dataset_revision":"eabec4b7a66324b79cc8a0ad856d1731dc26fe1a"}
 joblib.dump(bundle,a.output/'url_pipeline.joblib')
 metrics={"selection_metric":"validation macro-F1, then phishing F1 and recall; no test tuning","dummy_validation":dummy_metrics,"validation_candidates":results,"selected_parameters":jsonable_config(selected),"selected_validation":validation_metrics,"official_temporal_test":test_metrics,"diagnostics":diagnostics}
 (a.output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
 (a.output/'confusion_matrix.json').write_text(json.dumps({"labels":URL_LABELS,"validation":validation_metrics['confusion_matrix'],"test":test_metrics['confusion_matrix']},indent=2)+'\n')
 (a.output/'label_mapping.json').write_text(json.dumps({"ordered_labels":URL_LABELS,"meaning":{"benign":"Dataset label for a collected benign webpage; not a safety guarantee.","phish":"Dataset label for a collected phishing webpage; not proof about a submitted live site."}},indent=2)+'\n')
 errors.to_parquet(a.output/'error_analysis.parquet',index=False)
 provenance={"dataset":"phreshphish/phreshphish","version":"v1.0.1","revision":"eabec4b7a66324b79cc8a0ad856d1731dc26fe1a","source_urls":["https://huggingface.co/datasets/phreshphish/phreshphish","https://arxiv.org/abs/2507.10854"],"access_date":"2026-09-15","license":"CC BY 4.0; dataset card limits use to anti-phishing research","data_sha256":sha256(a.data),"manifest_sha256":sha256(a.manifest),"config_sha256":sha256(a.config),"model_sha256":sha256(a.output/'url_pipeline.joblib'),"trained_at_utc":datetime.now(timezone.utc).isoformat(),"versions":{"python":platform.python_version(),"pandas":pd.__version__,"numpy":np.__version__,"scipy":scipy.__version__,"sklearn":sklearn.__version__,"joblib":joblib.__version__},"code_version":source_version_identifier(ROOT)}
 (a.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
 print(json.dumps({"selected":jsonable_config(selected),"validation":validation_metrics,"test":test_metrics},indent=2))
if __name__=='__main__': main()
