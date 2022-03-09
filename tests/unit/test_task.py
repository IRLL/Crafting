# Crafting a gym-environment to simultate inventory managment
# Copyright (C) 2021-2022 Mathïs FEDERICO <https://www.gnu.org/licenses/>
# pylint: disable=no-self-use, attribute-defined-outside-init, protected-access

""" Test of abstract Task classes behavior """

import pytest
import pytest_check as check
from pytest_mock import MockerFixture

import numpy as np

from crafting.task import RewardShaping, Task, TaskList, TaskObtainItem


class DummyWorld:
    """DummyWorld"""

    def __init__(self):
        self.n_items = 7
        self.n_actions = 5


class TestTask:
    """Task"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.world = DummyWorld()
        self.previous_observation = np.ones(10)
        self.observation = 2 * np.ones(10)
        self.action = 2

    def test_init(self):
        """should instanciate correctly."""
        task = Task("task_name", self.world)
        check.equal(task.name, "task_name")
        check.equal(task.world, self.world)

    def test_call(self, mocker: MockerFixture):
        """should call `done` and `reward` on call."""
        mocker.patch("crafting.task.Task.reward", lambda *args: 1)
        mocker.patch("crafting.task.Task.done", lambda *args: True)
        task = Task("task_name", self.world)
        reward, done = task(self.observation, self.previous_observation, self.action)

        check.equal(reward, 1)
        check.is_true(done)


class TestTaskList:
    """TaskList"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup dummy tasks"""
        self.world = DummyWorld()
        self.previous_observation = np.ones(10)
        self.observation = 2 * np.ones(10)
        self.action = 2
        self.task_observe_123 = Task("obs_123", self.world)
        self.task_observe_123.reward = lambda obs, prev_obs, act: 2.1 * np.all(
            obs == 2 * np.ones(10)
        )
        self.task_prev_observe_312 = Task("prev_obs_312", self.world)
        self.task_prev_observe_312.reward = lambda obs, prev_obs, act: 3.4 * np.all(
            prev_obs == np.ones(10)
        )
        self.task_action_observe_213 = Task("action_213", self.world)
        self.task_action_observe_213.reward = lambda obs, prev_obs, act: 4.7 * (
            act == 2
        )
        self.tasks = [
            self.task_observe_123,
            self.task_prev_observe_312,
            self.task_action_observe_213,
        ]

    def test_init(self):
        """should instanciate correctly."""
        TaskList(self.tasks)

    def test_init_raise_not_task(self):
        """should raise TypeError if a task doesn't subclass crafting.Task."""
        tasks = [self.task_observe_123, "task_str"]
        with pytest.raises(TypeError, match=r".*must be.*crafting.Task.*"):
            TaskList(tasks)

    def test_call_none_task(self):
        """should return (0, False) if tasks is None."""
        tasks = TaskList(None)
        reward, done = tasks(self.observation, self.previous_observation, self.action)
        check.equal(reward, 0)
        check.is_false(done)

    def test_call(self, mocker: MockerFixture):
        """should return accumulated rewards and done on call."""
        mocker.patch("crafting.task.TaskList._get_task_weight", lambda *args: 1)
        mocker.patch("crafting.task.TaskList._get_task_can_end", lambda *args: True)
        mocker.patch("crafting.task.TaskList._stacked_dones", lambda *args: True)
        tasks = TaskList(self.tasks)
        reward, done = tasks(self.observation, self.previous_observation, self.action)
        check.equal(reward, 10.2)
        check.is_true(done)


class TestTaskListGetTaskWeight:
    """TaskList._get_task_weight"""

    def setup(self):
        """Setup dummy tasks"""
        self.world = DummyWorld()
        self.task_observe_123 = Task("obs_123", self.world)
        self.task_prev_observe_312 = Task("prev_obs_312", self.world)
        self.task_action_observe_213 = Task("action_213", self.world)
        self.tasks = [
            self.task_observe_123,
            self.task_prev_observe_312,
            self.task_action_observe_213,
        ]

    def test_list(self):
        """should assign weights correctly if tasks_weights is a list."""
        self.tasklist = TaskList(self.tasks)

        expected_tasks_weights = [0.2, 0.1, 5]
        self.tasklist.tasks_weights = expected_tasks_weights

        tasks_weights = [
            self.tasklist._get_task_weight(task, i)
            for i, task in enumerate(self.tasklist.tasks)
        ]

        for value, expected in zip(tasks_weights, expected_tasks_weights):
            check.equal(value, expected)

    def test_dict(self):
        """should assign weights correctly if tasks_weights is a dict."""
        self.tasklist = TaskList(self.tasks)

        expected_tasks_weights = {
            task.name: weight for task, weight in zip(self.tasks, [0.2, 0.1, 5])
        }
        self.tasklist.tasks_weights = expected_tasks_weights

        for i, task in enumerate(self.tasklist.tasks):
            value = self.tasklist._get_task_weight(task, i)
            expected = expected_tasks_weights[task.name]
            check.equal(value, expected)

    def test_none(self):
        """should assign weights of 1 if tasks_weights is None."""
        self.tasklist = TaskList(self.tasks)
        for i, task in enumerate(self.tasklist.tasks):
            value = self.tasklist._get_task_weight(task, i)
            check.equal(value, 1)


