import os
import sys
import sqlite3
import pygame
from PyQt6.QtWidgets import QApplication, QDialog, QFormLayout, QLineEdit, QPushButton, QMessageBox, QLCDNumber
from PyQt6.QtCore import pyqtSignal, QObject
import threading

DATABASE_FILE = "wallet.db"

pygame.init()
black = (0, 0, 0)
white = (255, 255, 255)
blue = (0, 0, 255)
red = (255, 0, 0)


def initialize_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            password TEXT,
            best_score INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


class MyApp(QObject):
    score_updated = pyqtSignal(int)  # Signal to update the score

    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.user_score = 0
        self.best_score = 0  # Initialize best score
        self.username = None  # Username

        self.score_updated.connect(self.update_score_display)

        self.open_login_dialog()  # Open login dialog

    def open_login_dialog(self):
        self.login_dialog = LoginDialog(self)
        self.login_dialog.show()

    def open_menu_dialog(self):
        self.load_user_data(self.username)  # Load user data, including best score
        self.menu_dialog = MenuDialog(self, self.username, self.best_score)
        self.menu_dialog.show()

    def start_game(self):
        # Start the game in a new thread
        pygame_thread = threading.Thread(target=startGame, args=(self.score_updated, self.username))
        pygame_thread.start()

    def update_score_display(self, score):
        self.user_score = score
        if score > self.best_score:  # Check if current score is better than best
            self.best_score = score  # Update best score
        if hasattr(self, 'menu_dialog'):
            self.menu_dialog.update_score(score, self.best_score)  # Pass current and best score

    def load_user_data(self, username):
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT best_score FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            if result:
                self.best_score = result[0]  # Load best score
            conn.close()
        except Exception as e:
            print(f"Failed to load user data: {e}")

    def update_user_score(self, username, new_score):
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET best_score = ? WHERE username = ?', (new_score, username))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to update user score: {e}")

    def register_user(self, username, password):
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                QMessageBox.warning(None, "Registration Failed", "Username already exists.")
                return

            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            self.username = username
            conn.commit()
            conn.close()
            self.open_menu_dialog()  # Open menu after registration
        except Exception as e:
            print(f"Failed to register user: {e}")

    def login_user(self, username, password):
        try:
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = cursor.fetchone()
            if user:
                self.username = username
                QMessageBox.information(None, "Login Successful", "You have successfully logged in.")
                self.open_menu_dialog()  # Open menu after successful login
                self.login_dialog.close()  # Close the login dialog
            else:
                QMessageBox.warning(None, "Login Failed", "Invalid username or password.")
            conn.close()
        except Exception as e:
            print(f"Failed to login user: {e}")


class LoginDialog(QDialog):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Login")
        self.setGeometry(100, 100, 300, 200)

        layout = QFormLayout()
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login)

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.open_register_dialog)

        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        layout.addRow(self.login_button, self.register_button)

        self.setLayout(layout)

    def login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        self.app.login_user(username, password)

    def open_register_dialog(self):
        self.register_dialog = RegisterDialog(self.app)
        self.register_dialog.show()
        self.close()


class RegisterDialog(QDialog):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Register")
        self.setGeometry(100, 100, 300, 200)

        layout = QFormLayout()
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.register)

        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)
        layout.addRow(self.register_button)

        self.setLayout(layout)

    def register(self):
        username = self.username_input.text()
        password = self.password_input.text()
        self.app.register_user(username, password)
        self.close()


