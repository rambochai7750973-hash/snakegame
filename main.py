import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.properties import NumericProperty, StringProperty
from random import randint
from collections import deque

CELL_SIZE = 20
INITIAL_SPEED = 0.15

class HUD(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [10, 5]
        self.spacing = 2
        self.size_hint_y = None
        self.height = 100

        top = BoxLayout(size_hint_y=0.5)
        self.score_label = Label(text='分数: 0', font_size=18, color=(0, 0.82, 1, 1),
                                 bold=True, halign='left', valign='middle',
                                 size_hint_x=0.5)
        self.score_label.bind(size=self.score_label.setter('text_size'))
        self.high_score_label = Label(text='最高分: 0', font_size=18,
                                      color=(1, 0.84, 0, 1), bold=True,
                                      halign='right', valign='middle',
                                      size_hint_x=0.5)
        self.high_score_label.bind(size=self.high_score_label.setter('text_size'))
        top.add_widget(self.score_label)
        top.add_widget(self.high_score_label)

        self.status_label = Label(text='点击屏幕 或 按方向键开始', font_size=16,
                                  color=(1, 1, 1, 0.7), halign='center',
                                  size_hint_y=0.5)
        self.status_label.bind(size=self.status_label.setter('text_size'))

        self.add_widget(top)
        self.add_widget(self.status_label)

    def update_score(self, score, high_score):
        self.score_label.text = f'分数: {score}'
        self.high_score_label.text = f'最高分: {high_score}'

    def update_status(self, text):
        self.status_label.text = text


class GameBoard(Widget):
    score = NumericProperty(0)
    high_score = NumericProperty(0)
    game_state = StringProperty('ready')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid_width = 0
        self.grid_height = 0
        self.snake = deque()
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.food = None
        self.speed = INITIAL_SPEED
        self._touch_start = None
        self.hud = None
        Window.bind(on_key_down=self.on_key_down)

    def set_hud(self, hud):
        self.hud = hud
        self._refresh_hud()

    def init_game(self):
        self.grid_width = int(self.width / CELL_SIZE)
        self.grid_height = int(self.height / CELL_SIZE)
        if self.grid_width < 5 or self.grid_height < 5:
            return
        cx, cy = self.grid_width // 2, self.grid_height // 2
        self.snake.clear()
        for i in range(3):
            self.snake.append((cx - i, cy))
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.speed = INITIAL_SPEED
        self.game_state = 'playing'
        self.spawn_food()
        Clock.unschedule(self.update)
        Clock.schedule_interval(self.update, self.speed)
        self._refresh_hud()

    def spawn_food(self):
        occupied = set(self.snake)
        for _ in range(200):
            x = randint(0, self.grid_width - 1)
            y = randint(0, self.grid_height - 1)
            if (x, y) not in occupied:
                self.food = (x, y)
                return
        self.food = None

    def update(self, dt):
        if self.game_state != 'playing':
            return
        self.direction = self.next_direction
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        if (new_head[0] < 0 or new_head[0] >= self.grid_width or
            new_head[1] < 0 or new_head[1] >= self.grid_height or
            new_head in self.snake):
            self.game_over()
            return
        self.snake.appendleft(new_head)
        if self.food and new_head == self.food:
            self.score += 10
            if self.score > self.high_score:
                self.high_score = self.score
            self.speed = max(0.05, self.speed * 0.97)
            Clock.unschedule(self.update)
            Clock.schedule_interval(self.update, self.speed)
            self.spawn_food()
        else:
            self.snake.pop()
        self._refresh_hud()
        self.canvas.ask_update()

    def game_over(self):
        self.game_state = 'game_over'
        Clock.unschedule(self.update)
        self._refresh_hud()
        self.canvas.ask_update()

    def restart(self):
        self.init_game()
        self.canvas.ask_update()

    def _refresh_hud(self):
        if not self.hud:
            return
        self.hud.update_score(self.score, self.high_score)
        if self.game_state == 'ready':
            self.hud.update_status('点击屏幕 或 按方向键开始')
        elif self.game_state == 'playing':
            self.hud.update_status('')
        elif self.game_state == 'game_over':
            self.hud.update_status('游戏结束! 点击屏幕重新开始')

    def on_touch_down(self, touch):
        if self.game_state in ('game_over', 'ready'):
            self.restart()
            return True
        self._touch_start = touch.pos
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._touch_start is None or self.game_state != 'playing':
            self._touch_start = None
            return
        dx = touch.x - self._touch_start[0]
        dy = touch.y - self._touch_start[1]
        self._touch_start = None
        if abs(dx) < 20 and abs(dy) < 20:
            return
        if abs(dx) > abs(dy):
            if dx > 0 and self.direction != (-1, 0):
                self.next_direction = (1, 0)
            elif dx < 0 and self.direction != (1, 0):
                self.next_direction = (-1, 0)
        else:
            if dy > 0 and self.direction != (0, -1):
                self.next_direction = (0, 1)
            elif dy < 0 and self.direction != (0, 1):
                self.next_direction = (0, -1)

    def on_key_down(self, keyboard, keycode, text, modifiers):
        if self.game_state in ('game_over', 'ready'):
            self.restart()
            return
        mapping = {
            'up': (0, 1), 'down': (0, -1),
            'left': (-1, 0), 'right': (1, 0),
            'w': (0, 1), 's': (0, -1),
            'a': (-1, 0), 'd': (1, 0),
        }
        if keycode[1] in mapping:
            nd = mapping[keycode[1]]
            reverse = (nd[0] * -1, nd[1] * -1)
            if reverse != self.direction:
                self.next_direction = nd

    def draw_game(self):
        self.canvas.clear()
        with self.canvas:
            Color(*get_color_from_hex('#1a1a2e'))
            Rectangle(pos=self.pos, size=self.size)
            if self.grid_width < 5 or self.grid_height < 5:
                return
            for i, seg in enumerate(self.snake):
                if i == 0:
                    Color(*get_color_from_hex('#00d2ff'))
                else:
                    alpha = max(0.25, 1.0 - i * 0.03)
                    Color(0, 0.82, 1, alpha)
                x = self.x + seg[0] * CELL_SIZE
                y = self.y + seg[1] * CELL_SIZE
                Rectangle(pos=(x, y), size=(CELL_SIZE - 1, CELL_SIZE - 1))
            if self.food:
                Color(*get_color_from_hex('#ff4757'))
                fx = self.x + self.food[0] * CELL_SIZE
                fy = self.y + self.food[1] * CELL_SIZE
                Rectangle(pos=(fx, fy), size=(CELL_SIZE - 1, CELL_SIZE - 1))
            if self.game_state == 'ready':
                Color(1, 1, 1, 0.3)
                Line(rectangle=(self.x + 2, self.y + 2,
                      self.width - 4, self.height - 4), width=2)

    def on_size(self, *args):
        self.grid_width = int(self.width / CELL_SIZE)
        self.grid_height = int(self.height / CELL_SIZE)
        if self.game_state == 'playing':
            self.draw_game()
            self.canvas.ask_update()


class SnakeApp(App):
    def build(self):
        self.title = '贪吃蛇'
        Window.clearcolor = get_color_from_hex('#0f0f23')

        root = BoxLayout(orientation='vertical')
        hud = HUD()
        game = GameBoard()
        game.set_hud(hud)
        root.add_widget(hud)
        root.add_widget(game)

        game.draw_game()
        game.bind(pos=game.draw_game, size=game.draw_game)
        return root


if __name__ == '__main__':
    SnakeApp().run()
