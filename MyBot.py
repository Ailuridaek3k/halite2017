# imports
import hlt
import logging
import math
import random
import numpy as np
import scipy.spatial.distance
import collections
from hlt.entity import Position

# communication with game engine
game = hlt.Game("Csinensis")
# start message
logging.info("Joining the game")

PARALLELTHRESHOLD = 3
SHIPTHRESHOLD = 8

# calculates how dangerous the planet is
def planetquality(ship, planet, ship_targets, dock_attempts):
    count_in_targets = len([target for target in ship_targets.values() if target == planet])
    dist = ship.calculate_distance_between(planet)
    pqual = (
        -50*int(planet.is_owned() and planet.owner == ship.owner and not planet.is_full())
        + 2000*int(planet.is_full() and planet.owner == ship.owner)
        + 100*int(planet.is_owned() and planet.owner != ship.owner)
        + 200 * count_in_targets
        + dist
        - 50 * int(dist < 10)
        # bigger owned planets by other people are less attractive
        - 2*(0.5 - int(planet.is_owned() and planet.owner != ship.owner))*planet.radius)
    return pqual

class NoShipAvailable(Exception):
    pass

cornershipID = None
def cornershipfinder():
    '''
    :return: 8th ship that isn't docked (not the ID)
    '''
    global cornershipID
    # if you don't do this then cornershipID creates a new local var with the same name
    ships = game_map.get_me().all_ships()
    if len(ships) <= SHIPTHRESHOLD and cornershipID is None:
        raise NoShipAvailable()
    if cornershipID is None:
        for ship in ships:
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                continue
            cornershipID = ship.id
            return ship
        # make sure if all ships are docked we don't exist the loop
        raise NoShipAvailable()
    else:
        if game_map.get_me().get_ship(cornershipID) is not None:
            return game_map.get_me().get_ship(cornershipID)
        else:
            cornershipID = None
            return cornershipfinder()


def cornershipmove():
    ship = cornershipfinder()
    shippos = np.array([[ship.x, ship.y]])
    corners = np.array([[0, 0],
                       [game_map.width, game_map.height],
                       [0, game_map.height],
                       [game_map.width, 0]])
    distances = scipy.spatial.distance.cdist(shippos, corners)
    index, distance = min(enumerate(distances[0]), key=lambda distance: distance[1])
    desiredcornerX, desiredcornerY = corners[index]
    navigate_command = ship.navigate(
        ship.closest_point_to(Position(desiredcornerX, desiredcornerY)),
        game_map,
        speed=int(hlt.constants.MAX_SPEED),
        ignore_ships=False, angular_step=8)
    if navigate_command:
        command_queue.append(navigate_command)

turn_number = 0
while True:
    # turn start
    turn_number += 1
    game_map = game.update_map()

    dock_attempts = {}
    ship_targets = {}

    target_moves = collections.defaultdict(list)

    # define commands sent to halite engine
    command_queue = []

    # move the cornership to the corner
    try:
        cornershipmove()
    except NoShipAvailable:
        pass

    # for avoiding timeouts due to too many active ships
    shiplist = game_map.get_me().all_ships()
    if len(shiplist) >= 400:
        shiplist = shiplist[:-400]

    # avoid crashing into each other at the start of the game
    if turn_number == 1:
        shiplist = list(sorted(shiplist, key=lambda s: (s.y, s.x)))

    # for the ships in my possession
    for ship in shiplist:
        # Ship docked?
        if ship.docking_status != ship.DockingStatus.UNDOCKED or ship.id == cornershipID:
            # Skip ship
            continue

        sortedplanets = sorted(game_map.all_planets(), key=lambda planet: planetquality(ship, planet, ship_targets, dock_attempts))
        # For the planets in the game
        for planet in sortedplanets:
            # Planet owned?

            # If we can dock
            if (
                    ship.can_dock(planet) and
                    # don't try to dock on a planet someone else owns
                    not (planet.is_owned() and planet.owner != ship.owner) and
                    not (planet.is_owned() and planet.owner == ship.owner and planet.is_full())):
                # We add the command by appending it to the command_queue
                dock_attempts[planet] = ship
                command_queue.append(ship.dock(planet))
                break
            else:
                # If we can't dock

                target_object = planet
                if planet.is_owned() and planet.owner != ship.owner:
                    # attack the docked ships
                    target_object = planet.all_docked_ships()[0]

                ship_targets[ship] = target_object
                if target_object in target_moves and len(shiplist) <= PARALLELTHRESHOLD:
                    navigate_command = target_moves[target_object][0].with_id(ship.id)
                elif target_object:
                    navigate_command = ship.navigate(
                        ship.closest_point_to(target_object),
                        game_map,
                        speed=int(hlt.constants.MAX_SPEED),
                        ignore_ships=False, angular_step=8)
                    if navigate_command:
                        target_moves[target_object].append(navigate_command)
            if navigate_command:
                command_queue.append(navigate_command)
                break


    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
