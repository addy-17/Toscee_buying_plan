"""
Graph Neural Network — Style Compatibility GNN
=================================================
A GNN that learns to predict compatibility between products.
Uses PyTorch Geometric for graph-based learning.
Architecture: LightGCN-style message passing.
"""
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple
from utils.config import GNN_HIDDEN_DIM, GNN_OUTPUT_DIM, GNN_LEARNING_RATE, GNN_EPOCHS

logger = logging.getLogger(__name__)


class StyleGNN(nn.Module):
    """
    Lightweight GNN for style compatibility prediction.
    
    Learns product embeddings such that compatible products
    are close in the embedding space.
    
    Architecture:
    - Input: Product features (from CLIP/DINOv2 embeddings)
    - 2-layer Graph Convolution (GCN)
    - Output: Style embedding vector for each product
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = GNN_HIDDEN_DIM,
        output_dim: int = GNN_OUTPUT_DIM,
    ):
        super().__init__()
        
        try:
            from torch_geometric.nn import GCNConv
        except ImportError:
            logger.warning("PyTorch Geometric not installed. Using simple MLP fallback.")
            self.use_pyg = False
            self.mlp = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(hidden_dim, output_dim),
            )
            return

        self.use_pyg = True
        self.conv1 = GCNConv(input_dim, hidden_dim)
        self.conv2 = GCNConv(hidden_dim, output_dim)
        self.dropout = nn.Dropout(0.2)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(output_dim)

    def forward(self, x, edge_index, edge_weight=None):
        """
        Forward pass.
        
        Args:
            x: Node features (num_nodes, input_dim)
            edge_index: Graph connectivity (2, num_edges)
            edge_weight: Edge weights (num_edges,)
            
        Returns:
            Node embeddings (num_nodes, output_dim)
        """
        if not self.use_pyg:
            return self.mlp(x)

        # First GCN layer
        x = self.conv1(x, edge_index, edge_weight)
        x = self.norm1(x)
        x = F.relu(x)
        x = self.dropout(x)

        # Second GCN layer
        x = self.conv2(x, edge_index, edge_weight)
        x = self.norm2(x)

        # Normalize output embeddings
        x = F.normalize(x, dim=-1)
        return x

    def predict_compatibility(self, emb_a: torch.Tensor, emb_b: torch.Tensor) -> torch.Tensor:
        """
        Predict compatibility score between two product embeddings.
        Higher = more compatible.
        """
        return (emb_a * emb_b).sum(dim=-1)  # Cosine similarity


class GNNTrainer:
    """Train the StyleGNN on compatibility data."""

    def __init__(self, model: StyleGNN, device: Optional[str] = None):
        self.model = model
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.optimizer = torch.optim.Adam(model.parameters(), lr=GNN_LEARNING_RATE)

    def train_step(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        pos_pairs: torch.Tensor,
        neg_pairs: torch.Tensor,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> float:
        """
        Single training step.
        
        Args:
            x: Node features
            edge_index: Graph edges
            pos_pairs: (num_pos_pairs, 2) tensor of compatible product pairs
            neg_pairs: (num_neg_pairs, 2) tensor of incompatible product pairs
            edge_weight: Edge weights
            
        Returns:
            Loss value
        """
        self.model.train()
        self.optimizer.zero_grad()

        # Get node embeddings
        embeddings = self.model(x, edge_index, edge_weight)

        # Compute positive pair similarities
        pos_emb_a = embeddings[pos_pairs[:, 0]]
        pos_emb_b = embeddings[pos_pairs[:, 1]]
        pos_scores = self.model.predict_compatibility(pos_emb_a, pos_emb_b)

        # Compute negative pair similarities
        neg_emb_a = embeddings[neg_pairs[:, 0]]
        neg_emb_b = embeddings[neg_pairs[:, 1]]
        neg_scores = self.model.predict_compatibility(neg_emb_a, neg_emb_b)

        # Bayesian Personalized Ranking (BPR) loss
        # Maximize difference between positive and negative scores
        loss = -torch.log(torch.sigmoid(pos_scores - neg_scores) + 1e-8).mean()

        # Add regularization: push positive pairs closer
        pos_dist = (1 - pos_scores).mean()
        loss = loss + 0.1 * pos_dist

        loss.backward()
        self.optimizer.step()

        return loss.item()

    def train(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        pos_pairs: torch.Tensor,
        neg_pairs: torch.Tensor,
        epochs: int = GNN_EPOCHS,
        edge_weight: Optional[torch.Tensor] = None,
    ) -> list:
        """Train the model for multiple epochs."""
        losses = []
        for epoch in range(epochs):
            loss = self.train_step(x, edge_index, pos_pairs, neg_pairs, edge_weight)
            losses.append(loss)
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}/{epochs} — Loss: {loss:.4f}")
        return losses

    def save_model(self, path: str):
        """Save model weights."""
        torch.save(self.model.state_dict(), path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Load model weights."""
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        logger.info(f"Model loaded from {path}")