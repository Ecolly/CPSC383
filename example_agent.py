from typing import override

from aegis import (
    CONNECT_OK,
    END_TURN,
    SEND_MESSAGE_RESULT,
    MOVE,
    MOVE_RESULT,
    OBSERVE_RESULT,
    PREDICT_RESULT,
    SAVE_SURV,
    SAVE_SURV_RESULT,
    SEND_MESSAGE,
    SLEEP_RESULT,
    TEAM_DIG,
    TEAM_DIG_RESULT,
    AgentCommand,
    AgentIDList,
    Direction,
    Rubble,
    SurroundInfo,
    Survivor,
)

from agent import BaseAgent, Brain, LogLevels
from typing import TypeVar, List, Tuple
import heapq

T = TypeVar('T')

#The a_star algorithm was taken from Assignment 1 by Yufei Zhang

class PriorityQueue:
    def __init__(self):
        self.elements: list[tuple[float, int, T]] = []
        self._counter = 0  # Tie-breaker counter

    def empty(self) -> bool:
        return not self.elements

    def put(self, item: T, priority: float):
        # Use the counter as a tie-breaker
        heapq.heappush(self.elements, (priority, self._counter, item))
        self._counter += 1

    def get(self) -> T:
        return heapq.heappop(self.elements)[2]  # Return the item (third element)


