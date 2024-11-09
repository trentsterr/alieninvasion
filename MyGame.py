import sys
from time import sleep
from turtle import Screen
import pygame

from pathlib import Path
from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from optionsButton import OptionsButton
from closeButton import CloseButton
from ship import Ship
from bullet import Bullet
from alien import Alien
from pygame._sdl2 import Window



class AlienInvasion:
    """Overall Class to manage game assets and behavior"""

    def __init__(self):
        pygame.init()
        
        self.clock = pygame.time.Clock()
        self.settings = Settings()
        

        self.screen = pygame.display.set_mode((0, 0), pygame.RESIZABLE)
        Window.from_display_module().maximize()
        self.settings.screen_width = self.screen.get_rect().width
        self.settings.screen_height = self.screen.get_rect().height
        pygame.display.set_caption("Alien Invasion")

        #Create an instance to store game statistics
        self.stats = GameStats(self)
        self.sb = Scoreboard(self)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        self._create_fleet()

        # Set Background Color
        self.bg_color = (230, 230, 230)
        #start alien invasion as inactive state.
        self.game_active = False
        is_paused = False

        #make the buttons
        self.play_button = Button(self, "Play")
        self.options_button = OptionsButton(self, "Options")
        self.close_button = CloseButton(self, "Exit")

    def run_game(self):

        while True:
            self._check_events()

            if self.game_active:    
                self.ship.update()
                self._update_bullets()
                self._update_aliens()
            
            self._update_screen()
            self.clock.tick(60)


    def _check_events(self):
        """Respond to keypresses and mouse events"""
        for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    self._check_keydown_events(event)
                elif event.type == pygame.KEYUP:
                    self._check_keyup_events(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    self._check_button(mouse_pos)

    def _check_button(self, mouse_pos):
        """Start a new game when the play presses play"""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.game_active:
            #reset game statistics 
            self.settings.initialize_dynamic_settings()
            self.stats.reset_stats()
            self.sb.prep_score()
            self.sb.prep_level()
            self.sb.prep_ships()
            self.game_active = True

            #get rid of any remaining bullets and aliens
            self.bullets.empty()
            self.aliens.empty()

            #create a new fleet and center ship
            self._create_fleet()
            self.ship.center_ship()

            #hide the mouse cursor
            pygame.mouse.set_visible(False)
            pygame.mixer.music.load('sound/8-bit-space-123218.mp3')
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)

        optionsButton_clicked = self.options_button.rect.collidepoint(mouse_pos)
        if optionsButton_clicked:
            sys.exit()
        
        CloseButton_clicked = self.close_button.rect.collidepoint(mouse_pos)
        if CloseButton_clicked:
            path = Path('high_score.txt')
            path.write_text(str(self.stats.high_score))
            sys.exit()

    def _check_keydown_events(self, event):
        """Responds to key presses"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_q:
            path = Path('high_score.txt')
            path.write_text(str(self.stats.high_score))
            sys.exit()
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
            
        elif event.key == pygame.K_ESCAPE:
            self._pause_game()
            

    def _check_keyup_events(self, event):
        """Responds to key releases"""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    def _fire_bullet(self):
        """Creates new bullet and adds it to bullets group"""
        if len(self.bullets) < self.settings.bullets_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)
            self._play_lazer_sound()

    def _play_lazer_sound(self):
        if self.game_active == True:
            lazer_sound = pygame.mixer.Sound('sound/retro-laser-1-236669.mp3')
            lazer_sound.set_volume(0.3)
            pygame.mixer.Sound.play(lazer_sound)
 

    def _create_fleet(self):
        """Create fleet of alients"""
        #Make an alien
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        
        current_x, current_y = alien_width, alien_height
        while current_y < (self.settings.screen_height - 3 * alien_height):
            while current_x < (self.settings.screen_width - 2 * alien_width):
                self._create_alien(current_x, current_y)
                current_x += 2 * alien_width

            #Finish a row, reset x value, and increment y value
            current_x = alien_width
            current_y += 2 * alien_height

    def _create_alien(self, x_position, y_position):
        """Create an alien and place it in row"""
        new_alien = Alien(self)
        new_alien.x = x_position
        new_alien.rect.x = x_position
        new_alien.rect.y = y_position
        self.aliens.add(new_alien)
        #current_x += 2 * alien_width

    def _update_bullets(self):
        """Update position of bullets and get rid of old bullets"""
        #Update bullet positions
        self.bullets.update()
        #Get rid of bullets that disappeared
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
               self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """Respond to bullet alien collisions"""
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points * len(aliens)
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            #destroy existing bullets and create new fleet
            self.bullets.empty()
            self._create_fleet()
            self.settings.increase_speed()

            #increase level
            self.stats.level += 1
            self.sb.prep_level()

    def _update_aliens(self):
        """Updates position of all aliens in fleet"""
        self._check_fleet_edges()
        self.aliens.update()

        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()

            # look for aliens hitting the bottom of the screen
            self._check_aliens_bottom()
            print("Ship hit!!!")

    def _check_fleet_edges(self):
        """Respond appropriately if any aliens have reached edge"""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Drop entire fleet and change fleets direction"""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1


    def _update_screen(self):
        self.screen.fill(self.settings.bg_color)
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.ship.blitme()
        self.aliens.draw(self.screen)

        #Draw the score info
        self.sb.show_score()

        #Draw the play button if the game is inactive
        if not self.game_active:
            self.play_button.draw_button()
            self.options_button.draw_button()
            self.close_button.draw_button()


        pygame.display.flip()

    
    def _ship_hit(self):
        """Respond to the ship being hit by the aliens."""
        if self.stats.ships_left > 0:
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            #Get rid of any remaining bullets and aliens.
            self.bullets.empty()
            self.aliens.empty()

            #create a new fleet and center the ship
            self._create_fleet()
            self.ship.center_ship()
            #pause
            sleep(0.5)
        else:
            self.game_active = False
            pygame.mouse.set_visible(True)

    def _check_aliens_bottom(self):
        """CHeck if any aliens have reached the bottom of the screen."""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.settings.screen_height:
                #tread this the same as if the ship got hit
                self._ship_hit()
                break

    def _pause_game(self):
        
        if self.game_active == True:
            is_paused = True
            #Create paued loop

            while is_paused:

                self.image = pygame.image.load("images/PAUSED.png") # Replace with your image path
                self.rect = self.image.get_rect()

                basicfont = pygame.font.SysFont(None, 48)
                text = basicfont.render('PAUSED', True, (255, 0, 0), (255, 255, 255))
                dest = (700, 400)
                self.screen.blit(text, dest)
                pygame.display.flip()
                # def _draw_text(text, font, text_col, x, y):
                #     img = font.render(text, True, text_col)
                #     self.screen.blit(img, (x, y))
                pygame.mouse.set_visible(True)    
                pygame.mixer.music.pause()
                
                # text_font = pygame.font.SysFont("Arial", 30)
                # _draw_text(f"PAUSED", text_font, (30, 30, 30), 220, 150)
                for event in pygame.event.get():    
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            is_paused = False
                            pygame.mouse.set_visible(False)
                            pygame.mixer.music.unpause()
                            self.ship.moving_right = False
                            self.ship.moving_left = False
                        elif event.key == pygame.K_q:
                            path = Path('high_score.txt')
                            path.write_text(str(self.stats.high_score))
                            pygame.QUIT()
                    if event.type == pygame.QUIT:
                        is_paused = False
                        sys.exit()
                

if __name__ == '__main__':
    ai = AlienInvasion()
    ai.run_game()