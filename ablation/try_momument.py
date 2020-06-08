import torch
import torch.nn as nn
from collections import OrderedDict
from torch.distributions.multivariate_normal import MultivariateNormal
from torch.distributions.normal import Normal
from torch.nn.parameter import Parameter
import numpy as np
import torch.nn.functional as F
import math
import models as models
from utils.visualize_kernel import Distribution
import matplotlib.pyplot as plt
from models.ResNet.resnet_dist5 import DPConv
from apex.parallel import DistributedDataParallel as DDP
from apex.fp16_utils import *

model = models.__dict__['dist5_resnet18']()
path = "/home/g1007540910/DistKernel/checkpoints/imagenet/new1_resnet18/model_best.pth.tar"
check_point = torch.load(path,map_location=lambda storage, loc: storage.cuda(0))
new_check_point = OrderedDict()

for k, v in check_point['optimizer'].items():
    # name = k[7:]  # remove `module.`
    # name = k[7:]  # remove `module.1.`
    # new_check_point[name] = v
    print(k)
    print(v)


