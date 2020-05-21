import torch.nn as nn
# import torch.utils.model_zoo as model_zoo
# from torch.nn.parameter import Parameter
import torch
import time
import torch.nn.functional as F
# from torch.nn import init
# from torch.autograd import Variable
# from collections import OrderedDict
import math
__all__ = ['validate5_resnet18', 'validate5_resnet34', 'validate5_resnet50', 'validate5_resnet101',
           'validate5_resnet152']

class AssConv(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=1, dilation=1, groups=1,bias=False):
        super(AssConv, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias)
        self.conv2 = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias)
        self.conv3 = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias)
        self.conv4 = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=bias)
        self.bn1 =  nn.BatchNorm2d(out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.bn3 = nn.BatchNorm2d(out_channels)
        self.bn4 = nn.BatchNorm2d(out_channels)

        self.fc = nn.Sequential(
            nn.Linear(in_channels,in_channels//4),
            nn.ReLU(inplace=True),
            nn.Linear(in_channels//4, 4),
            nn.Softmax(dim=1)
        )
        self.gap = nn.AdaptiveAvgPool2d(1)


    def forward(self, input):
        out_1 = self.bn1(self.conv1(input)).unsqueeze(dim=1)
        out_2 = self.bn2(self.conv2(input)).unsqueeze(dim=1)
        out_3 = self.bn3(self.conv3(input)).unsqueeze(dim=1)
        out_4 = self.bn4(self.conv4(input)).unsqueeze(dim=1)


        all_out = torch.cat([out_1,out_2,out_3,out_4],dim=1)

        gap = input.mean(dim=-1).mean(dim=-1)

        buffer1 = F.linear(gap,self.conv1.weight.clone().mean(dim=-1).mean(dim=-1))
        buffer1 = F.batch_norm(buffer1, self.bn1.running_mean, self.bn1.running_var, weight=self.bn1.weight,
                               bias=self.bn1.bias, training=False, momentum=0.1, eps=1e-5)

        buffer2 = F.linear(gap, self.conv2.weight.clone().mean(dim=-1).mean(dim=-1))
        buffer2 = F.batch_norm(buffer2, self.bn2.running_mean, self.bn2.running_var, weight=self.bn2.weight,
                               bias=self.bn2.bias, training=False, momentum=0.1, eps=1e-5)
        buffer3 = F.linear(gap, self.conv3.weight.clone().mean(dim=-1).mean(dim=-1))
        buffer3 = F.batch_norm(buffer3, self.bn3.running_mean, self.bn3.running_var, weight=self.bn3.weight,
                               bias=self.bn3.bias, training=False, momentum=0.1, eps=1e-5)
        buffer4 = F.linear(gap, self.conv4.weight.clone().mean(dim=-1).mean(dim=-1))
        buffer4 = F.batch_norm(buffer4, self.bn4.running_mean, self.bn4.running_var, weight=self.bn4.weight,
                               bias=self.bn4.bias, training=False, momentum=0.1, eps=1e-5)

        all_buffer = torch.cat([buffer1.unsqueeze(dim=1),buffer2.unsqueeze(dim=1),
                                buffer3.unsqueeze(dim=1),buffer4.unsqueeze(dim=1)],dim=1)

        all_buffer = torch.softmax(all_buffer,dim=1).unsqueeze(dim=-1).unsqueeze(dim=-1)


        out = all_buffer*all_out
        out = out.sum(dim=1,keepdim=False)
        return out











def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(BasicBlock, self).__init__()
        self.conv1 = AssConv(inplanes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        # self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = AssConv(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        # self.bn2 = nn.BatchNorm2d(planes)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        # out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        # out = self.bn2(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(Bottleneck, self).__init__()
        self.conv1 = conv1x1(inplanes, planes)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = AssConv(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        # self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = conv1x1(planes, planes * self.expansion)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        # out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            identity = self.downsample(x)

        out += identity
        out = self.relu(out)

        return out


class ResNet(nn.Module):

    def __init__(self, block, layers, num_classes=1000, zero_init_residual=False):
        super(ResNet, self).__init__()
        self.inplanes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

        # Zero-initialize the last BN in each residual branch,
        # so that the residual branch starts with zeros, and each residual block behaves like an identity.
        # This improves the model by 0.2~0.3% according to https://arxiv.org/abs/1706.02677
        if zero_init_residual:
            for m in self.modules():
                if isinstance(m, Bottleneck):
                    nn.init.constant_(m.bn3.weight, 0)
                elif isinstance(m, BasicBlock):
                    nn.init.constant_(m.bn2.weight, 0)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = nn.Sequential(
                conv1x1(self.inplanes, planes * block.expansion, stride),
                nn.BatchNorm2d(planes * block.expansion),
            )

        layers = []
        layers.append(block(self.inplanes, planes, stride, downsample))
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)

        return x


def validate5_resnet18(pretrained=False, **kwargs):
    """Constructs a ResNet-18 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    return model


def validate5_resnet34(pretrained=False, **kwargs):
    """Constructs a ResNet-34 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    return model


def validate5_resnet50(pretrained=False, **kwargs):
    """Constructs a ResNet-50 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
    return model


def validate5_resnet101(pretrained=False, **kwargs):
    """Constructs a ResNet-101 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 23, 3], **kwargs)
    return model


def validate5_resnet152(pretrained=False, **kwargs):
    """Constructs a ResNet-152 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 8, 36, 3], **kwargs)
    return model


def demo():
    st = time.perf_counter()
    for i in range(1):
        net = validate5_resnet18(num_classes=1000)
        y = net(torch.randn(2, 3, 224,224))
        print(y.size())
    print("CPU time: {}".format(time.perf_counter() - st))

def demo2():
    st = time.perf_counter()
    for i in range(1):
        net = validate5_resnet50(num_classes=1000).cuda()
        y = net(torch.randn(2, 3, 224,224).cuda())
        print(y.size())
    print("CPU time: {}".format(time.perf_counter() - st))

# demo()
# demo2()

