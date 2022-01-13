import os
import queue
import argparse
from glob import glob
from math import sqrt
from os.path import join, isdir, isfile, abspath
from tensorflow.keras import backend as K

import tensorflow as tf
from tensorflow.keras import optimizers
from tensorflow.data.experimental import sample_from_datasets

from noscope_conv_nn import model

from tensorflow.keras.preprocessing.image import save_img
from tensorflow.keras.layers.experimental.preprocessing import Normalization
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint

def binary_crossentropy_with_ranking(y_true, y_pred):
    """ Trying to combine ranking loss with numeric precision"""
    # first get the log loss like normal
    logloss = K.mean(K.binary_crossentropy(y_pred, y_true), axis=-1)
    # next, build a rank loss
    # clip the probabilities to keep stability
    y_pred_clipped = K.clip(y_pred, K.epsilon(), 1-K.epsilon())
    # translate into the raw scores before the logit
    y_pred_score = K.log(y_pred_clipped / (1 - y_pred_clipped))
    # determine what the maximum score for a zero outcome is
    y_pred_score_zerooutcome_max = K.max(
        y_pred_score * tf.cast(y_true < 1, tf.float32))
    # determine how much each score is above or below it
    rankloss = y_pred_score - y_pred_score_zerooutcome_max
    # only keep losses for positive outcomes
    rankloss = rankloss * y_true
    # only keep losses where the score is below the max
    rankloss = K.square(K.clip(rankloss, -100, 0))
    # average the loss for just the positive outcomes
    rankloss = K.sum(rankloss, axis=-1) / \
        (K.sum(tf.cast(y_true > 0, tf.float32)) + 1)
    # return (rankloss + 1) * logloss - an alternative to try
    return rankloss + logloss


def check_units(y_true, y_pred):
    if y_pred.shape[1] != 1:
        y_pred = y_pred[:, 1:2]  # The second column is the true label
        y_true = y_true[:, 1:2]
    return y_true, y_pred


def precision(y_true, y_pred):
    y_true, y_pred = check_units(y_true, y_pred)
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    predicted_positives = K.sum(K.round(K.clip(y_pred, 0, 1)))
    precision = true_positives / (predicted_positives + K.epsilon())
    return precision


def recall(y_true, y_pred):
    y_true, y_pred = check_units(y_true, y_pred)
    true_positives = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    possible_positives = K.sum(K.round(K.clip(y_true, 0, 1)))
    recall = true_positives / (possible_positives + K.epsilon())
    return recall


def png_to_image(filename, resize=None):
    decoded = tf.io.decode_png(tf.io.read_file(filename), channels=3)

    # print(decoded.shape)

    resized = decoded if resize is None else tf.image.resize(decoded, resize)

    mean = [102.06902, 95.29761, 87.123474]
    std = [sqrt(2023.6150), sqrt(1882.4359), sqrt(1584.6699)]

    #return resized
    return (resized - mean) / std


def parse_image_number_from_filepath(filepath):
    filename = filepath.split('/')[-1]

    return int(filename.split('.')[0])


def generate_image_dataset(image_roots, resize=None):
    file_list = []

    for image_root in image_roots:
        files = sorted(glob(join(image_root, '*')), key=lambda path: parse_image_number_from_filepath(path))
        file_list.extend(files)

    print(f'found {len(file_list)} images')
    filename_dataset = tf.data.Dataset.from_tensor_slices(file_list)

    image_dataset = filename_dataset.map(lambda filename: png_to_image(filename, resize), deterministic=True)

    return (image_dataset, file_list)


def generate_label_dataset(file_paths, class_to_detect):
    labels = []
    fns = []
    counted = [0] * 2

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            for line in f:
                label = [0.0] * 2
                if str(class_to_detect) in line.strip().split(' '):
                    label[1] = 1.0
                    counted[1] += 1
                else:
                    label[0] = 1.0
                    counted[0] += 1

                labels.append(label)
                fns.append(file_path)

    total_labels = counted[0] + counted[1]
    print(f'label distribution statistic: 0: {counted[0] / total_labels:.3} 1: {counted[1] / total_labels:.3}')

    return tf.data.Dataset.from_tensor_slices(tf.constant(labels)), fns


def generate_data(pair, class_to_detect, resize=None):
    image_path, index = pair[0], tf.strings.to_number(pair[1])

    label = tf.constant([1.0, 0.0]) if index == 0.0 else tf.constant([0.0, 1.0])
    return png_to_image(image_path, resize=resize), label


