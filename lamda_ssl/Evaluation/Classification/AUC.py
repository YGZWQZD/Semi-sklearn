from lamda_ssl.Evaluation.Classification.EvaluationClassification import EvaluationClassification
from sklearn.metrics import roc_auc_score
from lamda_ssl.utils import partial
from lamda_ssl.utils import class_status

class AUC(EvaluationClassification):
    def __init__(self,
                 average="macro",
                 sample_weight=None,
                 max_fpr=None,
                 multi_class="raise",
                 labels=None,):
        super().__init__()
        self.average=average
        self.sample_weight=sample_weight
        self.max_fpr=max_fpr
        self.multi_class=multi_class
        self.labels=labels
        self.score=partial(roc_auc_score,average=self.average,
                           sample_weight=self.sample_weight,max_fpr=self.max_fpr,
                           multi_class=self.multi_class,labels=self.labels)


    def scoring(self,y_true,y_pred=None,y_score=None):
        num_classes=class_status(y=y_true).num_classes
        if num_classes==2 and len(y_score.shape)==2:
            return self.score(y_true=y_true, y_score=y_score[:,1])
        else:
            return self.score(y_true=y_true,y_score=y_score)