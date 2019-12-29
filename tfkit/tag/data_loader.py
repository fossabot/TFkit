import sys
import os
dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path, os.pardir)))

import csv
import json
import pickle
from collections import defaultdict

import numpy as np
from torch.utils import data
from tqdm import tqdm
from transformers import AutoTokenizer
from utility.tok import *


class loadColTaggerDataset(data.Dataset):
    def __init__(self, fpath, tokenizer, maxlen=368, cache=False):
        samples = []
        tokenizer = AutoTokenizer.from_pretrained(tokenizer)
        cache_path = fpath + ".cache"
        if os.path.isfile(cache_path) and cache:
            with open(cache_path, "rb") as cf:
                savedict = pickle.load(cf)
                samples = savedict["samples"]
                labels = savedict["labels"]
        else:
            for i in get_data_from_file_col(fpath):
                tasks, task, input, target = i
                labels = tasks[task]
                feature = get_feature_from_data(tokenizer, labels, input, target, maxlen=maxlen)
                if len(feature['input']) == len(feature['target']) and len(feature['input']) <= 512:
                    samples.append(feature)

                if cache:
                    with open(cache_path, 'wb') as cf:
                        pickle.dump({'samples': samples, 'labels': labels}, cf)
        self.sample = samples
        self.label = labels

    def __len__(self):
        return len(self.sample)

    def __getitem__(self, idx):
        return self.sample[idx]


class loadRowTaggerDataset(data.Dataset):
    def __init__(self, fpath, tokenizer, maxlen=512, separator=" ", cache=False):
        samples = []
        labels = []
        tokenizer = AutoTokenizer.from_pretrained(tokenizer)
        cache_path = fpath + ".cache"
        if os.path.isfile(cache_path) and cache:
            with open(cache_path, "rb") as cf:
                savedict = pickle.load(cf)
                samples = savedict["samples"]
                labels = savedict["labels"]
        else:
            for i in get_data_from_file_row(fpath):
                tasks, task, input, target = i
                labels = tasks[task]
                feature = get_feature_from_data(tokenizer, labels, input, target, maxlen=maxlen)
                if len(feature['input']) == len(feature['target']) and len(feature['input']) <= 512:
                    samples.append(feature)
                if cache:
                    with open(cache_path, 'wb') as cf:
                        pickle.dump({'samples': samples, 'labels': labels}, cf)
        self.sample = samples
        self.label = labels

    def __len__(self):
        return len(self.sample)

    def __getitem__(self, idx):
        return self.sample[idx]


def get_data_from_file_row(fpath, text_index: int = 0, label_index: int = 1, separator=" "):
    tasks = defaultdict(list)
    task = 'default'
    labels = []
    with open(fpath, 'r', encoding='utf-8') as f:
        f_csv = csv.reader(f)
        for row in f_csv:
            for i in row[1].split(separator):
                if i not in labels and len(i.strip()) > 0:
                    labels.append(i)
                    labels.sort()
    tasks[task] = labels
    with open(fpath, 'r', encoding='utf-8') as f:
        f_csv = csv.reader(f)
        for row in tqdm(f_csv):
            yield tasks, task, row[text_index].strip(), row[label_index].strip()


def get_data_from_file_col(fpath, text_index: int = 0, label_index: int = 1, separator=" "):
    tasks = defaultdict(list)
    task = 'default'
    labels = []
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
        for line in tqdm(lines):
            rows = line.split(' ')
            if len(rows) > 1:
                if rows[label_index] not in labels and len(rows[label_index]) > 0:
                    labels.append(rows[label_index])
                    labels.sort()
    tasks[task] = labels
    with open(fpath, 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()
        x, y = "", ""
        for line in tqdm(lines):
            rows = line.split(' ')
            if len(rows) == 1:
                yield tasks, task, x.strip(), y.strip()
                x, y = "", ""
            else:
                if len(rows[text_index]) > 0:
                    x += rows[text_index].replace(" ", "_") + separator
                    y += rows[label_index].replace(" ", "_") + separator


def get_feature_from_data(tokenizer, labels, input, target=None, maxlen=512, separator=" "):
    # ``1`` for tokens that are NOT MASKED, ``0`` for MASKED tokens.
    row_dict = dict()
    tokenized_input = [tok_begin(tokenizer)] + tokenizer.tokenize(input) + [tok_sep(tokenizer)]
    input_id = tokenizer.convert_tokens_to_ids(tokenized_input)
    input = input.split()
    mapping_index = []

    pos = 1  # cls as start 0
    for i in input:
        for _ in range(len(tokenizer.tokenize(i))):
            if _ < 1:
                mapping_index.append({'char': i, 'pos': pos})
            pos += 1

    if target is not None:
        target = target.split(separator)
        target_token = []

        for i, t in zip(input, target):
            for _ in range(len(tokenizer.tokenize(i))):
                target_token += [labels.index(t)]

        target_id = [labels.index("O")] + target_token + [labels.index("O")]
        if len(input_id) != len(target_id):
            print("input target len no equal", len(input), len(target), input, target)
        target_id.extend([0] * (maxlen - len(target_id)))
        row_dict['target'] = np.asarray(target_id)

    row_dict['mapping'] = json.dumps(mapping_index, ensure_ascii=False)
    mask_id = [1] * len(input_id)
    mask_id.extend([0] * (maxlen - len(mask_id)))
    row_dict['mask'] = np.asarray(mask_id)
    row_dict['end'] = len(input_id)
    input_id.extend([0] * (maxlen - len(input_id)))
    row_dict['input'] = np.asarray(input_id)

    # if debug:
    #     print("*** Example ***")
    #     print(f"input: {len(input_id)}, {list(zip(enumerate(input_id)))} ")
    #     print(f"mask: {len(mask_id)}, {list(zip(enumerate(mask_id)))} ")
    #     if target is not None:
    #         print(f"target: {len(target_id)}, {list(zip(enumerate(mask_id)))} ")
    #     print(f"mapping: {row_dict['mapping']} ")

    return row_dict
