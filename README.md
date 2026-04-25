# 2D Runner Platform Game

A simple 2D runner platform game built using Python and Pygame. The player can move left and right and jump onto randomly positioned platforms. This game serves as a basic example of how to create a platformer using Pygame.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Controls](#controls)
- [Game Mechanics](#game-mechanics)
- [Config Notes](#config-notes)
- [Contributing](#contributing)
- [License](#license)

## Features

- Player movement (left, right, jump)
- Gravity and collision detection
- Randomly positioned platforms
- Simple graphics

## Installation

To run this game, you need to have Python and Pygame installed on your system.

1. **Install Python**: Download and install Python from [python.org](https://www.python.org/downloads/).

2. **Install Pygame**: Open your terminal or command prompt and run the following command:

```bash
pip install pygame
```


## Usage

Run the game from the project root:

```bash
python main.py
```

Legacy compatibility entry point:

```bash
python runnergame.py
```

## Controls

- **Up Arrow**: Jump
- **Left Arrow**: Slow world scroll / move relative to the auto-run camera
- **Right Arrow**: Speed up world scroll / move relative to the auto-run camera
- **Enter**: Select menu item
- **Escape**: Return to main menu (during gameplay)

## Game Mechanics

- The player starts on the ground and can jump onto platforms.
- The game uses an auto-run style camera that keeps the runner near a fixed x-position.
- Left/right input changes relative movement against the scrolling world.
- The game features basic gravity, making the player fall back to the ground after jumping.
- Platforms are randomly generated in different positions.

## Config Notes

- `background.image` is currently reserved and not rendered yet.
- `obstacles.*` values are currently reserved and not used in active gameplay.
- Core active gameplay values are `background.color`, `player.*`, and `platforms.*`.

## Contributing

Contributions are welcome! If you'd like to contribute to this project, please fork the repository and submit a pull request with your changes.

## License

No license file is currently provided in this repository.


