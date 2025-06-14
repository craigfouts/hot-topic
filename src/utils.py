"""
Craig Fouts (craig.fouts@uu.igp.se)
"""

import matplotlib.pyplot as plt
import numpy as np
import os
import pyro
import random
import torch
import torch.nn.functional as F
from matplotlib import cm, colormaps, colors
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import confusion_matrix

def set_seed(seed=9):
    """Sets a fixed environment-wide random state.
    
    Parameters
    ----------
    seed : int, default=9
        Random state seed.

    Returns
    -------
    None
    """

    if seed is not None:
        os.environ['PYTHONHASHSEED'] = str(seed)
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = True
        pyro.set_rng_seed(seed)

def itemize(length, *items):
    """Converts each item to a collection of the specified length, truncating if 
    the item is a tuple or list of longer length and repeating the last value if 
    the item is a tuple or list of shorter length.
    
    Parameters
    ----------
    length : int
        Length of item list.
    items : any
        Items to convert to lists.

    Yields
    ------
    tuple | list
        Collection of items.
    """

    for item in items:
        if isinstance(item, (tuple, list)):
            yield item[:length] + item[-1:]*(length - len(item))
        else:
            yield [item,]*length

def map_labels(targets, predictions):
    """Maps predicted cluster labels to the given target labels using linear sum
    assignment.
    
    Parameters
    ----------
    targets : ndarray
        Target cluster labels.
    predictions : ndarray
        Predicted cluster labels.

    Returns
    -------
    ndarray
        Optimal permutation of predicted cluster labels.
    """

    scores = confusion_matrix(predictions, targets)
    row, col = linear_sum_assignment(scores, maximize=True)
    labels = np.zeros_like(predictions)

    for i in row:
        labels[predictions == i] = col[i]
    
    return labels

def relabel(labels):
    if type(labels) == torch.Tensor:
        topics, inverse = labels.unique(return_inverse=True)
    else:
        topics, inverse = np.unique(labels, return_inverse=True)

    _, mapping = linear_sum_assignment(F.one_hot(inverse), maximize=True)
    labels = (labels[None, :] == topics[mapping][:, None]).int().argmax(0)

    return labels

def shuffle(data, labels=None, sort=False):
    mask = torch.randperm(data.shape[-2])
    data = data[:, mask] if len(data.shape) > 2 else data[mask]

    if labels is not None:
        labels = relabel(labels[mask]) if sort else labels[mask]

        return data, labels
    
    return data

def format_ax(ax, title=None, aspect='equal', show_ax=True):
    """Formats the given Matplotlib axis in place by setting the title, aspect 
    scaling, and axes visibility.
    
    Parameters
    ----------
    ax : axis
        Matplotlib axis.
    title : str, default=None
       Axis title.
    aspect : str, default='equal'
        Aspect scaling.
    show_ax : bool, default=True
        Whether to make axes visible.

    Returns
    -------
    axis
        Formated Matplotlib axis.
    """

    if title is not None:
        ax.set_title(title)

    ax.set_aspect(aspect)

    if not show_ax:
        ax.axis('off')

    return ax

def make_figure(n_sections=1, figsize=5, colormap=None, labels=None):
    fig, ax = plt.subplots(1, n_sections, figsize=figsize)
    axes = (ax,) if n_sections == 1 else ax

    if colormap is not None:
        cmap = colormaps.get_cmap(colormap)

        if labels is not None:
            norm = colors.Normalize(labels.min(), labels.max())

            return fig, axes, cmap, norm
        
        return fig, axes, cmap

    return fig, axes

def show_dataset(data, labels, sectioned=False, size=15, figsize=5, title=None, colormap='Set3', show_ax=False, show_colorbar=False, path=None):
    """Displays scatter plot(s) of sample points colored by label and separated
    by section.

    Parameters
    ----------
    data : ndarray
        Sample dataset.
    labels : ndarray
        Sample labels.
    sectioned : bool, default=False
        Whether the dataset includes a section column.
    size : int, default=15
        Sample point size.
    figsize : int | tuple | list, default=10
        Scatter plot size.
    title : str | tuple | list, default=None
        Scatter plot title(s).
    colormap : str | dict, default='Set3'
        Label color dictionary.
    show_ax : bool, default=False
        Whether to make axes visible.
    show_colorbar : bool, default=False
        Whether to show a colorbar.
    path : str, default=None
        Scatter plot save path.

    Returns
    -------
    None
    """

    if not sectioned:
        data = np.hstack((np.zeros((data.shape[0], 1)), data))

    sections = np.unique(data[:, 0])
    n_sections = sections.shape[0]
    title, size = itemize(n_sections, title, size)
    figsize, = itemize(2, figsize*n_sections)
    fig, axes, cmap, norm = make_figure(n_sections, figsize, colormap, labels)

    for i, a, t, s in zip(sections, axes, title, size):
        mask = data[:, 0] == i 
        a.scatter(*data[mask, 1:3].T, s=s, c=cmap(norm(labels[mask])))
        format_ax(a, t, aspect='equal', show_ax=show_ax)

    if show_colorbar:
        fig.colorbar(cm.ScalarMappable(cmap=cmap, norm=norm))

    if path is not None:
        fig.savefig(path, bbox_inches='tight', transparent=True)
        