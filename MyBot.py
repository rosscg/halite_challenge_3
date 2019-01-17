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

FULL_HOLD_PROPORTION = .95 # proportion of hold to fill before coming home
HOMETIME_TRAVEL_BUFFER = 1.8

""" <<<Game Begin>>> """
# This game object contains the initial game state.
game = hlt.Game()
ship_status = {}
next_turn_positions = []


def safe_move(ship, destination):
    if ship.position == destination and ship.position not in next_turn_positions:    # Harvesting
        next_turn_positions.append(ship.position)
        command_queue.append(ship.stay_still())
        return
    try:        # Valid, safe move detected
        logging.info("Movement allowed.")
        move = [item for item in game_map.get_unsafe_moves(ship.position, destination) if item not in next_turn_positions][0]
        next_turn_positions.append(ship.position.directional_offset(move))
        command_queue.append(ship.move(move))
        return
    except:     # Can't make favourite move, wait in place or get out of the way.
        logging.info("Can't move where I want. Going elsewhere.")
        try:
            logging.info("Random position found, going there instead.")
            pos = [item for item in ship.position.get_surrounding_cardinals() if item not in next_turn_positions][0]
            move = game_map.get_unsafe_moves(ship.position, pos)[0]
            next_turn_positions.append(pos)
            command_queue.append(ship.move(move))
            return
        except:     # No surrounding positions free
            logging.info("No free position, sitting still and hoping not to die")
            #pos = ship.position.directional_offset(random.choice([ Direction.North, Direction.West ])) ### Arbitrary death direction, TODO: be smarter.
            next_turn_positions.append(ship.position)
            command_queue.append(ship.stay_still())
            return


# Sends one ship to block enemy home port in 2p game. Only effective on rudimentary bots using naive move.
dockblock_coords = False
for player_id, player in game.players.items():
    if player_id != game.my_id and len(game.players) == 2:
        dockblock_coords = player.shipyard.position

game.ready("TestBot")

logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    command_queue = []
    next_turn_positions = []


    # TODO: Calculate baord value when deciding whether to spawn a ship (calc their expected return)
    friendly_at_home = False
    if game_map[me.shipyard].is_occupied:
        friendly_at_home = me.has_ship(game_map[me.shipyard].ship.id)
    if game.turn_number <= (constants.MAX_TURNS*.5) and me.halite_amount >= constants.SHIP_COST:
        if me.shipyard.position not in next_turn_positions and not friendly_at_home:
            command_queue.append(me.shipyard.spawn())


    #TODO: Consider sorting ships by value to prioritise.
    for ship in me.get_ships():
        logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))
        try:
            logging.info(ship_status[ship.id])
        except:
            pass

        if ship.halite_amount < game_map[ship.position].halite_amount / 10: # Can't afford to move off tile.
            safe_move(ship, ship.position) # Harvest
            continue

        ### Game ending, call all ships home ###
        turns_remaining = (constants.MAX_TURNS - game.turn_number)
        if turns_remaining < constants.WIDTH * HOMETIME_TRAVEL_BUFFER: # Allow some buffer time to get home.
            # TODO: find nearest dropoff rather than only using shipyard.
            if turns_remaining > game_map.calculate_distance(ship.position, me.shipyard.position) * HOMETIME_TRAVEL_BUFFER and turns_remaining > len(me.get_ships()):
                pass # close to home, work a bit longer
            else:
                ship_status[ship.id] = "returning"
                ### Wait on shipyard, allow destruction ###
                if ship.position == me.shipyard.position:
                    command_queue.append(ship.stay_still())
                    continue
                ### Force move when next to shipyard ###
                elif game_map.calculate_distance(ship.position, me.shipyard.position) == 1:
                    move = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
                    #move = ship.position.directional_offset(desired_direction)
                    command_queue.append(ship.move(move))
                    continue
                ### Safe move toward shipyard ###
                else:
                    #move = game_map.naive_navigate(ship, me.shipyard.position)
                    safe_move(ship, me.shipyard.position)
                    continue

        # Check if enemy ship is close
            # Compare halite cargo, if theirs is higher:
                # Determine which direction they are moving, and collide/shepherd.
            # If self is higher, evade.

        ### Assign job to new ship: ###
        if ship.id not in ship_status:
            if dockblock_coords and game.turn_number <= 5 and "dockblock" not in ship_status.values():
                ship_status[ship.id] = "dockblock"
            else:
                ship_status[ship.id] = "exploring"

        ### Dockblock mission: ###
        if ship_status[ship.id] == "dockblock":
            desired_direction = game_map.naive_navigate(ship, dockblock_coords)
            desired_pos = ship.position.directional_offset(desired_direction)
            # Check if desired_pos is threatened
            be_still = False
            for position in desired_pos.get_surrounding_cardinals():
                cell = game_map[position]
                if cell.is_occupied and cell.position != ship.position:
                    next_turn_positions.append(ship.position)
                    command_queue.append(ship.stay_still()) # Wait for cell to clear.
                    be_still = True
                    break
            if not be_still:
                next_turn_positions.append(ship.position.directional_offset(desired_direction))
                command_queue.append(ship.move(desired_direction))
            continue

        ### Holding too much, return to nearest dropoff: ###
        elif ship_status[ship.id] == "returning" or ship.halite_amount >= constants.MAX_HALITE * FULL_HOLD_PROPORTION: # Holding too much, return
            ship_status[ship.id] = "returning"
            ### Get closest dropoff position: ### TODO: Move into method.
            closest_dropoff = me.shipyard.position
            closest_dropoff_distance = game_map.calculate_distance(ship.position, me.shipyard.position)
            for dropoff in me.get_dropoffs():
                dist = game_map.calculate_distance(ship.position, dropoff.position)
                if closest_dropoff_distance > dist:
                    closest_dropoff_distance = dist
                    closest_dropoff = dropoff.position

            if ship.position == closest_dropoff: # Arrived home, send back out exploring
                ship_status[ship.id] = "exploring"
            else:
                safe_move(ship, closest_dropoff)
                continue

        ### Send ship exploring/harvesting: ###
        if ship_status[ship.id] == "exploring":
            ### Current tile too poor, explore: ###
            if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                #target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ]))

                #TODO: Check if neighbouring cell has Halite over 10%, otherwise harvest:

                # Find neighbouring cell with highest halite, otherwise random.
                highest_halite = 0
                target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.West ])) # TODO: choose better here.
                for cell_pos in ship.position.get_surrounding_cardinals(): # return a list of the positions of each cardinal direction from the given position.
                    cell = game_map[cell_pos]
                    present_halite = cell.halite_amount # return the halite at a given map location.
                    friendly_occupier = False
                    #if cell.is_occupied:    # Ship detected on cell
                    #    friendly_occupier = me.has_ship(cell.ship.id)
                    if cell.position in next_turn_positions:
                        friendly_occupier = True
                    if not friendly_occupier and present_halite > highest_halite: # TODO: Update to planned moves later.
                        highest_halite = present_halite
                        #if present_halite > constants.MAX_HALITE / 10:
                        target_cell = cell_pos
                safe_move(ship, target_cell)
                continue

            ### Harvest: ###
            else:
                logging.info("Attempting to harvest.")
                safe_move(ship, ship.position) # Harvest
                continue

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
