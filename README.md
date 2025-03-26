# PyxelPlumber

Side-scrolling platformer based on a certain mustached plumber who will not be mentioned due to copyright reasons

## Environment setup

This repo uses [`uv`](https://docs.astral.sh/uv/getting-started/installation) as the package/environment manager. Make sure to install it before proceeding.

The following command will install packages and setup a virtual environment

```bash
# Install packages
uv sync

# Activate virtual enviornment

## Linux/Unix
. .venv/bin/activate

## Windows
. .venv/Scripts/activate
```

# Gameplay

Play the game

```
pyxel run pyxel_plumber/app.py
```


## Developer notes

Edit graphics, tilemaps, and sound

```
pyxel edit pyxel_plumber/assets/pyxel_plumber.pyxres
```

### Development environment setup for contributors

Run the following to get pre-commit hooks for automating code linting.
```
pre-commit install
```

Feel free to fork, or open PRs to this project at will!