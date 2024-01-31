from matplotlib import pyplot as plt
import pytest
import pytest_check as check


from hcraft.examples import EXAMPLE_ENVS
from hcraft.examples.minecraft import MineHcraftEnv
from hcraft.env import HcraftEnv


@pytest.mark.slow
@pytest.mark.parametrize(
    "env_class", [env_class for env_class in EXAMPLE_ENVS if env_class != MineHcraftEnv]
)
def test_can_solve(env_class):
    env: HcraftEnv = env_class(max_step=50)
    draw_call_graph = False

    done = False
    observation = env.reset()
    for task in env.purpose.best_terminal_group.tasks:
        solving_behavior = env.solving_behavior(task)
        task_done = task.terminated
        while not task_done and not done:
            action = solving_behavior(observation)
            if draw_call_graph:
                _fig, ax = plt.subplots()
                solving_behavior.graph.call_graph.draw(ax)
                plt.show()
            if action == "Impossible":
                raise ValueError("Solving behavior could not find a solution.")
            observation, _reward, done, _ = env.step(action)
            task_done = task.terminated
    check.is_true(env.purpose.terminated)