class TestTaskListGetTaskCanEnd:
    """TaskList._get_task_can_end"""

    def setup(self):
        """Setup dummy tasks"""
        self.world = DummyWorld()
        self.task_observe_123 = Task("obs_123", self.world)
        self.task_prev_observe_312 = Task("prev_obs_312", self.world)
        self.task_action_observe_213 = Task("action_213", self.world)
        self.tasks = [
            self.task_observe_123,
            self.task_prev_observe_312,
            self.task_action_observe_213,
        ]

    def test_list(self):
        """should assign `can_end` correctly if tasks_can_end is a list."""
        self.tasklist = TaskList(self.tasks)

        expected_tasks_can_end = [True, False, True]
        self.tasklist.tasks_can_end = expected_tasks_can_end

        tasks_weights = [
            self.tasklist._get_task_can_end(task, i)
            for i, task in enumerate(self.tasklist.tasks)
        ]

        for value, expected in zip(tasks_weights, expected_tasks_can_end):
            check.equal(value, expected)

    def test_dict(self):
        """should assign `can_end` correctly if tasks_can_end is a dict."""
        self.tasklist = TaskList(self.tasks)

        expected_tasks_can_end = {
            task.name: can_end for task, can_end in zip(self.tasks, [True, False, True])
        }
        self.tasklist.tasks_can_end = expected_tasks_can_end

        for i, task in enumerate(self.tasklist.tasks):
            value = self.tasklist._get_task_can_end(task, i)
            expected = expected_tasks_can_end[task.name]
            check.equal(value, expected)

    def test_none(self):
        """should assign False to all if tasks_can_end is None."""
        self.tasklist = TaskList(self.tasks)
        for i, task in enumerate(self.tasklist.tasks):
            value = self.tasklist._get_task_can_end(task, i)
            check.is_false(value)


class TestTaskListStackDones:
    """TestList._stack_dones"""

    def test_all(self):
        """should return True only if all dones are True if early_stopping is 'all'."""
        tests = TaskList(None, early_stopping="all")

        done = tests.dones = [True, False, True]
        check.is_false(tests._stacked_dones())

        done = tests.dones = [True, True, True]
        check.is_true(tests._stacked_dones())

    def test_any(self):
        """should return True if any dones is True if early_stopping is 'any'."""
        tests = TaskList(None, early_stopping="any")

        tests.dones = [True, False, True]
        check.is_true(tests._stacked_dones())

        tests.dones = [False, False, False]
        check.is_false(tests._stacked_dones())

    def test_raise_othervalue(self):
        """should raise ValueError if early_stopping is not in ('any', 'all')."""
        tests = TaskList(None, early_stopping="x")
        tests.dones = [True, False, True]
        with pytest.raises(ValueError, match=r"Unknown value for early_stopping.*"):
            tests._stacked_dones()


class TestTaskObtainItem:
    """TaskObtainItem"""

    def test_goal_item(self, mocker: MockerFixture):
        """should have given item as goal_item and ending achivement."""
        init_mocker = mocker.patch("crafting.task.Task.__init__")
        add_achivement_mocker = mocker.patch(
            "crafting.task.Task.add_achivement_getitem"
        )

        class DummyItem:
            item_id = 0

        dummy_item = DummyItem()
        dummy_world = "dummy_world"

        task = TaskObtainItem(world=dummy_world, item=dummy_item)
        init_mocker.assert_called_with(f"obtain_{dummy_item}", dummy_world)
        check.equal(task.goal_item, dummy_item)
        add_achivement_mocker.assert_called_with(dummy_item.item_id, 10, end_task=True)

    def test_reward_shaping_all(self, mocker: MockerFixture):
        """should give achivement value for every world item."""
        mocker.patch("crafting.task.Task.__init__")
        add_achivement_mocker = mocker.patch(
            "crafting.task.Task.add_achivement_getitem"
        )

        class DummyItem:
            def __init__(self, item_id: int) -> None:
                self.item_id = item_id

        dummy_items = [DummyItem(i) for i in range(5)]
        dummy_item = dummy_items[1]

        class DummyWorld:
            items = dummy_items

        dummy_world = DummyWorld()

        shaping_value = 42

        TaskObtainItem(
            world=dummy_world,
            item=dummy_item,
            reward_shaping=RewardShaping.ALL,
            shaping_value=shaping_value,
        )

        is_called = {item.item_id: False for item in dummy_items}
        check.equal(
            add_achivement_mocker.call_args_list[0].args, (dummy_item.item_id, 10)
        )
        check.equal(add_achivement_mocker.call_args_list[0].kwargs, {"end_task": True})

        for call in add_achivement_mocker.call_args_list[1:]:
            is_called[call.args[0]] = True
            check.equal(call.args[1], shaping_value)
        check.is_true(all(is_called.values()))
