#!/usr/bin/env python3
# Python 3.6

#TODO:
# Watch enemy ships, evaluate and decide to hit.
# Give bots a general direction to go if nothing good nearby
# Judge value of harvest x2 vs move and harvest before moving.
# Evaluate board state and E(R) of bot when spawning new ship
# Consider sorting ships by value to prioritise.
# Use random.choice() instead of first element of list for directions.
# Use proper pathfinding to destination
#
# Consider a script with one efficient bot and the rest blocking the enemy shipyard

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

FULL_HOLD_PROPORTION = .75 # proportion of hold to fill before coming home
HOMETIME_TRAVEL_BUFFER = 2.5
MIN_HALITE_IGNORED = 50 #constants.MAX_HALITE / 10
MAX_SHIPS = 16 # Stop building ships. This should realistically be adjusted based on map size or map value.
DOCKBLOCK_STRAT = False # Sends one ship to block enemy home port in 2p game. Only effective on rudimentary bots using naive move.

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
ship_status = {}
destination_list = {}
next_turn_positions = []


def scan_radius(ship, scan_range):
    # TODO test whether this needs to be normalised?
    xrange = range(ship.position.x - scan_range, ship.position.x + scan_range + 1)
    yrange = range(ship.position.y - scan_range, ship.position.y + scan_range + 1)
    #xrange = range(me.shipyard.position.x - scan_range, me.shipyard.position.x + scan_range + 1)
    #yrange = range(me.shipyard.position.y - scan_range, me.shipyard.position.y + scan_range + 1)
    #logging.info("Scanning range: {}-{},{}-{}".format(ship.position.x - scan_range, ship.position.x - scan_range + 1, ship.position.y - scan_range, ship.position.y - scan_range + 1))
    highest_halite = MIN_HALITE_IGNORED*4
    candidate_cell = None
    for x in xrange:    # TODO: consider doing this once a turn and ordering, then take first in list and pop.
        for y in yrange:
            cell = game_map[Position(x,y)]
            if cell.halite_amount > highest_halite and cell.position not in destination_list:
                candidate_cell = cell.position
                highest_halite = cell.halite_amount
    return candidate_cell


def get_nearest_dropoff_position(ship, me):
    closest_dropoff = me.shipyard.position
    closest_dropoff_distance = game_map.calculate_distance(ship.position, me.shipyard.position)
    for dropoff in me.get_dropoffs():
        dist = game_map.calculate_distance(ship.position, dropoff.position)
        if closest_dropoff_distance > dist:
            closest_dropoff_distance = dist
            closest_dropoff = dropoff.position
    return closest_dropoff

def safe_move(ship, destination):
    if ship.position == destination and destination not in next_turn_positions:    # Harvesting
        logging.info("Harvesting.")
        next_turn_positions.append(ship.position)
        command_queue.append(ship.stay_still())
        return
    try:        # Valid, safe move detected
        move = [dir_item for dir_item in game_map.get_unsafe_moves(ship.position, destination) if ship.position.directional_offset(dir_item) not in next_turn_positions][0]
        logging.info("Move plan: {}".format(ship.position.directional_offset(move)))
        logging.info("next_turn_positions list: {}".format(next_turn_positions))
            #TODO: try left or right if up/down direction takes ship farther from base due to tailgater.
        next_turn_positions.append(ship.position.directional_offset(move))
        command_queue.append(ship.move(move))
        logging.info("Moving as desired to {}.".format(ship.position.directional_offset(move)))
        return
    except:     # Can't make favourite move, get out of the way or wait in place.
        try:
            pos = random.choice([pos_item for pos_item in ship.position.get_surrounding_cardinals() if pos_item not in next_turn_positions])
            #pos = [pos_item for pos_item in ship.position.get_surrounding_cardinals() if pos_item not in next_turn_positions][0]
            move = game_map.get_unsafe_moves(ship.position, pos)[0] #TODO: Consider random.choice here, need to reset seed.
            next_turn_positions.append(ship.position.directional_offset(move)) # Using directional_offset instead of pos variable to avoid random reseed
            #next_turn_positions.append(pos) # Using directional_offset instead of pos variable to avoid random reseed
            command_queue.append(ship.move(move))
            logging.info("Can't move to {} as desired: Random position found instead: {}.".format(destination, ship.position.directional_offset(move)))
            return
        except Exception as e:     # No surrounding positions free
            logging.info("ERROR: {}".format(e))
            logging.info("No free positions, sitting still and hoping not to die")
            next_turn_positions.append(ship.position)
            command_queue.append(ship.stay_still())
            return

