import numpy as np


def extend_dataset_with_window_length(X, Y, window_length=5):
    new_x = []
    for i in range(len(X) - window_length+1):
        lst = []
        for j in range(i, i+window_length):
            lst.extend(X[j])
        new_x.append(lst)
    return np.array(new_x), Y[window_length-1:]
