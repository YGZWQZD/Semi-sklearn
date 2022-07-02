import torch.nn as nn
from lamda_ssl.Opitimizer.Adam import Adam
from lamda_ssl.Transform.ToImage import ToImage
from lamda_ssl.Dataloader.UnlabeledDataloader import UnlabeledDataLoader
from lamda_ssl.Dataloader.LabeledDataloader import LabeledDataLoader
from lamda_ssl.Sampler.RandomSampler import RandomSampler
from lamda_ssl.Sampler.SequentialSampler import SequentialSampler
from lamda_ssl.Evaluation.Classification.Accuracy import Accuracy
from lamda_ssl.Evaluation.Classification.Top_k_Accuracy import Top_k_Accurary
from lamda_ssl.Evaluation.Classification.Precision import Precision
from lamda_ssl.Evaluation.Classification.Recall import Recall
from lamda_ssl.Evaluation.Classification.F1 import F1
from lamda_ssl.Evaluation.Classification.AUC import AUC
from lamda_ssl.Evaluation.Classification.Confusion_Matrix import Confusion_Matrix
from lamda_ssl.Dataset.LabeledDataset import LabeledDataset
from lamda_ssl.Dataset.UnlabeledDataset import UnlabeledDataset
from lamda_ssl.Transform.ImageToTensor import ImageToTensor

transforms = None
target_transform = None
pre_transform = ToImage()
transform = ImageToTensor()
unlabeled_transform = ImageToTensor()
test_transform = ImageToTensor()
valid_transform = ImageToTensor()

train_dataset=None
labeled_dataset=LabeledDataset(pre_transform=pre_transform,transforms=transforms,
                               transform=transform,target_transform=target_transform)
unlabeled_dataset=UnlabeledDataset(pre_transform=pre_transform,transform=unlabeled_transform)
valid_dataset=UnlabeledDataset(pre_transform=pre_transform,transform=valid_transform)
test_dataset=UnlabeledDataset(pre_transform=pre_transform,transform=test_transform)

#dataloader
train_dataloader=None
labeled_dataloader=LabeledDataLoader(batch_size=100,num_workers=0,drop_last=True)
unlabeled_dataloader=UnlabeledDataLoader(num_workers=0,drop_last=True)
valid_dataloader=UnlabeledDataLoader(batch_size=100,num_workers=0,drop_last=False)
test_dataloader=UnlabeledDataLoader(batch_size=100,num_workers=0,drop_last=False)

# Batch sampler
train_batch_sampler=None
labeled_batch_sampler=None
unlabeled_batch_sampler=None
valid_batch_sampler=None
test_batch_sampler=None

# sampler
train_sampler=None
labeled_sampler=RandomSampler(replacement=True,num_samples=100*540)
unlabeled_sampler=RandomSampler(replacement=False)
test_sampler=SequentialSampler()
valid_sampler=SequentialSampler()

# optimizer
optimizer=Adam(lr=0.02)

# scheduler
scheduler=None

# network
network=None

# evalutation
evaluation={
    'accuracy':Accuracy(),
    'top_5_accuracy':Top_k_Accurary(k=5),
    'precision':Precision(average='macro'),
    'Recall':Recall(average='macro'),
    'F1':F1(average='macro'),
    'AUC':AUC(multi_class='ovo'),
    'Confusion_matrix':Confusion_Matrix(normalize='true')
}

mu=1
weight_decay=0
ema_decay=None

epoch=500
num_it_epoch=540
num_it_total=540*500
eval_it=2000
eval_epoch=None

device='cpu'

parallel=None
file=None
verbose=False

alpha=1
num_labeled=None
dim_in=None
num_classes=None
dim_z=50
dim_hidden_de=[500, 500]
dim_hidden_en_y=[500, 500]
dim_hidden_en_z=[500, 500]
activations_de=[nn.Softplus(), nn.Softplus()]
activations_en_y=[nn.Softplus(), nn.Softplus()]
activations_en_z=[nn.Softplus(), nn.Softplus()]

