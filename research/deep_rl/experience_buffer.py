import random
import pickle
import os
from typing import List, Tuple, Any, Dict

class ExperienceBuffer:
    def __init__(self, capacity: int = 100000):
        """
        Initializes the experience buffer with a given maximum capacity.
        Suitable for DQN Replay Memory and PPO Rollout buffers.
        """
        self.capacity = capacity
        self.buffer: List[Tuple[Any, Any, float, Any, bool]] = []
        self.position = 0

    def push(self, state: Any, action: Any, reward: float, next_state: Any, done: bool):
        """
        Saves a transition experience (s, a, r, s', done).
        Operates as a circular queue when maximum capacity is reached.
        """
        transition = (state, action, reward, next_state, done)
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition
            self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Tuple[Any, Any, float, Any, bool]]:
        """
        Randomly samples a batch of transitions.
        """
        return random.sample(self.buffer, min(len(self.buffer), batch_size))

    def clear(self):
        """
        Clears the buffer. Required for PPO rollout buffers after policy updates.
        """
        self.buffer = []
        self.position = 0

    def save(self, filepath: str):
        """
        Serializes and saves the current buffer state to a file.
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "buffer": self.buffer,
                "position": self.position,
                "capacity": self.capacity
            }, f)

    def load(self, filepath: str):
        """
        Loads the buffer state from a saved file.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No buffer file found at {filepath}")
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            self.buffer = data.get("buffer", [])
            self.position = data.get("position", 0)
            self.capacity = data.get("capacity", 100000)

    def __len__(self) -> int:
        return len(self.buffer)
