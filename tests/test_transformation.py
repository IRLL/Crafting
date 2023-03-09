from dataclasses import dataclass

import numpy as np
import pytest
import pytest_check as check

from crafting.elements import Item, ItemStack, Zone
from crafting.transformation import Transformation, InventoryOwner
from crafting.world import World
from tests.custom_checks import check_np_equal


@dataclass
class DummyState:
    player_inventory: np.ndarray = None
    position: np.ndarray = None
    zones_inventories: np.ndarray = None

    @property
    def current_zone_inventory(self):
        if self.zones_inventories is None or self.position is None:
            return None
        return self.zones_inventories[self.position.nonzero()[0], :]


class TestTransformationIsValid:
    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.zones = [Zone("0"), Zone("1"), Zone("2")]
        self.items = [Item("0"), Item("1"), Item("2")]
        self.zones_items = [Item("0"), Item("z1")]
        self.world = World(self.items, self.zones, self.zones_items, [])

    def test_item_as_input(self):
        def check_stacks(stacks_lists):
            for stacks in stacks_lists:
                for stack in stacks:
                    check.is_instance(stack, ItemStack)

        transfo = Transformation(
            inventory_changes={
                InventoryOwner.PLAYER: {"add": [Item("0")], "remove": [Item("0")]},
                InventoryOwner.CURRENT: {"add": [Item("0")], "remove": [Item("0")]},
                InventoryOwner.DESTINATION: {"add": [Item("0")], "remove": [Item("0")]},
                Zone("0"): {"add": [Item("0")], "remove": [Item("0")]},
            }
        )

        for owner, changes in transfo.inventory_changes.items():
            if owner is InventoryOwner.ZONES:
                for zones_stacks in changes.values():
                    check_stacks(list(zones_stacks.values()))
                continue
            check_stacks(list(changes.values()))

    def test_position_is_valid(self):
        transfo = Transformation(
            destination=self.zones[0], zones=[self.zones[0], self.zones[2]]
        )
        transfo.build(self.world)

        check.is_false(transfo.is_valid(DummyState(position=np.array([1, 0, 0]))))
        check.is_false(transfo.is_valid(DummyState(position=np.array([0, 1, 0]))))
        check.is_true(transfo.is_valid(DummyState(position=np.array([0, 0, 1]))))

    def test_player_items_is_valid(self):
        transfo = Transformation(
            inventory_changes={
                InventoryOwner.PLAYER: {
                    "add": [ItemStack(self.items[1], 5)],
                    "remove": [
                        ItemStack(self.items[0], 2),
                        ItemStack(self.items[2], 3),
                    ],
                },
            }
        )
        transfo.build(self.world)
        position = np.array([1, 0, 0])

        state = DummyState(position=position, player_inventory=np.array([2, 0, 3]))
        check.is_true(transfo.is_valid(state))
        state = DummyState(position=position, player_inventory=np.array([1, 0, 3]))
        check.is_false(transfo.is_valid(state))
        state = DummyState(position=position, player_inventory=np.array([3, 5, 2]))
        check.is_false(transfo.is_valid(state))

    def test_zone_items_is_valid(self):
        transfo = Transformation(
            inventory_changes={
                InventoryOwner.CURRENT: {
                    "remove": [ItemStack(self.zones_items[0], 3)],
                },
            }
        )
        transfo.build(self.world)
        position = np.array([0, 1, 0])

        state = DummyState(
            position=position, zones_inventories=np.array([[0, 0], [3, 0], [0, 0]])
        )
        check.is_true(transfo.is_valid(state))
        state = DummyState(
            position=position, zones_inventories=np.array([[10, 10], [0, 10], [10, 10]])
        )
        check.is_false(transfo.is_valid(state))

    def test_zones_items_is_valid(self):
        transfo = Transformation(
            inventory_changes={
                self.zones[1]: {
                    "remove": [ItemStack(self.zones_items[0], 3)],
                },
            }
        )
        transfo.build(self.world)
        state = DummyState(zones_inventories=np.array([[0, 0], [3, 0], [0, 0]]))
        check.is_true(transfo.is_valid(state))
        state = DummyState(zones_inventories=np.array([[10, 10], [0, 10], [10, 10]]))
        check.is_false(transfo.is_valid(state))

    def test_destination_items_is_valid(self):
        transfo = Transformation(
            destination=self.zones[1],
            inventory_changes={
                "destination": {
                    "remove": [ItemStack(self.zones_items[0], 3)],
                    "add": [ItemStack(self.zones_items[1], 7)],
                },
            },
        )
        transfo.build(self.world)
        position = np.array([1, 0, 0])
        state = DummyState(
            position=position, zones_inventories=np.array([[0, 0], [3, 0], [0, 0]])
        )
        check.is_true(transfo.is_valid(state))
        state = DummyState(
            position=position, zones_inventories=np.array([[10, 10], [0, 10], [10, 10]])
        )
        check.is_false(transfo.is_valid(state))

    def test_destination_op(self):
        transfo = Transformation(destination=self.zones[1])
        transfo.build(self.world)

        expected_op = np.zeros(len(self.zones), dtype=np.int32)
        expected_op[1] = 1
        check_np_equal(transfo._destination, expected_op)

    def test_destination(self):
        transfo = Transformation(destination=self.zones[1])
        transfo.build(self.world)
        position = np.array([1, 0, 0])
        transfo.apply(None, position, None)
        check_np_equal(position, np.array([0, 1, 0]))

    def test_player_items(self):
        transfo = Transformation(
            inventory_changes={
                "player": {
                    "remove": [
                        ItemStack(self.items[0], 2),
                        ItemStack(self.items[2], 3),
                    ],
                    "add": [ItemStack(self.items[1], 5)],
                },
            }
        )
        transfo.build(self.world)
        position = np.array([1, 0, 0])
        inventory = np.array([3, 0, 3])
        transfo.apply(inventory, position, None)
        check_np_equal(inventory, np.array([1, 5, 0]))

    def test_zone_items(self):
        transfo = Transformation(
            inventory_changes={
                "current_zone": {
                    "remove": [ItemStack(self.zones_items[0], 3)],
                    "add": [ItemStack(self.zones_items[1], 7)],
                },
            }
        )
        transfo.build(self.world)
        position = np.array([0, 1, 0])
        zones_inventories = np.array([[3, 1], [4, 2], [5, 3]])
        transfo.apply(None, position, zones_inventories)
        check_np_equal(zones_inventories, np.array([[3, 1], [1, 9], [5, 3]]))

    def test_zones_items(self):
        transfo = Transformation(
            inventory_changes={
                self.zones[0]: {
                    "remove": [
                        ItemStack(self.zones_items[0], 3),
                        ItemStack(self.zones_items[1], 1),
                    ],
                },
                self.zones[2]: {"add": [ItemStack(self.zones_items[1], 7)]},
            }
        )
        transfo.build(self.world)
        position = np.array([0, 1, 0])
        zones_inventories = np.array([[3, 1], [4, 2], [5, 3]])
        transfo.apply(None, position, zones_inventories)
        check_np_equal(zones_inventories, np.array([[0, 0], [4, 2], [5, 10]]))

    def test_destination_items(self):
        transfo = Transformation(
            destination=self.zones[1],
            inventory_changes={
                "destination": {
                    "remove": [ItemStack(self.zones_items[0], 3)],
                    "add": [ItemStack(self.zones_items[1], 7)],
                },
            },
        )
        transfo.build(self.world)
        position = np.array([1, 0, 0])
        zones_inventories = np.array([[3, 1], [4, 2], [5, 3]])
        transfo.apply(None, position, zones_inventories)
        check_np_equal(zones_inventories, np.array([[3, 1], [1, 9], [5, 3]]))

    def test_no_destination(self):
        transfo = Transformation(destination=None)
        transfo.build(self.world)
        check.is_none(transfo._destination)

    def test_zones_requirement(self):
        tranfo = Transformation(zones=[self.zones[0], self.zones[2]])
        tranfo.build(self.world)

        expected_op = np.zeros(len(self.zones), dtype=np.int32)
        expected_op[0] = 1
        expected_op[2] = 1
        check_np_equal(tranfo._zones, expected_op)

    def test_no_zones_requirement(self):
        tranfo = Transformation(zones=None)
        tranfo.build(self.world)
        check.is_none(tranfo._zones)

    def test_str(self):
        tranfo = Transformation(
            inventory_changes={
                "player": {
                    "add": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "> wood[2],stone[3]")

        tranfo = Transformation(
            inventory_changes={
                "player": {
                    "remove": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "wood[2],stone[3] > ")

        tranfo = Transformation(
            inventory_changes={
                "current_zone": {
                    "add": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "> Zone(wood[2],stone[3])")

        tranfo = Transformation(
            inventory_changes={
                "current_zone": {
                    "remove": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "Zone(wood[2],stone[3]) > ")

        tranfo = Transformation(
            inventory_changes={
                "destination": {
                    "add": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "> Dest(wood[2],stone[3])")

        tranfo = Transformation(
            inventory_changes={
                "destination": {
                    "remove": [
                        ItemStack(Item("wood"), 2),
                        ItemStack(Item("stone"), 3),
                    ]
                }
            }
        )
        check_equal_str(str(tranfo), "Dest(wood[2],stone[3]) > ")

        tranfo = Transformation(destination=Zone("other zone"))
        check_equal_str(str(tranfo), "> | other zone")

        tranfo = Transformation(
            inventory_changes={
                "player": {
                    "remove": [
                        ItemStack(Item("P1")),
                        ItemStack(Item("P2")),
                    ],
                    "add": [
                        ItemStack(Item("P3")),
                        ItemStack(Item("P4")),
                    ],
                },
                "current_zone": {
                    "remove": [
                        ItemStack(Item("Z1")),
                        ItemStack(Item("Z2")),
                    ],
                    "add": [
                        ItemStack(Item("Z3")),
                        ItemStack(Item("Z4")),
                    ],
                },
                "destination": {
                    "remove": [
                        ItemStack(Item("D1")),
                        ItemStack(Item("D2")),
                    ],
                    "add": [
                        ItemStack(Item("D3")),
                        ItemStack(Item("D4")),
                    ],
                },
                Zone("A"): {
                    "remove": [
                        ItemStack(Item("A1")),
                        ItemStack(Item("A2")),
                    ],
                    "add": [
                        ItemStack(Item("A3")),
                        ItemStack(Item("A4")),
                    ],
                },
                Zone("B"): {
                    "remove": [
                        ItemStack(Item("B1")),
                        ItemStack(Item("B2")),
                    ],
                    "add": [
                        ItemStack(Item("B3")),
                        ItemStack(Item("B4")),
                    ],
                },
            },
            destination=Zone("D"),
        )
        check_equal_str(
            str(tranfo),
            "P1,P2 Zone(Z1,Z2) Dest(D1,D2) A(A1,A2) B(B1,B2) "
            "> P3,P4 Zone(Z3,Z4) Dest(D3,D4) A(A3,A4) B(B3,B4) | D",
        )


def check_equal_str(actual, expected):
    check.equal(actual, expected, msg=f"\n{expected}\n{actual}")
