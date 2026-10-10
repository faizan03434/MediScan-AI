"""Engineer-only checkpoint smoke inference; results are not clinical probabilities."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from train_skin_research import SkinCNN, image_tensor, ROOT


def load_research_model(directory):
    card = json.loads((directory / 'model_card.json').read_text(encoding='utf-8'))
    checkpoint = directory / 'weights.pt'
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != card['checkpoint_sha256']:
        raise ValueError('Checkpoint integrity failed')
    if card['architecture'] == 'SkinCNN':
        model = SkinCNN(len(card['classes']))
        transform = image_tensor
    elif card['architecture'] in {'MobileNetV3SmallFrozen', 'MobileNetV3SmallLastBlockFinetuned'}:
        from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
        from PIL import Image, ImageOps
        model = mobilenet_v3_small(weights=None)
        model.classifier = torch.nn.Sequential(torch.nn.Dropout(.2), torch.nn.Linear(576, len(card['classes'])))
        preprocessing = MobileNet_V3_Small_Weights.DEFAULT.transforms()
        def transform(path):
            with Image.open(path) as image:
                return preprocessing(ImageOps.exif_transpose(image).convert('RGB'))
    else:
        raise ValueError('Unsupported research architecture')
    model.load_state_dict(torch.load(checkpoint, weights_only=True))
    model.eval()
    return model, transform, card

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--model-directory', type=Path, default=ROOT / 'models/research/skin-cnn-v1')
    args = parser.parse_args()
    directory = args.model_directory
    torch.set_num_threads(4)
    model, transform, card = load_research_model(directory)
    with torch.no_grad():
        scores = model(transform(args.image).unsqueeze(0)).softmax(1)[0].tolist()
    print(json.dumps({'clinical_inference': False, 'diagnosis': None,
        'research_scores_uncalibrated': dict(zip(card['classes'], scores)),
        'warning': 'Unvalidated research baseline; healthy skin and unfamiliar conditions are not covered.'}, indent=2))

if __name__ == '__main__':
    main()
