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
    Location,
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
    agent_list = AgentIDList()
    def __init__(self) -> None:
        super().__init__()
        self._agent: BaseAgent = BaseAgent.get_base_agent()
        self._agent = BaseAgent.get_base_agent()
        self.path = None  # the path that will be taken
        self.current = None  # current
        self.survivor_location = None  # survivors location
        self.survivor_cell = None
        #Leader variables
        self.all_agent_information = []
        self.received_all_locations = False
    @override
    def handle_connect_ok(self, connect_ok: CONNECT_OK) -> None:
        BaseAgent.log(LogLevels.Always, "CONNECT_OK")

    @override
    def handle_disconnect(self) -> None:
        BaseAgent.log(LogLevels.Always, "DISCONNECT")

    @override
    def handle_dead(self) -> None:
        BaseAgent.log(LogLevels.Always, "DEAD")

    @override
    def handle_send_message_result(self, smr: SEND_MESSAGE_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"SEND_MESSAGE_RESULT: {smr}")
<<<<<<< Updated upstream
        
        #BaseAgent.log(LogLevels.Test, f"{smr}")
        #Differentiate the leader receiving the information vs everyone else here receiving information from the leader

        if (self._agent.get_agent_id().id==1):
            #append the info back to the consolidated list of agents
            msg = smr.msg 
            if msg.startswith("AGENT_INFO:"):
                agent_id = smr.from_agent_id.id #Get the agents ID
                info_part = msg.split(":")[1].strip() 
                x, y, energy = map(int, info_part.split(","))
                agent_info_tuple = (x, y, energy)
                self.all_agent_information.append(agent_info_tuple)
                if len(self.all_agent_information) == 7:  # Assuming there are 7 agents
                    self.received_all_locations = True
                    BaseAgent.log(LogLevels.Always, "All agent locations received.")
        
        if smr.msg.startswith("PATH:"):
            
=======

        # Leader logic for handling success messages
        if self._agent.get_agent_id().id == 1:  # Ensure this is executed by the leader
            if smr.msg.startswith("SUCCESS:"):
                # Parse the success message for agent's current state
                success_info = smr.msg.split(":")[1]
                x, y, energy = map(int, success_info.split(","))
                agent_id = smr.from_agent_id.id

                # Update the agent's information and add it back to the pool
                for agent_info in self.all_agent_information:
                    if agent_info[0] == agent_id:  # Find and update the agent's info
                        self.all_agent_information.remove(agent_info)
                        self.all_agent_information.append((agent_id, x, y, energy))
                        BaseAgent.log(LogLevels.Always, f"Agent {agent_id} added back to available pool.")
                        break

                # Trigger task reassignment
                self.reassign_tasks()

        # Agent logic for handling path updates
        if smr.msg.startswith("PATH:"):
>>>>>>> Stashed changes
            serialized_path = smr.msg[5:]  # Extract the path string after "PATH:"
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return
            try:
                # Convert the string back into a list of (x, y) coordinates
                path = [
                    world.get_cell_at(Location(int(x), int(y)))  # Convert to cell objects
                    for x, y in (point.split(",") for point in serialized_path.split(";"))
                ]
                self.path = path
                self.survivor_cell = path[-1]  # The last cell is the goal
                BaseAgent.log(LogLevels.Always, f"Path updated: {self.path}")
            except Exception as e:
                BaseAgent.log(LogLevels.Always, f"Error parsing path: {e}")
<<<<<<< Updated upstream
=======
                
    def reassign_tasks(self):
        # Check if there are unassigned survivors
        world = self.get_world()
        if world is None:
            return

        surv_list = self.survivors_list(world.get_world_grid())  # Get all survivors
        if not surv_list:
            BaseAgent.log(LogLevels.Always, "No survivors remaining. Tasks completed.")
            return

        # Reassign agents to unassigned survivors
        assignments = self.agent_to_survivor(self.all_agent_information, surv_list)
        for assignment in assignments:
            serialized_path = ";".join(f"{cell.location.x},{cell.location.y}" for cell in assignment[2])
            BaseAgent.log(LogLevels.Always, f"Serialized path {serialized_path}")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(assignment[0], 1)]), f"PATH:{serialized_path}"
                )
            )
            # Send Pair ID to Leader
            pair_id = assignment[3]
            BaseAgent.log(LogLevels.Always, f"Setting Pair ID to {pair_id}")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(1, 1)]), f"PAIR_INFO:{assignment[0]}w{pair_id}"
                )
            )



