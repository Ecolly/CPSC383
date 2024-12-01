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
        self.movement_queue = None
        self.survivor_cell = None
        #Leader variables
        self.all_agent_information = []
        self.all_agent_pairs = []
        self.received_all_locations = False
        self.inital_assignment = False
        self.current_goal = None  # Initialize the current goal
        self.goal_queue = []  # Queue of tasks
        self.current_goal = None  # Current task

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
        
        #Differentiate the leader receiving the information vs everyone else here receiving information from the leader
        #LEADER vvvvvvv
        if (self._agent.get_agent_id().id==1):
            #append the info back to the consolidated list of agents
            msg = smr.msg 
            #Processing the initital assignment with all the information the agents sent
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
                #Check for additional survivors
                #reassign them if there are additional survivors

        #AGENTS (also including leader as a regular agent)vvvvvvvvvvvvvv
        
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
        # Log the move result for debugging
        BaseAgent.log(LogLevels.Always, f"MOVE_RESULT: {mr}")
        BaseAgent.log(LogLevels.Always, f"MOVE_RESULT Attributes: {dir(mr)}")
        BaseAgent.log(LogLevels.Always, f"SURROUND_INFO: {mr.surround_info}")

        # Update the surroundings, including the current cell
        self.update_surround(mr.surround_info)

        # Retrieve the current cell using the agent's location
        current_cell = self.get_world().get_cell_at(self._agent.get_location())
        if current_cell is not None:
            BaseAgent.log(LogLevels.Always, f"Updated current cell: {current_cell}")

            # Update agent's location and energy
            self._agent.set_location(current_cell.location)
            self._agent.set_energy_level(mr.energy_level)

            # Check if the task is complete
            if self.current_goal and self.check_task_completion(self.current_goal):
                BaseAgent.log(LogLevels.Always, "Goal completed after movement. Reassigning task.")
                self.current_goal = None
                self.reassign_task()
        else:
            BaseAgent.log(LogLevels.Error, "Failed to retrieve the current cell after updating surroundings.")

    
    # Contain information about agent observations
    @override
    def handle_observe_result(self, ovr: OBSERVE_RESULT) -> None:
        ##BaseAgent.log(LogLevels.Always, f"OBSERVER_RESULT: {ovr}")
        ##BaseAgent.log(LogLevels.Test, f"{ovr}")
        ##print("#--- You need to implement handle_observe_result function! ---#")
        # Update surroundings
        self.update_surround(ovr.surround_info)
        # Detect new tasks (e.g., survivors) in observed surroundings
        for direction in Direction:
            cell_info = ovr.surround_info.get_surround_info(direction)
            if cell_info and isinstance(cell_info.top_layer, Survivor):
                survivor_cell = self.get_world().get_cell_at(cell_info.location)

                # Add new tasks to the queue, avoiding duplicates
                if survivor_cell not in self.goal_queue:
                    self.goal_queue.append(survivor_cell)

        # Trigger reassignment if no goal is set and tasks are available
        if not self.current_goal and self.goal_queue:
            self.reassign_task()

        

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
    
    #For reassignment logic
    def reassign_task(self):
    #Reassign a new task from the goal queue.
        if self.goal_queue:
            next_goal = self.goal_queue.pop(0)
            self.assign_task(self._agent.get_id(), next_goal)
            BaseAgent.log(LogLevels.Always, f"Reassigned to new goal: {next_goal.location}")
        else:
            BaseAgent.log(LogLevels.Always, "No tasks available for reassignment. Staying Idle.")
            self.path = []  # Clear the path if no tasks are available

    def assign_task(self, agent_id, goal):
    #Assign a new task to the agent.
        self.current_goal = goal  # Set the new goal
        self.path = self.calculate_path_to_goal(goal)  # Calculate the path to the goal
        if self.path:
            BaseAgent.log(LogLevels.Always, f"Path calculated for task: {self.path}")
        else:
            BaseAgent.log(LogLevels.Error, "Failed to calculate a path to the goal.")
            
        
    def check_and_handle_task_completion(self, current_cell):
        if self.current_goal and self._agent.get_location() == self.current_goal.location:
            top_layer = current_cell.get_top_layer()

            if isinstance(top_layer, WorldObject | None):
                # Task complete; send success message and reassign
                self._agent.send(
                    SEND_MESSAGE(
                        AgentIDList([AgentID(1, 1)]),
                        f"SUCCESS:{current_cell.location.x},{current_cell.location.y},{self._agent.get_energy_level()}"
                    )
                )
                self.current_goal = None
                print("--- Attempting Reassignment ---")
                self.reassign_task()
                return True

            elif isinstance(top_layer, Survivor):
                # Save the survivor and reassign
                self.send_and_end_turn(SAVE_SURV())
                self.current_goal = None
                print("--- Attempting Reassignment ---")
                self.reassign_task()
                return True

        return False
    
    def calculate_path_to_goal(self, goal):
        current_cell = self.get_world().get_cell_at(self._agent.get_location())
        goal_cell = self.get_world().get_cell_at(goal.location)
        if not current_cell or not goal_cell:
            BaseAgent.log(LogLevels.Error, "Invalid cells for path calculation.")
            return []

        came_from, _ = self.a_star(current_cell, goal_cell)  # Use A* for pathfinding
        return self.reconstruct_path(came_from, current_cell, goal_cell)

    @override
    def think(self) -> None:
        #BaseAgent.log(LogLevels.Always, "Thinking about me")
        BaseAgent.log(LogLevels.Always, "test")
        
        #LEADER CODE (agent with id of 1 will be assigned)
        if (self._agent.get_agent_id().id==1 and self.received_all_locations == True and self.inital_assignment == False):
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
            self.inital_assignment = True

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
        # if isinstance(top_layer, WorldObject | None): #AND toplayer cell = goal_survivor_cell
        #     BaseAgent.log(LogLevels.Always, f"SENDING MESSAGE")
        #     self._agent.send(
        #         #Send necessary information for the leader to redirect them to another task
        #         SEND_MESSAGE( 
        #             AgentIDList([AgentID(1,1)]), f"SUCCESS:{current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}" 
        #     )
        # )
        
        current_cell = self.get_world().get_cell_at(self._agent.get_location())
        # Check and handle task completion
        if self.check_and_handle_task_completion(current_cell):
            return
        
        
        # Move along the path if available
        if self.path and len(self.path) > 0:
            next_location = self.path.pop(0)
            direction = self.get_direction_to_move(
                self._agent.get_location().x,
                self._agent.get_location().y,
                next_location.location.x,
                next_location.location.y,
            )
            self.send_and_end_turn(MOVE(direction))
            return
        
         # Reassign task if no valid path or tasks are available
        if not self.current_goal and self.goal_queue:
            BaseAgent.log(LogLevels.Always, "No current goal. Attempting reassignment.")
            print("--- Attempting Reassignment ---")
            self.reassign_task()
            return
            
         
            #reassignment logic ends
            
        #first round everyone send their location to the leader for initial task
        if (self._agent.get_round_number()==1):
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

        for dir in Direction:
            cell_info = surround_info.get_surround_info(dir)
            if cell_info is None:
                continue

            cell = world.get_cell_at(cell_info.location)
            if cell is None:
                continue

            cell.move_cost = cell_info.move_cost
            cell.set_top_layer(cell_info.top_layer)