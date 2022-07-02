from lamda_ssl.Algorithm.Classifier.Self_Training import Self_Training
from lamda_ssl.Evaluation.Classification.Accuracy import Accuracy
from lamda_ssl.Dataset.Table.BreastCancer import BreastCancer
from lamda_ssl.Evaluation.Classification.Recall import Recall
from lamda_ssl.Evaluation.Classification.F1 import F1
from lamda_ssl.Evaluation.Classification.Precision import Precision
from lamda_ssl.Evaluation.Classification.AUC import AUC
from lamda_ssl.Evaluation.Classification.Confusion_Matrix import Confusion_Matrix
from sklearn.svm import SVC
import numpy as np

file = open("../Result/Self_Training_BreastCancer.txt", "w")

dataset=BreastCancer(test_size=0.3,labeled_size=0.1,stratified=True,shuffle=True,random_state=0,default_transforms=True)

labeled_X=dataset.labeled_X
labeled_y=dataset.labeled_y
unlabeled_X=dataset.unlabeled_X
unlabeled_y=dataset.unlabeled_y
test_X=dataset.test_X
test_y=dataset.test_y

# Pre_transform
pre_transform=dataset.pre_transform
pre_transform.fit(np.vstack([labeled_X, unlabeled_X]))

labeled_X=pre_transform.transform(labeled_X)
unlabeled_X=pre_transform.transform(unlabeled_X)
test_X=pre_transform.transform(test_X)

SVM=SVC(C=1.0,kernel='linear',probability=True,gamma='auto')

evaluation={
    'accuracy':Accuracy(),
    'precision':Precision(average='macro'),
    'Recall':Recall(average='macro'),
    'F1':F1(average='macro'),
    'AUC':AUC(multi_class='ovo'),
    'Confusion_matrix':Confusion_Matrix(normalize='true')
}

model=Self_Training(base_estimator=SVM,threshold=0.8,criterion="threshold",max_iter=100,evaluation=evaluation,file=file,verbose=True)

model.fit(X=labeled_X,y=labeled_y,unlabeled_X=unlabeled_X)

performance=model.evaluate(X=test_X,y=test_y)

result=model.y_pred

print(result,file=file)

print(performance,file=file)