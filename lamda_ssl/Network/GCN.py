import torch
from torch_geometric.nn import  GCNConv
import torch.nn.functional as F
class GCN(torch.nn.Module):
    def __init__(self,num_features,num_classes,normalize=False):
        super().__init__()
        self.conv1 = GCNConv(num_features, 16, cached=True,
                             normalize=normalize)
        self.conv2 = GCNConv(16, num_classes, cached=True,
                             normalize=normalize)

    def forward(self,data):
        x, edge_index, edge_weight = data.x, data.edge_index, data.edge_attr
        x = F.relu(self.conv1(x, edge_index, edge_weight))
        x = F.dropout(x, training=self.training)
        x = self.conv2(x, edge_index, edge_weight)
        return x