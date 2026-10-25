"""Offline engineer-only numeric-checkpoint smoke inference; not a clinical API."""
import argparse
import hashlib
import json

import numpy as np
import torch
from PIL import Image, ImageOps
from torch import nn
from torchvision.models import MobileNet_V3_Small_Weights, ResNet18_Weights, mobilenet_v3_small, resnet18

from train_feature_research import color_features
from train_medical_pilots import ROOT
from pathlib import Path


def numeric_probabilities(state, features, class_count):
    mean, scale = state['scaler_mean'], state['scaler_scale']
    coefficients, intercept = state['coefficients'], state['intercept']
    if not all(torch.isfinite(value).all() for value in state.values()) or not (scale > 0).all():
        raise ValueError('Nonfinite or invalid numeric model state')
    if mean.ndim != 1 or scale.shape != mean.shape or features.shape[-1] != len(mean):
        raise ValueError('Feature/scaler shape mismatch')
    if not torch.equal(state['classes'], torch.arange(class_count)):
        raise ValueError('Class order mismatch')
    decision = ((features.double() - mean.double()) / scale.double()) @ coefficients.double().T + intercept.double()
    if class_count == 2 and decision.shape[-1] == 1:
        decision = torch.cat([torch.zeros_like(decision), decision], dim=-1)
    if decision.shape[-1] != class_count or not torch.isfinite(decision).all():
        raise ValueError('Invalid classifier output shape or values')
    return decision.softmax(-1)


def predict(directory, image_path):
    torch.set_num_threads(2)
    card = json.loads((directory / 'model_card.json').read_text(encoding='utf-8'))
    if card.get('architecture') not in {'MobileNetV3ColorRegularizedFeatures', 'FrozenImageNetColorRegularizedFeatures'} or card.get('clinical_approved') is not False:
        raise ValueError('Unsupported/unapproved research checkpoint')
    weights = directory / 'weights.pt'
    if hashlib.sha256(weights.read_bytes()).hexdigest() != card['checkpoint_sha256']:
        raise ValueError('Checkpoint integrity mismatch')
    state = torch.load(weights, weights_only=True, map_location='cpu')
    backbone_name = card.get('backbone', 'mobilenet')
    if backbone_name not in {'mobilenet', 'resnet18'}:
        raise ValueError('Unsupported backbone')
    name = 'mobilenet_v3_small-047dcff4.pth' if backbone_name == 'mobilenet' else 'resnet18-f37072fd.pth'
    pretrained = ROOT / 'models/pretrained' / name
    if hashlib.sha256(pretrained.read_bytes()).hexdigest() != card['pretrained_sha256']:
        raise ValueError('Pretrained integrity mismatch')
    model = mobilenet_v3_small(weights=None) if backbone_name == 'mobilenet' else resnet18(weights=None)
    model.load_state_dict(torch.load(pretrained, weights_only=True, map_location='cpu'))
    if backbone_name == 'mobilenet':
        model.classifier = nn.Identity()
    else:
        model.fc = nn.Identity()
    model.eval()
    transform = (MobileNet_V3_Small_Weights.DEFAULT if backbone_name == 'mobilenet' else ResNet18_Weights.DEFAULT).transforms()
    if image_path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('Image byte budget exceeded')
    with Image.open(image_path) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError('Image pixel budget exceeded')
        image = ImageOps.exif_transpose(source).convert('RGB')
        color = torch.from_numpy(color_features(image)).unsqueeze(0)
        with torch.inference_mode():
            cnn = model(transform(image).unsqueeze(0))
    mode = card['selected_features']
    if mode not in {'cnn', 'color', 'cnn_color'}:
        raise ValueError('Unsupported feature recipe')
    features = cnn if mode == 'cnn' else color if mode == 'color' else torch.cat([cnn, color], dim=1)
    probabilities = numeric_probabilities(state, features, len(card['classes']))[0].tolist()
    if not np.isfinite(probabilities).all():
        raise ValueError('Nonfinite research scores')
    return {'clinical_inference': False, 'diagnosis': None,
        'research_scores_uncalibrated': dict(zip(card['classes'], probabilities)),
        'warning': 'Research-only scores; not disease confirmation, exclusion or medicine advice.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model-directory', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    print(json.dumps(predict(args.model_directory, args.image)), flush=True)
