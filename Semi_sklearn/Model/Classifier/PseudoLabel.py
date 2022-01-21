import copy
from Semi_sklearn.Base.InductiveEstimator import InductiveEstimator
from Semi_sklearn.Base.SemiDeepModelMixin import SemiDeepModelMixin
from Semi_sklearn.Opitimizer.SemiOptimizer import SemiOptimizer
from Semi_sklearn.Scheduler.SemiScheduler import SemiLambdaLR
from sklearn.base import ClassifierMixin
from Semi_sklearn.utils import EMA
import torch
from Semi_sklearn.utils import cross_entropy
from Semi_sklearn.utils import partial
import numpy as np
from torch.nn import Softmax

def fix_bn(m,train=False):
    classname = m.__class__.__name__
    if classname.find('BatchNorm') != -1:
        if train:
            m.train()
        else:
            m.eval()

class PseudoLable(InductiveEstimator,SemiDeepModelMixin,ClassifierMixin):
    def __init__(self,train_dataset=None,test_dataset=None,
                 train_dataloader=None,
                 test_dataloader=None,
                 augmentation=None,
                 network=None,
                 train_sampler=None,
                 train_batch_sampler=None,
                 test_sampler=None,
                 test_batch_sampler=None,
                 epoch=1,
                 num_it_epoch=None,
                 num_it_total=None,
                 warmup=None,
                 eval_epoch=None,
                 eval_it=None,
                 optimizer=None,
                 scheduler=None,
                 device='cpu',
                 evaluation=None,
                 lambda_u=None,
                 mu=None,
                 ema_decay=None,
                 weight_decay=None,
                 threshold=0.95
                 ):
        SemiDeepModelMixin.__init__(self,train_dataset=train_dataset,
                                    test_dataset=test_dataset,
                                    train_dataloader=train_dataloader,
                                    test_dataloader=test_dataloader,
                                    augmentation=augmentation,
                                    network=network,
                                    train_sampler=train_sampler,
                                    train_batch_sampler=train_batch_sampler,
                                    test_sampler=test_sampler,
                                    test_batch_Sampler=test_batch_sampler,
                                    epoch=epoch,
                                    num_it_epoch=num_it_epoch,
                                    num_it_total=num_it_total,
                                    eval_epoch=eval_epoch,
                                    eval_it=eval_it,
                                    mu=mu,
                                    optimizer=optimizer,
                                    scheduler=scheduler,
                                    device=device,
                                    evaluation=evaluation
                                    )
        self.ema_decay=ema_decay
        self.lambda_u=lambda_u
        self.threshold=threshold
        self.weight_decay=weight_decay
        self.warmup=warmup

        if self.ema_decay is not None:
            self.ema=EMA(model=self._network,decay=ema_decay)
            self.ema.register()
        else:
            self.ema=None
        if isinstance(self._augmentation,dict):
            self.weakly_augmentation=self._augmentation['augmentation']
            self.normalization = self._augmentation['normalization']
        elif isinstance(self._augmentation,(list,tuple)):
            self.weakly_augmentation = self._augmentation[0]
            self.normalization = self._augmentation[1]
        else:
            self.weakly_augmentation = copy.deepcopy(self._augmentation)
            self.normalization = copy.deepcopy(self._augmentation)

        if isinstance(self._optimizer,SemiOptimizer):
            no_decay = ['bias', 'bn']
            grouped_parameters = [
                {'params': [p for n, p in self._network.named_parameters() if not any(
                    nd in n for nd in no_decay)], 'weight_decay': self.weight_decay},
                {'params': [p for n, p in self._network.named_parameters() if any(
                    nd in n for nd in no_decay)], 'weight_decay': 0.0}
            ]
            self._optimizer=self._optimizer.init_optimizer(params=grouped_parameters)

        if isinstance(self._scheduler,SemiLambdaLR):
            self._scheduler=self._scheduler.init_scheduler(optimizer=self._optimizer)

    def train(self,lb_X,lb_y,ulb_X,*args,**kwargs):

        lb_X=self.weakly_augmentation.fit_transform(copy.deepcopy(lb_X))
        ulb_X=self.weakly_augmentation.fit_transform(copy.deepcopy(ulb_X))

        self._network.apply(partial(fix_bn, train=True))
        logits_x_lb = self._network(lb_X)
        self._network.apply(partial(fix_bn,train=False))

        logits_x_ulb = self._network(ulb_X)

        return logits_x_lb,lb_y,logits_x_ulb


    def get_loss(self,train_result,*args,**kwargs):
        logits_x_lb,lb_y,logits_x_ulb=train_result
        sup_loss = cross_entropy(logits_x_lb, lb_y, reduction='mean')  # CE_loss for labeled data

        _warmup = float(np.clip((self.it_total) / (self.warmup * self.num_it_total), 0., 1.))
        pseudo_label = torch.softmax(logits_x_ulb, dim=-1)
        max_probs, max_idx = torch.max(pseudo_label, dim=-1)
        mask = max_probs.ge(self.threshold).float()

        unsup_loss = (cross_entropy(logits_x_ulb, max_idx.detach())*mask ).mean() # MSE loss for unlabeled data

        loss = sup_loss + self.lambda_u * unsup_loss * _warmup
        return loss

    def get_predict_result(self,y_est,*args,**kwargs):

        self.y_score=Softmax(dim=-1)(y_est)
        max_probs,y_pred=torch.max(self.y_score, dim=-1)
        return y_pred

    def predict(self,X=None):
        return SemiDeepModelMixin.predict(self,X=X)

    def optimize(self,*args,**kwargs):
        self._optimizer.step()
        self._scheduler.step()
        if self.ema is not None:
            self.ema.update()
        self._network.zero_grad()

    def estimate(self,X,*args,**kwargs):
        X=self.normalization.fit_transform(X)
        if self.ema is not None:
            self.ema.apply_shadow()
        outputs = self._network(X)
        if self.ema is not None:
            self.ema.restore()
        return outputs


