from typing import override
import heapq

from aegis.common import Direction
from aegis.common.commands.aegis_commands import MOVE_RESULT, SAVE_SURV_RESULT
from aegis.common.commands.agent_command import AgentCommand
from aegis.common.commands.agent_commands import (
    END_TURN,
    MOVE,
    SAVE_SURV,
)
from aegis.common.world.grid import Grid
from aegis.common.world.info import SurroundInfo, SurvivorInfo, WorldObjectInfo
from aegis.common.world.objects import Survivor
from agent.base_agent import BaseAgent
from agent.brain import Brain
from agent.log_levels import LogLevels

from typing import TypeVar, List, Tuple
T = TypeVar('T')

################
#Reference: https://theory.stanford.edu/~amitp/GameProgramming/ImplementationNotes.html
################
#Name: Yufei Zhang
#Date October 7th
#Course: CPSC 383
#Semester: Fall 2024
#Tutorial: T01/02
##################



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
        self._agent = BaseAgent.get_base_agent()
        # self.frontier = PriorityQueue()
        # self.came_from = dict()
        # self.cost_from_start = dict()
        self.path = None #the path that will be taken
        self.current = None #current
        self.survivor_location = None #survivors location
        self.survivor_grid = None
        
        
    def locate_survivor(self, grid_2D):
        for grid_list in grid_2D:
            for grid in grid_list:
                if grid.percent_chance != 0: 
                    return grid.location
        return None
    
    # def heuristics (self,a,b):
    #     return abs(a.location.x-b.x)+abs(a.location.y-b.y)
    def heuristics (self,a,b):
        return max(abs(a.location.x-b.x),abs(a.location.y-b.y))
    def a_star(self, current_grid, goal):
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        #### QUEUE###
        frontier = PriorityQueue()
        came_from = dict()
        cost_from_start = dict()
        
        frontier.put(current_grid, 0)
        came_from[current_grid] = None
        cost_from_start[current_grid] = 0
        #agent_location = self._agent.get_location()
        while not frontier.empty():
            # Get the top layer at the agent’s current location.
            # If a survivor is present, save it and end the turn.
            if current_grid.location == goal:
                break
            current_grid = frontier.get()
            for dir in Direction:
                #for each neighbour of the current grid that is being evaluated
                neighbor = world.get_grid_at(current_grid.location.add(dir))
                #print(f"looking in direction {dir}")
                if neighbor is None:
                    continue
                if neighbor.is_stable(): #if the neighbor didn't come from anywhere yet
                    move_cost = neighbor.move_cost if neighbor.move_cost is not None else 1
                    new_cost = cost_from_start[current_grid] + move_cost #add the cost to move to neighbor cost
                    #the total cost of reaching the next node through the current node
                    if neighbor not in cost_from_start or new_cost < cost_from_start[neighbor]: #see if this has been visited before
                        #if the path hasnt' been visited, add to frontier
                        #if this new path to this neighbor node
                        cost_from_start[neighbor] = new_cost
                        weight = new_cost + self.heuristics(neighbor,goal)
                        frontier.put(neighbor, weight) #that means it was on the front line and need to be added
                        came_from[neighbor] = current_grid #link it to the grid that it came from
        return came_from, cost_from_start
    
    def reconstruct_path(self, came_from,
                     start, goal) -> list:
        current = goal
        path = [current.location]
        if goal not in came_from: # no path was found
            return []
        while current != start:
            path.append(current.location)
            #print(f"current location: ({current.location.x}, {current.location.y})")
            current = came_from[current]
        path.reverse() 
        #print("PATH" + str(path))
        return path
    
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

    @override
    def handle_move_result(self, mr: MOVE_RESULT) -> None:
        self.update_surround(mr.surround_info)

    @override
    def handle_save_surv_result(self, ssr: SAVE_SURV_RESULT) -> None:
        self.update_surround(ssr.surround_info)

    @override
    def think(self) -> None:
        BaseAgent.log(LogLevels.Always, "Thinking")

        # At the start of the first round, send a request for surrounding information
        # by moving to the center of the current grid. This will help initiate pathfinding.
        if self._agent.get_round_number() == 1:
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return
            #start_grid = world.get_grid_at(self._agent.get_location())
            self.survivor_location = self.locate_survivor(world.get_world_grid())
            self.survivor_grid = world.get_grid_at(self.survivor_location)
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        grid = world.get_grid_at(self._agent.get_location())
        if grid is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        top_layer = grid.get_top_layer()
        if top_layer:
            self.send_and_end_turn(SAVE_SURV())
            return
        
        current_grid = world.get_grid_at(self._agent.get_location())
        #print(str(current_grid.location.x)+str (current_grid.location.y))     
        returned_camefrom, returned_cost_from_start = self.a_star(current_grid, self.survivor_location)
        self.path = self.reconstruct_path(returned_camefrom, current_grid, self.survivor_grid)
        
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
        
        #self.send_and_end_turn(MOVE(Direction.CENTER))

    def send_and_end_turn(self, command: AgentCommand):
        """Send a command and end your turn."""
        BaseAgent.log(LogLevels.Always, f"SENDING {command}")
        self._agent.send(command)
        self._agent.send(END_TURN())

    def update_surround(self, surround_info: SurroundInfo):
        """Updates the current and surrounding grid cells of the agent."""
        world = self.get_world()
        if world is None:
            return

        for dir in Direction:
            grid_info = surround_info.get_surround_info(dir)
            if grid_info is None:
                continue

            grid = world.get_grid_at(grid_info.location)
            if grid is None:
                continue

            grid.move_cost = grid_info.move_cost
            self.update_top_layer(grid, grid_info.top_layer_info)

    def update_top_layer(self, grid: Grid, top_layer: WorldObjectInfo):
        """Updates the top layer of the grid. Converting WorldObjectInfo to WorldObject"""
        if isinstance(top_layer, SurvivorInfo):
            layer = Survivor(
                top_layer.id,
                top_layer.energy_level,
                top_layer.damage_factor,
                top_layer.body_mass,
                top_layer.mental_state,
            )
            grid.set_top_layer(layer)
