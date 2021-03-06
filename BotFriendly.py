#!/usr/bin/env python3
# Python 3.6

##############################################################################
##### This is bot used for testing. It explores cells next to the current ####
##### ship, otherwise moving randomly. Still using naive_navigate method. ####
##############################################################################

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

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
ship_status = {}

# Sends one ship to block enemy home port in 2p game. Only effective on rudimentary bots using naive move.
dockblock_coords = False
for player_id, player in game.players.items():
    if player_id != game.my_id and len(game.players) == 2:
        #dockblock_coords = player.shipyard.position
        pass

game.ready("FriendlyBot")

logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    command_queue = []


    for ship in me.get_ships():
        #logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))

        if ship.halite_amount < game_map[ship.position].halite_amount / 10: # Can't afford to move off tile.
            command_queue.append(ship.stay_still())
            continue

        ### Assign job to new ship: ###
        if ship.id not in ship_status:
            if dockblock_coords and game.turn_number <= 5 and "dockblock" not in ship_status.values():
                ship_status[ship.id] = "dockblock"
            else:
                ship_status[ship.id] = "exploring"

        ### Dockblock mission: ###
        if ship_status[ship.id] == "dockblock":
            move = game_map.naive_navigate(ship, dockblock_coords)
            command_queue.append(ship.move(move))

        ### Holding too much, return to nearest dropoff: ###
        elif ship_status[ship.id] == "returning" or ship.halite_amount >= constants.MAX_HALITE / 4*3: # Holding too much, return
            ### Get closest dropoff position: ###
            closest_dropoff = me.shipyard.position
            closest_dropoff_dist = game_map.calculate_distance(ship.position, me.shipyard.position)
            for dropoff in me.get_dropoffs():
                dist = game_map.calculate_distance(ship.position, dropoff.position)
                if closest_dropoff_dist > dist:
                    closest_dropoff_dist = dist
                    closest_dropoff = dropoff.position

            if ship.position == closest_dropoff: # Arrived home, send back out exploring
                ship_status[ship.id] = "exploring"
            else:
                move = game_map.naive_navigate(ship, closest_dropoff)
                command_queue.append(ship.move(move))
                ship_status[ship.id] = "returning"
                continue

        ### Send ship exploring/harvesting: ###
        if ship_status[ship.id] == "exploring":
            ### Current tile too poor, explore: ###
            if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                #target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ]))

                # Find neighbouring cell with highest halite, otherwise random.
                highest_halite = 0
                target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ]))
                for cell in ship.position.get_surrounding_cardinals(): # return a list of the positions of each cardinal direction from the given position.
                    present_halite = game_map[cell].halite_amount # return the halite at a given map location.
                    if present_halite > highest_halite:
                        highest_halite = present_halite
                        target_cell = cell

                move = game_map.naive_navigate(ship, target_cell)
                command_queue.append(ship.move(move))
                continue

            ### Harvest: ###
            else:
                command_queue.append(ship.stay_still())
                continue

    friendly_at_home = False
    if game_map[me.shipyard].is_occupied:
        friendly_at_home = me.has_ship(game_map[me.shipyard].ship.id)
    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not friendly_at_home:
        command_queue.append(me.shipyard.spawn())


    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
