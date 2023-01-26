# Crafting a meta-environment to simultate inventory managment
# Copyright (C) 2021-2023 Mathïs FEDERICO <https://www.gnu.org/licenses/>
# pylint: disable=arguments-differ, inconsistent-return-statements

""" MineCrafting Environment

Crafting environment adapted to the Minecraft inventory

"""

import os

from crafting.env import CraftingEnv
from crafting.examples.minecraft.transformations import (
    build_minecrafting_transformations,
)
from crafting.examples.minecraft.zones import FOREST


class MineCraftingEnv(CraftingEnv):

    """MineCrafting Environment: A minecraft-like Crafting Environment."""

    def __init__(self, **kwargs):
        # mc_dir = os.path.dirname(__file__)
        # resources_path = os.path.join(mc_dir, "resources")
        mc_transformations = build_minecrafting_transformations()
        start_zone = kwargs.pop("start_zone", FOREST)
        super().__init__(
            mc_transformations,
            name="MineCrafting",
            start_zone=start_zone,
            **kwargs,
        )
        self.metadata["video.frames_per_second"] = kwargs.pop("fps", 10)
