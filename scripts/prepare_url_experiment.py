"""Create leakage-controlled URL-only experiment assignments."""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scamlens.runtime import sha256
from scamlens.url_analysis import MAX_URL_CHARACTERS

SEED = 42
CUTOFF = pd.Timestamp("2025-08-01").date()
TRAIN_LIMIT = 60_000

def rank(row: pd.Series) -> str:
    return hashlib.sha256(f"{SEED}|{row.sha256}".encode()).hexdigest()

def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument('--input',type=Path,required=True); parser.add_argument('--output-manifest',type=Path,required=True); parser.add_argument('--output-config',type=Path,required=True); args=parser.parse_args()
    data=pd.read_parquet(args.input); data['assignment']='excluded_invalid'
    valid=data.hostname.ne('') & data.label.isin(['benign','phish']) & data.url.str.len().le(MAX_URL_CHARACTERS)
    early=valid & data.official_split.eq('train') & data.date.lt(CUTOFF)
    later=valid & data.official_split.eq('train') & data.date.ge(CUTOFF)
    early_domains=set(data.loc[early,'registered_domain'])
    validation=later & ~data.registered_domain.isin(early_domains)
    data.loc[later & ~validation,'assignment']='excluded_validation_domain_overlap'
    data.loc[validation,'assignment']='validation'
    pool=data.loc[early].copy(); pool['month']=pool.date.astype(str).str[:7]; pool['rank']=pool.apply(rank,axis=1)
    sizes=pool.groupby(['month','label']).size(); raw=sizes/sizes.sum()*TRAIN_LIMIT
    quotas=raw.astype(int); remainder=TRAIN_LIMIT-int(quotas.sum())
    for key in (raw-quotas).sort_values(ascending=False).index[:remainder]: quotas[key]+=1
    selected=[]
    for key, group in pool.groupby(['month','label']): selected.extend(group.sort_values('rank').head(int(quotas[key])).index)
    data.loc[early,'assignment']='unused_training_pool'; data.loc[selected,'assignment']='train'
    official_train_norm=set(data.loc[valid & data.official_split.eq('train'),'normalized_url'])
    test=valid & data.official_split.eq('test')
    leakage=test & data.normalized_url.isin(official_train_norm)
    data.loc[test,'assignment']='test'; data.loc[leakage,'assignment']='excluded_test_normalized_overlap'
    manifest=data[['sha256','official_split','source_shard','label','date','assignment']].copy()
    args.output_manifest.parent.mkdir(parents=True,exist_ok=True); manifest.to_parquet(args.output_manifest,index=False)
    selected_data=data[data.assignment.isin(['train','validation','test'])]
    config={
      'random_seed':SEED,'validation_cutoff':str(CUTOFF),'training_subset_limit':TRAIN_LIMIT,
      'selection':'Proportional month-by-label allocation; lowest SHA-256(seed|published sha256) ranks per stratum.',
      'validation':'Training-period rows on/after cutoff whose registered domain is absent before cutoff.',
      'test':'Official temporal test, excluding invalid inputs and normalized equivalents of official training URLs.',
      'feature':'Raw published URL string only; normalization and domain are audit/grouping-only.',
      'input_sha256':sha256(args.input),'manifest_sha256':sha256(args.output_manifest),
      'assignments':{str(k):int(v) for k,v in data.assignment.value_counts().items()},
      'class_by_assignment':{'|'.join(k):int(v) for k,v in selected_data.groupby(['assignment','label']).size().items()},
    }
    args.output_config.write_text(json.dumps(config,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(config,indent=2))
if __name__=='__main__': main()
