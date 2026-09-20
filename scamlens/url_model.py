"""Interpretable URL-string model construction and metrics."""
from __future__ import annotations
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
import numpy as np

URL_LABELS=["benign","phish"]

def build_url_pipeline(*, ngram_range: tuple[int,int], min_df: int, c_value: float, class_weight: str|None) -> Pipeline:
    return Pipeline([
        ("tfidf",TfidfVectorizer(analyzer="char",ngram_range=ngram_range,min_df=min_df,sublinear_tf=True,max_features=100_000,dtype=np.float32)),
        ("classifier",LogisticRegression(C=c_value,class_weight=class_weight,max_iter=1000,random_state=42)),
    ])

def classification_metrics(y_true, y_pred) -> dict[str,object]:
    precision,recall,f1,support=precision_recall_fscore_support(y_true,y_pred,labels=URL_LABELS,zero_division=0)
    per={label:{"precision":float(precision[i]),"recall":float(recall[i]),"f1":float(f1[i]),"support":int(support[i])} for i,label in enumerate(URL_LABELS)}
    weighted=sum(per[label]["f1"]*per[label]["support"] for label in URL_LABELS)/sum(support)
    matrix=confusion_matrix(y_true,y_pred,labels=URL_LABELS)
    return {"accuracy":float(accuracy_score(y_true,y_pred)),"macro_f1":float(f1.mean()),"weighted_f1":float(weighted),"per_class":per,"confusion_matrix":matrix.tolist(),"confusion_matrix_labels":URL_LABELS,"false_positives":int(matrix[0,1]),"false_negatives":int(matrix[1,0])}
