import copy

from lamda_ssl.Base.InductiveEstimator import InductiveEstimator
from lamda_ssl.Base.DeepModelMixin import DeepModelMixin
from torch.utils.data.dataset import Dataset
from torch_geometric.data.data import Data
from sklearn.base import ClassifierMixin
import lamda_ssl.Network.SDNE as SDNENET
import scipy.sparse as sparse
import torch
import lamda_ssl.Config.SDNE as config

class SDNE(InductiveEstimator,DeepModelMixin,ClassifierMixin):
    def __init__(self,
                 base_estimator=config.base_estimator,
                 alpha=config.alpha,
                 beta=config.beta,
                 gamma=config.gamma,
                 xeqs=config.xeqs,
                 num_features=config.num_features,
                 num_nodes=config.num_nodes,
                 hidden_layers=config.hidden_layers,
                 weight_decay=config.weight_decay,
                 epoch=config.epoch,
                 eval_epoch=config.eval_epoch,
                 device=config.device,
                 network=config.network,
                 optimizer=config.optimizer,
                 scheduler=config.scheduler,
                 parallel=config.parallel,
                 evaluation=config.evaluation,
                 file=config.file,
                 verbose=config.verbose
                 ):

        DeepModelMixin.__init__(self,
                                    epoch=epoch,
                                    weight_decay=weight_decay,
                                    network=network,
                                    optimizer=optimizer,
                                    scheduler=scheduler,
                                    device=device,
                                    eval_epoch=eval_epoch,
                                    evaluation=evaluation,
                                    parallel=parallel,
                                    file=file,
                                    verbose=verbose
                                    )
        self.num_nodes=num_nodes
        self.hidden_layers=hidden_layers
        self.num_features=num_features
        self.alpha=alpha
        self.beta=beta
        self.xeqs=xeqs
        self.gamma=gamma
        self.base_estimator=base_estimator
        self._estimator_type = ClassifierMixin._estimator_type

    def fit(self,X=None,y=None,unlabeled_X=None,valid_X=None,valid_y=None,
            edge_index=None,train_mask=None,labeled_mask=None,unlabeled_mask=None,valid_mask=None,test_mask=None):
        self.init_train_dataset(X,y,unlabeled_X,edge_index,train_mask,labeled_mask,unlabeled_mask,valid_mask,test_mask)
        self.init_train_dataloader()
        self.start_fit()
        self.epoch_loop(valid_X,valid_y)
        self.end_fit()
        return self

    def start_fit(self):
        self.num_features= self.data.x.shape[1] if self.num_features is None else self.num_features
        self.num_nodes=self.data.x.shape[0] if self.num_nodes is None else self.num_nodes
        if self.network is None:
            self.network=SDNENET.SDNE(dim_in=self.num_nodes,hidden_layers=self.hidden_layers) if self.xeqs else \
                SDNENET.SDNE(dim_in=self.num_features,hidden_layers=self.hidden_layers)
            self._network=copy.deepcopy(self.network)
            self.init_model()
            self.init_ema()
            self.init_optimizer()
            self.init_scheduler()
        self._network.zero_grad()
        self._network.train()

    def init_train_dataloader(self):
        pass

    def init_pred_dataloader(self, valid=False):
        pass

    def init_train_dataset(self, X=None, y=None, unlabeled_X=None,
                           edge_index=None,train_mask=None,labeled_mask=None,
                           unlabeled_mask=None,val_mask=None,test_mask=None):
        if isinstance(X,Dataset):
            X=X.data
        if not isinstance(X,Data):
            if not isinstance(X,torch.Tensor):
                X=torch.Tensor(X)
            if not isinstance(y,torch.Tensor):
                y=torch.LongTensor(y)
            if not isinstance(unlabeled_X,torch.Tensor):
                unlabeled_X=torch.Tensor(unlabeled_X)
            if not isinstance(edge_index,torch.Tensor):
                edge_index=torch.LongTensor(edge_index)
            if not isinstance(train_mask,torch.Tensor):
                train_mask=torch.BoolTensor(train_mask)
            if not isinstance(labeled_mask,torch.Tensor):
                labeled_mask=torch.BoolTensor(labeled_mask)
            if not isinstance(unlabeled_mask,torch.Tensor):
                unlabeled_mask=torch.BoolTensor(unlabeled_mask)
            if not isinstance(val_mask,torch.Tensor):
                val_mask=torch.BoolTensor(val_mask)
            if not isinstance(val_mask,torch.Tensor):
                test_mask=torch.BoolTensor(test_mask)

            if unlabeled_X is not None:
                X = torch.cat((X, unlabeled_X),dim=0)
                unlabeled_y = torch.ones(unlabeled_X.shape[0]) * -1
                y = torch.cat((y, unlabeled_y),dim=0)

            X=Data(X=X,y=y,edge_index=edge_index,train_mask=train_mask,labeled_mask=labeled_mask,
                   unlabeled_mask=unlabeled_mask,val_mask=val_mask,test_mask=test_mask)

        self.data=X.to(self.device)
        self.train_mask = self.data.train_mask.to(self.device) if hasattr(self.data, 'train_mask') else None
        self.labeled_mask = self.data.labeled_mask.to(self.device) if hasattr(self.data,'labeled_mask') else None
        self.unlabeled_mask = self.data.unlabeled_mask.to(self.device) if hasattr(self.data,'unlabeled_mask') else None
        self.valid_mask = self.data.val_mask.to(self.device) if hasattr(self.data, 'val_mask') else None
        self.test_mask = self.data.test_mask.to(self.device) if hasattr(self.data, 'test_mask') else None
        adjacency_matrix, laplace_matrix = self.create_adjacency_laplace_matrix()
        self.adjacency_matrix = torch.from_numpy(adjacency_matrix.toarray()).float().to(self.device)
        self.laplace_matrix = torch.from_numpy(laplace_matrix.toarray()).float().to(self.device)

    def estimator_fit(self):
        X=self.embedding[self.data.labeled_mask] if hasattr(self.data,'labeled_mask') and  self.data.labeled_mask is not None \
            else self.embedding[self.data.train_mask]
        y=self.data.y[self.labeled_mask] if hasattr(self.data,'labeled_mask') and  self.data.labeled_mask is not None \
            else self.data.y[self.data.train_mask]

        X=X.cpu().detach().numpy()
        y=y.cpu().detach().numpy()
        self.base_estimator.fit(X,y)

    def create_adjacency_laplace_matrix(self):
        self.edge_index=self.data.edge_index
        adjacency_matrix_data = []
        adjacency_matrix_row_index = []
        adjacency_matrix_col_index = []
        self.num_node=self.data.x.shape[0]
        for _ in range(self.edge_index.shape[1]):
            adjacency_matrix_data.append(1.0)
            adjacency_matrix_row_index.append(self.edge_index[0][_])
            adjacency_matrix_col_index.append(self.edge_index[1][_])

        adjacency_matrix = sparse.csr_matrix((adjacency_matrix_data,
                                              (adjacency_matrix_row_index, adjacency_matrix_col_index)),
                                             shape=(self.num_node, self.num_node))
        # L = D - A  有向图的度等于出度和入度之和; 无向图的领接矩阵是对称的，没有出入度之分直接为每行之和
        # 计算度数
        adjacency_matrix_ = sparse.csr_matrix((adjacency_matrix_data+adjacency_matrix_data,
                                               (adjacency_matrix_row_index+adjacency_matrix_col_index,
                                                adjacency_matrix_col_index+adjacency_matrix_row_index)),
                                              shape=(self.num_node, self.num_node))
        degree_matrix = sparse.diags(adjacency_matrix_.sum(axis=1).flatten().tolist()[0])
        laplace_matrix = degree_matrix - adjacency_matrix_
        return adjacency_matrix, laplace_matrix

    def epoch_loop(self, valid_X=None, valid_y=None):
        self.data=self.data.to(self.device)
        if valid_X is None:
            valid_X=self.data.val_mask
        for self._epoch in range(1,self.epoch+1):
            print(self._epoch,file=self.file)
            train_result = self.train(lb_X=self.data.labeled_mask)
            self.end_batch_train(train_result)
            if valid_X is not None and self.eval_epoch is not None and self._epoch % self.eval_epoch==0:
                self.estimator_fit()
                self.evaluate(X=valid_X,y=valid_y,valid=True)

    def end_fit(self):
        self.estimator_fit()

    def train(self, lb_X=None, lb_y=None, ulb_X=None, lb_idx=None, ulb_idx=None, *args, **kwargs):
        if self.xeqs:
            X=self.adjacency_matrix
        else:
            X=self.data.x
        Y,X_hat = self._network(X=X)
        self.embedding=Y
        return X,X_hat,Y

    def get_loss(self,train_result,*args,**kwargs):
        X,X_hat,Y=train_result

        if self.xeqs:
            beta_matrix = torch.ones_like(self.adjacency_matrix)

            mask = self.adjacency_matrix != 0
            beta_matrix[mask] = self.beta

            loss_2nd = torch.mean(torch.sum(torch.pow((X - X_hat) * beta_matrix, 2), dim=1))
        else:
            loss_2nd = torch.mean(torch.sum(torch.pow((X - X_hat) , 2), dim=1))
        L_reg = 0
        for param in self._network.parameters():
            L_reg += self.gamma * torch.sum(param * param)
        # loss_1st 一阶相似度损失函数 论文公式(9) alpha * 2 *tr(Y^T L Y)
        loss_1st =  self.alpha * 2 * torch.trace(torch.matmul(torch.matmul(Y.transpose(0,1), self.laplace_matrix), Y))
        return loss_1st+loss_2nd+L_reg



    def predict(self,X=None,valid=False):
        if X is not None and not isinstance(X, torch.Tensor):
            X = torch.BoolTensor(X).to(self.device)
        if valid:
            X = self.embedding[X] if X is not None else self.embedding[self.data.val_mask]
        else:
            X = self.embedding[X] if X is not None else self.embedding[self.data.test_mask]
        if isinstance(X,torch.Tensor):
            X=X.cpu().detach().numpy()
        return self.base_estimator.predict(X)

    def predict_proba(self, X=None, valid=False):
        if X is not None and not isinstance(X, torch.Tensor):
            X = torch.BoolTensor(X).to(self.device)
        if valid:
            X = self.embedding[X] if X is not None else self.embedding[self.data.val_mask]
        else:
            X = self.embedding[X] if X is not None else self.embedding[self.data.test_mask]
        if isinstance(X,torch.Tensor):
            X=X.cpu().detach().numpy()
        return self.base_estimator.predict_proba(X)

    @torch.no_grad()
    def evaluate(self, X, y=None,valid=False):
        y_pred = self.predict(X,valid=valid)
        if hasattr(self.base_estimator,'predict_proba'):
            y_score = self.predict_proba(X,valid=valid)
        else:
            y_score=None
        self.y_score=y_score
        self.y_pred=y_pred
        if y is not None:
            y=y
        elif valid:
            y = self.data.y[self.data.val_mask]
        else:
            y = self.data.y[X] if X is not None else self.data.y[self.data.test_mask]
        if self.evaluation is None:
            return None
        elif isinstance(self.evaluation, (list, tuple)):
            result = []
            for eval in self.evaluation:
                score=eval.scoring(y, self.y_pred, self.y_score)
                if self.verbose:
                    print(score, file=self.file)
                result.append(score)
            self.result = result
            return result
        elif isinstance(self.evaluation, dict):
            result = {}
            for key, val in self.evaluation.items():
                result[key] = val.scoring(y, self.y_pred, self.y_score)
                if self.verbose:
                    print(key, ' ', result[key],file=self.file)
            self.result = result
            return result
        else:
            result = self.evaluation.scoring(y, self.y_pred, self.y_score)
            if self.verbose:
                print(result, file=self.file)
            self.result=result
            return result