import torch.nn as nn
from LAMDA_SSL.Opitimizer.Adam import Adam
from LAMDA_SSL.Transform.ToImage import ToImage
from LAMDA_SSL.Dataloader.UnlabeledDataloader import UnlabeledDataLoader
from LAMDA_SSL.Dataloader.LabeledDataloader import LabeledDataLoader
from LAMDA_SSL.Sampler.RandomSampler import RandomSampler
from LAMDA_SSL.Sampler.SequentialSampler import SequentialSampler
from LAMDA_SSL.Evaluation.Classification.Accuracy import Accuracy
from LAMDA_SSL.Evaluation.Classification.Top_k_Accuracy import Top_k_Accurary
from LAMDA_SSL.Evaluation.Classification.Precision import Precision
from LAMDA_SSL.Evaluation.Classification.Recall import Recall
from LAMDA_SSL.Evaluation.Classification.F1 import F1
from LAMDA_SSL.Evaluation.Classification.AUC import AUC
from LAMDA_SSL.Evaluation.Classification.Confusion_Matrix import Confusion_Matrix
from LAMDA_SSL.Dataset.LabeledDataset import LabeledDataset
from LAMDA_SSL.Dataset.UnlabeledDataset import UnlabeledDataset
from LAMDA_SSL.Transform.ImageToTensor import ImageToTensor
from LAMDA_SSL.Scheduler.Linear_Warmup import Linear_Warmup

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
scheduler=Linear_Warmup(num_warmup_steps=15,num_training_steps=10,verbose=False)

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
weight_decay=5e-4
ema_decay=None
epoch=10
num_it_epoch=540
num_it_total=540*10
eval_epoch=None
eval_it=None
device='cpu'

parallel=None
file=None
verbose=False

dim_in=None
num_classes=None
noise_std=0.2
lambda_u=[0.1, 0.1, 0.1, 0.1, 0.1, 10., 1000.]
dim_encoder=[1000, 500, 250, 250, 250]
encoder_activations=[nn.ReLU(), nn.ReLU(), nn.ReLU(), nn.ReLU(), nn.ReLU()]


