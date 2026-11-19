"""CNN própria: sem pesos pré-treinados ou arquitetura importada de torchvision."""
from torch import nn


class LandscapeCNN(nn.Module):
    def __init__(self, filters=(16, 32, 64), classes=10, dropout=0.25):
        super().__init__()
        blocks = []
        inputs = 3
        for outputs in filters:
            blocks.extend([
                nn.Conv2d(inputs, outputs, kernel_size=3, padding=1),
                nn.BatchNorm2d(outputs), nn.ReLU(), nn.MaxPool2d(2),
            ])
            inputs = outputs
        self.features = nn.Sequential(*blocks, nn.AdaptiveAvgPool2d((2, 2)))
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(inputs * 4, 64), nn.ReLU(),
            nn.Dropout(dropout), nn.Linear(64, classes),
        )

    def forward(self, images):
        return self.classifier(self.features(images))
