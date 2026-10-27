"""
models/deep_learning/waveform_models.py
---------------------------------------
PyTorch neural network architectures for raw-waveform power quality classification:
1. Compact1DCNN: Hierarchical multi-scale 1D convolutional network with batch normalization.
2. TCN (Temporal Convolutional Network): Dilated residual convolutions capturing multi-scale temporal context.
3. HybridPQNet: Dual-branch fusion combining learned waveform representations and engineered electrical features.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class Compact1DCNN(nn.Module):
    """
    Compact 3-phase 1D Convolutional Neural Network for raw voltage waveforms.
    Input shape: [Batch, 3, Length] (where Length is 4,000 for 20 kHz or 1,000 for 5 kHz).
    """
    def __init__(self, in_channels: int = 3, num_classes: int = 8, feature_dim: int = 64):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, 32, kernel_size=15, stride=2, padding=7)
        self.bn1 = nn.BatchNorm1d(32)
        self.pool1 = nn.MaxPool1d(kernel_size=2)

        self.conv2 = nn.Conv1d(32, 64, kernel_size=9, stride=2, padding=4)
        self.bn2 = nn.BatchNorm1d(64)
        self.pool2 = nn.MaxPool1d(kernel_size=2)

        self.conv3 = nn.Conv1d(64, 128, kernel_size=7, stride=1, padding=3)
        self.bn3 = nn.BatchNorm1d(128)
        self.pool3 = nn.AdaptiveAvgPool1d(1)

        self.fc_embed = nn.Sequential(
            nn.Linear(128, feature_dim),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        self.classifier = nn.Linear(feature_dim, num_classes)

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool1(F.relu(self.bn1(self.conv1(x))))
        x = self.pool2(F.relu(self.bn2(self.conv2(x))))
        x = self.pool3(F.relu(self.bn3(self.conv3(x))))
        x = x.squeeze(-1)
        return self.fc_embed(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.extract_features(x)
        return self.classifier(feat)


class TCNBlock(nn.Module):
    """Residual dilated convolution block with weight normalization and dropout."""
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int, dilation: int, dropout: float = 0.2):
        super().__init__()
        padding = (kernel_size - 1) * dilation // 2
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, padding=padding, dilation=dilation)
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, padding=padding, dilation=dilation)
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout)

        self.downsample = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        res = x if self.downsample is None else self.downsample(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = self.bn2(self.conv2(out))
        out = self.dropout(out)
        return F.relu(out + res)


class TemporalConvNet(nn.Module):
    """
    Temporal Convolutional Network (TCN) with dilated residual convolutions.
    Dilations: [1, 2, 4, 8, 16] provide receptive field covering transient to multi-cycle scale.
    """
    def __init__(self, in_channels: int = 3, num_classes: int = 8, num_channels: list = [32, 64, 64, 128], kernel_size: int = 5, dropout: float = 0.2):
        super().__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_ch = in_channels if i == 0 else num_channels[i-1]
            out_ch = num_channels[i]
            layers.append(TCNBlock(in_ch, out_ch, kernel_size, dilation=dilation_size, dropout=dropout))

        self.network = nn.Sequential(*layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.fc = nn.Sequential(
            nn.Linear(num_channels[-1], 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        y = self.network(x)
        y = self.pool(y).squeeze(-1)
        return y

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.extract_features(x)
        return self.fc(feat)


class HybridPQNet(nn.Module):
    """
    Dual-branch hybrid architecture:
    - Branch 1: 1D CNN extracting 64-dim representation from 3-phase raw waveform
    - Branch 2: Dense MLP extracting 32-dim representation from 32 engineered features
    - Fusion: Concatenation (96-dim) -> Dense fusion layer (64-dim) -> 8-class classifier.
    """
    def __init__(self, in_waveform_channels: int = 3, in_features_dim: int = 32, num_classes: int = 8):
        super().__init__()
        self.waveform_encoder = Compact1DCNN(in_channels=in_waveform_channels, num_classes=num_classes, feature_dim=64)
        
        self.feature_encoder = nn.Sequential(
            nn.Linear(in_features_dim, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.BatchNorm1d(32),
            nn.ReLU()
        )

        self.fusion_head = nn.Sequential(
            nn.Linear(64 + 32, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )

    def forward(self, waveform: torch.Tensor, features: torch.Tensor) -> torch.Tensor:
        w_feat = self.waveform_encoder.extract_features(waveform)  # [B, 64]
        f_feat = self.feature_encoder(features)                   # [B, 32]
        fused = torch.cat([w_feat, f_feat], dim=1)                 # [B, 96]
        return self.fusion_head(fused)
