import sys
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.abspath(os.path.join(dir_path, os.pardir)))

import torch
import torch.nn as nn
from transformers import *
from torch.nn.functional import softmax, sigmoid
from classifier.data_loader import get_feature_from_data
from utility.loss import *


class BertMtClassifier(nn.Module):

    def __init__(self, tasks_detail, model_config, maxlen=512, dropout=0.1):
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print('Using device:', self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_config)
        self.pretrained = AutoModel.from_pretrained(model_config)

        self.dropout = nn.Dropout(dropout)
        self.loss_fct = FocalLoss()
        self.loss_fct_mt = BCEFocalLoss()
        # self.loss_fct = FocalLoss()
        # self.loss_fct = GWLoss()

        self.tasks = dict()
        self.tasks_detail = tasks_detail
        self.classifier_list = nn.ModuleList()
        for task, labels in tasks_detail.items():
            self.classifier_list.append(nn.Linear(self.pretrained.config.hidden_size, len(labels)).to(self.device))
            self.tasks[task] = len(self.classifier_list) - 1
        self.maxlen = maxlen

        self.pretrained = self.pretrained.to(self.device)
        self.classifier_list = self.classifier_list.to(self.device)
        self.loss_fct = self.loss_fct.to(self.device)
        self.loss_fct_mt = self.loss_fct_mt.to(self.device)

    def forward(self, batch_data, eval=False):
        tasks = batch_data['task']
        inputs = torch.tensor(batch_data['input']).to(self.device)
        targets = torch.tensor(batch_data['target']).to(self.device)
        masks = torch.tensor(batch_data['mask']).to(self.device)

        result_logits = []
        result_labels = []
        result_item = []

        for p, zin in enumerate(zip(tasks, inputs, masks)):
            task, input, mask = zin
            task_id = self.tasks[task]
            task_lables = self.tasks_detail[task]

            output = self.pretrained(input.unsqueeze(0), mask.unsqueeze(0))[0]
            pooled_output = self.dropout(output)
            classifier_output = self.classifier_list[task_id](pooled_output)[0, 0]
            reshaped_logits = classifier_output.view(-1, len(task_lables))  # 0 for cls position
            result_logits.append(reshaped_logits)
            if 'multi_target' in task:
                reshaped_logits = sigmoid(reshaped_logits)
            else:
                reshaped_logits = softmax(reshaped_logits)
            logit_prob = reshaped_logits[0].data.tolist()
            logit_label = dict(zip(task_lables, logit_prob))
            result_item.append(logit_label)

            if eval is False:
                target = targets[p]
                result_labels.append(target)
        if eval:
            outputs = (result_item,)
        else:
            outputs = (result_labels,)
        if eval is False:
            loss = 0
            for logits, labels, task in zip(result_logits, result_labels, tasks):
                if 'multi_target' in task:
                    loss += self.loss_fct_mt(logits, labels)
                else:
                    loss += self.loss_fct(logits, labels)
            outputs = (loss,) + outputs
        return outputs

    def predict(self, task, input, topk=1):
        self.eval()
        with torch.no_grad():
            feature_dict = get_feature_from_data(self.tokenizer, self.maxlen, self.tasks_detail[task], task, input)
            if len(feature_dict['input']) <= self.maxlen:
                for k, v in feature_dict.items():
                    feature_dict[k] = [v]
                result = self.forward(feature_dict, eval=True)
                result = result[0][0]
                res = sorted(result, key=result.get, reverse=True)
                return res[:topk], result
            else:
                return [""], []
