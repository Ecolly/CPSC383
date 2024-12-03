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
#Status meaning
#9 is no status - put at the start of the round
#0 is free and no task assigned (usually assigned 0 when the agent finishes saving survivor)
#1 is need help
#2 is busy

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
        self.survivor_cell = None  # assigned survivor cell, ultimate goal
        self.movement_queue = None
        self.goal_cell = None #Goal cell
        self.partner = None
        #Leader variables
        self.all_agent_information = []
        self.all_agent_status = {}
        self.all_agent_task_assignment = {}
        self.all_agent_pairs = {}
        self.detour = [] #List of cells to make a detour to, but the ultimate goal is the survivor cell!!
        self.received_all_locations = False
        self.inital_assignment = False
        self.assigned_survivors = set()
        

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
        msg = smr.msg
        #Differentiate the leader receiving the information vs everyone else here receiving information from the leader
        #LEADER vvvvvvv
        if (self._agent.get_agent_id().id==1):
            #append the info back to the consolidated list of agents
            #Processing the initital assignment with all the information the agents sent
            if msg.startswith("AGENT_INFO:"):
                agent_id = smr.from_agent_id.id #Get the agents ID
                info_part = msg.split(":")[1].strip() 
                x, y, energy = map(int, info_part.split(","))
                agent_info_tuple = (agent_id, x, y, energy)
                self.all_agent_information.append(agent_info_tuple)
                if len(self.all_agent_information) == 7:  # Assuming there are 7 agents
                    self.received_all_locations = True
                    BaseAgent.log(LogLevels.Always, "All agent information received.")
            #get the status of the agent
            if msg.startswith("STATUS:"):
                info_part = msg.split(":")[1].strip()
                status = int(info_part) 
                agent_id = smr.from_agent_id.id
                self.all_agent_status[agent_id] = status
                BaseAgent.log(LogLevels.Always, f"Received Agent{agent_id}, status:{status}")
                
                if(status == 0):
                    self.all_agent_pairs[agent_id] = None
                    self.all_agent_task_assignment[agent_id] = None
                #assign the status to the agent list the leader keep track of:
            # Processes initial pairs into a list "agent_id_pair", that has a list (agent_id, pair_id).
                
            # Update the agents status, likely after completing a task
            if msg.startswith("UPDATE:"):
                agent_id = smr.from_agent_id.id
                info_part = msg.split(":")[1].strip() 
                x, y, energy = map(int, info_part.split(","))
                self.update_agent_state(self.all_agent_information, agent_id, x, y, energy)
            #Check for additional survivors
            #reassign them if there are additional survivors
            
        #AGENTS (also including leader as a regular agent)vvvvvvvvvvvvvv
        
        if msg.startswith("SURVIVOR:"):
            info_part = msg.split(":")[1].strip()
            survivor_x, survivor_y = map(int, info_part.split(","))
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return
            try:
                self.survivor_cell = world.get_cell_at(Location(int(survivor_x), int(survivor_y)))
            except Exception as e:
                BaseAgent.log(LogLevels.Always, f"Error parsing survivor: {e}")
        if msg.startswith("HELP_LOCATION:"):
            info_part = msg.split(":")[1].strip()
            detour_x, detour_y = map(int, info_part.split(","))
            world = self.get_world()
            if world is None:
                self.send_and_end_turn(MOVE(Direction.CENTER))
                return
            try:
                self.detour = world.get_cell_at(Location(int(detour_x), int(detour_y)))
            except Exception as e:
                BaseAgent.log(LogLevels.Always, f"Error parsing survivor: {e}")
        if msg.startswith("PATH:"):
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
                #BaseAgent.log(LogLevels.Always, f"Path updated: {self.path}")
            except Exception as e:
                BaseAgent.log(LogLevels.Always, f"Error parsing path: {e}")
        if msg.startswith("SENT_HELP:"):
            #TODO the agent asked for help and leader found help
            info_part = msg.split(":")[1].strip()
            parnter_id = int(info_part) 
            self.partner = parnter_id
        if msg.startswith("PARTNER:"):
            info_part = msg.split(":")[1].strip()
            if info_part == "None":
                self.partner = None
            else:
                partner = int(info_part) 
                self.partner = partner
                BaseAgent.log(LogLevels.Always, f"{self._agent.get_agent_id()} Assigned partner {partner}")
            
        # if msg.startswith("REASSIGNED:"):
            #TODO The agent was free and the leader reassigned them
            #Receive info on survivor they are saving
        
            

    # When the agent attempts to move in a direction, and receive the result of that movement
    # Did the agent successfully move to the intended cell
    # How much was used during the move

    def handle_move_result(self, mr: MOVE_RESULT) -> None:
        #BaseAgent.log(LogLevels.Always, f"MOVE_RESULT: {mr}")
        #BaseAgent.log(LogLevels.Test, f"{mr}")
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
        
        self.update_surround(tdr.surround_info)
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
    
    def update_agent_state(self, agent_info_list, target_agent, new_pos_x, new_pos_y, new_energy):
        for i, agent in enumerate(agent_info_list):
            if agent[0] == target_agent:  # Match agent by ID
                # Create a new tuple with the updated status
                updated_agent = (agent[0], new_pos_x, new_pos_y, new_energy)
                # Replace the old tuple in the list
                agent_info_list[i] = updated_agent
                break
    #returns a list of cost to get to each survivor on the map
    def agent_to_survivor(self, agent_list, survivor_list):
        #print(f"SURVIVOR LIST {survivor_list}")
        # agent is a tuple
        # survivor_list is a list of survivor cells
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return

        agent_costs = []
        for survivor in survivor_list:
            #print(f"SURVIVOR {survivor}")

            for agent in agent_list:
                # Get the cell of the agent
                current_grid = world.get_cell_at(Location(agent[1], agent[2]))
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, survivor)
                path = self.reconstruct_path(returned_came_from, current_grid, survivor)

                if path:  # Valid path
                    cost = returned_cost_from_start.get(survivor, float('inf'))
                    agent_costs.append((cost, agent[0], survivor, path))

        # Sort the agent_costs based on cost
        agent_costs.sort(key=lambda x: x[0])

        # Initialize sets and list for assignments
        assigned_survivor2 = set()
        assigned_agents = set()
        assignments = []
        pairings = {}
        # First pass: Assign one agent to each survivor
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor not in self.assigned_survivors:
                assignments.append((agent_id, survivor, path))  # Assign the agent to the survivor
                assigned_agents.add(agent_id)             # Mark the agent as assigned
                self.assigned_survivors.add(survivor)          # Mark the survivor as assigned
                #print(f"ASSIGNED SURVIVORS {self.assigned_survivors}")
        agent_costs.sort(key=lambda x: x[0])
        
        first_assign = assignments
        # Second pass: Assign remaining agents to survivors/original agents
        for cost, agent_id, survivor, path in agent_costs:
            if agent_id not in assigned_agents and survivor not in assigned_survivor2:
               for primary_agent_id, assigned_survivor, primary_path in first_assign:
                    if assigned_survivor == survivor:
                        pairings[primary_agent_id] = agent_id
                        pairings[agent_id] = primary_agent_id                   
                        assignments.append((agent_id, survivor, path))  # Assign the agent to the survivor
                        assigned_agents.add(agent_id)  
                        assigned_survivor2.add(survivor)   # Mark the agent as assigned   
                        break
        return assignments, pairings
    def get_agent_info(self, agent_id):
        for agent in self.all_agent_information:
            if agent[0] == agent_id:  # Check if the first element matches the agent_id
                x, y, energy = agent[1], agent[2], agent[3]
                return x, y, energy
        return None

    @override
    def think(self) -> None:
        #BaseAgent.log(LogLevels.Always, "Thinking about me")
        BaseAgent.log(LogLevels.Always, "test")
        
        world = self.get_world()
        if world is None:
            self.send_and_end_turn(MOVE(Direction.CENTER))
            return
        
        current_grid = world.get_cell_at(self._agent.get_location()) #get the cell that the agent is located on
        surv_list = self.survivors_list(world.get_world_grid()) 
        print(f"ASSIGNED PARTNER: {self.partner}")
        
        #LEADER CODE (agent with id of 1 will be assigned)
        if (self._agent.get_agent_id().id==1 and self.received_all_locations == True and self.inital_assignment == False):
            BaseAgent.log(LogLevels.Always, f"THE GREAT LEADER IS THINKING")
            #Calculates the path of each agent to each survivor
            #get the list of the survivors cells
            assignments, pairings = self.agent_to_survivor(self.all_agent_information, surv_list)
            self.all_agent_pairs = pairings
            for assignment in assignments:
                
                #((agent_id, survivor, path, pair_id))
                print(f"Assignment: {assignment}")
                #iterate each pair in the list
                partner_id = self.all_agent_pairs.get(assignment[0], None)

                serialized_path = ";".join(f"{cell.location.x},{cell.location.y}" for cell in assignment[2])
                seriaized_survivor_location = f"{assignment[1].location.x},{assignment[1].location.y}" 
                self.all_agent_task_assignment[assignment[0]] = assignment[1]
                BaseAgent.log(LogLevels.Always, f"Serialized path{serialized_path}")
                self._agent.send(
                    SEND_MESSAGE(
                        AgentIDList([AgentID(assignment[0], 1)]), f"SURVIVOR:{seriaized_survivor_location}"
                    )
                )
                self._agent.send(
                    SEND_MESSAGE(
                        AgentIDList([AgentID(assignment[0], 1)]), f"PARTNER:{partner_id}"
                    )
                ) 
                
            self.inital_assignment = True
        
        if (self._agent.get_agent_id().id==1):
            print(f"all agent info: {self.all_agent_information}")  #List of all agent locations
            print(f"Agent status: {self.all_agent_status}")
            print(f"assigned survior: {self.assigned_survivors}")
            #if the leader, check the status of all agents on the map each round
            agents_needing_help = [agent_id for agent_id, status in self.all_agent_status.items() if status == 1]
            for agent_id in agents_needing_help:
                print(f"Agent {agent_id} need help")
                partner = self.all_agent_pairs.get(agent_id, None)
                if partner is None:
                    for helper_id, helper_status in self.all_agent_status.items():
                        #if they are available
                        if (helper_status == 0):
                            hx, hy, henergy = self.get_agent_info(helper_id)
                            helper_agent_cell = world.get_cell_at(Location(hx, hy))
                            #check path validity to survivor
                            survivor = self.all_agent_task_assignment[agent_id]
                            returned_came_from, returned_cost_from_start = self.a_star(helper_agent_cell, survivor)
                            valid_path = self.reconstruct_path(returned_came_from, helper_agent_cell, survivor)
                            seriaized_survivor_location = f"{survivor.location.x},{survivor.location.y}"
                            if valid_path:
                                print(f"{helper_id} go help {agent_id}")
                                self._agent.send(
                                    SEND_MESSAGE(
                                        AgentIDList([AgentID(helper_id, 1)]), f"SURVIVOR:{seriaized_survivor_location}"
                                    )
                                )
                                self._agent.send(
                                    SEND_MESSAGE(
                                        AgentIDList([AgentID(helper_id, 1)]), f"PARTNER:{agent_id}"
                                    )
                                )
                                self._agent.send(
                                    SEND_MESSAGE(
                                        AgentIDList([AgentID(agent_id, 1)]), f"PARTNER:{helper_id}"
                                    )
                                )
                                self.all_agent_status[helper_id] = 2  # Helper is now busy
                                self.all_agent_status[agent_id] = 2  # Helper is now busy
                                self.all_agent_pairs[helper_id] = agent_id
                                self.all_agent_pairs[agent_id] = helper_id
                                break
                    else:
                        for potential_helper_id in agents_needing_help: 
                            # for case where another agent in help need to be redirected if theres no other people available
                            if potential_helper_id != agent_id:
                                #TODO send message to agent that help is being assigned
                                #TODO send message to the helper agent to go to agent location and go to x survivor
                                print(f"Redirecting Agent {potential_helper_id} to help Agent {agent_id}.")
                                self.all_agent_status[potential_helper_id] = 1  # Redirected helper is now busy
                                self.all_agent_status[agent_id] = 1  # Agent being helped
                                help_resolved = True  # Mark help as resolved
                                break
            for agent_id, status in self.all_agent_status.items():
                #if no one needs help and we have free agents
                #check the map for survivors
                if status == 0: 
                    task = self.all_agent_task_assignment.get(agent_id, None)
                    #d no one needs help, assignment them to new task
                    if task is None:
                        print("Reassign tasks")
                        for survivor in surv_list:
                            if survivor not in self.assigned_survivors:
                                x, y, energy = self.get_agent_info(agent_id)
                                agent_cell = world.get_cell_at(Location(x, y))
                                                            
                                returned_came_from, returned_cost_from_start = self.a_star(agent_cell, survivor)
                                valid_path = self.reconstruct_path(returned_came_from, agent_cell, survivor)
                                if valid_path:
                                    #and check for energy
                                    #send reassignment message
                                    print(f"Reassigned {agent_id} to {survivor}")
                                    seriaized_survivor_location = f"{survivor.location.x},{survivor.location.y}" 
                                    self._agent.send(
                                        SEND_MESSAGE(
                                            AgentIDList([AgentID(agent_id, 1)]), f"SURVIVOR: {seriaized_survivor_location}"
                                        )
                                    )
                                    self.all_agent_status[agent_id] = 2
                                    self.assigned_survivors.add(survivor)
                                    self.all_agent_task_assignment[agent_id] = survivor #update their task
                                    break
                    if status == 1:
                        print("busy") #for both dig and team dig
                    if status == 2:
                        print("travelling") 
                
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
        
        
        # If a survivor is present, save them and end the turn.
        if isinstance(top_layer, Survivor):
            self.send_and_end_turn(SAVE_SURV())
            return
        
        current_grid = world.get_cell_at(self._agent.get_location())
        
        print(cell.get_cell_info().agent_id_list.size())
        
        if (isinstance(top_layer, Rubble) and cell == self.survivor_cell):
            # Rubble only needs 1 person
            if top_layer.remove_agents == 1:
                self.send_and_end_turn(TEAM_DIG())
            # Rubble needs 2 people and we have 2 people on the cell, do dig                
            #if it needs two  people
            elif(top_layer.remove_agents == 2 and self.partner is None):
                self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(1, 1)]), f"STATUS:1"
                ))
                self._agent.send(SEND_MESSAGE(
                    AgentIDList([AgentID(1,1)]), f"UPDATE:{current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}"
                ))
                self._agent.send(END_TURN())
            else:
                self.send_and_end_turn(TEAM_DIG())
                print(f"{self._agent.get_agent_id().id} No other options")
            return
        
        #if the agent is on top of the goal cell and there's nothing on top of it
        if (top_layer is None and self.survivor_cell == cell): 
            self._agent.send( SEND_MESSAGE(
                AgentIDList([AgentID(1, 1)]), f"STATUS:0"
            ))
            #update the leader with all the agents most up to date information
            self._agent.send(SEND_MESSAGE(
                AgentIDList([AgentID(1,1)]), f"UPDATE:{current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}"
            ))
            #disband the pair
            self.partner = None
            BaseAgent.log(LogLevels.Always, "Saved all survivors on that block.")

    
        print("testing")

        
        #first round everyone send their location to the leader for initial task
        if (self._agent.get_round_number()==1):
            BaseAgent.log(LogLevels.Always, f"SENDING MESSAGE")
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(1,1)]), f"AGENT_INFO: {current_grid.location.x},{current_grid.location.y},{self._agent.get_energy_level()}"
                    #sends the leader their location, their energy level, and status (0) being no status 
                )    
            ) 
            self._agent.send(
                SEND_MESSAGE(
                    AgentIDList([AgentID(1,1)]), f"STATUS:9"
                    #sends leader their status
            )
            )
            print("Sending STATUS:9 to the leader.")
            self._agent.send(END_TURN())
        
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
        if (not self.path and self.survivor_cell is not None):
            #look up their movement queue and direct themselves
            if len(self.detour)>0:
                next_detour = self.detour.pop(0) 
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, next_detour)
                valid_path = self.reconstruct_path(returned_came_from, current_grid, next_detour)
                self.path = valid_path
            elif (current_grid != self.survivor_cell):
                returned_came_from, returned_cost_from_start = self.a_star(current_grid, self.survivor_cell)
                valid_path = self.reconstruct_path(returned_came_from, current_grid, self.survivor_cell)
                self.path = valid_path
            
        if self.path and len(self.path) > 0:
            next_location = self.path.pop(0)  # Get the next step in the path and remove it from the list
            agent_location = self._agent.get_location()
            direction = self.get_direction_to_move(agent_location.x, agent_location.y,
                                                   next_location.location.x, next_location.location.y)
            self.send_and_end_turn(MOVE(direction))  # Send the move command for the calculated direction
            SEND_MESSAGE(
                AgentIDList([AgentID(1, 1)]), f"STATUS:2"
            )
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