from lamda_ssl.Base.InductiveEstimator import InductiveEstimator
from lamda_ssl.Base.DeepModelMixin import DeepModelMixin
from sklearn.base import RegressorMixin
from lamda_ssl.Loss.MSE import MSE
import numpy as np
import torch
from lamda_ssl.Transform.Mixup import Mixup
from lamda_ssl.utils import Bn_Controller
from lamda_ssl.Network.MLP_Reg import MLP_Reg
import torch.nn as nn
import copy
import lamda_ssl.Config.ICTReg as config
from lamda_ssl.Loss.Semi_supervised_Loss import Semi_supervised_loss

class ICTReg(DeepModelMixin,InductiveEstimator,RegressorMixin):
    def __init__(self,
                 alpha=config.alpha,
                 lambda_u=config.lambda_u,
                 warmup=config.warmup,
                 dim_in=config.dim_in,
                 mu=config.mu,
                 ema_decay=config.ema_decay,
                 weight_decay=config.weight_decay,
                 epoch=config.epoch,
                 num_it_epoch=config.num_it_epoch,
                 num_it_total=config.num_it_total,
                 eval_epoch=config.eval_epoch,
                 eval_it=config.eval_it,
                 device=config.device,
                 train_dataset=config.train_dataset,
                 labeled_dataset=config.labeled_dataset,
                 unlabeled_dataset=config.unlabeled_dataset,
                 valid_dataset=config.valid_dataset,
                 test_dataset=config.test_dataset,
                 train_dataloader=config.train_dataloader,
                 labeled_dataloader=config.labeled_dataloader,
                 unlabeled_dataloader=config.unlabeled_dataloader,
                 valid_dataloader=config.valid_dataloader,
                 test_dataloader=config.test_dataloader,
                 train_sampler=config.train_sampler,
                 train_batch_sampler=config.train_batch_sampler,
                 valid_sampler=config.valid_sampler,
                 valid_batch_sampler=config.valid_batch_sampler,
                 test_sampler=config.test_sampler,
                 test_batch_sampler=config.test_batch_sampler,
                 labeled_sampler=config.labeled_sampler,
                 unlabeled_sampler=config.unlabeled_sampler,
                 labeled_batch_sampler=config.labeled_batch_sampler,
                 unlabeled_batch_sampler=config.unlabeled_batch_sampler,
                 augmentation=config.augmentation,
                 network=config.network,
                 optimizer=config.optimizer,
                 scheduler=config.scheduler,
                 evaluation=config.evaluation,
                 parallel=config.parallel,
                 file=config.file,
                 verbose=config.verbose
                 ):
        DeepModelMixin.__init__(self,train_dataset=train_dataset,
                                    valid_dataset=valid_dataset,
                                    test_dataset=test_dataset,
                                    train_dataloader=train_dataloader,
                                    valid_dataloader=valid_dataloader,
                                    test_dataloader=test_dataloader,
                                    augmentation=augmentation,
                                    network=network,
                                    train_sampler=train_sampler,
                                    train_batch_sampler=train_batch_sampler,
                                    valid_sampler=valid_sampler,
                                    valid_batch_sampler=valid_batch_sampler,
                                    test_sampler=test_sampler,
                                    test_batch_sampler=test_batch_sampler,
                                    labeled_dataset=labeled_dataset,
                                    unlabeled_dataset=unlabeled_dataset,
                                    labeled_dataloader=labeled_dataloader,
                                    unlabeled_dataloader=unlabeled_dataloader,
                                    labeled_sampler=labeled_sampler,
                                    unlabeled_sampler=unlabeled_sampler,
                                    labeled_batch_sampler=labeled_batch_sampler,
                                    unlabeled_batch_sampler=unlabeled_batch_sampler,
                                    epoch=epoch,
                                    num_it_epoch=num_it_epoch,
                                    num_it_total=num_it_total,
                                    eval_epoch=eval_epoch,
                                    eval_it=eval_it,
                                    mu=mu,
                                    weight_decay=weight_decay,
                                    ema_decay=ema_decay,
                                    optimizer=optimizer,
                                    scheduler=scheduler,
                                    device=device,
                                    evaluation=evaluation,
                                    parallel=parallel,
                                    file=file,
                                    verbose=verbose
                                    )
        self.dim_in=dim_in
        self.ema_decay=ema_decay
        self.lambda_u=lambda_u
        self.weight_decay=weight_decay
        self.warmup=warmup
        self.alpha=alpha
        self.bn_controller=Bn_Controller()
        self._estimator_type = RegressorMixin._estimator_type

    def init_transform(self):
        self._train_dataset.add_transform(self.weakly_augmentation,dim=1,x=0,y=0)
        self._train_dataset.add_unlabeled_transform(self.weakly_augmentation,dim=1,x=0,y=0)

    def start_fit(self):
        self.dim_in=self.dim_in if self.dim_in is not None else \
            self._train_dataset.labeled_dataset.X.shape[-1]
        if self.network is None:
            self.network=MLP_Reg(hidden_dim=[100, 50, 10], activations=[nn.ReLU(), nn.ReLU(), nn.ReLU()], dim_in=self.dim_in)
            self._network=copy.deepcopy(self.network)
            self.init_model()
            self.init_ema()
            self.init_optimizer()
            self.init_scheduler()
        self._network.zero_grad()
        self._network.train()

    def train(self,lb_X,lb_y,ulb_X,lb_idx=None,ulb_idx=None,*args,**kwargs):
        lb_x = lb_X[0] if isinstance(lb_X, (tuple, list)) else lb_X
        lb_y = lb_y[0] if isinstance(lb_y, (tuple, list)) else lb_y
        ulb_x_1 = ulb_X[0] if isinstance(ulb_X, (tuple, list)) else ulb_X
        logits_x_lb = self._network(lb_x)
        index = torch.randperm(ulb_x_1.size(0)).to(self.device)
        ulb_x_2=ulb_x_1[index]
        mixup=Mixup(self.alpha)

        if self.ema is not None:
            self.ema.apply_shadow()
        with torch.no_grad():
            logits_x_ulb_1 = self._network(ulb_x_1)
        if self.ema is not None:
            self.ema.restore()
        logits_x_ulb_2=logits_x_ulb_1[index]
        mixed_x= mixup.fit(ulb_x_1).transform(ulb_x_2)
        lam=mixup.lam
        self.bn_controller.freeze_bn(self._network)
        logits_x_ulb_mix = self._network(mixed_x)
        self.bn_controller.unfreeze_bn(self._network)
        return logits_x_lb,lb_y,logits_x_ulb_1,logits_x_ulb_2,logits_x_ulb_mix,lam

    def get_loss(self,train_result,*args,**kwargs):
        logits_x_lb,lb_y,logits_x_ulb_1,logits_x_ulb_2,logits_x_ulb_mix,lam=train_result
        sup_loss = MSE(reduction='mean')(logits_x_lb, lb_y)  # CE_loss for labeled data
        _warmup = float(np.clip((self.it_total) / (self.warmup * self.num_it_total), 0., 1.))
        unsup_loss = _warmup * (lam*MSE(reduction='mean')(logits_x_ulb_mix,logits_x_ulb_1)+
                                (1.0 - lam)*MSE(reduction='mean')(logits_x_ulb_mix,logits_x_ulb_2))

        loss =Semi_supervised_loss(self.lambda_u)(sup_loss ,   unsup_loss)
        return loss

    def predict(self,X=None,valid=None):
        return DeepModelMixin.predict(self,X=X,valid=valid)


