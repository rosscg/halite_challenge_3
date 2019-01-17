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

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
ship_status = {}

FULL_HOLD_PROPORTION = .95 # proportion of hold to fill before coming home

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


    for ship in me.get_ships():
        #logging.info("Ship {} has {} halite.".format(ship.id, ship.halite_amount))
        #command_queue.append(ship.make_dropoff()) # Creates dropoff building

        if ship.halite_amount < game_map[ship.position].halite_amount / 10: # Can't afford to move off tile.
            command_queue.append(ship.stay_still())
            continue

        ### Game ending, call all ships home ###
        turns_remaining = (constants.MAX_TURNS - game.turn_number)
        if turns_remaining < constants.WIDTH * 1.5: # Allow some buffer time to get home.
            # TODO: find nearest dropoff rather than only using shipyard.
            if turns_remaining > game_map.calculate_distance(ship.position, me.shipyard.position) * 1.5:
                pass # close to hom, work a bit longer
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
                ### Naive move toward shipyard ###
                else:
                    move = game_map.naive_navigate(ship, me.shipyard.position)
                    command_queue.append(ship.move(move))
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
                    command_queue.append(ship.stay_still()) # Wait for cell to clear.
                    be_still = True
                    break
            if not be_still:
                command_queue.append(ship.move(desired_direction))
            continue

        ### Holding too much, return to nearest dropoff: ###
        elif ship_status[ship.id] == "returning" or ship.halite_amount >= constants.MAX_HALITE * FULL_HOLD_PROPORTION: # Holding too much, return
            ship_status[ship.id] = "returning"
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
                continue

        ### Send ship exploring/harvesting: ###
        if ship_status[ship.id] == "exploring":
            ### Current tile too poor, explore: ###
            if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10:
                #target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ]))

                # Find neighbouring cell with highest halite, otherwise random.
                highest_halite = 0
                target_cell = ship.position.directional_offset(random.choice([ Direction.North, Direction.South, Direction.East, Direction.West ]))
                for cell_pos in ship.position.get_surrounding_cardinals(): # return a list of the positions of each cardinal direction from the given position.
                    present_halite = game_map[cell_pos].halite_amount # return the halite at a given map location.
                    if present_halite > highest_halite and me.has_ship(game_map[cell_pos].ship) == False: # TODO: Update to planned moves later.
                        highest_halite = present_halite
                        target_cell = cell_pos

                move = game_map.naive_navigate(ship, target_cell)
                command_queue.append(ship.move(move))
                continue

            ### Harvest: ###
            else:
                command_queue.append(ship.stay_still())
                continue

    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
