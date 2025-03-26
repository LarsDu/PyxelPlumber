import math
import random
from collections.abc import Hashable
from enum import Enum
from functools import partial
from typing import Callable

import pyxel

SCREEN_WIDTH = 256
SCREEN_HEIGHT = 240
DEFAULT_TRANSPARENT_COLOR = 2
TILE_SIZE = 8

SCROLL_BORDER_X = 240 * TILE_SIZE
SCROLL_BORDER_Y = 16 * TILE_SIZE
SCROLL_BORDER_Y_CEILING = -20 * TILE_SIZE
GRAVITY = 0.2
TERMINAL_VELOCITY = 3
MIN_DX = -1
MAX_DX = 1
MIN_DY = -1
MAX_DY = 1

PLAYER_START = (5, 7)

HERO = (0, 1)
DEAD_HERO = (3, 1)
CLIMB_HERO = (2, 0)
COIN = (0, 3)
STAR = ()
SHROOM = (0, 2)
DEAD_SHROOM = (2, 2)
PIRANHA_PLANT = (0, 4)
TURTLE = (0, 5)
SPIKES = (4, 5)
SPRING = (0, 9)
BREAK_BLOCK = (0, 8)
DEBRIS1 = (1, 0)
SPARKLES = (3, 8)
LADDER = (6, 5)
VINE_LADDER = (5, 5)

SOLID_GRASS = (4, 0)
SOLID_CHECKER = (4, 1)
SOLID_BRICK = (5, 0)
SOLID_CERA = (5, 1)
SOLID_BLOCK = (4, 7)
SOLID_GRAY = (5, 7)
SOLID_PIPE_UPPER_LEFT = (4, 8)
SOLID_PIPE_UPPER_RIGHT = (5, 8)
SOLID_PIPE_LOWER_LEFT = (4, 9)
SOLID_PIPE_LOWER_RIGHT = (5, 9)

MOVING_PLAT1 = (0, 10)
MOVING_PLAT2 = (1, 10)
FALL_PLAT1 = (0, 11)
FIREBALL = (2, 11)
FIREBALL_IMG = (3, 11)
FIRE_CIRCLE = (0, 12)
FIRE_CIRCLE_BLOCK = (2, 12)
FIRE_CIRCLE_SPRITE = (1, 12)

BULLET_BILLY_IMG = (0, 6)
BULLET_BILLY_GUN_IMG = (2, 6)
CANNONBALL_IMG = (3, 6)

marker_tiles = {
    HERO,
    COIN,
    SHROOM,
    PIRANHA_PLANT,
    TURTLE,
    SPIKES,
    SPRING,
    BREAK_BLOCK,
    MOVING_PLAT1,
    MOVING_PLAT2,
    FALL_PLAT1,
    FIREBALL,
    FIRE_CIRCLE,
    # FIRE_CIRCLE_BLOCK, # Don't hide this
}
solid_tiles = {
    SOLID_GRASS,
    SOLID_CHECKER,
    SOLID_BRICK,
    SOLID_CERA,
    SOLID_BLOCK,
    SOLID_GRAY,
    SOLID_PIPE_UPPER_LEFT,
    SOLID_PIPE_UPPER_RIGHT,
    SOLID_PIPE_LOWER_LEFT,
    SOLID_PIPE_LOWER_RIGHT,
}


def get_tile(tile_x: float, tile_y: float, tilemap_idx: int = 0) -> tuple[int]:
    """Get the tile being drawn at the current coordinates

    Args:
        tile_x: Tile col index (world_coords_x//TILE_SIZE)
        tile_y: Tile row index (world_coords_7//TILE_SIZE)
    Returns:
        tuple[int]: image_tx, image_ty
          that is, u//8, v//8 for your image
          This is basically a tile id tuple
    """
    return pyxel.tilemaps[tilemap_idx].pget(tile_x, tile_y)


def is_solid_tile(image_tx: float, image_ty: float) -> bool:
    """Given tile_id tuple, determine if it's solid

    Args:
        image_tx: Image col index u//TILE_SIZE
        image_ty: Image row index. v//TILE_SIZE

    """
    if (image_tx, image_ty) in solid_tiles:
        return True
    return False


def is_ladder_tile(image_tx: float, image_ty: float) -> bool:
    """Given tile_id tuple, determine if it's a ladder

    Args:
        image_tx: Image col index u//TILE_SIZE
        image_ty: Image row index. v//TILE_SIZE

    """
    if (image_tx, image_ty) in {LADDER, VINE_LADDER}:
        return True
    return False


