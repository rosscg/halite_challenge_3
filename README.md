# Halite Challenge 3
Bot Submission for the 3rd *2 Sigma Halite Challenge* built during a hackathon event at Oxford University in Jan 2019.

The final submission was ec2652823a3399ca6e3246b7e794efd06317ca35, which reached top 10% of players.

All original content is stored in MyBot.py (and any other bot files used for testing). The other files were provided by the challenge and are used for evaluation.

## Running:
The bots can be run locally once the competition has ended on 22/01/19. See the Halite-README.md for instructions.

##### TODO:
Key aspects not addressed due to time constraints are listed in the script header and include:
* **Destination Choice** -- The most limiting current issue is turtles waiting behind harvesting turtles. When choosing a destination, consider evaluating the path to the destination and checking whether cells along the path have already been marked for harvest by a turtle in front of the deciding turtle (thus will cause a jam).
* **Turtle spawn decision** -- currently spawns until halfway through the game without consideration for board value and expected return.
* **Turtle priority** -- allow high-value turtles to move before lower-valued turtles.
* **Turtle happiness** -- turtles which cannot move as desired currently sit still or move elsewhere. Instead, consider marking turtle as 'unhappy' and iterate the return/explore loop with a different turtle order until a lower unhappiness value is reached, then process unhappy turtles as required. Include prioritisation of high-value turtles in measurement.
* **Enemy comprehension** -- currently entirely ignored. Consider flee routines and intentional collisions when enemy is of higher value.
* **Dropoffs** -- Not implemented at all. Evaluate board state and place accordingly.
* **Pathfinding** -- Currently chooses the most direct route (with a left-turn bias) and harvests along the way. Consider evaluating shorted path with respect to time and/or Halite toll cost. Also congestion.
