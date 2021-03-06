"""
Authors: Kwanho Kim, Saideep Gona, Jinke Liu

Contains code for actually counting the number of spines present in a
given image given the scanned output map from the scanning step
"""

import os, argparse
from pathlib import Path
import numpy as np
import torch
from cnn import ConvNet
import torch.nn as nn
import torch.nn.functional as F
import torch.optim  as optim
import random
import torchvision
import torchvision.transforms as transforms
from PIL import Image
import re
import pickle
import matplotlib.pyplot as plt

from sklearn.cluster import DBSCAN

class DBScan_Counter():

    def __init__(self, data_path, output_dir, clust_scalings, distance_metrics, epsilon_iter, min_samp_iter):
        """
        :param data_path: Path to the full scanned image data dictionary
        :param output_dir: Output directory for the scanned outputs
        :param clust_scalings: Hyperparameter iterator over scaling factor for probability element of pixel clustering vector
        :param distance_metric: Hyperparameter iterator of distance metric function objects used in DBSCAN
        :param epsilon_iter: Hyperparameter iterator over epsilon hyperparam in DBSCAN
        :param min_samp_iter: Hyperparameter iterator over minimum samples in DBSCAN
        """
        self.data = pickle.load(open(data_path, "rb"))
        # print(self.data)
        self.clust_scalings = clust_scalings
        self.distance_metrics = distance_metrics

        self.epsilon_iter = epsilon_iter
        self.min_samp_iter = min_samp_iter

    def convert_to_clusterables(self, scaling):
        """
        Creates clusterable objects from images and stores them in the data dict
        """

        def convert_single(image):
            imshape = image.shape
            clusterable = []

            c_ind = 0
            # plt.imshow(image)
            # plt.show()
            for x in range(imshape[0]):
                for y in range(imshape[1]):
                    # print(image[x,y], x, y)
                    if image[x,y] < 0.3:
                        # clusterable.append(1000 * np.ones((1,3)))
                        continue
                    else:
                        cur_vec = np.zeros((1,3))
                        cur_vec[0,0] = image[x,y] * scaling
                        cur_vec[0,1] = x        
                        cur_vec[0,2] = y

                        clusterable.append(cur_vec[:])

                    c_ind += 1
            if len(clusterable) == 0:
                return np.array([[0,0,0]])
            stacked = np.stack(clusterable, axis=0)
            correct_stacked = stacked.reshape((stacked.shape[0],stacked.shape[2]))
            return correct_stacked


        for x in range(len(self.data)):
            self.data[x]["clusterable"] = convert_single(self.data[x]["scanned output"])


    def full_grid_search(self):
        """
        Runs a full grid search over the hyper-parameter space for a given accuracy metric
        """

        grid_shape = (len(self.clust_scalings), len(self.distance_metrics), len(self.epsilon_iter), len(self.min_samp_iter), len(self.data))
        full_grid_array = np.zeros((grid_shape))
        print("Grid Shape", grid_shape)
        for w in range(grid_shape[0]):
            self.convert_to_clusterables(self.clust_scalings[w])
            for x in range(grid_shape[1]):
                for y in range(grid_shape[2]):
                    for z in range(grid_shape[3]):
                        for i in range(0,grid_shape[4], 100):
                            print([w,x,y,z,i])
                            image_dict = self.data[i]
                            count, masses = self.count_single_image(image_dict["clusterable"], 
                                                                    self.distance_metrics[x],
                                                                    self.epsilon_iter[y], 
                                                                    self.min_samp_iter[z]
                                                                    )
                            accuracy = self.compute_accuracy(count, image_dict)
                            full_grid_array[w,x,y,z,i] = accuracy
        full_grid_array = full_grid_array[:,:,:,:,::100]
        average_accs_full = np.mean(full_grid_array, axis=4)

        min_coords = np.unravel_index(np.argmin(average_accs_full), average_accs_full.shape)
        min_acc = np.min(average_accs_full)

        min_hyperparams = [
                            self.clust_scalings[min_coords[0]],
                            self.distance_metrics[min_coords[1]],
                            self.epsilon_iter[min_coords[2]],
                            self.min_samp_iter[min_coords[3]]
                        ]

        print("Averages Shape: ", average_accs_full.shape)
        print("Minimum Val: ", np.min(average_accs_full))
        print("Min Hyperparams: ", min_hyperparams)

    def count_single_image(self, clusterable, metric, eps, min_samples):

        print("Computing Single Clustering for: " + str(eps) + " , " + str(min_samples))
        print(clusterable.shape)
        scanned_output = DBSCAN(eps=eps, min_samples=min_samples, metric=metric).fit(clusterable)
        clus_labels = scanned_output.labels_
        count = len(set(clus_labels)) - (1 if -1 in clus_labels else 0)

        masses = []
        
        return count, masses
        
    def compute_accuracy(self, count, image_dict):

        raw_dist = abs(image_dict["count"]- count)
        print("count: " + str(count))
        print("true count: " + str(image_dict["count"]))
        print("error: ", str(raw_dist))
        return raw_dist


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Processing of scanned output maps into actual dendritic spine counts")
    parser.add_argument("scans_path", help="Output path of scanned image maps")
    parser.add_argument("output_dir", help="Output directory for counting output")
    args = parser.parse_args()

    clust_scaling_iter = [2*x for x in range(1,10)]
    distance_metric_iter = ["euclidean", "manhattan"]
    eps_iter = [x for x in range(1,15)]
    min_samp_iter = [10*x for x in range(1, 20)]

    counter = DBScan_Counter(args.scans_path, args.output_dir, clust_scaling_iter, distance_metric_iter, eps_iter, min_samp_iter)
    counter.full_grid_search()

    # python scanner.py 40 C:\Users\Saideep\Documents\Github_Repos\MSCB_Sem1\Deep_Learning\Project\Labeled_Spines_Tavita\ C:\Users\Saideep\Documents\Github_Repos\MSCB_Sem1\Deep_Learning\Project\counting_spines\src\training_sessions\2019-04-1515_00_29\weights.pt C:\Users\Saideep\Documents\Github_Repos\MSCB_Sem1\Deep_Learning\Project\counting_spines\src\training_sessions\2019-04-1515_00_29\
    # Create scanner object
