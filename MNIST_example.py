pip install --verbose dionysus

import dionysus as d
import numpy as np
import math
import matplotlib.pyplot as plt
import networkx as nx
from skimage.morphology import skeletonize
from sklearn import datasets

mkdir "data"

cd "data"

#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' prepare_data.py: Saves n_samples images of digits to numpy array.'''

import numpy as np
from sklearn.datasets import fetch_openml
import sys

n_samples = 10000
if len(sys.argv) == 2:
    print('Setting n_samples to: %i' % (n_samples))
    n_samples = int(sys.argv[1])

# load data from https://www.openml.org/d/554
print('Loading digits...')
X, y = fetch_openml('mnist_784', version=1, return_X_y=True)

np.save('../data/' + 'X_' + str(n_samples) + '.npy', X[:n_samples])
np.save('../data/' + 'y_' + str(n_samples) + '.npy', y[:n_samples])

data_X = np.load('../data/X_' + str(n_samples) + '.npy', allow_pickle=True)
data_y = np.load('../data/y_'  + str(n_samples) + '.npy', allow_pickle=True)

print(data_X.shape)
print(data_y.shape)
print(data_X[0].shape)

def get_image(n, plot = False):
  img = data_X[n]
  img = img.reshape((28,28))
  if plot:
    plt.imshow(img, cmap=plt.cm.gray_r)
    plt.show()
  return img

def get_binary(img, plot = False):
  bi = img != 0
  if plot:
    plt.imshow(bi, cmap=plt.cm.gray_r)
    plt.show()
  return bi

def get_sk(bin_img, plot = False):
  skeleton = skeletonize(bin_img)
  if plot:
    plt.imshow(skeleton, cmap=plt.cm.gray_r)
    plt.show()
  return skeleton

def construct_graph(image):
    graph = {}
    vertices = []
    rows, cols = len(image), len(image)
    img = image.T

    # Add vertices to the graph
    for i in range(rows):
        for j in range(cols):
            if img[i][j] == 1:
                vertex = (i, j)
                graph[vertex] = []
                vertices.append(vertex)

    # Add edges between adjacent points
    for vertex in graph.keys():
        i, j = vertex
        neighbors = get_neighbors(i, j, rows, cols)
        for neighbor in neighbors:
            if neighbor in graph:
                graph[vertex].append(neighbor)

    # Remove cycles of length 3
    remove_cycles_of_length_3(graph)

    # Construct adjacency matrix
    adjacency_matrix = np.zeros((len(vertices), len(vertices)), dtype=int)
    for i, vertex in enumerate(vertices):
        neighbors = graph[vertex]
        for neighbor in neighbors:
            j = vertices.index(neighbor)
            adjacency_matrix[i, j] = 1

    G = nx.from_numpy_array(adjacency_matrix)
    return G

def get_neighbors(i, j, rows, cols):
    neighbors = []
    directions = [(1,0), (1, 1), (0, 1), (-1, 1), (-1,0), (-1,-1), (0,-1), (1,-1)]

    for direction in directions:
        ni, nj = i + direction[0], j + direction[1]
        if 0 <= ni < rows and 0 <= nj < cols:
            neighbors.append((ni, nj))

    return neighbors

def remove_cycles_of_length_3(graph):
    for vertex in graph.keys():
        if len(graph[vertex]) == 2:
            neighbors = graph[vertex]
            if neighbors[0] in graph[neighbors[1]]:
                graph[neighbors[1]].remove(vertex)
                graph[vertex].remove(neighbors[1])

# Construcción de la filtración or simplejos a partir de la gráfica de la imagen

def simp_fil(G):
  import time
  NV = G.nodes()
  EV = G.edges()
  simplices = []
  number_of = {}

  tic = time.time()
  for node in NV:
    clock = (time.time() - tic) * 1000
    simplices.append(([node], clock))
    number_of[node] = node

  for edge in EV:
    clock = (time.time() - tic) * 1000
    simplices.append((edge, clock))

  f = d.Filtration()
  for simplex, time in simplices:
    f.append(d.Simplex(simplex, time))

  f.sort()

  return f