>>>>>>> Stashed changes
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
            # BaseAgent.log(LogLevels.Always, f"a_star current: {current_cell}")
            # BaseAgent.log(LogLevels.Always, f"a_star goal: {goal_cell}")
            current_cell = frontier.get()
            for dir in Direction:
                # for each neighbour of the current grid that is being evaluated
                neighbor = world.get_cell_at(current_cell.location.add(dir))
                # BaseAgent.log(LogLevels.Always, f"neighbor: {neighbor}")
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
        return came_from, cost_from_start #returns the list of cells
        #came from is  dictionary that maps each node to the node it reached
        #cost_from_start gets the cost to reach every visited node from the start node
    
    def reconstruct_path(self, came_from, start, goal) -> list:
        current = goal
        path = [current]
        if goal not in came_from:  # no path was found
            return []
        while current != start:
            path.append(current)
            # print(f"current location: ({current.location.x}, {current.location.y})")
            current = came_from[current]
        path.reverse()
        return path

    def survivors_list(self, grid): 
        #returns a list of survivor cells
        surv_list = []
        for row in grid:
            for cell in row:
                if cell.survivor_chance != 0:
                    surv_list.append(cell)
        return surv_list
    
    def charging_cell_list(self, grid): 
        #returns a list of survivor cells
        charging_cell = []
        for row in grid:
            for cell in row:
                if cell.is_charging_cell() == True:
                    charging_cell.append(cell)
        return charging_cell

    def heuristics(self, a, b):
        return max(abs(a.location.x - b.location.x), abs(a.location.y - b.location.y))
<<<<<<< Updated upstream

    @override
    def think(self) -> None:
        #BaseAgent.log(LogLevels.Always, "Thinking about me")
        BaseAgent.log(LogLevels.Always, "test")
        
        
        #LEADER CODE (agent with id of 1 will be assigned)
        if (self._agent.get_agent_id().id==1 and self.received_all_locations == True):
            BaseAgent.log(LogLevels.Always, f"THE GREAT LEADER IS THINKING")
            #Calculates the path of each agent to each survivor
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return
            print(self.all_agent_information)  #List of all agent locations
            current_grid = world.get_cell_at(self._agent.get_location()) #get the cell that the agent is located on
            #READ ME:
            surv_list = self.survivors_list(world.get_world_grid()) #get the list of the survivors cells
            self.survivor_location = surv_list[0] #pick one right now, for testing
            BaseAgent.log(LogLevels.Always, f" Survival List {self.survivor_location}")
            # cost_list = []
            # target_cell = current_grid
            
            # self.survivor_cell = world.get_cell_at(self.survivor_location)
            
            
            # if surv_list:
            #     for cell in surv_list:
            #         returned_came_from, returned_cost_from_start = self.a_star(current_grid, cell.location)
            #         cost_list.append(returned_cost_from_start[cell])
            #     lowest_cost = min(cost_list)
            #     target_cell_index = cost_list.index(lowest_cost)
            #     target_cell = surv_list[target_cell_index]
            # else:
            #     # There are no more survivors left, do nothing
            #     self.send_and_end_turn(MOVE(Direction.CENTER))

            # self.survivor_location = target_cell.location
                    
            returned_came_from, returned_cost_from_start = self.a_star(current_grid, self.survivor_location)
            path = self.reconstruct_path(returned_came_from, current_grid, self.survivor_location)
            
            
            
            serialized_path = ";".join(f"{cell.location.x},{cell.location.y}" for cell in path)
            BaseAgent.log(LogLevels.Always, f"Serialized path{serialized_path}")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList(), f"PATH:{serialized_path}"
                )
            ) 

=======
      
    def agent_to_survivor(self, agent_list, survivor_list):
    
        #Assigns agents to survivors based on the cost to reach them.
        #Includes multi-agent collaboration if needed.

        #Args:
            #agent_list (list): List of agents with their information (ID, x, y, energy).
            
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        agent_costs = []
        for survivor in survivor_list:
            for agent in agent_list:
                # Get the agent's current location as a cell
                current_grid = world.get_cell_at(Location(agent[1], agent[2]))
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, survivor)
                path = self.reconstruct_path(returned_came_from, current_grid, survivor)

                if path:  # Valid path
                    cost = returned_cost_from_start.get(survivor, float('inf'))
                    agent_costs.append((cost, agent[0], survivor, path))
                else:
                    BaseAgent.log(LogLevels.Always, f"Agent {agent[0]} cannot reach Survivor at {survivor.location}.")

        # Filter out invalid paths (cost = float('inf')) and sort by cost
        agent_costs = [cost_entry for cost_entry in agent_costs if cost_entry[0] != float('inf')]
        agent_costs.sort(key=lambda x: x[0])

        # Initialize sets and list for assignments
        assigned_survivors = set()
        assigned_agents = set()
        assignments = []
        pair_id = 0

        # First pass: Assign one agent to each survivor
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor not in assigned_survivors:
                pair_id += 1
                assignments.append((agent_id, survivor, path, pair_id))  # Assign the agent to the survivor
                assigned_agents.add(agent_id)  # Mark the agent as assigned
                assigned_survivors.add(survivor)  # Mark the survivor as assigned

        # Second pass: Assign additional agents for collaboration if needed
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor in assigned_survivors:
                # Find the original agent assigned to this survivor
                original_assignment = next((a for a in assignments if a[1] == survivor), None)
                if original_assignment and agent_id != original_assignment[0]:
                    # Get agent cells
                    original_agent_cell = world.get_cell_at(Location(agent_list[original_assignment[0] - 1][1],
                                                                    agent_list[original_assignment[0] - 1][2]))
                    partner_agent_cell = world.get_cell_at(Location(agent_list[agent_id - 1][1],
                                                                    agent_list[agent_id - 1][2]))
                    # Find path from partner agent to the original agent
                    returned_came_from, returned_cost_from_start = self.a_star(partner_agent_cell, original_agent_cell)
                    valid_path = self.reconstruct_path(returned_came_from, partner_agent_cell, original_agent_cell)

                    if valid_path:
                        pair_id = original_assignment[3]  # Use the same pair_id as the original assignment
                        combined_path = valid_path + original_assignment[2]  # Path from partner to survivor
                        assignments.append((agent_id, survivor, combined_path, pair_id))
                        assigned_agents.add(agent_id)

        return assignments

    
    @override
    def think(self) -> None:
        """
        The main decision-making logic for the agent.
        Handles tasks such as rubble clearing, survivor saving, and reassignment after task completion.
        """
        BaseAgent.log(LogLevels.Always, "Thinking about task execution.")
