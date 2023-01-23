# Crafting a meta-environment to simultate inventory managment
# Copyright (C) 2021-2023 Mathïs FEDERICO <https://www.gnu.org/licenses/>
# pylint: disable=missing-function-docstring, protected-access

from copy import copy
import pytest

from crafting.examples.minecraft.abc import McTool, Block, ItemStack
from crafting.examples.minecraft.abc import McPlayer


@pytest.fixture
def wooden_pickaxe():
    return McTool(270, "wooden_pickaxe", durability=59, speed=2)


@pytest.fixture
def iron_pickaxe():
    return McTool(257, "iron_pickaxe", durability=151, speed=6)


@pytest.fixture
def cobblestone():
    return Block(4, "cobblestone", hardness=2)


@pytest.fixture
def stone(cobblestone, wooden_pickaxe, iron_pickaxe):
    return Block(
        1,
        "stone",
        hardness=1.5,
        drops=[cobblestone],
        required_tools=[wooden_pickaxe, iron_pickaxe],
    )


def test_use(wooden_pickaxe, iron_pickaxe, stone, cobblestone):
    expected_stack_sizes = (2, 5)
    for i, pickaxe in enumerate((wooden_pickaxe, iron_pickaxe)):
        initial_durability = copy(pickaxe._durability)
        findings = pickaxe.use(stone)

        print()
        print(pickaxe)
        print(f"durability: {initial_durability}->{pickaxe._durability}")
        print(findings)

        if len(findings) != 1 or findings[0].item_id != cobblestone.item_id:
            raise ValueError("Unexpected findings item id")

        if findings[0].size != expected_stack_sizes[i]:
            raise ValueError("Unexpected findings size")

        if pickaxe._durability != initial_durability - findings[0].size:
            raise ValueError("Unexpected durability after use")


def test_broken_tool():
    from crafting.examples.minecraft.world import McWorld
    from crafting.examples.minecraft.tools import WOODEN_PICKAXE
    from crafting.examples.minecraft.items import STONE

    player = McPlayer(McWorld())

    WOODEN_PICKAXE._durability = 2
    player.inventory.add_stacks([ItemStack(WOODEN_PICKAXE)])
    print(f"WOODEN_PICKAXE durability: {WOODEN_PICKAXE._durability}")

    n_items_found = player.search_for(STONE, WOODEN_PICKAXE)
    if n_items_found == 0:
        raise ValueError("Pickaxe should have found items")

    print(f"WOODEN_PICKAXE durability: {WOODEN_PICKAXE._durability}")
    if WOODEN_PICKAXE.is_broken:
        raise ValueError("Pickaxe is not supposed to be broken yet")

    n_items_found = player.search_for(STONE, WOODEN_PICKAXE)
    if n_items_found == 0:
        raise ValueError("Pickaxe should have found items")

    slot = player.inventory.item_id_to_slot(WOODEN_PICKAXE.item_id)
    print(f"WOODEN_PICKAXE durability: {WOODEN_PICKAXE._durability}")
    if player.inventory.content[slot] > 0:
        raise ValueError("Pickaxe supposed to be removed from inventory")