class MenuDialog(QDialog):
    def __init__(self, app, username, best_score):
        super().__init__()
        self.app = app
        self.username = username
        self.setWindowTitle("Menu")
        self.setGeometry(100, 100, 300, 300)

        layout = QFormLayout()

        self.score_display = QLCDNumber(self)  # LCD for displaying current score
        self.score_display.setDigitCount(6)  # Set number of displayed digits
        self.score_display.display(self.app.user_score)  # Initial value from app
        layout.addRow("Current Score:", self.score_display)

        self.best_score_display = QLCDNumber(self)  # LCD for displaying best score
        self.best_score_display.setDigitCount(6)
        self.best_score_display.display(best_score)  # Display best score
        layout.addRow("Best Score:", self.best_score_display)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.start_game)
        layout.addRow(self.play_button)

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.close_application)
        layout.addRow(self.exit_button)

        self.setLayout(layout)

    def start_game(self):
        self.app.start_game()

    def update_score(self, score, best_score):
        self.score_display.display(score)  # Update current score display
        self.best_score_display.display(best_score)  # Update best score display

    def close_application(self):
        reply = QMessageBox.question(self, 'Exit', 'Are you sure you want to exit?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            pygame.quit()


def startGame(score_signal, username):
    black = (0, 0, 0)
    white = (255, 255, 255)
    blue = (0, 0, 255)
    red = (255, 0, 0)
    yellow = (255, 255, 0)

    Trollicon = pygame.image.load('Trollman.png')
    pygame.display.set_icon(Trollicon)

    pygame.mixer.init()
    pygame.mixer.music.load('pacman.mp3')
    pygame.mixer.music.play(-1, 0.0)

    class Wall(pygame.sprite.Sprite):
        def __init__(self, x, y, width, height, color):
            pygame.sprite.Sprite.__init__(self)

            self.image = pygame.Surface([width, height])
            self.image.fill(color)

            self.rect = self.image.get_rect()
            self.rect.top = y
            self.rect.left = x

    def setupRoomOne(all_sprites_list):
        wall_list = pygame.sprite.RenderPlain()

        walls = [[0, 0, 6, 600], [0, 0, 600, 6], [0, 600, 606, 6], [600, 0, 6, 606],
                 [300, 0, 6, 66], [60, 60, 186, 6], [360, 60, 186, 6], [60, 120, 66, 6],
                 [60, 120, 6, 126], [180, 120, 246, 6], [300, 120, 6, 66], [480, 120, 66, 6],
                 [540, 120, 6, 126], [120, 180, 126, 6], [120, 180, 6, 126], [360, 180, 126, 6],
                 [480, 180, 6, 126], [180, 240, 6, 126], [180, 360, 246, 6], [420, 240, 6, 126],
                 [240, 240, 42, 6], [324, 240, 42, 6], [240, 240, 6, 66], [240, 300, 126, 6],
                 [360, 240, 6, 66], [0, 300, 66, 6], [540, 300, 66, 6], [60, 360, 66, 6],
                 [60, 360, 6, 186], [480, 360, 66, 6], [540, 360, 6, 186], [120, 420, 366, 6],
                 [120, 420, 6, 66], [480, 420, 6, 66], [180, 480, 246, 6], [300, 480, 6, 66],
                 [120, 540, 126, 6], [360, 540, 126, 6]]

        for item in walls:
            wall = Wall(item[0], item[1], item[2], item[3], blue)
            wall_list.add(wall)
            all_sprites_list.add(wall)

        return wall_list

    def setupGate(all_sprites_list):
        gate = pygame.sprite.RenderPlain()
        gate.add(Wall(282, 242, 42, 2, white))
        all_sprites_list.add(gate)
        return gate

    class Block(pygame.sprite.Sprite):
        def __init__(self, color, width, height):
            pygame.sprite.Sprite.__init__(self)

            self.image = pygame.Surface([width, height])
            self.image.fill(white)
            self.image.set_colorkey(white)
            pygame.draw.ellipse(self.image, color, [0, 0, width, height])

            self.rect = self.image.get_rect()

    class Player(pygame.sprite.Sprite):
        change_x = 0
        change_y = 0

        def __init__(self, x, y, filename):
            pygame.sprite.Sprite.__init__(self)

            self.image = pygame.image.load(filename).convert()

            self.rect = self.image.get_rect()
            self.rect.top = y
            self.rect.left = x
            self.prev_x = x
            self.prev_y = y

        def prevdirection(self):
            self.prev_x = self.change_x
            self.prev_y = self.change_y

        def changespeed(self, x, y):
            self.change_x += x
            self.change_y += y

        def update(self, walls, gate):
            old_x = self.rect.left
            new_x = old_x + self.change_x
            prev_x = old_x + self.prev_x
            self.rect.left = new_x

            old_y = self.rect.top
            new_y = old_y + self.change_y
            prev_y = old_y + self.prev_y

            x_collide = pygame.sprite.spritecollide(self, walls, False)
            if x_collide:
                self.rect.left = old_x
            else:
                self.rect.top = new_y
                y_collide = pygame.sprite.spritecollide(self, walls, False)
                if y_collide:
                    self.rect.top = old_y

            if gate != False:
                gate_hit = pygame.sprite.spritecollide(self, gate, False)
                if gate_hit:
                    self.rect.left = old_x
                    self.rect.top = old_y

    class Ghost(Player):
        def changespeed(self, list, ghost, turn, steps, l):
            try:
                z = list[turn][2]
                if steps < z:
                    self.change_x = list[turn][0]
                    self.change_y = list[turn][1]
                    steps += 1
                else:
                    if turn < l:
                        turn += 1
                    elif ghost == "clyde":
                        turn = 2
                    else:
                        turn = 0
                    self.change_x = list[turn][0]
                    self.change_y = list[turn][1]
                    steps = 0
                return [turn, steps]
            except IndexError:
                return [0, 0]

    Pinky_directions = [[0, -30, 4], [15, 0, 9], [0, 15, 11], [-15, 0, 23], [0, 15, 7],
                        [15, 0, 3], [0, -15, 3], [15, 0, 19], [0, 15, 3], [15, 0, 3],
                        [0, 15, 3], [15, 0, 3], [0, -15, 15], [-15, 0, 7], [0, 15, 3],
                        [-15, 0, 19], [0, -15, 11], [15, 0, 9]]

    Blinky_directions = [[0, -15, 4], [15, 0, 9], [0, 15, 11], [15, 0, 3], [0, 15, 7],
                         [-15, 0, 11], [0, 15, 3], [15, 0, 15], [0, -15, 15], [15, 0, 3],
                         [0, -15, 11], [-15, 0, 3], [0, -15, 11], [-15, 0, 3], [0, -15, 3],
                         [-15, 0, 7], [0, -15, 3], [15, 0, 15], [0, 15, 15], [-15, 0, 3],
                         [0, 15, 3], [-15, 0, 3], [0, -15, 7], [-15, 0, 3], [0, 15, 7],
                         [-15, 0, 11], [0, -15, 7], [15, 0, 5]]

    Inky_directions = [[30, 0, 2], [0, -15, 4], [15, 0, 10], [0, 15, 7], [15, 0, 3],
                       [0, -15, 3], [15, 0, 3], [0, -15, 15], [-15, 0, 15], [0, 15, 3],
                       [15, 0, 15], [0, 15, 11], [-15, 0, 3], [0, -15, 7], [-15, 0, 11],
                       [0, 15, 3], [-15, 0, 11], [0, 15, 7], [-15, 0, 3], [0, -15, 3],
                       [-15, 0, 3], [0, -15, 15], [15, 0, 15], [0, 15, 3], [-15, 0, 15],
                       [0, 15, 11], [15, 0, 3], [0, -15, 11], [15, 0, 11], [0, 15, 3],
                       [15, 0, 1]]

    Clyde_directions = [[-30, 0, 2], [0, -15, 4], [15, 0, 5], [0, 15, 7], [-15, 0, 11],
                        [0, -15, 7], [-15, 0, 3], [0, 15, 7], [-15, 0, 7], [0, 15, 15],
                        [15, 0, 15], [0, -15, 3], [-15, 0, 11], [0, -15, 7], [15, 0, 3],
                        [0, -15, 11], [15, 0, 9]]

    pl = len(Pinky_directions) - 1
    bl = len(Blinky_directions) - 1
    il = len(Inky_directions) - 1
    cl = len(Clyde_directions) - 1

    screen = pygame.display.set_mode([606, 606])
    pygame.display.set_caption('Pacman')

    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill(black)

    clock = pygame.time.Clock()
    pygame.font.init()
    font = pygame.font.Font("freesansbold.ttf", 24)

    w = 303 - 16
    p_h = (7 * 60) + 19
    m_h = (4 * 60) + 19
    b_h = (3 * 60) + 19
    i_w = 303 - 16 - 32
    c_w = 303 + (32 - 16)

    def startGame():
        all_sprites_list = pygame.sprite.RenderPlain()
        block_list = pygame.sprite.RenderPlain()
        monsta_list = pygame.sprite.RenderPlain()
        pacman_collide = pygame.sprite.RenderPlain()

        wall_list = setupRoomOne(all_sprites_list)
        gate = setupGate(all_sprites_list)

        p_turn = 0
        p_steps = 0

        b_turn = 0
        b_steps = 0

        i_turn = 0
        i_steps = 0

        c_turn = 0
        c_steps = 0

        Pacman = Player(w, p_h, "pacman.png")
        all_sprites_list.add(Pacman)
        pacman_collide.add(Pacman)

        Blinky = Ghost(w, b_h, "Blinky.png")
        monsta_list.add(Blinky)
        all_sprites_list.add(Blinky)

        Pinky = Ghost(w, m_h, "Pinky.png")
        monsta_list.add(Pinky)
        all_sprites_list.add(Pinky)

        Inky = Ghost(i_w, m_h, "Inky.png")
        monsta_list.add(Inky)
        all_sprites_list.add(Inky)

        Clyde = Ghost(c_w, m_h, "Clyde.png")
        monsta_list.add(Clyde)
        all_sprites_list.add(Clyde)

        for row in range(19):
            for column in range(19):
                if (row == 7 or row == 8) and (column == 8 or column == 9 or column == 10):
                    continue
                else:
                    block = Block(yellow, 4, 4)

                    block.rect.x = (30 * column + 6) + 26
                    block.rect.y = (30 * row + 6) + 26

                    b_collide = pygame.sprite.spritecollide(block, wall_list, False)
                    p_collide = pygame.sprite.spritecollide(block, pacman_collide, False)
                    if b_collide:
                        continue
                    elif p_collide:
                        continue
                    else:
                        block_list.add(block)
                        all_sprites_list.add(block)

        bll = len(block_list)
        score = 0
        done = False

        while not done:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    done = True

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        Pacman.changespeed(-30, 0)
                    if event.key == pygame.K_RIGHT:
                        Pacman.changespeed(30, 0)
                    if event.key == pygame.K_UP:
                        Pacman.changespeed(0, -30)
                    if event.key == pygame.K_DOWN:
                        Pacman.changespeed(0, 30)

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_LEFT:
                        Pacman.changespeed(30, 0)
                    if event.key == pygame.K_RIGHT:
                        Pacman.changespeed(-30, 0)
                    if event.key == pygame.K_UP:
                        Pacman.changespeed(0, 30)
                    if event.key == pygame.K_DOWN:
                        Pacman.changespeed(0, -30)

            Pacman.update(wall_list, gate)

            returned = Pinky.changespeed(Pinky_directions, False, p_turn, p_steps, pl)
            p_turn = returned[0]
            p_steps = returned[1]
            Pinky.changespeed(Pinky_directions, False, p_turn, p_steps, pl)
            Pinky.update(wall_list, False)

            returned = Blinky.changespeed(Blinky_directions, False, b_turn, b_steps, bl)
            b_turn = returned[0]
            b_steps = returned[1]
            Blinky.changespeed(Blinky_directions, False, b_turn, b_steps, bl)
            Blinky.update(wall_list, False)

            returned = Inky.changespeed(Inky_directions, False, i_turn, i_steps, il)
            i_turn = returned[0]
            i_steps = returned[1]
            Inky.changespeed(Inky_directions, False, i_turn, i_steps, il)
            Inky.update(wall_list, False)

            returned = Clyde.changespeed(Clyde_directions, "clyde", c_turn, c_steps, cl)
            c_turn = returned[0]
            c_steps = returned[1]
            Clyde.changespeed(Clyde_directions, "clyde", c_turn, c_steps, cl)
            Clyde.update(wall_list, False)

            blocks_hit_list = pygame.sprite.spritecollide(Pacman, block_list, True)

            if len(blocks_hit_list) > 0:
                score += len(blocks_hit_list)
                score_signal.emit(score)
                update_user_score(username, score)

            screen.fill(black)

            wall_list.draw(screen)
            gate.draw(screen)
            all_sprites_list.draw(screen)
            monsta_list.draw(screen)

            text = font.render("Score: " + str(score) + "/" + str(bll), True, red)
            screen.blit(text, [10, 10])

            if score == bll:
                doNext("Congratulations, you won!", 145, all_sprites_list, block_list, monsta_list, pacman_collide,
                       wall_list, gate)
                update_user_score(username, score)

            monsta_hit_list = pygame.sprite.spritecollide(Pacman, monsta_list, False)

            if monsta_hit_list:
                doNext("Game Over", 235, all_sprites_list, block_list, monsta_list, pacman_collide, wall_list, gate)

            pygame.display.flip()

            clock.tick(10)

    def doNext(message, left, all_sprites_list, block_list, monsta_list, pacman_collide, wall_list, gate):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                    if event.key == pygame.K_RETURN:
                        del all_sprites_list
                        del block_list
                        del monsta_list
                        del pacman_collide
                        del wall_list
                        del gate
                        startGame()

            w = pygame.Surface((400, 200))
            w.set_alpha(10)
            w.fill((128, 128, 128))
            screen.blit(w, (100, 200))

            text1 = font.render(message, True, white)
            screen.blit(text1, [left, 233])

            text2 = font.render("To play again, press ENTER.", True, white)
            screen.blit(text2, [135, 303])
            text3 = font.render("To quit, press ESCAPE.", True, white)
            screen.blit(text3, [165, 333])

            pygame.display.flip()

            clock.tick(60)

    startGame()


def update_user_score(username, new_score):
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET best_score = ? WHERE username = ?', (new_score, username))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to update user score: {e}")


if __name__ == "__main__":
    initialize_database()
    my_app = MyApp()
    sys.exit(my_app.app.exec())
