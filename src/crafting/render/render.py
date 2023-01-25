# Crafting a meta-environment to simultate inventory managment
# Copyright (C) 2021-2023 Mathïs FEDERICO <https://www.gnu.org/licenses/>
# pylint: disable=no-member

""" Rendering of the Crafting environments """

import os
import sys
from io import BytesIO
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, Tuple

import numpy as np


try:
    import pygame
    from pygame import Surface
    from pygame.time import Clock
    from pygame_menu.baseimage import BaseImage
    from pygame_menu.menu import Menu
    from pygame_menu.themes import THEME_BLUE, THEME_GREEN, THEME_ORANGE
    from pygame_menu.widgets import Button
except ImportError:
    pass

from crafting.render.utils import load_or_create_image, surface_to_rgb_array


if TYPE_CHECKING:
    from PIL.Image import Image
    from pygame.event import Event

    from crafting.env import CraftingEnv
    from crafting.world import World
    from crafting.transformation import Transformation


class CraftingWindow:
    def __init__(self, env: "CraftingEnv") -> None:
        """Initialise pygame window, menus and widgets for the UI.

        Args:
            env: The running Crafting environment.
        """
        try:
            pygame.init()
        except NameError as error:
            raise ImportError(
                "Missing import for rendering user interface. "
                "Install using 'pip install crafting-gym[gui]'."
            ) from error

        self.env = env
        self.window_shape = (int(16 / 9 * 600), 720)
        os.environ["SDL_VIDEO_CENTERED"] = "1"
        self.clock = Clock()

        # Create window
        self.screen = pygame.display.set_mode(self.window_shape)
        pygame.display.set_caption("Crafting")

        # Create menus
        self.menus = self.make_menus()

    def update_rendering(
        self,
        additional_events: Optional[List["Event"]] = None,
        fps: Optional[float] = None,
    ) -> Union[int, None]:
        """Update the User Interface returning action if one was found.

        Args:
            additional_events (Optional): Additional pygame events to simulate.
            fps: frames_per_seconds

        Returns:
            Action found while updating the UI. (can be None)

        """
        # Tick
        if fps is not None:
            self.clock.tick(fps)

        # Paint background
        self.screen.fill((198, 198, 198))

        # Execute main from principal menu if is enabled
        events = pygame.event.get()
        if additional_events is not None:
            events += additional_events
        for event in events:
            if event.type == pygame.QUIT:
                sys.exit()

        # for widget in widgets:
        #     widget.update(env)
        #     widget.draw(screen)

        action_taken = None
        # action_is_legal = env.action_masks()

        for menu in self.menus:
            buttons = [
                widget for widget in menu.get_widgets() if isinstance(widget, Button)
            ]
            for button in buttons:
                action = self.button_id_to_action[button.get_id()]
                # show_button = action_is_legal[action_id]
                show_button = True
                if show_button:
                    button.show()
                else:
                    button.hide()

            menu.update(events)
            menu.draw(self.screen)

            selected_widget = menu.get_selected_widget()
            if selected_widget is not None and selected_widget.update(events):
                action_taken = selected_widget.apply()

        # Update surface
        pygame.display.update()
        return action_taken

    def make_menus(self):
        """Build menus for user interface.

        Args:
            world: The current world.
            window_shape: Shape of the window containing menus.

        """

        self.button_id_to_action = {}

        # Transformations Menu
        transformations_menu_width = int(0.4 * self.window_shape[0])
        transformations_menu_height = self.window_shape[1]

        transformations_menu = Menu(
            title="Transformations",
            center_content=True,
            height=transformations_menu_height,
            width=transformations_menu_width,
            keyboard_enabled=True,
            joystick_enabled=False,
            rows=len(self.env.transformations),
            columns=1,
            position=(0, 0),
            overflow=(False, True),
        )

        for action, transfo in enumerate(self.env.transformations):
            button_id = _add_button_to_menu(
                transformations_menu,
                text=str(transfo),
                text_width=8,
                index=action,
                padding=(16, 0, 16, 0),
            )
            self.button_id_to_action[button_id] = action

        return (transformations_menu,)


def _add_button_to_menu(
    menu: "Menu",
    text_width: int,
    index: int,
    padding,
    image: Optional["Image"] = None,
    text: Optional[str] = None,
):
    if text is None:
        text = " " * text_width
    button = menu.add.button(
        text,
        lambda x: x,
        index,
        padding=padding,
        font_size=16,
    )
    if image is not None:
        decorator = button.get_decorator()
        decorator.add_baseimage(0, 0, image, centered=True)
    return button.get_id()


def _scale_image(image: "Image", scaling: float) -> BaseImage:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    buffered.seek(0)
    return BaseImage(buffered).scale(scaling, scaling)


def get_human_action(
    env: "CraftingEnv",
    additional_events: List["Event"] = None,
    can_be_none: bool = False,
    fps: Optional[float] = None,
):
    """Update the environment rendering and gather potential action given by the UI.

    Args:
        env: The running Crafting environment.
        additional_events (Optional): Additional simulated pygame events.
        can_be_none: If False, this function will loop on rendering until an action is found.
            If True, will return None if no action was found after one rendering update.

    Returns:
        The action found using the UI.

    """
    action_chosen = False
    while not action_chosen:
        action = env.render_window.update_rendering(additional_events, fps)
        action_chosen = action is not None or can_be_none
    return action


def render_env_with_human(env: "CraftingEnv", n_episodes: int = 1):
    """Render the given environment with human iteractions.

    Args:
        env (CraftingEnv): The Crafting environment to run.
        n_episodes (int, optional): Number of episodes to run. Defaults to 1.
    """
    print("Purpose: ", env.purpose)

    for _ in range(n_episodes):
        env.reset()
        done = False
        total_reward = 0
        while not done:
            env.render()
            action = get_human_action(env)
            print(f"Human did: {env.transformations[action]}")

            _observation, reward, done, _info = env.step(action)
            total_reward += reward

        print("SCORE: ", total_reward)