game.ready("MyBot")
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

############################################
############################################
""" <<<Game Loop>>> """
############################################
############################################

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    command_queue = []
    next_turn_positions = []

    # Remove dead ships from dictionary
    r = dict(ship_status)
    for key in ship_status:
        if key not in [ x.id for x in me.get_ships() ]:
            del r[key]
            # TODO: remove from destination_list
    ship_status = dict(r)
    logging.info(ship_status)


    ############################################
    ############ Shipyard Commands #############
    ############################################
    # TODO: Calculate board value when deciding whether to spawn a ship (calc their expected return)
    current_ship_count = len(me.get_ships()) #TODO: If this is used, need to adjust test to account for map size/value

    #ship_income_per_turn =  0# TODO: Work this out!
    #expected_ship_value = (constants.MAX_TURNS-game.turn_number) * ship_income_per_turn
    #if expected_ship_value > constants.SHIP_COST and me.halite_amount >= constants.SHIP_COST:

    if game.turn_number <= (constants.MAX_TURNS*.5) and me.halite_amount >= constants.SHIP_COST and current_ship_count < MAX_SHIPS:
        if me.shipyard.position not in next_turn_positions:
            command_queue.append(me.shipyard.spawn())
            next_turn_positions.append(me.shipyard.position)
            logging.info("Building a new turtle.")


    ############################################
    ########## Initial Ship Commands ###########
    ############################################
    logging.info('RUNNING INITIAL SHIP COMMANDS')
    for ship in me.get_ships():
        ### Assign job to new ship: ###
        if ship.id not in ship_status:
            if DOCKBLOCK_STRAT and game.turn_number <= 5 and len(game.players) == 2 and "dockblock" not in ship_status.values():
                ship_status[ship.id] = "dockblock"
            else:
                ship_status[ship.id] = "exploring"

        logging.info("1ST LOOP: Ship: {} at {} has job: {}. Cargo: {}, Cell Halite: {}".format(ship.id,
            ship.position, ship_status[ship.id], ship.halite_amount, game_map[ship.position].halite_amount))

        # Identify ships dead in the water, add to next_turn_positions before other commands.
        sufficient_fuel = ship.halite_amount >= game_map[ship.position].halite_amount / 10
        if not sufficient_fuel: # Can't afford to move off tile.
            logging.info("Out of fuel, harvesting.")
            if not ship_status[ship.id] == "dockblock":
                ship_status[ship.id] = "harvesting"
            next_turn_positions.append(ship.position)
            command_queue.append(ship.stay_still())
            continue

    ############################################
    ########## High Priority Commands ##########
    ############################################
    logging.info('RUNNING HIGH PRIORITY SHIP COMMANDS')
    for ship in me.get_ships():

        sufficient_fuel = ship.halite_amount >= game_map[ship.position].halite_amount / 10
        if not sufficient_fuel: # Already harvesting from first pass.
            continue

        # Check if enemy ship is close
            # Compare halite cargo, if theirs is higher:
                # Determine which direction they are moving, and collide/shepherd.
            # If self is higher, evade.

        ### Game ending soon, call all ships home ###
        turns_remaining = (constants.MAX_TURNS - game.turn_number)
        if turns_remaining < constants.WIDTH/2 * HOMETIME_TRAVEL_BUFFER: # Allow some buffer time to get home.
            logging.info("Hometime!")
            dropoff_position = get_nearest_dropoff_position(ship, me)
            if turns_remaining > game_map.calculate_distance(ship.position, dropoff_position) * HOMETIME_TRAVEL_BUFFER:# and turns_remaining > len(me.get_ships()):
                ship_status[ship.id] = "exploring"
                pass # close enough to home, work a bit longer
            else:
                ship_status[ship.id] = "going_to_bed"
                ### Wait on shipyard, allow destruction ###
                if ship.position == dropoff_position:
                    command_queue.append(ship.stay_still())
                    continue
                ### Force move when next to shipyard, kill layabouts ###
                elif game_map.calculate_distance(ship.position, dropoff_position) == 1:
                    move = random.choice(game_map.get_unsafe_moves(ship.position, dropoff_position))
                    command_queue.append(ship.move(move))
                    continue
                ### Safe move toward shipyard ###
                else:
                    safe_move(ship, dropoff_position)
                    continue

        ### Explorer harvests instead of moving ###
        if current_ship_count == 1 or current_ship_count > 6 or game.turn_number > (constants.MAX_TURNS*.5):
            full_hold_check = ship.halite_amount >= constants.MAX_HALITE * FULL_HOLD_PROPORTION
        else: # Come home early to buy more ships.
            full_hold_check = ship.halite_amount >= constants.SHIP_COST/current_ship_count*1.1
            # TODO: Replace the 1.1 buffer above by calculating the cost to get home for each ship, regardless of individual holds, and send them all home?
        if ship_status[ship.id] == "exploring" or (ship_status[ship.id] == "harvesting" and sufficient_fuel):
            if full_hold_check and (game_map[ship.position].halite_amount < 500 or ship.halite_amount >= constants.MAX_HALITE *.95): # Holding too much, return
                ship_status[ship.id] = "returning"
                logging.info("Changing job to returning")
                continue
            elif game_map[ship.position].halite_amount > MIN_HALITE_IGNORED:      # Rich vein, harvest
                ship_status[ship.id] = "harvesting"
                safe_move(ship, ship.position) # Harvest
                continue
            else:                                                                 # Resume exploring
                ship_status[ship.id] = "exploring"
                logging.info("Changing job to exploring")
                continue

        ### Returning ship harvests on the way home ###
        #if ship_status[ship.id] == "returning" and game_map[ship.position].halite_amount > MIN_HALITE_IGNORED*2 and ship.halite_amount <= constants.MAX_HALITE - 30:
        #    safe_move(ship, ship.position) # Harvest
        #    continue



    ############################################
    ########## Low Priority Commands ###########
    ############################################
    logging.info('RUNNING LOW PRIORITY SHIP COMMANDS')
    for ship in me.get_ships():
        logging.info("2ND LOOP: Ship: {} at {} has job: {}. Cargo: {}, Cell Halite: {}".format(ship.id,
            ship.position, ship_status[ship.id], ship.halite_amount, game_map[ship.position].halite_amount))

        ### Dockblock mission: ###
        #TODO: needs testing
        if ship_status[ship.id] == "dockblock":
            if ship.halite_amount < game_map[ship.position].halite_amount / 10: # Already harvesting fuel
                continue
            #for player_id, player in game.players.items():
            #    if player_id != game.my_id:
            #        dockblock_coords = player.shipyard.position
            dockblock_coords = [player.shipyard.position for player_id, player in game.players.items() if player_id != game.my_id][0]
            try:
                desired_direction = game_map.get_unsafe_moves(ship.position, dockblock_coords)[0]
            except: # Arrived at dock
                next_turn_positions.append(ship.position)
                continue
            desired_pos = ship.position.directional_offset(desired_direction)
            # Check if desired_pos is threatened, checking this can neuter the bot so consider risking it.
            be_still = False
            #sufficient_fuel = ship.halite_amount >= game_map[ship.position].halite_amount / 10
            if (game_map[desired_pos].is_occupied and me.has_ship(game_map[desired_pos].ship.id) == False):
                next_turn_positions.append(ship.position)
                command_queue.append(ship.stay_still()) # Wait for cell to clear.
                continue
            for position in desired_pos.get_surrounding_cardinals():
                cell = game_map[position]
                if (cell.is_occupied and me.has_ship(cell.ship.id) == False): #cell.position != ship.position: # Enemy ship detected
                    next_turn_positions.append(ship.position)
                    command_queue.append(ship.stay_still()) # Wait for cell to clear.
                    be_still = True
                    break
            if not be_still:
                next_turn_positions.append(desired_pos)
                command_queue.append(ship.move(desired_direction))
            continue

        ### Holding too much, return to nearest dropoff: ###
        #TODO: consider returning early if waiting to buy new ships and need cash
        elif ship_status[ship.id] == "returning": # Holding too much, return
            #if ship_status[ship.id] == "returning" and game_map[ship.position].halite_amount > MIN_HALITE_IGNORED*2 and ship.halite_amount <= constants.MAX_HALITE - 30:
            #    continue # Already given commend in previous loop.
            dropoff_position = get_nearest_dropoff_position(ship, me)
            if ship.position == dropoff_position: # Arrived home, send back out exploring
                logging.info("Dropped off load at shipyard last turn, go out and explore!")
                destination_list.pop(ship.id, None) # Clear ship's destination entry
                ship_status[ship.id] = "exploring"
            else:
                logging.info("Moving toward dropoff_position: {}.".format(dropoff_position))
                safe_move(ship, dropoff_position)
                continue

        ### Send ship exploring/harvesting: ###
        if ship_status[ship.id] == "exploring":# and game_map[ship.position].halite_amount <= MIN_HALITE_IGNORED:
            logging.info("Exploring!")
            #logging.info(constants.WIDTH)

            if ship.id in destination_list:
                destination = destination_list[ship.id]
                if ship.position != destination:
                    safe_move(ship, destination)
                    continue
                else:   # At destination, not enough Halite to harvest, so reset.
                    destination_list.pop(ship.id, None) # Clear ship's destination entry

            if ship.id not in destination_list:
                ### Check what side of the map home is on, split map in half. ###
                #if me.shipyard.position.x <= constants.WIDTH/2:
                #    xrange = range(0, int(constants.WIDTH/2 + 1))
                #else:
                #    xrange = range(int(constants.WIDTH/2), constants.WIDTH + 1)
                #yrange = range(constants.HEIGHT)

                ### Search radii of 3,6,9 and 12 ###
                for i in range(3,13,3):
                    target_cell = scan_radius(ship, i)
                    if target_cell:
                        break
                if target_cell:
                    destination_list[ship.id] = target_cell
                else: # No valuable cells within radius, move randomly. TODO: Do something better.
                    target_cell = ship.position.directional_offset(random.choice([Direction.North, Direction.West, Direction.South, Direction.East])) # TODO: choose better here, adventure!.
                safe_move(ship, target_cell)

            '''
            # Find neighbouring cell with highest halite, otherwise random.
            highest_halite = 0
            target_cell = ship.position.directional_offset(random.choice([Direction.North, Direction.West, Direction.South, Direction.East])) # TODO: choose better here, adventure!.
            for cell_pos in ship.position.get_surrounding_cardinals(): # return a list of the positions of each cardinal direction from the given position.
                local_halite = game_map[cell_pos].halite_amount # return the halite at a given map location.
                if cell_pos not in next_turn_positions and local_halite > highest_halite:
                    highest_halite = local_halite
                    if local_halite > MIN_HALITE_IGNORED:
                        target_cell = cell_pos
                    logging.info("Better halite ({}) detected nearby in cell {}".format(local_halite, target_cell))
            if highest_halite == 0:
                logging.info("No halite in neighbouring cells, travelling randomly to {}.".format(target_cell))
            safe_move(ship, target_cell)
            '''
            continue

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
