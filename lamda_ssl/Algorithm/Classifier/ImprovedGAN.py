import copy
import torch.nn.functional as F
from lamda_ssl.Base.InductiveEstimator import InductiveEstimator
from lamda_ssl.Base.DeepModelMixin import DeepModelMixin
from lamda_ssl.Opitimizer.BaseOptimizer import BaseOptimizer
import lamda_ssl.Network.ImprovedGAN as ImGAN
from sklearn.base import ClassifierMixin
import torch
from torch.autograd import Variable
from lamda_ssl.utils import to_device
from lamda_ssl.Scheduler.BaseScheduler import BaseScheduler
from lamda_ssl.utils import EMA
import lamda_ssl.Config.ImprovedGAN as config
from lamda_ssl.utils import class_status

class ImprovedGAN(InductiveEstimator,DeepModelMixin,ClassifierMixin):
    def __init__(self,
                 dim_in=config.dim_in,
                 num_classes=config.num_classes,
                 num_labeled=config.num_labeled,
                 dim_z=config.dim_z,
                 hidden_G=config.hidden_G,
                 hidden_D=config.hidden_D,
                 noise_level=config.noise_level,
                 activations_G=config.activations_G,
                 activations_D=config.activations_D,
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
                 epoch=config.epoch,
                 network=config.network,
                 num_it_epoch=config.num_it_epoch,
                 num_it_total=config.num_it_total,
                 eval_epoch=config.eval_epoch,
                 eval_it=config.eval_it,
                 mu=config.mu,
                 optimizer=config.optimizer,
                 weight_decay=config.weight_decay,
                 lambda_u=config.lambda_u,
                 ema_decay=config.ema_decay,
                 scheduler=config.scheduler,
                 device=config.device,
                 evaluation=config.evaluation,
                 train_sampler=config.train_sampler,
                 labeled_sampler=config.labeled_sampler,
                 unlabeled_sampler=config.unlabeled_sampler,
                 train_batch_sampler=config.train_batch_sampler,
                 labeled_batch_sampler=config.labeled_batch_sampler,
                 unlabeled_batch_sampler=config.unlabeled_batch_sampler,
                 valid_sampler=config.valid_sampler,
                 valid_batch_sampler=config.valid_batch_sampler,
                 test_sampler=config.test_sampler,
                 test_batch_sampler=config.test_batch_sampler,
                 parallel=config.parallel,
                 file=config.file,
                 verbose=config.verbose):
        DeepModelMixin.__init__(self, train_dataset=train_dataset,
                                    labeled_dataset=labeled_dataset,
                                    unlabeled_dataset=unlabeled_dataset,
                                    valid_dataset=valid_dataset,
                                    test_dataset=test_dataset,
                                    train_dataloader=train_dataloader,
                                    labeled_dataloader=labeled_dataloader,
                                    unlabeled_dataloader=unlabeled_dataloader,
                                    valid_dataloader=valid_dataloader,
                                    test_dataloader=test_dataloader,
                                    network=network,
                                    train_sampler=train_sampler,
                                    labeled_sampler=labeled_sampler,
                                    unlabeled_sampler=unlabeled_sampler,
                                    train_batch_sampler=train_batch_sampler,
                                    labeled_batch_sampler=labeled_batch_sampler,
                                    unlabeled_batch_sampler=unlabeled_batch_sampler,
                                    valid_sampler=valid_sampler,
                                    valid_batch_sampler=valid_batch_sampler,
                                    test_sampler=test_sampler,
                                    test_batch_sampler=test_batch_sampler,
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
        self.hidden_G = hidden_G
        self.hidden_D = hidden_D
        self.noise_level = noise_level
        self.activations_G = activations_G
        self.activations_D = activations_D
        self.dim_z=dim_z
        self.dim_in=dim_in
        self.num_classes=num_classes
        self.lambda_u=lambda_u
        self.num_labeled=num_labeled
        self._estimator_type = ClassifierMixin._estimator_type

    def start_fit(self):
        self.num_classes = self.num_classes if self.num_classes is not None else \
            class_status(self._train_dataset.labeled_dataset.y).num_classes
        self.num_labeled = self.num_labeled if self.num_labeled is not None else \
            self._train_dataset.labeled_dataset.X.shape[0]
        self.dim_in=self.dim_in if self.dim_in is not None else \
            self._train_dataset.labeled_dataset.X.shape[1:]
        if self.network is None:
            self.network=ImGAN.ImprovedGAN(dim_in = self.dim_in, hidden_G=self.hidden_G,
                                       hidden_D=self.hidden_D,activations_D=self.activations_D,
                                       activations_G=self.activations_G,
                                       noise_level=self.noise_level,
                                       dim_out = self.num_classes,dim_z=self.dim_z,device=self.device)
            self._network=copy.deepcopy(self.network)
            self.init_model()
            self.init_ema()
            self.init_optimizer()
            self.init_scheduler()
        self._network.zero_grad()
        self._network.train()

    def train_batch_loop(self,valid_X=None,valid_y=None):
        for (lb_idx, lb_X, lb_y), (ulb_idx, ulb_X, _) in zip(self._labeled_dataloader, self._unlabeled_dataloader):
            if self.it_epoch >= self.num_it_epoch or self.it_total >= self.num_it_total:
                break

            self.start_batch_train()

            lb_idx = to_device(lb_idx,self.device)

            lb_X = to_device(lb_X,self.device)
            lb_y = to_device(lb_y,self.device)
            ulb_idx = to_device(ulb_idx,self.device)
            ulb_X  = to_device(ulb_X,self.device)

            lb_X = lb_X[0] if isinstance(lb_X, (list, tuple)) else lb_X
            lb_y = lb_y[0] if isinstance(lb_y, (list, tuple)) else lb_y
            ulb_X = ulb_X[0] if isinstance(ulb_X, (list, tuple)) else ulb_X

            num_unlabeled = ulb_X.shape[0]
            # lb_X=lb_X*1/255.
            # ulb_X = ulb_X * 1 / 255.
            ulb_X_1, ulb_X_2 = ulb_X[:num_unlabeled // 2], ulb_X[num_unlabeled // 2:]

            train_D_result = self.train_D(lb_X, lb_y, ulb_X_1)

            self.end_batch_train_D(train_D_result)

            train_G_result = self.train_G(ulb_X_2)

            self.end_batch_train_G(train_G_result)
            # self.end_batch_train(train_result)

            self.it_total += 1
            self.it_epoch += 1
            if self.verbose:
                print(self.it_total,file=self.file)

            if valid_X is not None and self.eval_it is not None and self.it_total % self.eval_it == 0:
                self.evaluate(X=valid_X, y=valid_y,valid=True)

    def init_optimizer(self):
        if isinstance(self._optimizer,(list,tuple)):
            self._optimizerG=self._optimizer[0]
            self._optimizerD = self._optimizer[1]
        elif isinstance(self._optimizer,dict):
            self._optimizerG = self._optimizer['Generator'] if 'Generator' in self._optimizer.keys() \
                else self._optimizer['Generation']
            self._optimizerD = self._optimizer['Discriminator'] if 'Discriminator' in self._optimizer.keys() \
                else self._optimizer['Discrimination']
        else:
            self._optimizerG=self._optimizer
            self._optimizerD=copy.deepcopy(self._optimizer)

        if isinstance(self._optimizerG,BaseOptimizer):
            no_decay = ['bias', 'bn']
            grouped_parameters = [
                {'params': [p for n, p in self._network.G.named_parameters() if not any(
                    nd in n for nd in no_decay)], 'weight_decay': self.weight_decay},
                {'params': [p for n, p in self._network.G.named_parameters() if any(
                    nd in n for nd in no_decay)], 'weight_decay': 0.0}
            ]
            self._optimizerG=self._optimizerG.init_optimizer(params=grouped_parameters)

        if isinstance(self._optimizerD,BaseOptimizer):
            no_decay = ['bias', 'bn']
            grouped_parameters = [
                {'params': [p for n, p in self._network.D.named_parameters() if not any(
                    nd in n for nd in no_decay)], 'weight_decay': self.weight_decay},
                {'params': [p for n, p in self._network.D.named_parameters() if any(
                    nd in n for nd in no_decay)], 'weight_decay': 0.0}
            ]
            self._optimizerD=self._optimizerD.init_optimizer(params=grouped_parameters)


    def init_scheduler(self):
        if isinstance(self._scheduler,(list,tuple)):
            self._schedulerG=self._scheduler[0]
            self._schedulerD = self._scheduler[1]
        elif isinstance(self._scheduler,dict):
            self._schedulerG = self._scheduler['Generator'] if 'Generator' in self._scheduler.keys() \
                else self._scheduler['Generation']
            self._schedulerD = self._scheduler['Discriminator'] if 'Discriminator' in self._scheduler.keys() \
                else self._scheduler['Discrimination']
        else:
            self._schedulerG=self._scheduler
            self._schedulerD=copy.deepcopy(self._scheduler)

        if isinstance(self._schedulerG,BaseScheduler):
            self._schedulerG=self._schedulerG.init_scheduler(optimizer=self._optimizerG)
        if isinstance(self._schedulerD,BaseScheduler):
            self._schedulerD=self._schedulerD.init_scheduler(optimizer=self._optimizerD)

    def init_ema(self):
        if self.ema_decay is not None:
            if isinstance(self.ema_decay, (list, tuple)):
                self.ema_decayG = self.ema_decay[0]
                self.ema_decayD = self.ema_decay[1]
            elif isinstance(self.ema_decay, dict):
                self.ema_decayG = self.ema_decay['Generator'] if 'Generator' in self.ema_decay.keys() \
                    else self.ema_decay['Generation']
                self.ema_decayD = self.ema_decay['Discriminator'] if 'Discriminator' in self.ema_decay.keys() \
                    else self.ema_decay['Discrimination']
            else:
                self.ema_decayG = self.ema_decay
                self.ema_decayD = copy.deepcopy(self.ema_decay)
            self.emaG=EMA(model=self._network.G,decay=self.ema_decayG)
            self.emaG.register()
            self.emaD=EMA(model=self._network.D,decay=self.ema_decayD)
            self.emaD.register()
        else:
            self.emaG = None
            self.emaD = None

    def get_loss_D(self,train_result_D):
        output_label, lb_y,output_unlabel, output_fake=train_result_D
        logz_label, logz_unlabel, logz_fake = self.log_sum_exp(output_label), \
                                              self.log_sum_exp(output_unlabel), \
                                              self.log_sum_exp(output_fake) # log ∑e^x_i
        prob_label = torch.gather(output_label, 1, lb_y.unsqueeze(1)) # log e^x_label = x_label
        loss_supervised = -torch.mean(prob_label) + torch.mean(logz_label)
        loss_unsupervised = 0.5 * (-torch.mean(logz_unlabel) + torch.mean(F.softplus(logz_unlabel))  + # real_data: log Z/(1+Z)
                            torch.mean(F.softplus(logz_fake)))
        loss=loss_supervised+self.lambda_u*loss_unsupervised
        return loss

    def get_loss_G(self,train_result_G):
        mom_fake, mom_unlabel=train_result_G
        loss_fm = torch.mean((mom_fake - mom_unlabel) ** 2)
        loss =loss_fm
        return loss

    def end_batch_train_D(self,train_result_D):
        loss = self.get_loss_D(train_result_D)
        self.optimize_D(loss)

    def end_batch_train_G(self,train_result_G):
        loss = self.get_loss_G(train_result_G)
        self.optimize_G(loss)

    def optimize_D(self,loss):
        self._optimizerD.zero_grad()
        loss.backward()
        self._optimizerD.step()
        if self._schedulerD is not None:
            self._schedulerD.step()
        if self.emaD is not None:
            self.emaD.update()


    def optimize_G(self,loss):
        self._optimizerG.zero_grad()
        self._optimizerD.zero_grad()
        loss.backward()
        self._optimizerG.step()
        if self._schedulerG is not None:
            self._schedulerG.step()
        if self.emaG is not None:
            self.emaG.update()

    def log_sum_exp(self,x, axis=1):
        m = torch.max(x, dim=1)[0]
        return m + torch.log(torch.sum(torch.exp(x - m.unsqueeze(1)), dim=axis))

    def train_D(self,X,y,unlabeled_X):
        X=X.view(X.shape[0],-1)
        unlabeled_X=unlabeled_X.view(unlabeled_X.shape[0],-1)
        output_label=self._network.D(X)
        output_unlabel=self._network.D(unlabeled_X)
        fake_X=self._network.G(unlabeled_X.size()[0]).view(unlabeled_X.size()).detach()
        output_fake =self._network.D(fake_X)
        return output_label, y, output_unlabel, output_fake

    def train_G(self, unlabeled_X):
        unlabeled_X = unlabeled_X.view(unlabeled_X.shape[0], -1)
        fake = self._network.G(unlabeled_X.size()[0]).view(unlabeled_X.size())
        output_fake = self._network.D(fake)
        mom_fake=self._network.D.feature

        output_unlabeled = self._network.D(Variable(unlabeled_X))
        mom_unlabeled=self._network.D.feature

        mom_fake = torch.mean(mom_fake, dim = 0)
        mom_unlabel = torch.mean(mom_unlabeled, dim = 0)

        # self.Goptim.zero_grad()
        # self.Doptim.zero_grad()
        # loss.backward()
        # self.Goptim.step()
        return mom_fake,mom_unlabel

    # def optimize(self,*args,**kwargs):
    #     self._optimizer.step()
    #     self._network.zero_grad()

    @torch.no_grad()
    def estimate(self, X, idx=None, *args, **kwargs):
        X=X.view(X.shape[0],-1)
        # X=X*1/255.
        outputs = self._network(X)
        return outputs

    def predict(self,X=None,valid=None):
        return DeepModelMixin.predict(self,X=X,valid=valid)

    def generate(self,num,z=None):

        z = Variable(torch.randn(num, self.dim_z).to(self.device)) if z is None else z
        z=self._network.G(num,z)
        # print(z,file=self.file)
        z=z.view(tuple([z.shape[0]])+tuple(self.dim_in))
        return z