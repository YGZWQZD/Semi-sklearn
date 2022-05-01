import torch
import torch.nn as nn
class MLP_Reg(torch.nn.Module):
    # define model elements
    def __init__(self, input_dim = 28 ** 2,hidden_dim=[10],
                 activations=[nn.ReLU()]):
        super(MLP_Reg, self).__init__()
        # input to first hidden layer
        self.num_hidden=len(hidden_dim)
        self.activations=activations
        self.layers=torch.nn.ModuleList()
        for _ in range(self.num_hidden):
            if _==0:
                in_dim=input_dim
            else:
                in_dim=hidden_dim[_-1]
            out_dim=hidden_dim[_]
            fc=nn.Linear(in_dim, out_dim, bias=False)
            nn.init.xavier_uniform_(fc.weight)
            self.layers.append(fc)
        self.final=nn.Linear(hidden_dim[self.num_hidden-1], 1, bias=False)

    def forward(self, X):
        for _ in range(self.num_hidden):
            X = self.activations[_](self.layers[_](X))
        if len(self.activations)==self.num_hidden+1:
            X = self.activations[self.num_hidden](self.final(X))
        else:
            X=self.final(X)
        X=torch.flatten(X)
        return X