"""
Metric Learner — pytorch-metric-learning
==========================================
Learns an embedding space where compatible products are close together
and incompatible products are far apart.
Uses contrastive learning with advanced loss functions.
"""
import logging
import torch
import numpy as np
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class MetricLearner:
    """
    Metric learning for style compatibility.
    
    Uses pytorch-metric-learning to train a projection head
    that maps product features into a style compatibility space.
    """

    def __init__(self, input_dim: int, embedding_dim: int = 128, device: Optional[str] = None):
        self.input_dim = input_dim
        self.embedding_dim = embedding_dim
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.loss_func = None
        self.miner = None
        self._init_model()

    def _init_model(self):
        """Initialize the embedding model and loss function."""
        try:
            from pytorch_metric_learning import miners, losses, trainers
            from pytorch_metric_learning.utils import common_functions

            # Simple MLP projection head
            self.model = torch.nn.Sequential(
                torch.nn.Linear(self.input_dim, 512),
                torch.nn.ReLU(),
                torch.nn.BatchNorm1d(512),
                torch.nn.Dropout(0.2),
                torch.nn.Linear(512, self.embedding_dim),
            ).to(self.device)

            # MultiSimilarityLoss — state-of-the-art for metric learning
            self.loss_func = losses.MultiSimilarityLoss(
                alpha=2.0,
                beta=50.0,
                base=0.5,
            )

            # Mining hard examples
            self.miner = miners.MultiSimilarityMiner(
                epsilon=0.1,
            )

            logger.info(f"Metric learner initialized (dim {self.input_dim} → {self.embedding_dim}).")
        except ImportError:
            logger.warning("pytorch-metric-learning not installed. Using simple contrastive loss.")
            self.model = torch.nn.Sequential(
                torch.nn.Linear(self.input_dim, self.embedding_dim),
            ).to(self.device)
            self.loss_func = None

    def train(
        self,
        embeddings: np.ndarray,
        labels: np.ndarray,
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001,
    ) -> list:
        """
        Train the metric learning model.
        
        Args:
            embeddings: Product features (n_products, input_dim)
            labels: Compatibility group labels. Products with same label
                    are considered compatible/grouped together.
            epochs: Number of training epochs
            batch_size: Batch size
            learning_rate: Learning rate
            
        Returns:
            List of losses per epoch
        """
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        embeddings_tensor = torch.tensor(embeddings, dtype=torch.float32).to(self.device)
        labels_tensor = torch.tensor(labels, dtype=torch.long).to(self.device)

        losses_history = []
        n_samples = len(embeddings)
        indices = np.arange(n_samples)

        for epoch in range(epochs):
            np.random.shuffle(indices)
            epoch_loss = 0.0
            n_batches = 0

            for start in range(0, n_samples, batch_size):
                end = min(start + batch_size, n_samples)
                batch_idx = indices[start:end]

                batch_emb = embeddings_tensor[batch_idx]
                batch_labels = labels_tensor[batch_idx]

                optimizer.zero_grad()

                # Forward through projection head
                projected = self.model(batch_emb)

                if self.loss_func is not None and self.miner is not None:
                    # Use pytorch-metric-learning
                    hard_pairs = self.miner(projected, batch_labels)
                    loss = self.loss_func(projected, batch_labels, hard_pairs)
                else:
                    # Simple contrastive loss
                    loss = self._contrastive_loss(projected, batch_labels)

                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()
                n_batches += 1

            avg_loss = epoch_loss / max(n_batches, 1)
            losses_history.append(avg_loss)

            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} — Loss: {avg_loss:.4f}")

        return losses_history

    def _contrastive_loss(self, embeddings: torch.Tensor, labels: torch.Tensor, margin: float = 0.5):
        """Simple contrastive loss fallback."""
        n = embeddings.shape[0]
        loss = 0.0
        count = 0

        for i in range(n):
            for j in range(i + 1, n):
                sim = torch.cosine_similarity(embeddings[i].unsqueeze(0), embeddings[j].unsqueeze(0))
                same_label = (labels[i] == labels[j]).float()

                # Positive pair: maximize similarity
                # Negative pair: minimize similarity (push apart)
                pair_loss = same_label * (1 - sim) + (1 - same_label) * torch.clamp(sim - margin, min=0)
                loss += pair_loss
                count += 1

        return loss / max(count, 1)

    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """Transform embeddings into metric learning space."""
        self.model.eval()
        with torch.no_grad():
            tensor = torch.tensor(embeddings, dtype=torch.float32).to(self.device)
            projected = self.model(tensor)
            return projected.cpu().numpy()

    def save(self, path: str):
        """Save model weights."""
        torch.save(self.model.state_dict(), path)
        logger.info(f"Metric learner saved to {path}")

    def load(self, path: str):
        """Load model weights."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"Metric learner loaded from {path}")