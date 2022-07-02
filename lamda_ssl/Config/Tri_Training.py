from lamda_ssl.Evaluation.Classification.F1 import F1
from lamda_ssl.Evaluation.Classification.Accuracy import Accuracy
from lamda_ssl.Evaluation.Classification.Recall import Recall
from lamda_ssl.Evaluation.Classification.Precision import Precision
from lamda_ssl.Evaluation.Classification.AUC import AUC
from lamda_ssl.Evaluation.Classification.Confusion_Matrix import Confusion_Matrix
from sklearn.svm import SVC
base_estimator=SVC(C=1.0,kernel='linear',probability=True,gamma='auto')
base_estimator_2=SVC(C=1.0,kernel='linear',probability=True,gamma='auto')
base_estimator_3=SVC(C=1.0,kernel='linear',probability=True,gamma='auto')
evaluation={
    'accuracy':Accuracy(),
    'precision':Precision(average='macro'),
    'Recall':Recall(average='macro'),
    'F1':F1(average='macro'),
    'AUC':AUC(multi_class='ovo'),
    'Confusion_matrix':Confusion_Matrix(normalize='true')
}
verbose=False
file=None