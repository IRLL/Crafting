# Crafting a gym-environment to simultate inventory managment
# Copyright (C) 2021 Mathïs FEDERICO <https://www.gnu.org/licenses/>

""" Utilitaries functions for rendering of the Crafting environments """

from __future__ import annotations
from typing import TYPE_CHECKING, Tuple, Union

import os
import numpy as np

import pygame
from pygame.surface import Surface

from PIL import Image, ImageFont, ImageDraw

from crafting.world.zones import Zone
from crafting.world.items import Item
from crafting.world.recipes import Recipe

if TYPE_CHECKING:
    from crafting.world.world import World


def pilImageToSurface(pilImage: Image.Image):
    return pygame.image.fromstring(
        pilImage.tobytes(), pilImage.size, pilImage.mode
    ).convert_alpha()


def load_image(
    world: World,
    obj: Union[Item, Zone, Recipe, str],
    text: str = None,
    text_relative_size: float = 0.3,
    as_array=True,
):
    if obj is None:
        return None

    if isinstance(obj, Item):
        image_path = os.path.join(world.resources_path, "items", f"{obj.item_id}.png")
    elif isinstance(obj, Zone):
        image_path = os.path.join(world.resources_path, "zones", f"{obj.zone_id}.png")
    elif isinstance(obj, str):
        image_path = os.path.join(world.resources_path, "properties", f"{obj}.png")
    elif isinstance(obj, Recipe):
        if obj.outputs is not None:
            return load_image(world, obj.outputs[0], text, text_relative_size, as_array)
        if len(obj.added_properties) > 0:
            prop, _ = obj.added_properties.popitem()
            return load_image(world, prop, text, text_relative_size, as_array)
        raise ValueError(f"Recipe {obj} has no output nor added_properties.")
    else:
        raise TypeError(f"Unkowned type {type(obj)}")

    try:
        image = Image.open(image_path).convert("RGBA")
    except FileNotFoundError:
        if isinstance(obj, Zone):
            image_size = (699, 394)
        else:
            image_size = (120, 120)
        image = Image.new("RGBA", image_size, (0, 255, 0, 0))
        draw = ImageDraw.Draw(image)
        cx, cy = image_size[0] // 2, image_size[1] // 2
        text_pt_size = int(0.26 * image_size[0])
        font = ImageFont.truetype(world.font_path, size=text_pt_size)
        if text is None:
            draw.text((cx, cy), str(obj), fill=(0, 0, 0), font=font, anchor="mm")

    if text is not None:
        image_draw = ImageDraw.Draw(image)
        image_shape = np.array(image).shape

        text_px_size = int(3 * text_relative_size * min(image_shape[:1]))
        text_pt_size = int(0.75 * text_px_size)
        font = ImageFont.truetype(world.font_path, size=text_pt_size)
        font_offset = (int(0.05 * image_shape[0]), int(0.95 * image_shape[1]))
        image_draw.text(font_offset, text, font=font, anchor="lb")

    if as_array:
        image = np.array(image)
    return image


def scale(
    image: Surface,
    canevas_shape: Tuple[int],
    size_ratio: float,
    relative_to: str = "width",
) -> Surface:
    """Load and rescales an image using pygame.

    Load and rescales an image relatively to canevas_shape preserving aspect ratio.

    Args:
        path: Path to the image file.
        canevas_shape: Shape of the canevas where the image will be blited.
        size_ratio: Size (in percent) of the loaded image compared to canevas shape.
        relative_to: One of ('width', 'height'), dimention to consider for size_ratio.

    """
    image_shape = image.get_size()

    if relative_to.startswith("w"):
        scale_ratio = int(size_ratio * canevas_shape[0]) / image_shape[0]
    elif relative_to.startswith("h"):
        scale_ratio = int(size_ratio * canevas_shape[1]) / image_shape[1]
    else:
        raise ValueError(f"Unknowed value for 'relative_to': {relative_to}")

    new_shape = (int(image_shape[0] * scale_ratio), int(image_shape[1] * scale_ratio))
    return pygame.transform.scale(image, new_shape)
