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
    AgentID,
    WorldObject,
    SLEEP,
)

from agent import BaseAgent, Brain, LogLevels
from typing import TypeVar
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
        self.movement_queue = None
        self.survivor_cell = None
        #Leader variables
        self.all_agent_information = []
        self.all_agent_pairs = []
        self.received_all_locations = False
        self.initial_assignment = False

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
        
        # Differentiate the leader receiving information vs everyone else receiving information from the leader
        # For the LEADER
        if self._agent.get_agent_id().id==1:
            #append the info back to the consolidated list of agents
            msg = smr.msg 
            #Processing the initial assignment with all the information the agents sent
            if msg.startswith("AGENT_INFO:"):
                agent_id = smr.from_agent_id.id #Get the agents ID
                info_part = msg.split(":")[1].strip() 
                x, y, energy = map(int, info_part.split(","))
                agent_info_tuple = (agent_id, x, y, energy)
                self.all_agent_information.append(agent_info_tuple)
                if len(self.all_agent_information) == 7:  # Assuming there are 7 agents
                    self.received_all_locations = True
                    BaseAgent.log(LogLevels.Always, "All agent locations received.")

            # Processes initial pairs into a list "agent_id_pair", that has a list (agent_id, pair_id).
            if msg.startswith("PAIR_INFO:"):
                info_part = msg.split(":")[1].strip() 
                agent_id_str, pair_id_str = info_part.split("w")
                agent_id = int(agent_id_str.strip())
                pair_id = int(pair_id_str.strip())
                agent_id_pair = (agent_id, pair_id)
                self.all_agent_pairs.append(agent_id_pair)
                BaseAgent.log(LogLevels.Always, f"Pair ID: {pair_id}")
                
            # If any agents reports back after competing task
            if msg.startswith("SUCCESS:"):
                agent_id = smr.from_agent_id.id
                # Check for additional survivors
                # reassign them if there are additional survivors

        #AGENTS (also including leader as a regular agent)
        
        if smr.msg.startswith("PATH:"):
            serialized_path = smr.msg[5:]  # Extract the path string after "agentID:"
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
                BaseAgent.log(LogLevels.Always, f"Path updated: {self.path}")

            except Exception as e:
                BaseAgent.log(LogLevels.Always, f"Error parsing path: {e}")

    # When the agent attempts to move in a direction, and receive the result of that movement
    # Did the agent successfully move to the intended cell
    # How much was used during the move

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
        self.update_surround(ssr.surround_info)
        print("#--- You need to implement handle_save_surv_result function! ---#")

    # prd, the instance of PREDICT_RESULT, details of prediction

    @override
    def handle_predict_result(self, prd: PREDICT_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"PREDICT_RESULT: {prd}")
        BaseAgent.log(LogLevels.Test, f"{prd}")

    # Gets the result of the agent's attempt to rest or recover
    @override
    def handle_sleep_result(self, sr: SLEEP_RESULT) -> None:
        BaseAgent.log(LogLevels.Always, f"SLEEP_RESULT: {sr}")
        BaseAgent.log(LogLevels.Test, f"{sr}")

        if sr.was_successful:
            BaseAgent.log(LogLevels.Always, f"Agent has slept. Current energy level: {sr.charge_energy}")
        else:
            BaseAgent.log(LogLevels.Always, f"Agent could not sleep")

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
        self.update_surround(tdr.surround_info)

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
        # Get the world
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        #### QUEUE ###
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
            for direction in Direction:
                # for each neighbour of the current grid that is being evaluated
                neighbor = world.get_cell_at(current_cell.location.add(direction))
                # BaseAgent.log(LogLevels.Always, f"neighbor: {neighbor}")
                if neighbor is None:
                    continue
                if neighbor.is_normal_cell() or neighbor.is_charging_cell():
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

    def heuristics(self, a, b):
        return max(abs(a.location.x - b.location.x), abs(a.location.y - b.location.y))
      
    #returns a list of cost to get to each survivor on the map
    def agent_to_survivor(self, agent_list, survivor_list):
        print(f"SURVIVOR LIST {survivor_list}")
        # agent is a tuple
        # survivor_list is a list of survivor cells
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        agent_costs = []

        for survivor in survivor_list:
            print(f"SURVIVOR {survivor}")

            for agent in agent_list:
                # Get the cell of the agent
                current_grid = world.get_cell_at(Location(agent[1], agent[2]))
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, survivor)
                path = self.reconstruct_path(returned_came_from, current_grid, survivor)

                if path:  # Valid path
                    cost = returned_cost_from_start.get(survivor, float('inf'))
                    agent_costs.append((cost, agent[0], survivor, path))
                else:
                    print(f"Agent{agent[0]} Path not valid")

        # Sort the agent_costs based on cost
        agent_costs.sort(key=lambda x: x[0])

        # Initialize sets and list for assignments
        assigned_survivors = set()
        assigned_survivor2 = set()
        assigned_agents = set()
        assignments = []
        pair_id = 0

        # First pass: Assign one agent to each survivor
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor not in assigned_survivors:
                pair_id += 1
                assignments.append((agent_id, survivor, path, pair_id))  # Assign the agent to the survivor
                assigned_agents.add(agent_id)             # Mark the agent as assigned
                assigned_survivors.add(survivor)          # Mark the survivor as assigned
        agent_costs.sort(key=lambda x: x[0])
        
        # Second pass: Assign remaining agents to survivors/original agents
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor not in assigned_survivor2: # Pairs remaining agent to lowest-cost survivor
                for original_agent in assignments:
                    if original_agent[1] == survivor and agent_id != original_agent[0]: # Checks original agent that was already assigned to that survivor
                        
                        for agent_info in self.all_agent_information:
                            if original_agent[0] == agent_info[0]:
                                original_agent_cell = world.get_cell_at(Location(agent_info[1], agent_info[2])) # Get original agent's cell
                            elif agent_id == agent_info[0]:
                                partner_agent_cell = world.get_cell_at(Location(agent_info[1], agent_info[2])) # Get partner agent's cell
                        # Create path from partner agent to original agent
                        returned_came_from, returned_cost_from_start = self.a_star(partner_agent_cell, original_agent_cell)
                        valid_path = self.reconstruct_path(returned_came_from, partner_agent_cell, original_agent_cell)
                        
                        if valid_path:
                            pair_id = original_agent[3]  # Assigns the same pair_id as original agent
                            path = valid_path + original_agent[2] # Create path from partner agent to original agent to survivor
                            assignments.append((agent_id, survivor, path, pair_id))  # Assign the agent to the survivor
                            assigned_agents.add(agent_id)  
                            assigned_survivor2.add(survivor)   # Mark the agent as assigned   
        return assignments


    ###################################################################

    #Helper function for identifying charging cells in the world
    def charging_cell_list(self, grid):
        # returns a list of survivor cells
        charging_cell = []
        for row in grid:
            for cell in row:
                if cell.is_charging_cell():
                    charging_cell.append(cell)
        return charging_cell

    # Helper function for moving towards charging station
    def move_towards_charging_station(self):
        # calculate where charging cells are located in the cell
        world = self.get_world()
        world_grid = world.get_world_grid()
        charging_cell = self.charging_cell_list(world_grid)

        # locate nearest charging station
        charging_cells = self.charging_cell_list(world_grid)
        if not charging_cells:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        # if charging stations exist
        agent_location = self._agent.get_location()
        nearest_charging_cell = min(charging_cell, key=lambda cell: abs(cell.location.x - agent_location.x) + abs(cell.location.y - agent_location.y))

        # move towards charging station
        direction_to_move = self.get_direction_to_move(
            agent_location.x,
            agent_location.y,
            nearest_charging_cell.location.x,
            nearest_charging_cell.location.y
        )
        self.send_and_end_turn(MOVE(direction_to_move))

    # Helper function to find cost of the movement to survivor
    def energy_to_survivor(self, current_cell, survivor_cell):
        # Get the world
        world = self.get_world()
        if world is None:
            return None

        #### QUEUE ###
        frontier = []  # Use a heap-based priority queue
        heapq.heappush(frontier, (0, current_cell))
        cost_from_start = dict()
        cost_from_start[current_cell] = 0

        while frontier:
            # Get the cell with the lowest cost
            current_cost, current_cell = heapq.heappop(frontier)

            # If we reach the survivor, return the energy (cost) required
            if current_cell == survivor_cell:
                return current_cost

            # Check the neighboring cells for path
            for direction in Direction:
                # Update the neighbor location using the direction
                neighbor_location = current_cell.location.add(direction)
                neighbor = world.get_cell_at(neighbor_location)

                # Skip invalid spaces to move
                if neighbor is None or neighbor.is_killer_cell() or neighbor.is_fire_cell() or neighbor.is_on_fire():
                    continue

                # Check if the neighbor is a valid cell to move to (normal or charging cell)
                if neighbor.is_normal_cell() or neighbor.is_charging_cell():
                    # Calculate the new cost to reach the neighbor
                    move_cost = neighbor.move_cost if neighbor.move_cost is not None else 1
                    new_cost = current_cost + move_cost

                    # If this path to the neighbor is better (lower cost), update cost and add to the frontier
                    if neighbor not in cost_from_start or new_cost < cost_from_start[neighbor]:
                        cost_from_start[neighbor] = new_cost
                        # Add the neighbor with the updated cost to the queue
                        heapq.heappush(frontier,(new_cost, neighbor))

        # If the loop finishes without finding the survivor, return None
        return None

    ###################################################################

    @override
    def think(self) -> None:
        #BaseAgent.log(LogLevels.Always, "Thinking about me")
        BaseAgent.log(LogLevels.Always, "test")
        
        #LEADER CODE (agent with id of 1 will be assigned)
        if self._agent.get_agent_id().id==1 and self.received_all_locations == True and self.initial_assignment == False:
            BaseAgent.log(LogLevels.Always, f"THE GREAT LEADER IS THINKING")
            #Calculates the path of each agent to each survivor
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return

            print(self.all_agent_information)  #List of all agent locations
            
            current_grid = world.get_cell_at(self._agent.get_location()) #get the cell that the agent is located on
            surv_list = self.survivors_list(world.get_world_grid()) #get the list of the survivors cells
            assignments = self.agent_to_survivor(self.all_agent_information, surv_list)

            for assignment in assignments:
            
                serialized_path = ";".join(f"{cell.location.x},{cell.location.y}" for cell in assignment[2])
                BaseAgent.log(LogLevels.Always, f"Serialized path{serialized_path}")
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
                BaseAgent.log(LogLevels.Always, f"Sent")
            self.initial_assignment = True


        # get world information
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        grid = world.get_cell_at(self._agent.get_location())
        if grid is None:
            self.send_and_end_turn(MOVE(Direction.CENTER)) 
            return

        cell = world.get_cell_at(self._agent.get_location())
        if cell is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        # calculate move cost to see if the agents need energy
        # move_cost = self.calculate_move_cost_to_goal()

        # Check if the agent needs charging
        if self._agent.get_energy_level() < 251:
            # Move towards the nearest charging station if not on one already
            if not cell.is_charging_cell():
                self.move_towards_charging_station()
            if cell.is_charging_cell():
                # Stay and sleep while energy is not enough
                while self._agent.get_energy_level() < 250:
                    # Sleep until fully charged
                    self.send_and_end_turn(SLEEP())
                    # Keep the agent sleeping until it is fully recharged
                    return

        # Check if the agent needs charging
        # if move cost is greater than agent should look for a charging cell
        #         if self._agent.get_energy_level() < move cost to survivor from current position :
        #         if self._agent.get_energy_level() < move cost to survivor from current position :
        #             # Move towards the nearest charging station if not on one already
        #             if not cell.is_charging_cell():
        #                 self.move_towards_charging_station()
        #                 return
        #
        #             # charge until agent has enough energy to move to the survivor
        #             if cell.is_charging_cell():
        #                 # Stay and sleep while energy is below the threshold
        #                 while self._agent.get_energy_level() < move cost to survivor from current position :
        #                     self.send_and_end_turn(SLEEP())  # Sleep until fully charged
        #                     return  # Keep the agent sleeping until it is fully recharged


        # Get the top layer at the agent’s current location.
        top_layer = cell.get_top_layer()

        # If rubble is present, clear it and end the turn.
        if isinstance(top_layer, Rubble):

            # Rubble only needs 1 person
            if top_layer.remove_agents == 1:
                self.send_and_end_turn(TEAM_DIG())
            
            else:
                ## The rubble requires 2 people!
                ### NEED TO IMPLEMENT
                ### Check if pairs are together
                ### If not, reassign pairs!
                self.send_and_end_turn(TEAM_DIG())
            return

        # If a survivor is present, save them and end the turn.
        if isinstance(top_layer, Survivor):
            self.send_and_end_turn(SAVE_SURV())
            return
        
        current_grid = world.get_cell_at(self._agent.get_location())
        
        ############FOR REASSIGNING TASK##############################
        # If the top layer has no layers (aka no survivors no rubble) - maybe this should be in OBSERVE RESULTS INSTEAD? Not sure 
        # Send message back to leader indicating mission was successful
        # if isinstance(top_layer, WorldObject | None): #AND top layer cell = goal_survivor_cell
        #     BaseAgent.log(LogLevels.Always, f"SENDING MESSAGE")
        #     self._agent.send(
        #         #Send necessary information for the leader to redirect them to another task
        #         SEND_MESSAGE( 
        #             AgentIDList([AgentID(1,1)]), f"SUCCESS:{current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}" 
        #     )
        # )

        #first round everyone send their location to the leader for initial task
        if self._agent.get_round_number()==1:
            BaseAgent.log(LogLevels.Always, f"SENDING MESSAGE")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(1,1)]), f"AGENT_INFO: {current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}" 
            )
        )
            
        #Charging cell code(ish)
        #When an agent lands on a charging cell:
            #Calculates its own energy
            #compare with allocated path energy
            #WARNING: YOU MIGHT NEED MORE THAN CALCULATED BECAUSE IT MAY TAKE ENERGY TO DIG RUBBLE
            #if energy < path energy:
            #   stay on cell (end its turn)
            #if energy > path energy (plus more for digging maybe)
            #   move to the next step in path (look at the function below for implementation)
                        
        ##### IF YOU'RE DOING CHARGING CELLS, MAKE SURE TO NOT TRIGGER THE PATH FOLLOWING BELOW, END TURN BEFORE IT REACHES IT############################
        ########################PATH FOLLOWING ALGORITHM BELOW#####################################################################################    

        if self.path and len(self.path) > 0:
            next_location = self.path.pop(0)  # Get the next step in the path and remove it from the list
            agent_location = self._agent.get_location()
            direction = self.get_direction_to_move(agent_location.x, agent_location.y,
                                                   next_location.location.x, next_location.location.y)
            self.send_and_end_turn(MOVE(direction))  # Send the move command for the calculated direction
            return
        else:
            # Default action: Stay in place if no path is available or path is empty
            self.send_and_end_turn(MOVE(Direction.CENTER))

        # Default action: Move the agent north if no other specific conditions are met.
        self.send_and_end_turn(MOVE(Direction.CENTER))

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

        for direction in Direction:
            cell_info = surround_info.get_surround_info(direction)
            if cell_info is None:
                continue

            cell = world.get_cell_at(cell_info.location)
            if cell is None:
                continue

            cell.move_cost = cell_info.move_cost
            cell.set_top_layer(cell_info.top_layer)