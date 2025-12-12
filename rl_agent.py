import random
import math

class RLLightAgent:
    def __init__(self, actions):
        self.actions = actions  # ["stay", "switch"]
        self.Q = {}             # Q-table: Q[state][action]
        self.alpha = 0.1        # learning rate
        self.gamma = 0.9        # discount factor
        self.epsilon = 0.05      # exploration chance

    def get_Q(self, state):
        if state not in self.Q:
            self.Q[state] = {a: 0.0 for a in self.actions}
        return self.Q[state]

    def choose_action(self, state):
        # Explore
        if random.random() < self.epsilon:
            return random.choice(self.actions)

        # Exploit
        q_vals = self.get_Q(state)
        return max(q_vals, key=q_vals.get)

    def update(self, state, action, reward, next_state):
        q_vals = self.get_Q(state)
        next_q_vals = self.get_Q(next_state)

        best_next = max(next_q_vals.values())
        old_q = q_vals[action]

        # Q-learning formula:
        q_vals[action] = old_q + self.alpha * (reward + self.gamma * best_next - old_q)