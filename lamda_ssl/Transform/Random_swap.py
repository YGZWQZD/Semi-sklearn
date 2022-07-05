from lamda_ssl.Transform.Transformer import Transformer
import random
from lamda_ssl.Transform.Tokenizer import Tokenizer

class Random_swap(Transformer):
    def __init__(self,n=1,tokenizer=None):
        super(Random_swap, self).__init__()
        self.n=n
        self.tokenizer=tokenizer if tokenizer is not None else Tokenizer('basic_english','en')

    def swap(self,X):
        random_idx_1 = random.randint(0, len(X) - 1)
        random_idx_2 = random_idx_1
        counter = 0
        while random_idx_2 == random_idx_1:
            random_idx_2 = random.randint(0, len(X) - 1)
            counter += 1
            if counter > 3:
                return X
        X[random_idx_1], X[random_idx_2] = X[random_idx_2], X[random_idx_1]
        return X

    def transform(self,X):
        tokenized=True
        if isinstance(X, str):
            X = self.tokenizer.fit_transform(X)
            tokenized = False
        for _ in range(self.n):
            X = self.swap(X)
        if tokenized is not True:
            X=' '.join(X)
        return X