def generate_datasets(data_root, class_to_detect, resize=None):
    data_pairs = []

    path_to_search = queue.Queue()
    path_to_search.put(data_root)

    while path_to_search.empty() == False:
        path = path_to_search.get()

        candidate_image_root = join(path, 'images')
        candidate_label_path = join(path, 'label.txt')

        if isdir(candidate_image_root) and isfile(candidate_label_path):
            with open(candidate_label_path, 'r') as f:
                frame_idx = 0
                for line in f:
                    label = '0'
                    if str(class_to_detect) in line.strip().split(' '):
                        label = '1'

                    data_pairs.append([join(candidate_image_root, f'{frame_idx}.png'), label])

                    frame_idx += 1
        else:
            filenames = os.listdir(path)

            for filename in filenames:
                candidate_path = join(path, filename)
                if isdir(candidate_path):
                    path_to_search.put(candidate_path)

    data_pair_dataset = tf.data.Dataset.from_tensor_slices(data_pairs)

    image_dataset = data_pair_dataset.map(lambda pair: generate_data(pair, class_to_detect, resize))

    if len(data_pairs) == 0:
        print('there\'s no any data: counted zero')
        exit(1)

    return image_dataset


def generate_data_paths(data_root):
    image_roots = []
    label_paths = []

    path_to_search = queue.Queue()
    path_to_search.put(data_root)

    while path_to_search.empty() == False:
        path = path_to_search.get()

        candidate_image_root = join(path, 'images')
        candidate_label_path = join(path, 'label.txt')

        if isdir(candidate_image_root) and isfile(candidate_label_path):
            image_roots.append(candidate_image_root)
            label_paths.append(candidate_label_path)
        else:
            filenames = os.listdir(path)

            for filename in filenames:
                candidate_path = join(path, filename)
                if isdir(candidate_path):
                    path_to_search.put(candidate_path)

    if len(image_roots) == 0 or len(label_paths) == 0:
        print('there\'s no any data: counted zero')
        exit(1)

    if len(image_roots) != len(label_paths):
        print(f'data cannot be paired, # of image roots: {len(image_roots)} # of label paths: {len(label_paths)}')
        exit(1)

    return (image_roots, label_paths)


def sample_by_ratio(dataset, ratio_list, seed=None):
    datasets = []

    for i in range(len(ratio_list)):
        filtered = dataset.filter(lambda data, label: label[i] == 1.0).repeat()
        datasets.append(filtered)

    return sample_from_datasets(datasets, ratio_list, seed)


def train(model, dataset):
    for batch_index, (input_data, target) in enumerate(dataset):
        model.fit(input_data, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--data-root', help='root path containing input data: pairs of image directory and label file')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        exit(1)

    # model input/output dimension configurations to generate
    input_shape = [640, 640, 3]
    class_to_detect = 2  # vehicle

    batch_size = 16 # 6
    epoch_cnt = 5
    iters_per_epoch = int(32451 / batch_size)

    train_dataset = generate_datasets(args.data_root, class_to_detect, resize=input_shape[0:2])
    train_dataset = sample_by_ratio(train_dataset, ratio_list=[0.5, 0.5], seed=0).batch(batch_size).take(iters_per_epoch)

    #image_roots, label_paths = generate_data_paths(args.data_root)
    #image_dataset, filenames = generate_image_dataset(image_roots, resize=input_shape[0:2])
    #label_dataset, fns = generate_label_dataset(label_paths, class_to_detect)

    '''
    i = 0
    iterator = iter(label_dataset)
    for filename, fn in zip(filenames, fns):
        #print(filename)
        #print(fn)
        label = iterator.get_next()
        filepath = join(filename.split('/images')[0], 'label.txt')
        #print(filepath)
        frame_idx = parse_image_number_from_filepath(filename)
        #print(filename)
        with open(filepath, 'r') as f:
            for i in range(int(frame_idx) + 1):
                line = f.readline()
            #print(filepath)
            print(f'{line.strip().split()} | {label}')

        i += 1

    train_dataset = tf.data.Dataset.zip((image_dataset, label_dataset))
    train_dataset = sample_by_ratio(train_dataset, [0.5, 0.5]).batch(batch_size).take(iters_per_epoch)
    '''

    '''
    i = 0
    with open('./png/labels.txt', 'w') as f:
        for _, (data, label) in enumerate(train_dataset):
            if label[0][0] ==
            save_img(f'./png/{i}.png', data[0])
            f.write(f'{i}: {label[0][0]} {label[0][1]}\n')
            i += 1
    '''

    model = model.generate_conv_net(input_shape, 2)

    model.compile(
        optimizer=optimizers.Adam(learning_rate=0.001),
        loss=binary_crossentropy_with_ranking,
        metrics=[precision, recall])
    # model = tf.keras.models.load_model('./training_output')#model.generate_conv_net(input_shape, 2)

    # for _, (i, t) in enumerate(train_dataset):
    #     o = model.predict(i)
    #     print(f'{o} {t}')

    tb_callback = TensorBoard('./tensorboard_log', update_freq=1)
    checkpoint = ModelCheckpoint('./checkpoints', save_best_only=True)
    model.fit(train_dataset, batch_size=batch_size, epochs=epoch_cnt, callbacks=[tb_callback, checkpoint])
    model.save('./training_output')
