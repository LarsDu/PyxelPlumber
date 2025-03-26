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




## Developer notes

Edit graphics, tilemaps, and sound

```
pyxel edit pyxel_plumber/assets/
```

### Development environment setup
Run the following to get pre-commit hooks for automating code linting.
```
pre-commit install
```