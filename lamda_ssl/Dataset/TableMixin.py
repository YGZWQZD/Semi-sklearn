from sklearn.pipeline import Pipeline
from sklearn import preprocessing
from lamda_ssl.Transform.ToTensor import ToTensor

class TableMixin:
    def __init__(self):
        pass

    def init_default_transforms(self):
        self.transforms=None
        self.target_transform=None
        self.pre_transform=Pipeline([('StandardScaler',preprocessing.StandardScaler())
                              ])
        self.transform=Pipeline([('ToTensor', ToTensor())])
        self.unlabeled_transform=Pipeline([('ToTensor', ToTensor())])
        self.test_transform=Pipeline([('ToTensor', ToTensor())])
        self.valid_transform=Pipeline([('ToTensor', ToTensor())])
        return self