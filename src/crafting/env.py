"""# Crafting Environment builder


"""

import collections
import os
from typing import List, Dict, Optional, Union

import numpy as np

import crafting
from crafting.solving_behaviors import (
    Behavior,
    build_all_solving_behaviors,
    task_to_behavior_name,
)
from crafting.purpose import Purpose, TerminalGroup
from crafting.task import Task
from crafting.render.render import CraftingWindow
from crafting.render.utils import surface_to_rgb_array
from crafting.requirements import Requirements
from crafting.world import World
from crafting.state import CraftingState

# Gym is an optional dependency.
try:
    import gym

    DiscreteSpace = gym.spaces.Discrete
    BoxSpace = gym.spaces.Box
    TupleSpace = gym.spaces.Tuple
    MultiBinarySpace = gym.spaces.MultiBinary
    Env = gym.Env
except ImportError:
    DiscreteSpace = collections.namedtuple("DiscreteSpace", "n")
    BoxSpace = collections.namedtuple("BoxSpace", "low, high, shape, dtype")
    TupleSpace = collections.namedtuple("TupleSpace", "spaces")
    MultiBinarySpace = collections.namedtuple("MultiBinary", "n")
    Env = object


class CraftingEnv(Env):
    """A gym-like environment to simulate inventory management."""

    def __init__(
        self,
        world: World,
        purpose: Optional[Union[Purpose, List[Task], Task]] = None,
        invalid_reward: float = -10.0,
        render_window: Optional[CraftingWindow] = None,
        resources_path: Optional[str] = None,
        name: str = "Crafting",
        max_step: Optional[int] = None,
    ) -> None:
        """
        Args:
            world: World defining the environment.
            purpose: Purpose of the player, defining rewards and termination.
                Defaults to None, hence a sandbox environment.
            invalid_reward: Reward given to the agent for invalid actions.
                Defaults to -10.0.
            render_window: Window using to render the environment with pygame.
            name: Name of the environement. Defaults to 'Crafting'.
            max_step: (Optional[int], optional): Maximum number of steps before episode truncation.
                If None, never truncates the episode. Defaults to None.
        """
        self.world = world
        self.invalid_reward = invalid_reward
        self.max_step = max_step
        self.name = name
        self._requirements = None
        self._all_behaviors = None

        self.render_window = render_window
        self.render_mode = "rgb_array"
        if resources_path is None:
            resources_path = _default_resources_path()
        self.resources_path = resources_path

        self.state = CraftingState(self.world)
        self.current_step = 0
        self.current_score = 0
        self.cumulated_score = 0
        self.episodes = 0
        self.task_successes = {}
        self.terminal_successes = {}

        if purpose is None:
            purpose = Purpose(None)
        if not isinstance(purpose, Purpose):
            purpose = Purpose(tasks=purpose)
        self.purpose = purpose
        self.metadata = {}

    @property
    def truncated(self) -> bool:
        """Whether the time limit has been exceeded."""
        if self.max_step is None:
            return False
        return self.current_step >= self.max_step

    @property
    def terminated(self) -> bool:
        """Whether the environment tasks are all done (if any)"""
        return self.purpose.is_terminal(self.state)

    @property
    def observation_space(self) -> Union[BoxSpace, TupleSpace]:
        """Observation space for the Agent in the Crafting environment."""
        obs_space = BoxSpace(
            low=np.array(
                [0 for _ in range(self.world.n_items)]
                + [0 for _ in range(self.world.n_zones)]
                + [0 for _ in range(self.world.n_zones_items)]
            ),
            high=np.array(
                [np.inf for _ in range(self.world.n_items)]
                + [1 for _ in range(self.world.n_zones)]
                + [np.inf for _ in range(self.world.n_zones_items)]
            ),
        )

        return obs_space

    @property
    def action_space(self) -> DiscreteSpace:
        """Action space for the Agent in the Crafting environment.

        Actions are expected to often be invalid.
        """
        return DiscreteSpace(len(self.world.transformations))

    @property
    def actions_mask(self) -> np.ndarray:
        """Boolean mask of valid actions."""
        return np.array([t.is_valid(self.state) for t in self.world.transformations])

    def step(self, action: int):
        """Perform one step in the environment given the index of a wanted transformation.

        If the selected transformation can be performed, the state is updated and
        a reward is given depending of the environment tasks.
        Else the state is left unchanged and the `invalid_reward` is given to the player.

        """
        self.current_step += 1

        tasks_states = {task: task.terminated for task in self.purpose.tasks}
        terminal_groups_states = {
            group: group.terminated for group in self.purpose.terminal_groups
        }
        success = self.state.apply(action)
        if success:
            reward = self.purpose.reward(self.state)
        else:
            reward = self.invalid_reward

        for task in self.purpose.tasks:
            # Just terminated
            if task.terminated != tasks_states[task]:
                self.task_successes[task] += 1
        for terminal_group in self.purpose.terminal_groups:
            # Just terminated
            if terminal_group.terminated != terminal_groups_states[terminal_group]:
                self.terminal_successes[terminal_group] += 1

        self.current_score += reward
        self.cumulated_score += reward
        return self._step_output(reward)

    def render(self, mode: Optional[str] = None, **_kwargs) -> Union[str, np.ndarray]:
        """Render the observation of the agent in a format depending on `render_mode`."""
        if mode is not None:
            self.render_mode = mode

        if self.render_mode in ("human", "rgb_array"):  # for human interaction
            return self._render_rgb_array()
        if self.render_mode == "console":  # for console print
            raise NotImplementedError
        raise NotImplementedError

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> np.ndarray:
        """Resets the state of the environement.

        Returns:
            (np.ndarray): The first observation.
        """
        if not self.purpose.built:
            self.purpose.build(self)
            self.task_successes = {task: 0 for task in self.purpose.tasks}
            self.terminal_successes = {
                group: 0 for group in self.purpose.terminal_groups
            }
        self.current_step = 0
        self.current_score = 0
        self.episodes += 1
        self.state.reset()
        self.purpose.reset()
        return self.state.observation

    def close(self):
        """Closes the environment."""
        if self.render_window is not None:
            self.render_window.close()

    @property
    def all_behaviors(self) -> Dict[str, "Behavior"]:
        """All solving behaviors using hebg."""
        if self._all_behaviors is None:
            self._all_behaviors = build_all_solving_behaviors(self)
        return self._all_behaviors

    def solving_behavior(self, task: "Task") -> "Behavior":
        """Get the solving behavior for a given task.

        Args:
            task: Task to solve.

        Returns:
            Behavior: Behavior solving the task.
        """
        return self.all_behaviors[task_to_behavior_name(task)]

    @property
    def requirements(self) -> Requirements:
        if self._requirements is None:
            self._requirements = Requirements(self.world, self.resources_path)
        return self._requirements

    def _step_output(self, reward: float):
        infos = {
            "action_is_legal": self.actions_mask,
            "score": self.current_score,
            "score_average": self.cumulated_score / self.episodes,
        }
        infos.update(self._tasks_infos())
        return (
            self.state.observation,
            reward,
            self.terminated or self.truncated,
            infos,
        )

    def _tasks_infos(self):
        def _is_done_str(group: TerminalGroup):
            if len(self.purpose.terminal_groups) == 1:
                return "Purpose is done"
            return f"Terminal group '{group.name}' is done"

        def _rate_str(group: TerminalGroup):
            if len(self.purpose.terminal_groups) == 1:
                return "Purpose success rate"
            return f"Terminal group '{group.name}' success rate"

        tasks_are_done = {
            f"{task.name} is done": task.terminated for task in self.purpose.tasks
        }
        tasks_rates = {
            f"{task.name} success rate": self.task_successes[task] / self.episodes
            for task in self.purpose.tasks
        }
        terminal_done = {
            _is_done_str(group): group.terminated
            for group in self.purpose.terminal_groups
        }
        terminal_rates = {
            _rate_str(group): self.terminal_successes[group] / self.episodes
            for group in self.purpose.terminal_groups
        }

        infos = {}
        infos.update(tasks_are_done)
        infos.update(tasks_rates)
        infos.update(terminal_done)
        infos.update(terminal_rates)
        return infos

    def _render_rgb_array(self) -> np.ndarray:
        """Render an image of the game.

        Create the rendering window if not existing yet.
        """
        if self.render_window is None:
            self.render_window = CraftingWindow()
        if not self.render_window.built:
            self.render_window.build(self)
        fps = self.metadata.get("video.frames_per_second")
        self.render_window.update_rendering(fps=fps)
        return surface_to_rgb_array(self.render_window.screen)


def _default_resources_path() -> str:
    render_dir = os.path.dirname(crafting.render.__file__)
    return os.path.join(render_dir, "default_resources")