>>>>>>> Stashed changes

        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
<<<<<<< Updated upstream
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
=======

        # Get the current grid cell the agent is on
>>>>>>> Stashed changes
        grid = world.get_cell_at(self._agent.get_location())
        if grid is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        # Get the top layer of the current cell
        cell = world.get_cell_at(self._agent.get_location())
        if cell is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        top_layer = cell.get_top_layer()

<<<<<<< Updated upstream
        # If rubble is present, clear it and end the turn.
        if isinstance(top_layer, Rubble):
            self.send_and_end_turn(TEAM_DIG())
=======
        # Task reassignment logic: Check if task is completed.
        if top_layer is None and self.survivor_cell is not None:
            if grid.location == self.survivor_cell.location:
                BaseAgent.log(LogLevels.Always, "Task completed. Sending success message to leader.")
                self._agent.send(
                    SEND_MESSAGE(
                        AgentIDList([AgentID(1, 1)]),  # Send message to the leader (ID 1)
                        f"SUCCESS:{grid.location.x},{grid.location.y},{self._agent.get_energy_level()}"
                    )
                )
                self.survivor_cell = None  # Reset survivor cell for reassignment
                return

        # Handle rubble clearing
        if isinstance(top_layer, Rubble):
            if top_layer.remove_agents == 1:  # Single-agent rubble clearing
                self.send_and_end_turn(TEAM_DIG())
            else:  # Multi-agent rubble clearing
                self.send_and_end_turn(TEAM_DIG())  # Placeholder for pair coordination
>>>>>>> Stashed changes
            return

        # Handle saving a survivor
        if isinstance(top_layer, Survivor):
            # self.survivor_cell.set_top_layer(None)
            # self.survivor_cell.survivor_chance = 0  # this should only be applied if all layers are checked
            self.send_and_end_turn(SAVE_SURV())
            return

<<<<<<< Updated upstream
        current_grid = world.get_cell_at(self._agent.get_location())
        # print(str(current_grid.location.x)+str (current_grid.location.y))

        # returned_came_from, returned_cost_from_start = self.a_star(current_grid, self.survivor_location)
        # self.path = self.reconstruct_path(returned_came_from, current_grid, self.survivor_cell)

        # Follow the next step in the path, if available.
        
        #first round everyone send their location
        if (self._agent.get_round_number()==1):
            BaseAgent.log(LogLevels.Always, f"SENDING MESSAGE")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList(), f"AGENT_INFO: {current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}" 
                    #I dont know how to make it send to one specific person only >:(
            )
        ) 
=======
        # Follow the assigned path
>>>>>>> Stashed changes
        if self.path and len(self.path) > 0:
            next_location = self.path.pop(0)  # Get the next step in the path
            agent_location = self._agent.get_location()
            direction = self.get_direction_to_move(agent_location.x, agent_location.y,
                                                next_location.location.x, next_location.location.y)
            self.send_and_end_turn(MOVE(direction))  # Move in the calculated direction
            return

<<<<<<< Updated upstream
        # Default action: Move the agent north if no other specific conditions are met.
        self.send_and_end_turn(MOVE(Direction.NORTH))
    
    #new function added 
    def split_agents_to_goals(self, agents, survivors):
      
        # Validate inputs
        if not agents or not survivors:
            return {}
        remaining_survivors = survivors[:]
        assignments = {}

        for agent in agents:
            if not remaining_survivors:
                break
 
        # Find the nearest survivor using A* pathfinding cost
        nearest_survivor = min(
            remaining_survivors,
            key=lambda s: self.a_star(
                self.get_world().get_cell_at(agent.location),
                self.get_world().get_cell_at(s.location),
            )[1].get(
                self.get_world().get_cell_at(s.location), float('inf')
            )
        )

        # Assign the agent to the nearest survivor
        assignments[agent.id] = nearest_survivor

        # Remove the assigned survivor from the list
        remaining_survivors.remove(nearest_survivor)

        return assignments
=======
        # Default action: Stay in place
        self.send_and_end_turn(MOVE(Direction.CENTER))
>>>>>>> Stashed changes

   
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