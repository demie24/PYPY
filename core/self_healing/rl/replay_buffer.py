import random
import numpy as np
from collections import deque
from typing import Dict, Any, List, Tuple

class ReplayBuffer:
    """
    Experience Replay Buffer for DQN training.
    Supports fixed capacity and random uniform sampling.
    """
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)
        
    def push(self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool):
        self.buffer.append((state, action, reward, next_state, done))
        
    def sample(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        transitions = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*transitions)
        
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32)
        )
        
    def __len__(self) -> int:
        return len(self.buffer)


class PPOMemory:
    """
    Trajectory memory storage for PPO batch training.
    """
    def __init__(self):
        self.states: List[np.ndarray] = []
        self.actions: List[int] = []
        self.probs: List[float] = []
        self.vals: List[float] = []
        self.rewards: List[float] = []
        self.dones: List[bool] = []

    def push(self, state: np.ndarray, action: int, prob: float, val: float, reward: float, done: bool):
        self.states.append(state)
        self.actions.append(action)
        self.probs.append(prob)
        self.vals.append(val)
        self.rewards.append(reward)
        self.dones.append(done)

    def sample(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # Return complete trajectory as numpy arrays
        return (
            np.array(self.states, dtype=np.float32),
            np.array(self.actions, dtype=np.int64),
            np.array(self.probs, dtype=np.float32),
            np.array(self.vals, dtype=np.float32),
            np.array(self.rewards, dtype=np.float32),
            np.array(self.dones, dtype=np.float32)
        )

    def clear(self):
        self.states.clear()
        self.actions.clear()
        self.probs.clear()
        self.vals.clear()
        self.rewards.clear()
        self.dones.clear()
        
    def __len__(self) -> int:
        return len(self.states)
