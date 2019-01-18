#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

FULL_HOLD_PROPORTION = .2 # proportion of hold to fill before coming home
HOMETIME_TRAVEL_BUFFER = 2
MIN_HALITE_IGNORED = 100 #constants.MAX_HALITE / 10
DOCKBLOCK_STRAT = False # Sends one ship to block enemy home port in 2p game. Only effective on rudimentary bots using naive move.

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
ship_status = {}
next_turn_positions = []

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
        #logging.info("Can't move where I want. Going elsewhere.")
        try:
            pos = random.choice([pos_item for pos_item in ship.position.get_surrounding_cardinals() if pos_item not in next_turn_positions])
            move = game_map.naive_navigate(ship, pos)
            next_turn_positions.append(ship.position.directional_offset(move))
            command_queue.append(ship.move(move))
            logging.info("Can't Move as desired to {}: Random position found instead: {}.".format(destination, ship.position.directional_offset(move)))
            return
        except:     # No surrounding positions free
            logging.info("No free positions, sitting still and hoping not to die")
            next_turn_positions.append(ship.position)
            command_queue.append(ship.stay_still())
            return

game.ready("TestBot")
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
    #ship_list = list(me.get_ships())
    command_queue = []
    next_turn_positions = []

    # Remove dead ships from dictionary
    r = dict(ship_status)
    for key in ship_status:
        if key not in [ x.id for x in me.get_ships() ]:
            del r[key]
    ship_status = dict(r)
    logging.info(ship_status)

    #logging.info(ship_list)


    ############################################
    ############ Shipyard Commands #############
    ############################################
    # TODO: Calculate board value when deciding whether to spawn a ship (calc their expected return)
    #friendly_at_home = False
    #if game_map[me.shipyard].is_occupied:
    #    friendly_at_home = me.has_ship(game_map[me.shipyard].ship.id)
    if game.turn_number <= (constants.MAX_TURNS*.5) and me.halite_amount >= constants.SHIP_COST:
        if me.shipyard.position not in next_turn_positions:# and not friendly_at_home:
            command_queue.append(me.shipyard.spawn())
            next_turn_positions.append(me.shipyard.position)
            logging.info("Building a new turtle.")


    ############################################
    ########## High Priority Commands ##########
    ############################################
    logging.info('Running high priority ship commands')
    for ship in me.get_ships():
        ### Assign job to new ship: ###
        if ship.id not in ship_status:
            if DOCKBLOCK_STRAT and game.turn_number <= 5 and "dockblock" not in ship_status.values():
                ship_status[ship.id] = "dockblock"
            else:
                ship_status[ship.id] = "exploring"

        logging.info("1st Loop: Ship: {} at {} has job: {}. Cargo: {}, Cell Halite: {}".format(ship.id,
            ship.position, ship_status[ship.id], ship.halite_amount, game_map[ship.position].halite_amount))

        sufficient_fuel = ship.halite_amount >= game_map[ship.position].halite_amount / 10
        if not sufficient_fuel: # Can't afford to move off tile.
            logging.info("Out of fuel, harvesting.")
            ship_status[ship.id] = "harvesting"
            next_turn_positions.append(ship.position)
            command_queue.append(ship.stay_still())
            continue

        ### Game ending soon, call all ships home ###
        turns_remaining = (constants.MAX_TURNS - game.turn_number)
        if turns_remaining < constants.WIDTH/2 * HOMETIME_TRAVEL_BUFFER: # Allow some buffer time to get home.
            logging.info("Hometime!")
            dropoff_position = get_nearest_dropoff_position(ship, me)
            if turns_remaining > game_map.calculate_distance(ship.position, dropoff_position) * HOMETIME_TRAVEL_BUFFER:# and turns_remaining > len(me.get_ships()):
                pass # close enough to home, work a bit longer
            else:
                ship_status[ship.id] = "going_to_bed"
                ### Wait on shipyard, allow destruction ###
                if ship.position == dropoff_position:
                    command_queue.append(ship.stay_still())
                    continue
                ### Force move when next to shipyard, kill layabouts ###
                elif game_map.calculate_distance(ship.position, dropoff_position) == 1:
                    move = game_map.get_unsafe_moves(ship.position, dropoff_position)[0] #TODO: May not be best to choose [0] always
                    #move = ship.position.directional_offset(desired_direction)
                    command_queue.append(ship.move(move))
                    continue
                ### Safe move toward shipyard ###
                else:
                    safe_move(ship, dropoff_position)
                    continue

        ### Explorer harvests instead of moving ###
        if ship_status[ship.id] == "exploring" or (ship_status[ship.id] == "harvesting" and sufficient_fuel):
            if ship.halite_amount >= constants.MAX_HALITE * FULL_HOLD_PROPORTION: # Holding too much, return
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



    ############################################
    ########## Low Priority Commands ###########
    ############################################
    logging.info('Running low priority ship commands')
    #TODO: Consider sorting ships by value to prioritise.
    for ship in me.get_ships():
        logging.info("2nd Loop: Ship: {} at {} has job: {}. Cargo: {}, Cell Halite: {}".format(ship.id,
            ship.position, ship_status[ship.id], ship.halite_amount, game_map[ship.position].halite_amount))

        # Check if enemy ship is close
            # Compare halite cargo, if theirs is higher:
                # Determine which direction they are moving, and collide/shepherd.
            # If self is higher, evade.

        ### Dockblock mission: ###
        if ship_status[ship.id] == "dockblock":
            dockblock_coords = False
            for player_id, player in game.players.items():
                if player_id != game.my_id and len(game.players) == 2:
                    dockblock_coords = player.shipyard.position
            desired_direction = game_map.naive_navigate(ship, dockblock_coords)
            desired_pos = ship.position.directional_offset(desired_direction)
            # Check if desired_pos is threatened
            be_still = False
            for position in desired_pos.get_surrounding_cardinals():
                cell = game_map[position]
                if cell.is_occupied and me.has_ship(cell.ship.id) == False: #cell.position != ship.position: # Enemy ship detected
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
            dropoff_position = get_nearest_dropoff_position(ship, me)
            if ship.position == dropoff_position: # Arrived home, send back out exploring
                logging.info("Dropped off load at shipyard last turn, go out and explore!")
                ship_status[ship.id] = "exploring"
            else:
                logging.info("Moving toward dropoff_position: {}.".format(dropoff_position))
                safe_move(ship, dropoff_position)
                continue

        ### Send ship exploring/harvesting: ###
        if ship_status[ship.id] == "exploring":# and game_map[ship.position].halite_amount <= MIN_HALITE_IGNORED:
            logging.info("Exploring!")
            # Find neighbouring cell with highest halite, otherwise random.
            highest_halite = 0
            target_cell = ship.position.directional_offset(random.choice([Direction.North, Direction.West])) # TODO: choose better here, adventure!.
            for cell_pos in ship.position.get_surrounding_cardinals(): # return a list of the positions of each cardinal direction from the given position.
                local_halite = game_map[cell_pos].halite_amount # return the halite at a given map location.
                if cell_pos not in next_turn_positions and local_halite > highest_halite:
                    highest_halite = local_halite
                    #if local_halite > MIN_HALITE_IGNORED: # TODO: Currently will back and forth between two nodes if they are less than threshold. Grass is always greener!
                    target_cell = cell_pos
                    logging.info("Better halite ({}) detected nearby in cell {}".format(local_halite, target_cell))
            if highest_halite == 0:
                logging.info("No halite in neighbouring cells, travelling randomly to {}.".format(target_cell))
            safe_move(ship, target_cell)
            continue

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
