import urllib2
import os
import struct
import sklearn.datasets.mldata as fetcher
import numpy as np
import logging
from utils.config import load_config

logger = logging.getLogger(__name__)
config = load_config("global_config.yaml")

PROJECT_DATA_DIR = config['general']['data_dir']
np.random.seed(config['general']['seed'])


def load_mnist(local_data_path=None, one_hot=True, binarised=True):
    """
    Load the MNIST dataset from local file or download it if not available.
    
    Args:
        local_data_path: path to the MNIST dataset. Assumes unpacked files and original filenames. 
        one_hot: bool whether tha data targets should be converted to one hot encoded labels
        binarised: bool, whether the images should be ceiled/floored to 1 and 0 respectively.

    Returns:
        A dict with `data` and `target` keys with the MNIST data converted to [0, 1] floats. 
    """

    def convert_to_one_hot(raw_target):
        n_uniques = len(np.unique(raw_target))
        one_hot_target = np.zeros((raw_target.shape[0], n_uniques))
        one_hot_target[np.arange(raw_target.shape[0]), raw_target.astype(np.int)] = 1
        return one_hot_target

    def binarise(raw_data, mode='sampling', **kwargs):
        if mode == 'sampling':
            return np.random.binomial(1, p=raw_data).astype(np.int32)
        elif mode == 'threshold':
            threshold = kwargs.get('threshold', 0.3)
            return (raw_data > threshold).astype(np.int32)

    if local_data_path is None:
        logger.info("Path to locally stored data not provided. Proceeding with downloading the MNIST dataset.")
        mnist_path = os.path.join(PROJECT_DATA_DIR, "MNIST")
        try:
            mnist = fetcher.fetch_mldata("MNIST Original", data_home=mnist_path)
            if one_hot:
                mnist.target = convert_to_one_hot(mnist.target)
            if binarised:
                mnist.data = binarise(mnist.data, mode='threshold', threshold=0.2)
            mnist = {'data': mnist.data, 'target': mnist.target}
        except urllib2.HTTPError:
            logger.warning("Fetching data from mldata.org failed. The server is probably unreachable. "
                           "Proceeding with fetching from Tensorflow.examples.tutorials.mnist.")
            from tensorflow.examples.tutorials.mnist import input_data
            mnist = input_data.read_data_sets(mnist_path, one_hot=one_hot)
            mnist_data = np.concatenate((mnist.train.images, mnist.test.images, mnist.validation.images))
            mnist_labels = np.concatenate((mnist.train.labels, mnist.test.labels, mnist.validation.labels))
            if binarised:
                mnist_data = binarise(mnist_data, mode='threshold', threshold=0.2)
            mnist = {'data': mnist_data,
                     'target': mnist_labels}
    else:
        logger.info("Loading MNIST dataset from {}".format(local_data_path))
        if os.path.exists(local_data_path):
            mnist_imgs, mnist_labels = _load_mnist_from_file(local_data_path)
            if one_hot:
                mnist_labels = convert_to_one_hot(mnist_labels)
            if binarised:
                mnist_imgs = binarise(mnist_imgs, mode='threshold', threshold=0.2)
            mnist = {'data': mnist_imgs, 'target': mnist_labels}
        else:
            logger.error("Path to locally stored MNIST does not exist.")
            raise ValueError

    return mnist


def _load_mnist_from_file(data_dir=None):
    """
    Load the binary files from disk. 
    
    Args:
        data_dir: path to folder containing the MNIST dataset blobs. 

    Returns:
        A numpy array with the images and a numpy array with the corresponding labels. 
    """
    # The files are assumed to have these names and should be found in 'path'
    image_files = ('train-images-idx3-ubyte', 't10k-images-idx3-ubyte')
    label_files = ('train-labels-idx1-ubyte', 't10k-labels-idx1-ubyte')

    def read_labels(fname):
        with open(os.path.join(data_dir, fname), 'rb') as flbl:
            # remove header
            magic, num = struct.unpack(">II", flbl.read(8))
            labels = np.fromfile(flbl, dtype=np.int8)
        return labels

    def read_images(fname):
        with open(os.path.join(data_dir, fname), 'rb') as fimg:
            # remove header
            magic, num, rows, cols = struct.unpack(">IIII", fimg.read(16))
            images = np.fromfile(fimg, dtype=np.uint8).reshape(num, -1)
        return images

    images = np.concatenate([read_images(fname) for fname in image_files]) / 255.
    labels = np.concatenate([read_labels(fname) for fname in label_files])

    return images, labels


def load_8schools():
    """
    Load Eight Schools experiment as in "Estimation in parallel randomized experiments, Donald B. Rubin, 1981"
    
    Returns:
        A dict with keys `effect` and `stderr` with numpy arrays of shape (8,) for each of the schools 
    """
    #   school effect stderr
    # 1      A  28.39   14.9
    # 2      B   7.94   10.2
    # 3      C  -2.75   16.3
    # 4      D   6.82   11.0
    # 5      E  -0.64    9.4
    # 6      F   0.63   11.4
    # 7      G  18.01   10.4
    # 8      H  12.16   17.6
    estimated_effects = np.array([28.39, 7.74, -2.75, 6.82, -0.64, 0.63, 18.01, 12.16])
    std_errors = np.array([14.9, 10.2, 16.3, 11.0, 9.4, 11.4, 10.4, 17.6])
    return {'effect': estimated_effects, 'stderr': std_errors}


def load_npoints(n=4):
    """
    Load a generalisation of the 4 points synthetic dataset as described in the Experiments section, Generative models, 
    Synthetic example in "Adversarial Variational Bayes, L. Mescheder et al., 2017". 
    
    Args:
        Number of distinct data points (i.e. dimensionality of the (vector) space in which they reside)
        
    Returns:
        A dict with keys `data` and `target` containing the data points and a fictitious label (completely unnecessary)
    """
    return {'data': np.repeat(np.eye(n), 512, axis=0), 'target': np.repeat(np.arange(n), 512, axis=0)}
