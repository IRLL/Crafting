from typing import List, Set, Tuple, Optional, Union

import numpy as np

from crafting.world import Item, ItemStack, Zone, World
from crafting.transformation import Transformation
from crafting.purpose import Purpose

from crafting.render.render import CraftingWindow
from crafting.render.utils import surface_to_rgb_array


class CraftingEnv:
    """A gym-like environment built from a list of `Transformation`."""

    def __init__(
        self,
        transformations: List[Transformation],
        start_zone: Optional[Zone] = None,
        purpose: Optional[Purpose] = None,
        invalid_reward: float = -10.0,
        render_mode="human",
    ) -> None:
        self.transformations = transformations
        self.start_zone = start_zone
        self.invalid_reward = invalid_reward
        self.world = self._build_world()
        self._build_transformations()

        self.player_inventory = np.array([], dtype=np.uint16)
        self.position = np.array([], dtype=np.uint16)
        self.zones_inventories = np.array([], dtype=np.uint16)
        self._reset_state()

        if purpose is None:
            purpose = Purpose(None)
        if not isinstance(purpose, Purpose):
            purpose = Purpose(tasks=purpose)
        self.purpose = purpose
        self.purpose.build(self.world)

        self.render_mode = render_mode
        self.render_window = None

        self.metadata = {}

    @property
    def state(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Current state of the environment."""
        return self.player_inventory, self.position, self.zones_inventories

    @property
    def observation(self) -> np.ndarray:
        """Observation given to the player."""
        current_zone_slot = self.position.nonzero()[0]
        return np.concatenate(
            (
                self.player_inventory,
                self.position,
                self.zones_inventories[current_zone_slot, :][0],
            )
        )

    @property
    def truncated(self) -> bool:
        """Whether the time limit has been exceeded."""
        return False

    @property
    def terminated(self) -> bool:
        """Whether the environment tasks are all done (if any)"""
        return self.purpose.is_terminal(*self.state)

    def step(self, action: int):
        """Perform one step in the environment given the index of a wanted transformation.

        If the selected transformation can be performed, the state is updated and
        a reward is given depending of the environment tasks.
        Else the state is left unchanged and the `invalid_reward` is given to the player.

        """
        choosen_transformation = self.transformations[action]
        if not choosen_transformation.is_valid(*self.state):
            return self._step_output(self.invalid_reward)
        choosen_transformation.apply(
            self.player_inventory,
            self.position,
            self.zones_inventories,
        )
        reward = self.purpose.reward(*self.state)
        return self._step_output(reward)

    def _step_output(self, reward: float):
        return (self.observation, reward, self.terminated or self.truncated, {})

    def reset(self, seed: int = 0):
        """Resets the state of the environement."""
        self._reset_state()

    def _build_world(self) -> World:
        """Reads the transformation to build the list of items, zones and zones_items
        composing the world."""
        items, zones, zones_items = set(), set(), set()
        for transfo in self.transformations:
            if transfo.destination is not None:
                zones.add(transfo.destination)
            if transfo.zones is not None:
                zones |= set(transfo.zones)
            items = _add_items_to(transfo.removed_player_items, items)
            items = _add_items_to(transfo.added_player_items, items)
            zones_items = _add_items_to(transfo.removed_destination_items, zones_items)
            zones_items = _add_items_to(transfo.added_destination_items, zones_items)
            zones_items = _add_items_to(transfo.removed_zone_items, zones_items)
            zones_items = _add_items_to(transfo.added_zone_items, zones_items)

        return World(list(items), list(zones), list(zones_items))

    def _build_transformations(self):
        for transformation in self.transformations:
            transformation.build(self.world)

    def _reset_state(self) -> None:
        self.player_inventory = np.zeros(self.world.n_items, dtype=np.uint16)

        self.position = np.zeros(self.world.n_zones, dtype=np.uint16)
        start_slot = 0  # Start in first Zone by default
        if self.start_zone is not None:
            start_slot = self.world.slot_from_zone(self.start_zone)
        self.position[start_slot] = 1

        self.zones_inventories = np.zeros(
            (self.world.n_zones, self.world.n_zones_items), dtype=np.uint16
        )

    def render(self, mode: Optional[str] = None, **kwargs) -> Union[str, np.ndarray]:
        """Render the observation of the agent in a format depending on `render_mode`."""
        if mode is not None:
            self.render_mode = mode

        if self.render_mode in ("human", "rgb_array"):  # for human interaction
            return self.render_rgb_array()
        if self.render_mode == "console":  # for console print
            raise NotImplementedError
        raise NotImplementedError

    def render_rgb_array(self) -> np.ndarray:
        """Render an image of the game.

        Create the rendering window if not existing yet.
        """
        if self.render_window is None:
            self.render_window = CraftingWindow(self)
        fps = self.metadata.get("video.frames_per_second")
        self.render_window.update_rendering(fps=fps)
        return surface_to_rgb_array(self.render_window.screen)


def _add_items_to(itemstacks: Optional[List[ItemStack]], items_set: Set[Item]):
    if itemstacks is not None:
        for itemstack in itemstacks:
            items_set.add(itemstack.item)
    return items_set