class ExampleAgent(Brain):
    def __init__(self) -> None:
        super().__init__()
        self._agent: BaseAgent = BaseAgent.get_base_agent()
        self._agent = BaseAgent.get_base_agent()
        # self.frontier = PriorityQueue()
        # self.came_from = dict()
        # self.cost_from_start = dict()
        self.path = None  # the path that will be taken
        self.current = None  # current
        self.survivor_location = None  # survivors location
        self.survivor_cell = None

    @override
    def handle_connect_ok(self, connect_ok: CONNECT_OK) -> None:
        BaseAgent.log(LogLevels.Always, "CONNECT_OK")

    @override
    def handle_disconnect(self) -> None:
        BaseAgent.log(LogLevels.Always, "DISCONNECT")

    @override
    def handle_dead(self) -> None:
        BaseAgent.log(LogLevels.Always, "DEAD")

    # Call back functions that handle the outcome of actions
    # smr is the result of the SEND_MESSAGE action may have error codes and status of the message
    @override
    def handle_send_message_result(self, smr: SEND_MESSAGE_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"SEND_MESSAGE_RESULT: {smr}")
        BaseAgent.log(LogLevels.Test, f"{smr}")
        print("#--- You need to implement handle_send_message_result function! ---#")

    # When the agent attempts to move in a direction, and receive the result of that movement
    # Did the agent successfully move to the intended cell
    # How much was used during the move
    @override
    def handle_move_result(self, mr: MOVE_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"MOVE_RESULT: {mr}")
        BaseAgent.log(LogLevels.Test, f"{mr}")
        # after issuing MOVE command, simulation determines if the move is valid
        # generates a MOVE_RESULT object mr
        print("#--- You need to implement handle_move_result function! ---#")
        self.update_surround(mr.surround_info)

    # Contain information about agent observations
    @override
    def handle_observe_result(self, ovr: OBSERVE_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"OBSERVER_RESULT: {ovr}")
        BaseAgent.log(LogLevels.Test, f"{ovr}")

        print("#--- You need to implement handle_observe_result function! ---#")

    # Details about the result of attempting to save a survivor
    @override
    def handle_save_surv_result(self, ssr: SAVE_SURV_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"SAVE_SURV_RESULT: {ssr}")
        BaseAgent.log(LogLevels.Test, f"{ssr}")

        print("#--- You need to implement handle_save_surv_result function! ---#")

    # prd, the instance of PREDICT_RESULT, details of predication
    @override
    def handle_predict_result(self, prd: PREDICT_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"PREDICT_RESULT: {prd}")
        BaseAgent.log(LogLevels.Test, f"{prd}")

    # Gets the result of the agent's attempt to rest or recover

    @override
    def handle_sleep_result(self, sr: SLEEP_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"SLEEP_RESULT: {sr}")
        BaseAgent.log(LogLevels.Test, f"{sr}")
        print("#--- You need to implement handle_sleep_result function! ---#")

    # Information about the result of a cooperative rubble clearing action
    @override
    def handle_team_dig_result(self, tdr: TEAM_DIG_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"TEAM_DIG_RESULT: {tdr}")
        BaseAgent.log(LogLevels.Test, f"{tdr}")

        # get energy level after the dig action
        energy_level = tdr.energy_level
        BaseAgent.log(LogLevels.Test, f"Agent's energy level after dig: {energy_level}")

        # get surround info
        surround_info = tdr.surround_info
        if surround_info is None:
            return

        # Check the current cell info
        current_cell = surround_info.get_current_info()
        if current_cell is None:
            return

        # Check the top layer to see if rubble was removed
        top_layer = current_cell.top_layer
        if top_layer is None:
            BaseAgent.log(LogLevels.Always, "Rubble cleared.")
        elif isinstance(top_layer, Survivor):
            BaseAgent.log(LogLevels.Always, "Rubble cleared, found a survivor!")
            # Save survivor if found
            self.send_and_end_turn(SAVE_SURV())
        else:
            BaseAgent.log(LogLevels.Always, f"Rubble cleared, updated top layer: {top_layer}")

        print("#--- You need to implement handle_team_dig_result function! ---#")

    ################################################################
    def get_direction_to_move(self, current_x, current_y, target_x, target_y):
        # Determine horizontal direction
        if target_x > current_x:
            horizontal = Direction.EAST
        elif target_x < current_x:
            horizontal = Direction.WEST
        else:
            horizontal = None  # No horizontal movement needed

        if target_y > current_y:
            vertical = Direction.NORTH
        elif target_y < current_y:
            vertical = Direction.SOUTH
        else:
            vertical = None

        # Return direction or combination of directions
        if horizontal and vertical:
            # Move diagonally
            if horizontal == Direction.EAST and vertical == Direction.NORTH:
                return Direction.NORTH_EAST
            elif horizontal == Direction.EAST and vertical == Direction.SOUTH:
                return Direction.SOUTH_EAST
            elif horizontal == Direction.WEST and vertical == Direction.NORTH:
                return Direction.NORTH_WEST
            elif horizontal == Direction.WEST and vertical == Direction.SOUTH:
                return Direction.SOUTH_WEST
        elif horizontal:
            return horizontal
        elif vertical:
            return vertical
        else:
            return Direction.CENTER  # Already at target

    def a_star(self, current_cell, goal_cell):
        # Get hte world
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        #### QUEUE###
        frontier = PriorityQueue()
        came_from = dict()
        cost_from_start = dict()

        frontier.put(current_cell, 0)
        came_from[current_cell] = None
        cost_from_start[current_cell] = 0
        # agent_location = self._agent.get_location()

        while not frontier.empty():
            # Get the top layer at the agent’s current location.
            # If a survivor is present, save it and end the turn.
            if current_cell == goal_cell:
                break
            current_cell = frontier.get()
            for dir in Direction:
                # for each neighbour of the current grid that is being evaluated
                neighbor = world.get_cell_at(current_cell.location.add(dir))
                if neighbor is None:
                    continue
                if neighbor.is_normal_cell():
                    # if the neighbor didn't come from anywhere yet
                    move_cost = neighbor.move_cost if neighbor.move_cost is not None else 1
                    new_cost = cost_from_start[current_cell] + move_cost  # add the cost to move to neighbor cost
                    # the total cost of reaching the next node through the current node
                    if neighbor not in cost_from_start or new_cost < cost_from_start[
                        neighbor]:  # see if this has been visited before
                        # if the path hasn't been visited, add to frontier
                        # if this new path to this neighbor node
                        cost_from_start[neighbor] = new_cost
                        weight = new_cost + self.heuristics(neighbor, goal_cell)
                        frontier.put(neighbor, weight)  # that means it was on the front line and need to be added
                        came_from[neighbor] = current_cell  # link it to the grid that it came from
        return came_from, cost_from_start
        #came from is  dictionary that maps each node to the node it reached
        #cost_from_start gets the cost to reach every visited node from the start node


    def reconstruct_path(self, came_from, start, goal) -> list:
        current = goal
        path = [current.location]
        if goal not in came_from:  # no path was found
            return []
        while current != start:
            path.append(current.location)
            # print(f"current location: ({current.location.x}, {current.location.y})")
            current = came_from[current]
        path.reverse()
        # print("PATH" + str(path))
        return path

    def survivors_list(self, grid):
        surv_list = []
        for row in grid:
            for cell in row:
                if cell.survivor_chance != 0:
                    surv_list.append(cell)
        return surv_list

    def heuristics(self, a, b):
        return max(abs(a.location.x - b.x), abs(a.location.y - b.y))

    @override
    def think(self) -> None:
        BaseAgent.log(LogLevels.Always, "Thinking")

        #LEADER CODE (agent with id of 1 will be assigned)
    #if (self._agent.get_agent_id==1):
            #Calculates the path of each agent to each survivor
            
            
            
        # Send a message to other agents in my group.
        # Empty AgentIDList will send to group members.
        self._agent.send(
            SEND_MESSAGE(
                AgentIDList(), f"Hello from agent {self._agent.get_agent_id().id}"            
            )
        )
        
        
            
        
        # Retrieve the current state of the world.
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        current_grid = world.get_cell_at(self._agent.get_location())

        surv_list = self.survivors_list(world.get_world_grid())

        # From list of survivors, checks the least cost
        cost_list = []
        target_cell = current_grid
        if surv_list:
            for cell in surv_list:
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, cell.location)
                cost_list.append(returned_cost_from_start[cell])
            lowest_cost = min(cost_list)
            target_cell_index = cost_list.index(lowest_cost)
            target_cell = surv_list[target_cell_index]
        else:
            # There are no more survivors left, do nothing
            self.send_and_end_turn(MOVE(Direction.CENTER))

        self.survivor_location = target_cell.location

        # Fetch the cell at the agent’s current location. If the location is outside the world’s bounds,
        # return a default move action and end the turn.
        cell = world.get_cell_at(self._agent.get_location())

        self.survivor_cell = world.get_cell_at(self.survivor_location)

        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        grid = world.get_cell_at(self._agent.get_location())
        if grid is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        if cell is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        # Get the top layer at the agent’s current location.
        top_layer = cell.get_top_layer()

        # If rubble is present, clear it and end the turn.
        if isinstance(top_layer, Rubble):
            self.send_and_end_turn(TEAM_DIG())
            return

        # If a survivor is present, save them and end the turn.
        if isinstance(top_layer, Survivor):
            self.survivor_cell.set_top_layer(None)
            self.survivor_cell.survivor_chance = 0  # this should only be applied if all layers are checked
            self.send_and_end_turn(SAVE_SURV())

            return

        current_grid = world.get_cell_at(self._agent.get_location())
        # print(str(current_grid.location.x)+str (current_grid.location.y))

        returned_came_from, returned_cost_from_start = self.a_star(current_grid, self.survivor_location)
        self.path = self.reconstruct_path(returned_came_from, current_grid, self.survivor_cell)

        # Follow the next step in the path, if available.
        if self.path and len(self.path) > 0:
            next_location = self.path.pop(0)  # Get the next step in the path and remove it from the list
            agent_location = self._agent.get_location()
            direction = self.get_direction_to_move(agent_location.x, agent_location.y,
                                                   next_location.x, next_location.y)
            self.send_and_end_turn(MOVE(direction))  # Send the move command for the calculated direction
            return
        else:
            # Default action: Stay in place if no path is available or path is empty
            self.send_and_end_turn(MOVE(Direction.CENTER))

        # Default action: Move the agent north if no other specific conditions are met.
        self.send_and_end_turn(MOVE(Direction.NORTH))

    def send_and_end_turn(self, command: AgentCommand):
        """Send a command and end your turn."""
        BaseAgent.log(LogLevels.Always, f"SENDING {command}")
        self._agent.send(command)
        self._agent.send(END_TURN())

    def update_surround(self, surround_info: SurroundInfo):
        """
        Updates the current and surrounding cells of the agent.

        You can check assignment 1 to figure out how to use this function.
        """
        world = self.get_world()
        if world is None:
            return

        for dir in Direction:
            cell_info = surround_info.get_surround_info(dir)
            if cell_info is None:
                continue

            cell = world.get_cell_at(cell_info.location)
            if cell is None:
                continue

            cell.move_cost = cell_info.move_cost
            cell.set_top_layer(cell_info.top_layer)