def is_tile_at_world_coord_solid(x: float, y: float, tilemap_idx: int = 0) -> bool:
    """Check if the current tile is solid

    Args:
        x: World coord x
        y: World coord y
        tilemap_idx: Tilemap index

    Returns:
        bool: True if the tile is solid
    """
    return is_solid_tile(
        *get_tile(int(x) // TILE_SIZE, int(y) // TILE_SIZE, tilemap_idx)
    )


def is_tile_at_world_coord_ladder(x: float, y: float, tilemap_idx: int = 0) -> bool:
    """Check if the current tile is a ladder

    Args:
        x: World coord x
        y: World coord y
        tilemap_idx: Tilemap index

    Returns:
        bool: True if the tile is a ladder
    """
    return is_ladder_tile(
        *get_tile(int(x) // TILE_SIZE, int(y) // TILE_SIZE, tilemap_idx)
    )


def collide_aabb(
    x1: int, y1: int, w1: int, h1: int, x2: int, y2: int, w2: int, h2: int
) -> bool:
    return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2


def pushback_entity(
    this: "Entity",
    other: "Entity",
    horz_pushback: float = 0,
    vert_pushback: float = 0,
    on_hit: Callable | None = None,
    on_hit_below: Callable | None = None,
    on_hit_above: Callable | None = None,
    on_hit_left: Callable | None = None,
    on_hit_right: Callable | None = None,
    pushback_x_right: bool = True,
    pushback_x_left: bool = True,
    pushback_y_up: bool = True,
    pushback_y_down: bool = True,
) -> None:
    pushback_x = pushback_x_right or pushback_x_left
    pushback_y = pushback_y_up or pushback_y_down

    # Determine collision direction by checking overlap amounts
    left_overlap = (other.x + other.w) - this.x
    right_overlap = (this.x + this.w) - other.x
    top_overlap = (other.y + other.h) - this.y
    bottom_overlap = (this.y + this.h) - other.y

    # Find the smallest overlap to determine collision direction
    min_overlap = min(left_overlap, right_overlap, top_overlap, bottom_overlap)

    def apply_horz_pushback() -> None:
        if pushback_x_left and other.dx > 0:
            other.dx = -horz_pushback
        elif pushback_x_right and other.dx < 0:
            other.dx = horz_pushback

    def apply_vert_pushback() -> None:
        if pushback_y_up and other.dy > 0:
            # If falling, bounce up
            other.dy = -vert_pushback
        elif pushback_y_down and other.dy < 0:
            # If jumping, bounce down
            other.dy = vert_pushback

    at_least_one_hit: bool = False
    # Horizontal collision from right
    if min_overlap == left_overlap and other.dx > 0:
        if pushback_x:
            other.x = this.x - other.w
            apply_horz_pushback()
        if on_hit_right is not None:
            on_hit_right()
        at_least_one_hit = True

    # Horizontal collision from left
    elif min_overlap == right_overlap and other.dx < 0:
        if pushback_x:
            other.x = this.x + this.w
            apply_horz_pushback()
        if on_hit_left is not None:
            on_hit_left()
        at_least_one_hit = True
    # Vertical collision from below (player jumping up)
    elif min_overlap == bottom_overlap and other.dy < 0:
        if pushback_y:
            other.y = this.y + this.h
            apply_vert_pushback()
        if on_hit_below is not None:
            on_hit_below()
        at_least_one_hit = True

    # Vertical collision from above (player falling down)
    elif min_overlap == top_overlap and other.dy > 0:
        if pushback_y:
            other.y = this.y - other.h
            apply_vert_pushback()
            if isinstance(other, Player):
                other.state_key = PlayerStateKey.GROUND
        if on_hit_above is not None:
            on_hit_above()
        at_least_one_hit = True
    if at_least_one_hit and on_hit is not None:
        on_hit()


def check_horizontal_tile_collision(
    x: float, y: float, dx: float, w: float, h: float, tilemap_idx: int = 0
) -> bool:
    """Check if the entity is colliding with a solid tile horizontally"""
    if dx > 0:
        # Top right corner
        if is_tile_at_world_coord_solid(x + w, y, tilemap_idx=tilemap_idx):
            return True
        # Bottom right corner
        if is_tile_at_world_coord_solid(x + w, y + h - 1, tilemap_idx=tilemap_idx):
            return True
    elif dx < 0:
        # Top left corner
        if is_tile_at_world_coord_solid(x, y, tilemap_idx=tilemap_idx):
            return True
        # Bottom left corner
        if is_tile_at_world_coord_solid(x, y + h - 1, tilemap_idx=tilemap_idx):
            return True
    return False


def check_vertical_tile_collision(
    x: float, y: float, dy: float, w: float, h: float, tilemap_idx: int = 0
) -> bool:
    """Check if the entity is colliding with a solid tile vertically"""
    if dy > 0:
        # Bottom left corner
        if is_tile_at_world_coord_solid(x, y + h, tilemap_idx=tilemap_idx):
            return True
        # Bottom right corner
        if is_tile_at_world_coord_solid(x + w, y + h, tilemap_idx=tilemap_idx):
            return True
    elif dy < 0:
        # Top left corner
        if is_tile_at_world_coord_solid(x, y, tilemap_idx=tilemap_idx):
            return True
        # Top right corner
        if is_tile_at_world_coord_solid(x + w, y, tilemap_idx=tilemap_idx):
            return True
    return False


def check_ladder_collision(
    x: float, y: float, w: float, h: float, tilemap_idx: int = 0
) -> bool:
    # Check corners for presence inside ladder
    for cx, cy in [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]:
        if is_tile_at_world_coord_ladder(cx, cy, tilemap_idx=tilemap_idx):
            return True
    return False


def cleanup_entities(entities: list["Entity"]) -> None:
    for entity in entities:
        if not entity.is_alive:
            entities.remove(entity)
            del entity


class Entity:
    def __init__(self, x, y, w, h) -> None:
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.is_active = True
        self.is_alive = True
        self._camera: Camera | None = None
        self._manager: GameManager | None = None
        self.is_colliding = False

    @property
    def camera(self) -> "Camera":
        if self._camera is None:
            self._camera = Camera.instance()
        return self._camera

    @property
    def manager(self) -> "GameManager":
        if self._manager is None:
            self._manager = GameManager.instance()
        return self._manager

    @property
    def sx(self) -> float:
        return self.x - self.camera.x

    @property
    def sy(self) -> float:
        return self.y - self.camera.y

    def draw(self) -> None:
        pass

    def update(self) -> None:
        pass

    def collide_with(self, other: "Entity") -> bool:
        if collide_aabb(
            self.x, self.y, self.w, self.h, other.x, other.y, other.w, other.h
        ):
            self.on_collision(other)
            self.is_colliding = True
            return True
        elif self.is_colliding:
            self.on_collision_end(other)
            self.is_colliding = False
        return False

    def on_collision(self, other: "Entity") -> None:
        pass

    def on_collision_end(self, other: "Entity") -> None:
        pass

    def die(self) -> None:
        # Don't do anything by default
        # some entities die by switching states
        pass


class MovableEntity(Entity):
    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
    ) -> None:
        super().__init__(x, y, w, h)
        self.dx = 0
        self.dy = 0
        self.is_facing_right = True


class DefaultMovableEntity(MovableEntity):
    def __init__(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        marker_tile: tuple[int, int],
        transparent_color: int = DEFAULT_TRANSPARENT_COLOR,
    ) -> None:
        super().__init__(x, y, w, h)
        self.is_facing_right = True
        self.marker_tile = marker_tile
        self.transparent_color = transparent_color

    def draw(self) -> None:
        tx, ty = self.marker_tile
        if abs(self.dx) > 0:
            u = TILE_SIZE * (tx + 1) + TILE_SIZE * (pyxel.frame_count // 4 % 2)
        else:
            u = TILE_SIZE * (tx + 1)
        v = ty * TILE_SIZE
        w = self.w if self.is_facing_right else -self.w
        pyxel.blt(
            self.sx,
            self.sy,
            0,
            u,
            v,
            w,
            self.h,
            self.transparent_color,
        )


class Coin(Entity):
    def draw(self) -> None:
        tx, ty = COIN
        u = (tx + 1) * TILE_SIZE + TILE_SIZE * (pyxel.frame_count // 9 % 3)
        v = ty * TILE_SIZE
        pyxel.blt(
            self.sx,
            self.sy,
            0,
            u,
            v,
            self.w,
            self.h,
            DEFAULT_TRANSPARENT_COLOR,
        )

    def on_collision(self, other):
        if isinstance(other, Player):
            self.manager.coins += 1
            self.die()

    def die(self) -> None:
        self.is_alive = False
        self.manager.particles.append(
            DeathSprite(
                self.x,
                self.y,
                self.w * random.choice([-1, 1]),
                self.h * random.choice([-1, 1]),
                marker_tile=SPARKLES,
                dx=0,
                dy=0,
                feels_gravity=False,
                lifespan_ticks=6,
            )
        )


class BreakBlock(Entity):
    hit_offset_decay = 0.5

    def __init__(self, x: int, y: int, w: int, h: int, hp: int) -> None:
        super().__init__(x, y, w, h)
        self.hp = hp
        self.hit_offset = 0

    def on_collision(self, other: Entity) -> None:
        if isinstance(other, Player):
            pushback_entity(self, other, on_hit_below=self.on_hit_below)

    def draw(self) -> None:
        u, v = (BREAK_BLOCK[0] + 1) * TILE_SIZE, BREAK_BLOCK[1] * TILE_SIZE
        pyxel.blt(
            self.sx,
            self.sy - int(self.hit_offset) * 2,
            0,
            u,
            v,
            self.w,
            self.h,
            DEFAULT_TRANSPARENT_COLOR,
        )
        if self.hit_offset > 0:
            self.hit_offset = max(0, self.hit_offset - self.hit_offset_decay)

    def on_hit_below(self) -> None:
        self.hit_offset = 2
        self.spawn_particles(3, 4)
        self.hp -= 1
        if self.hp <= 0:
            self.break_block()

    def break_block(self) -> None:
        self.is_alive = False

    def spawn_particles(self, min_particles: int, max_particles: int) -> None:
        # Spawn particles or effects
        for _ in range(random.randint(min_particles, max_particles)):
            self.manager.doodads.append(
                DeathSprite(
                    self.x,
                    self.y,
                    self.w,
                    self.h,
                    marker_tile=DEBRIS1,  # Use appropriate tile for block breaking
                    dx=random.uniform(-1, 1),
                    dy=random.uniform(-1, -2),
                    feels_gravity=True,
                    lifespan_ticks=24,
                )
            )


class DeathSprite(DefaultMovableEntity):
    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        marker_tile: tuple[int, int],
        transparent_color: int = DEFAULT_TRANSPARENT_COLOR,
        flip_horizontal: bool = False,
        flip_vertical: bool = False,
        dx: float = 0.1,
        dy: float = -1,
        lifespan_ticks: int = 1000,
        feels_gravity: bool = True,
    ):
        super().__init__(
            x, y, w, h, marker_tile=marker_tile, transparent_color=transparent_color
        )
        self.flip_horizontal = flip_horizontal
        self.flip_vertical = flip_vertical
        self.dx = dx
        self.dy = dy
        self.cur_lifespan = lifespan_ticks
        self.feels_gravity = feels_gravity

    def draw(self) -> None:
        tx, ty = self.marker_tile
        u = tx * TILE_SIZE
        v = ty * TILE_SIZE
        w = self.w if not self.flip_horizontal else -self.w
        h = self.h if not self.flip_vertical else -self.h
        pyxel.blt(self.sx, self.sy, 0, u, v, w, h, self.transparent_color)

    def update(self) -> None:
        self.x += self.dx
        if self.cur_lifespan <= 0:
            self.is_alive = False
        if self.feels_gravity:
            self.dy = min(self.dy + GRAVITY, TERMINAL_VELOCITY)
        self.y += self.dy
        if self.y > Camera.instance().y + SCREEN_HEIGHT:
            self.is_alive = False
        self.cur_lifespan -= 1


class CollidableDeathSprite(DeathSprite):
    def on_collision(self, other: Entity) -> None:
        if isinstance(other, Player):
            pushback_entity(
                self, other, on_hit_below=partial(self.on_hit_player_below, other)
            )

    def on_hit_player_below(self, player: "Player") -> None:
        if self.dy > 0:
            player.die()


class State:
    def __init__(self) -> None:
        self.parent: Entity | Player | None

    def set_parent(self, parent: Entity) -> None:  # FIXME: Entity or Player
        self.parent = parent

    def on_enter(self) -> None:
        if not hasattr(self, "parent"):
            raise AttributeError("State must have a parent")

    def on_exit(self) -> None:
        if not hasattr(self, "parent"):
            raise AttributeError("State must have a parent")

    def update(self) -> None:
        if not hasattr(self, "parent"):
            raise AttributeError("State must have a parent")

    def draw(self) -> None:
        if not hasattr(self, "parent"):
            raise AttributeError("State must have a parent")


class StateMachine:
    def init_state_machine(
        self, state_map: dict[Hashable, State], starting_state_key: Hashable
    ) -> None:
        self.state_map = state_map
        self._state_key = starting_state_key
        self.state = self.state_map[self._state_key]
        for state in self.state_map.values():
            state.set_parent(self)

    @property
    def state_key(self) -> Hashable:
        raise AttributeError("State key is read-only")

    @state_key.setter
    def state_key(self, new_state_key: Hashable) -> None:
        if new_state_key not in self.state_map:
            raise ValueError(f"State key {new_state_key} not found in state map")
        if self._state_key == new_state_key:
            return
        self.state.on_exit()
        self._state_key = new_state_key
        self.state = self.state_map[self._state_key]
        self.state.on_enter()


class PlayerStateKey(Enum):
    GROUND = 0
    AIR = 1
    CLIMB = 2
    DEAD = 3


class PlayerGroundState(State):
    def update(self) -> None:
        parent = self.parent
        # Rather than stopping immediately, we'll slow down
        parent.dx = int(parent.dx * parent.momentum)

        if (
            pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
        ) and parent.x > 0:
            parent.dx = -parent.speed
            parent.is_facing_right = False
        elif (
            pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
        ) and parent.x < SCROLL_BORDER_X:
            parent.dx = parent.speed
            parent.is_facing_right = True

        # Horizontal Movement
        parent.x += parent.dx
        if check_horizontal_tile_collision(
            parent.x, parent.y, parent.dx, parent.w, parent.h, tilemap_idx=0
        ):
            # Undo movement
            parent.x -= parent.dx
            # Stop
            parent.dx = 0

        # Vertical Movement
        ## Apply Gravity
        parent.dy = min(parent.dy + GRAVITY, TERMINAL_VELOCITY)

        if (
            pyxel.btn(pyxel.KEY_UP)
            or pyxel.btn(pyxel.KEY_SPACE)
            or pyxel.btn(pyxel.GAMEPAD1_BUTTON_A)
            or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP)
            or pyxel.btn(pyxel.GAMEPAD1_BUTTON_B)
        ):
            parent.dy = -parent.jump
            parent.state_key = PlayerStateKey.AIR

        parent.y += parent.dy

        if check_vertical_tile_collision(
            parent.x, parent.y, parent.dy, parent.w, parent.h, tilemap_idx=0
        ):
            if parent.dy > 0:
                # Falling and landed on something
                # Snap to top of tile
                parent.y = int((parent.y + parent.h) // TILE_SIZE) * TILE_SIZE - int(
                    parent.h
                )
            else:
                # Hitting ceiling, snap to bottom of tile
                parent.y = (int(parent.y) // TILE_SIZE + 1) * TILE_SIZE
            parent.dy = 0
        else:
            parent.state_key = PlayerStateKey.AIR

        if check_ladder_collision(parent.x, parent.y, parent.w, parent.h):
            parent.state_key = PlayerStateKey.CLIMB

        # Cap boundaries to worldmap
        parent.check_world_bounds()

    def draw(self) -> None:
        parent = self.parent
        tx, ty = HERO[0] + 1, HERO[1]
        if abs(parent.dx) > 0:
            u = TILE_SIZE * (tx + 1) + TILE_SIZE * (pyxel.frame_count // 4 % 2)
        else:
            u = TILE_SIZE * (tx + 1)
        v = ty * TILE_SIZE
        w = parent.w if parent.is_facing_right else -parent.w
        pyxel.blt(
            parent.sx,
            parent.sy,
            0,
            u,
            v,
            w,
            parent.h,
            DEFAULT_TRANSPARENT_COLOR,
        )


class PlayerAirState(State):
    def update(self) -> None:
        parent = self.parent
        # Rather than stopping immediately, we'll slow down
        parent.dx = int(parent.dx * parent.momentum)

        if pyxel.btn(pyxel.KEY_LEFT) and parent.x > 0:
            parent.dx = -parent.speed
            parent.is_facing_right = False
        elif pyxel.btn(pyxel.KEY_RIGHT) and parent.x < SCROLL_BORDER_X:
            parent.dx = parent.speed
            parent.is_facing_right = True

        # Horizontal Movement
        parent.x += parent.dx
        if check_horizontal_tile_collision(
            parent.x, parent.y, parent.dx, parent.w, parent.h, tilemap_idx=0
        ):
            # Undo movement
            parent.x -= parent.dx
            # Stop
            parent.dx = 0

        # Vertical Movement
        ## Apply Gravity
        parent.dy = min(parent.dy + GRAVITY, TERMINAL_VELOCITY)
        parent.y += parent.dy

        if check_vertical_tile_collision(
            parent.x, parent.y, parent.dy, parent.w, parent.h, tilemap_idx=0
        ):
            if parent.dy > 0:
                # Falling and landed on something
                parent.state_key = PlayerStateKey.GROUND
                # Snap to top of tile
                parent.y = int((parent.y + parent.h) // TILE_SIZE) * TILE_SIZE - int(
                    parent.h
                )
            else:
                # Hitting ceiling, snap to bottom of tile
                parent.y = (int(parent.y) // TILE_SIZE + 1) * TILE_SIZE
            parent.dy = 0
        else:
            parent.state_key = PlayerStateKey.AIR

        if check_ladder_collision(parent.x, parent.y, parent.w, parent.h):
            parent.state_key = PlayerStateKey.CLIMB
        parent.check_world_bounds()

    def draw(self) -> None:
        parent = self.parent
        tx, ty = HERO[0] + 1, HERO[1]
        if abs(parent.dx) > 0:
            u = TILE_SIZE * (tx + 1) + TILE_SIZE * (pyxel.frame_count // 4 % 2)
        else:
            u = TILE_SIZE * (tx + 1)
        v = ty * TILE_SIZE
        pyxel.blt(
            parent.sx,
            parent.sy,
            0,
            u,
            v,
            parent.w if parent.is_facing_right else -parent.w,
            parent.h,
            DEFAULT_TRANSPARENT_COLOR,
        )


class PlayerDeathState(State):
    def on_enter(self) -> None:
        if not hasattr(self, "parent"):
            raise AttributeError("State must have a parent")
        self.cur_lifespan = 70
        self.parent.dx = 0
        self.parent.dy = 0
        self.parent.manager.particles.append(
            DeathSprite(
                self.parent.x,
                self.parent.y,
                self.parent.w,
                self.parent.h,
                marker_tile=DEAD_HERO,
                flip_horizontal=self.parent.dx < 0,
                flip_vertical=True,
                dx=random.uniform(-0.1, 0.1),
                dy=-3,
                feels_gravity=True,
                lifespan_ticks=self.cur_lifespan,
            )
        )

    def update(self) -> None:
        self.cur_lifespan -= 1
        if self.cur_lifespan <= 0:
            self.parent.is_alive = False

    def draw(self) -> None:
        pass


class PlayerClimbState(State):
    def update(self) -> None:
        parent = self.parent

        parent.dx = 0
        # Horizontal movement
        if pyxel.btn(pyxel.KEY_LEFT):
            parent.dx = -parent.climb_speed / 2.0
            parent.is_facing_right = not parent.is_facing_right
        elif pyxel.btn(pyxel.KEY_RIGHT):
            parent.dx = parent.climb_speed / 2.0
            parent.is_facing_right = not parent.is_facing_right

        # Horizontal collision
        parent.x += parent.dx
        if check_horizontal_tile_collision(
            parent.x, parent.y, parent.dx, parent.w, parent.h, tilemap_idx=0
        ):
            parent.x -= parent.dx
            parent.dx = 0

        # Vertical movement
        if pyxel.btn(pyxel.KEY_UP):
            parent.y -= parent.climb_speed
            parent.is_facing_right = not parent.is_facing_right
        elif pyxel.btn(pyxel.KEY_DOWN):
            parent.y += parent.climb_speed
            parent.is_facing_right = not parent.is_facing_right

        if not check_ladder_collision(parent.x, parent.y, parent.w, parent.h):
            parent.state_key = PlayerStateKey.AIR
        parent.check_world_bounds()

    def draw(self) -> None:
        parent = self.parent
        tx, ty = CLIMB_HERO
        u = tx * TILE_SIZE
        v = ty * TILE_SIZE

        # Horz mirror on even frames
        w = parent.w if parent.is_facing_right else -parent.w
        pyxel.blt(
            parent.sx,
            parent.sy,
            0,
            u,
            v,
            w,
            parent.h,
            DEFAULT_TRANSPARENT_COLOR,
        )


class Player(MovableEntity, StateMachine):
    def __init__(
        self,
        x: int,
        y: int,
        w: int = 6,
        h: int = TILE_SIZE,
        speed: int = 1.6,
        jump: int = 4,
        momentum: float = 0.8,
        climb_speed: int = 1,
    ) -> None:
        super().__init__(
            x,
            y,
            w,
            h,
        )
        self.dx = 0
        self.dy = 0
        self.health = 0
        self.speed = speed
        self.climb_speed = climb_speed
        self.jump = jump
        self.momentum = momentum
        self.is_grounded = True  # TODO: Remove
        self.init_state_machine(
            {
                PlayerStateKey.GROUND: PlayerGroundState(),
                PlayerStateKey.AIR: PlayerAirState(),
                PlayerStateKey.CLIMB: PlayerClimbState(),
                PlayerStateKey.DEAD: PlayerDeathState(),
            },
            PlayerStateKey.GROUND,
        )

    def update(self):
        self.state.update()

    def draw(self):
        self.state.draw()

    def die(self) -> None:
        # NOTE: Let the PlayerDeathState handle the is_alive flag
        self.state_key = PlayerStateKey.DEAD

    def check_world_bounds(self) -> None:
        # Cap boundaries to worldmap
        if self.y < SCROLL_BORDER_Y_CEILING:
            self.y = 0
        if self.y > SCROLL_BORDER_Y - self.h:
            self.y = SCROLL_BORDER_Y - self.h - 1
            self.state_key = PlayerStateKey.DEAD
            self.die()
        if self.x < 0:
            self.x = 0
        if self.x > SCROLL_BORDER_X:
            self.x = SCROLL_BORDER_X - self.w


class Camera:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        xoff: float = -SCREEN_WIDTH // 2,
        yoff: float = -SCREEN_HEIGHT // 2,
        target: Player | None = None,
    ) -> None:
        if hasattr(self, "initialized"):
            raise RuntimeError("Camera is a singleton. Use Camera.instance() instead")
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.xoff = xoff
        self.yoff = yoff
        self.target = target
        self.initialized = True

    @classmethod
    def instance(cls):
        if cls._instance is None:
            raise RuntimeError("Camera is not initialized")
        return cls._instance

    def update(self) -> None:
        if self.target is None:
            return
        # Follow the target unless target encounters scroll limit
        self.x = self.target.x + self.xoff
        self.x = min(SCROLL_BORDER_X - self.w, max(0, self.x))
        self.y = min(0, self.target.y + self.yoff)
        self.y = min(SCROLL_BORDER_Y - self.h, max(0, self.y))


class ShroomHead(DefaultMovableEntity):
    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        speed: float = 0.2,
        marker_tile: tuple[int, int] = SHROOM,
        transparent_color: int = DEFAULT_TRANSPARENT_COLOR,
        score: int = 100,
        death_marker_tile: tuple[int, int] = DEAD_SHROOM,
    ) -> None:
        super().__init__(x, y, w, h, marker_tile, transparent_color)
        self.dx = speed * random.choice([-1, 1])
        self.score = score
        self.death_marker_tile = death_marker_tile

    def update(self) -> None:
        # Horizontal movement
        self.is_facing_right = self.dx >= 0
        self.x += self.dx
        if check_horizontal_tile_collision(
            self.x, self.y, self.dx, self.w, self.h, tilemap_idx=0
        ):
            self.x -= self.dx
            self.dx = -self.dx

        # Vertical movement
        ## Apply Gravity
        self.dy = min(self.dy + GRAVITY, TERMINAL_VELOCITY)
        self.y += self.dy

        if check_vertical_tile_collision(
            self.x, self.y, self.dy, self.w, self.h, tilemap_idx=0
        ):
            if self.dy > 0:
                # Falling
                self.y = int((self.y + self.h) // TILE_SIZE) * TILE_SIZE - int(self.h)
            else:
                # Hitting ceiling, snap to bottom of tile
                self.y = (int(self.y) // TILE_SIZE + 1) * TILE_SIZE
            self.dy = 0

    def on_collision(self, other: "Entity") -> None:
        if isinstance(other, Player):
            if other.y + other.h < self.y + int(self.h * 0.65):
                if other.dy > 0:
                    other.dy -= other.jump * 2
                    self.die()
                else:
                    other.die()
            else:
                other.die()
        if isinstance(other, FireBall):
            self.die()

    def die(self) -> None:
        manager = GameManager.instance()
        manager.score += self.score
        manager.particles.append(
            DeathSprite(
                self.x,
                self.y,
                self.w,
                self.h,
                marker_tile=self.death_marker_tile,
                flip_horizontal=self.dx < 0,
                flip_vertical=True,
            )
        )
        self.is_alive = False


class Turtle(ShroomHead):
    pass


class FireBall(MovableEntity):
    def __init__(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        speed_per_tick: float = 1,
        ceiling: int = 100,
    ) -> None:
        super().__init__(x, y, w, h)
        self.speed_per_tick = speed_per_tick
        self.dy = -speed_per_tick
        self.ceiling = ceiling
        self.start_y = y

    def draw(self) -> None:
        tx, ty = FIREBALL_IMG
        u = tx * TILE_SIZE
        v = ty * TILE_SIZE
        w = self.w if (pyxel.frame_count // 9) & 1 else -self.w
        h = self.h if self.dy < 0 else -self.h
        pyxel.blt(self.sx, self.sy, 0, u, v, w, h, DEFAULT_TRANSPARENT_COLOR)

    def update(self) -> None:
        # Reverse motion if hitting ceiling or floor
        if self.y < self.start_y - self.ceiling or self.y > self.start_y:
            self.dy = -self.dy
        self.y += self.dy

    def on_collision(self, other):
        if isinstance(other, Player):
            other.die()


class SpinnyFireball(MovableEntity):
    def update(self) -> None:
        """Update controlled by FireCircle"""
        super().update()
        pass

    def draw(self) -> None:
        u, v = FIRE_CIRCLE_SPRITE
        u *= TILE_SIZE
        v *= TILE_SIZE
        fc = pyxel.frame_count
        w = self.w if fc // 9 & 1 else -self.w
        h = self.h if fc // 2 & 1 else -self.h
        pyxel.blt(self.sx, self.sy, 0, u, v, w, h, DEFAULT_TRANSPARENT_COLOR)

    def on_collision(self, other: "Entity") -> None:
        if isinstance(other, Player):
            other.die()


class FireCircle(Entity):
    def __init__(
        self,
        x: float,
        y: float,
        w: int,
        h: int,
        rotation_speed: float = -0.05,
        num_fireballs: int = 5,
    ) -> None:
        super().__init__(x, y, w, h)
        self.rotation_speed = rotation_speed
        self.fireballs = [
            SpinnyFireball(x + TILE_SIZE * i, y, TILE_SIZE, TILE_SIZE)
            for i in range(num_fireballs)
        ]
        self.manager.enemies.extend(self.fireballs)

    def update(self):
        fc: int = pyxel.frame_count
        for i, fireball in enumerate(self.fireballs):
            fireball.x = self.x + TILE_SIZE * i * math.cos(fc * self.rotation_speed)
            fireball.y = self.y + TILE_SIZE * i * math.sin(fc * self.rotation_speed)
            fireball.update()

    def draw(self):
        for fireball in self.fireballs:
            fireball.draw()


class FireCircleBlock(FireCircle):
    def on_collision(self, other):
        if isinstance(other, Player):
            pushback_entity(self, other)


class Spring(Entity):
    pass


class PiranhaPlant(Entity):
    def draw(self) -> None:
        tx, ty = PIRANHA_PLANT
        u = (tx + (1 if (pyxel.frame_count // 9 % 3) else 2)) * TILE_SIZE
        v = ty * TILE_SIZE
        pyxel.blt(self.sx, self.sy, 0, u, v, self.w, self.h, DEFAULT_TRANSPARENT_COLOR)

    def on_collision(self, other):
        if isinstance(other, Player):
            other.die()


class PiranhaPlantTurret(PiranhaPlant):
    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        super().__init__(x, y, w, h)
        self.player = self.manager.player

    def update(self) -> None:
        if self.player is None:
            print("Warning: PiranhaPlantTurret has no player reference")
            return
        # TODO: Finish this
        # if pyxel.frame_count % 120 == 0:
        #    px, py = self.player.x, self.player.y


class Bullet(MovableEntity):
    pass


class Spikes(Entity):
    pass


class Slime(Entity):
    pass


class MovingPlatform(MovableEntity):
    def __init__(
        self,
        x,
        y,
        w=TILE_SIZE * 2,
        h=TILE_SIZE,
    ):
        super().__init__(x, y, w, h)
        self.dx = 0.25
        self.distance = 5 * TILE_SIZE
        self.cur_distance = self.distance

    def update(self):
        # Horizontal movement
        self.x += self.dx
        self.cur_distance -= abs(self.dx)
        if self.cur_distance <= 0:
            self.dx = -self.dx
            self.cur_distance = self.distance

    # Alter player position
    def on_collision(self, other: "Entity") -> None:
        pass
        if isinstance(other, Player):
            # Use this logic purely to detect the direction of the collision
            pushback_entity(
                self,
                other,
                on_hit_above=partial(self.on_hit_above_by_player, other),
                pushback_y_up=False,
                pushback_y_down=False,
                pushback_x_left=False,
                pushback_x_right=False,
            )

    def on_hit_above_by_player(self, player: Player) -> None:
        player.y = self.y - player.h
        player.x += self.dx
        player.dy = 0
        player.state_key = PlayerStateKey.GROUND

    def draw(self) -> None:
        tx, ty = MOVING_PLAT1
        u = (tx + 2) * TILE_SIZE
        v = ty * TILE_SIZE
        pyxel.blt(self.sx, self.sy, 0, u, v, self.w, self.h, DEFAULT_TRANSPARENT_COLOR)


class FallingPlatform(Entity):
    def __init__(
        self, x, y, w=TILE_SIZE, h=TILE_SIZE, fall_delay_ticks=60, jiggle_amount=0.5
    ):
        super().__init__(x, y, w, h)
        self.fall_delay_ticks = fall_delay_ticks
        self.ticks_remaining = self.fall_delay_ticks

        # Slight offset when player is standing on the block
        self.dy = 0

        # Jiggle
        self.jiggle_amount = jiggle_amount
        self.jy = 0

    @property
    def y_off(self):
        return self.dy + (self.jy - 1) * self.jiggle_amount

    def update(self):
        if self.ticks_remaining < self.fall_delay_ticks * 0.75:
            # Oscillate and jiggle offset
            self.jy = (self.jy + 1) % 3

    def on_collision(self, other: "Entity") -> None:
        if isinstance(other, Player):
            pushback_entity(
                self,
                other,
                on_hit_above=partial(self.on_hit_above_by_player, other),
                pushback_y_up=False,
                pushback_y_down=False,
                pushback_x_left=False,
                pushback_x_right=False,
            )
            self.dy = 1

    def on_collision_end(self, other: "Entity") -> None:
        # Reset timer
        self.ticks_remaining = self.fall_delay_ticks
        self.dy = 0
        self.jy = 0

    def on_hit_above_by_player(self, player: Player) -> None:
        player.state_key = PlayerStateKey.GROUND
        player.y = self.y - player.h
        player.dy = 1  # Dip slightly
        self.ticks_remaining -= 1
        if self.ticks_remaining <= 0:
            self.die()  # Fixme: Transition state instead

    def die(self) -> None:
        FALL_PLAT_VIS = (FALL_PLAT1[0] + 1, FALL_PLAT1[1])
        self.manager.doodads.append(
            CollidableDeathSprite(
                self.x,
                self.y,
                self.w,
                self.h,
                marker_tile=FALL_PLAT_VIS,
                dx=0,
                dy=0,
                feels_gravity=True,
                lifespan_ticks=20,
            )
        )
        self.is_alive = False

    def draw(self) -> None:
        tx, ty = FALL_PLAT1
        u = (tx + 1) * TILE_SIZE
        v = ty * TILE_SIZE
        pyxel.blt(
            self.sx,
            self.sy + self.y_off,
            0,
            u,
            v,
            self.w,
            self.h,
            DEFAULT_TRANSPARENT_COLOR,
        )


class GameManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self.doodads: list[Entity] = []
        self.enemies: list[Entity] = []
        self.particles: list[Entity] = []
        self.coins: int = 0
        self.score: int = 0

    @classmethod
    def instance(cls):
        if cls._instance is None:
            raise RuntimeError("GameManager is not initialized")
        return cls._instance

    def clear(self) -> None:
        self.doodads = []
        self.enemies = []
        self.particles = []
        self.coins = 0
        self.score = 0


class App:
    @property
    def doodads(self) -> list[Entity]:
        return self.manager.doodads

    @property
    def enemies(self) -> list[Entity]:
        return self.manager.enemies

    @property
    def particles(self) -> list[Entity]:
        return self.manager.particles

    def __init__(self) -> None:
        pyxel.init(
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            title="Pyxel Plumber",
            fps=60,
            quit_key=pyxel.KEY_ESCAPE,
        )
        pyxel.load("assets/pyxel_plumber.pyxres")
        # Make editor tiles invisible
        self.camera = Camera(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.player: Player
        self.manager: GameManager
        self.make_editor_tiles_invisible()
        self.reset()

        pyxel.run(self.update, self.draw)

    def update(self) -> None:
        # Spawn as we scroll, not all at once at the beginning
        # self.spawn_enemies_and_doodads(
        #    self.camera.x + self.camera.w,
        #    self.camera.x + self.camera.w * 0.5,
        #    tilemap_idx=0,
        # )
        for doodad in self.doodads:
            doodad.update()
            doodad.collide_with(self.player)
        for enemy in self.enemies:
            enemy.update()
            enemy.collide_with(self.player)
        for particle in self.particles:
            particle.update()
        self.player.update()
        self.camera.update()

        cleanup_entities(self.doodads)
        cleanup_entities(self.enemies)
        cleanup_entities(self.particles)
        if not self.player.is_alive:
            self.reset()

    def reset(self) -> None:
        self.player = Player(PLAYER_START[0] * TILE_SIZE, PLAYER_START[1] * TILE_SIZE)
        self.manager = GameManager()
        self.camera.target = self.player
        self.spawn_enemies_and_doodads(0, SCROLL_BORDER_X)

    def draw(self) -> None:
        pyxel.cls(0)

        # Draw level
        pyxel.camera()
        # Draw background
        u, vb = 0, 24 * TILE_SIZE
        wb, hb = 16 * TILE_SIZE, 19 * TILE_SIZE

        vf = vb + 19 * TILE_SIZE
        wf, hf = 16 * TILE_SIZE, 11 * TILE_SIZE
        for xoff in range(-1, 2):
            for yoff in range(0, 1):
                # Far background
                pyxel.bltm(
                    (-self.camera.x // 3) % wb + xoff * wb,
                    yoff * hb,
                    0,
                    u,
                    vb,
                    wb,
                    hb,
                    0,
                )
                # Near background
                pyxel.bltm(
                    (-self.camera.x // 2) % wf + xoff * wf,
                    hb + yoff * hf,
                    0,
                    u,
                    vf,
                    wf,
                    hf,
                    0,
                )

        # Draw foreground tiles in screen space
        # Note our camera offset is our uv offset
        pyxel.bltm(
            0, 0, 0, self.camera.x, self.camera.y, self.camera.w, self.camera.h, 0
        )

        # Draw doodads
        for doodad in self.doodads:
            doodad.draw()

        # Draw enemies
        for enemy in self.enemies:
            enemy.draw()

        # Draw player
        self.player.draw()

        # Draw particles
        for particle in self.particles:
            particle.draw()

        # Draw HUD
        self.draw_hud()

    def make_editor_tiles_invisible(self) -> None:
        # Change enemy spawn tiles invisible
        for tx, ty in marker_tiles:
            pyxel.images[0].rect(
                tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE, 0
            )

    def spawn_enemies_and_doodads(
        self, left_x: float, right_x: float, tilemap_idx: int = 0
    ) -> None:
        left_x = pyxel.ceil(left_x / TILE_SIZE)
        right_x = pyxel.floor(right_x / TILE_SIZE)
        for x in range(left_x, right_x + 1):
            for y in range(
                3 * SCREEN_HEIGHT // TILE_SIZE
            ):  # FIXME Don't spawn everything
                tile = get_tile(x, y, tilemap_idx)  # FIXME

                if tile == COIN:
                    self.enemies.append(
                        Coin(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    )
                elif tile == SHROOM:
                    self.enemies.append(
                        ShroomHead(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                            marker_tile=SHROOM,
                        ),
                    )
                elif tile == TURTLE:
                    self.enemies.append(
                        Turtle(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                            marker_tile=TURTLE,
                            death_marker_tile=(TURTLE[0] + 1, TURTLE[1]),
                        ),
                    )
                elif tile == PIRANHA_PLANT:
                    self.enemies.append(
                        PiranhaPlant(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                        )
                    )
                elif tile == SPIKES:
                    pass
                elif tile == SPRING:
                    pass
                elif tile == BREAK_BLOCK:
                    self.doodads.append(
                        BreakBlock(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                            hp=random.randrange(2, 4),
                        )
                    )
                elif tile == MOVING_PLAT1:
                    self.doodads.append(
                        MovingPlatform(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                        )
                    )
                elif tile == FALL_PLAT1:
                    self.doodads.append(
                        FallingPlatform(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            fall_delay_ticks=30,
                        )
                    )
                elif tile == FIREBALL:
                    self.enemies.append(
                        FireBall(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                        )
                    )
                elif tile == FIRE_CIRCLE:
                    self.doodads.append(
                        FireCircle(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                        )
                    )

                elif tile == FIRE_CIRCLE_BLOCK:
                    self.doodads.append(
                        FireCircleBlock(
                            x * TILE_SIZE,
                            y * TILE_SIZE,
                            TILE_SIZE,
                            TILE_SIZE,
                        )
                    )
                elif tile == SPRING:
                    pass

    def draw_hud(self) -> None:
        pyxel.text(TILE_SIZE, TILE_SIZE * 2, f"SCORE: {self.manager.score}", 7)
        pyxel.text(TILE_SIZE, TILE_SIZE, f"X  : {self.manager.coins}", 7)
        pyxel.blt(
            TILE_SIZE * 1.5,
            TILE_SIZE - 2,
            0,
            (COIN[0] + 1) * TILE_SIZE,
            (COIN[1]) * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE,
            DEFAULT_TRANSPARENT_COLOR,
        )


App()
