# imports
import hlt
import logging
import math
import random

# communication with game engine
game = hlt.Game("Csinensis")
# start message
logging.info("Joining the game")

#TODO: Make it so ships dont crash into each other

# calculates how dangerous the planet is
def planetquality(ship, planet, ship_targets, dock_attempts):
    count_in_targets = len([target for target in ship_targets.values() if target == planet])
    message = "The dock attempts in planetquality are" + str(dock_attempts)
    logging.info(message)
    pqual = (
        -20*int(planet.is_owned() and planet.owner == ship.owner and not planet.is_full())
        + 1000 * int(planet in dock_attempts)
        + 100*int(planet.is_owned() and planet.owner != ship.owner)
        + 200*count_in_targets
        + ship.calculate_distance_between(planet)
        # bigger owned planets by other people are less attractive
        - 2*(0.5 - int(planet.is_owned() and planet.owner != ship.owner))*planet.radius)

    message2 = "The planetquality score for" + str(planet) + "is" + str(pqual)
    logging.info(message2)

    return pqual

'''
def monotonicDeflection(seed=0, deflection_range=math.pi / 4):
    deflection = seed
    while True:
        deflection += random.uniform(0, deflection_range)
        yield deflection

        deflections = monotonicDeflection()
'''

while True:
    # turn start
    game_map = game.update_map()

    dock_attempts = {}
    ship_targets = {}

    # define commands sent to halite engine
    command_queue = []
    # for the ships in my possession
    for ship in game_map.get_me().all_ships():
        # Ship docked?
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip ship
            continue

        #logging
        sortedplanets = sorted(game_map.all_planets(), key=lambda planet: planetquality(ship, planet, ship_targets, dock_attempts))
        messagesort = "The order of planets for" + str(ship) + "is" + str(sortedplanets)
        logging.info(messagesort)

        # For the planets in the game
        for planet in sortedplanets:
            # Planet owned?
            if (planet.is_owned() and planet.owner == ship.owner) or planet in dock_attempts:
                continue

            # If we can dock
            if (
                    ship.can_dock(planet) and
                    # don't try to dock on a planet someone else owns
                    not (planet.is_owned() and planet.owner != ship.owner) and
                    not planet in dock_attempts):
                # We add the command by appending it to the command_queue
                dock_attempts[planet] = ship
                command_queue.append(ship.dock(planet))
            else:
                # If we can't dock

                target_object = planet
                if planet.is_owned() and planet.owner != ship.owner:
                    # attack the docked ships
                    target_object = planet.all_docked_ships()[0]

                ship_targets[ship] = target_object
                navigate_command = ship.navigate(
                    ship.closest_point_to(target_object),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False)
                # movement
                if navigate_command:
                    command_queue.append(navigate_command)
            break

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