def betti_barcodes(f):
  p_hom = d.homology_persistence(f)
  dgms = d.init_diagrams(p_hom, f)

  barcodes = []
  for i, dgm in enumerate(dgms):
    for pt in dgm:
      barcodes.append([i, (pt.birth, pt.death)])

  return barcodes

def extract_features(intervals):
    ''' Extracts 4 features:
        	sum_i { x_i * (y_i - x_i) }
        	sum_i { (y_max - y_i) * (y_i - x_i) }
        	sum_i { x_i^2 * (y_i - x_i)^4 }
        	sum_i { (y_max - y_i)^2 * (y_i - x_i)^4 }
    From the barcode intervals:
        (x1, y1), (x2, y2), ..., (x_n, y_n);
    Args:
        intervals::list
            Betti barcode intervals, for example: [[3.0, inf], [5.0, inf]]
    Returns:
        features::list
            The 4 computed features.
    '''
    xs = []
    ys = []
    for interval in intervals:
        x = interval[1][0]
        y = interval[1][1]
        if str(y) == 'inf': # replace the inf with image_size
            y = img_size
        xs.append(x)
        ys.append(y)

    f1, f2, f3, f4 = 0., 0., 0., 0.
    for i in range(len(xs)):
        f1 += xs[i] * (ys[i] - xs[i])
        f2 += (max(ys) - ys[i]) * (ys[i] - xs[i])
        f3 += math.pow(xs[i], 2) * math.pow(ys[i] - xs[i], 4)
        f4 += math.pow(max(ys) - ys[i], 2) * math.pow(ys[i] - xs[i], 4)

    return [f1, f2, f3, f4]

example = get_image(101)
imagen = get_binary(example)
imagen = get_sk(imagen)
G = construct_graph(imagen)
f = simp_fil(G)
betti = betti_barcodes(f)
print(extract_features(betti))

#for interval in betti:
# print("Dimensión:", str(interval[0]) + ",", "intervalo:", interval[1])





def extract_all_features(n):
    ''' Extracts features of nth image, all together:
            4 sweeps * (2 barcodes * 4 features) = 32 features
        Args:
            n::int
                The number of the handwritten digit image, for example:
                    n = 17 for image of number 8.
        Returns:
            all_features::list
                The 32 computed features.
    '''
    image = get_image(n)
    binary_image = get_binary(image)
    skeleton = get_sk(binary_image)

    all_features = []
    G_d = construct_graph(skeleton)
    f_d = simp_fil(G_d)
    betti_d = betti_barcodes(f_d)
    f0 = extract_features(betti_d)
    G_u = construct_graph(skeleton.T)
    f_u = simp_fil(G_u)
    betti_u = betti_barcodes(f_u)
    f1 = extract_features(betti_u)

    #for sweep_direction in ['right', 'left', 'top', 'bottom']:
    #    points = get_points(skeleton, sweep_direction)
    #    point_list = PointList(points)
    #    emb_graph = point_list.get_emb_graph()
    #    simplices = get_simplices(emb_graph)
    #    intervals = get_betti_barcodes(simplices)

        f0 = extract_features(intervals[0])
        f1 = extract_features(intervals[1])
        features = f0 + f1
        all_features += features

    return all_features

def save_features_matrix(n_samples=1000):
    ''' Saves the feature matrix of shape (n_samples, n_features) to ../data
    directory.
    Args:
        n_samples::int
            Number of samples of handwritten digit images.
    '''
    df = np.zeros((n_samples, n_features))

    # extract all features of each image and save it to an array
    print('Extracting all features...')
    for n in range(n_samples):
        df[n] = extract_all_features(n)

    #print('Features extracted.')
    #np.save('../data/' + 'features_' + str(n_samples) + '.npy', df)





