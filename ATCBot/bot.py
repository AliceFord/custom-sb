import pygame,random
pygame.init()
font = pygame.font.Font(None,25)

class Bot:
    def __init__(self):
        self.planes = []
        self.landing_order = []
        self.s_width,self.s_height = 800,800
        self.screen = pygame.display.set_mode((self.s_width,self.s_height))
        self.runway_pos = (0,self.s_height//2)
        pygame.draw.circle(self.screen,(255,255,255),self.runway_pos,5)
        pygame.draw.line(self.screen, (255,255,255), self.runway_pos,(self.s_width,self.s_height//2),1)
        for i in range(2, self.s_width, 100):  # Assuming 50 pixels = 1 mile
            pygame.draw.line(self.screen, (255,255,255), (i, self.s_height // 2 - 10), (i, self.s_height // 2 + 10), 1)

        # Extend the 10-mile tick across the whole screen
        pygame.draw.line(self.screen, (255,255,255), (550, 0), (550, self.s_height), 1)

        # Update the display
        pygame.display.flip()

    def get_landing_order(self):
        """gets new planes (as when a handoff occurs) and puts them into a landing order
        """
        print("Getting landing order")
        self.landing_order = sorted(self.planes, key=lambda plane: plane.d)
        

    def test_planes(self,mx,my):
        plane_position = (mx,my)
        id = len(self.planes) + 1
        pygame.draw.circle(self.screen, (255,0,0), plane_position, 5)
        pygame.draw.line(self.screen, (255,255,255), plane_position, (550, plane_position[1]), 1)
        id_surf = font.render(str(id),True, (255,255,255))
        self.screen.blit(id_surf,(mx, my-20))

        distance_to_line = abs(550 - plane_position[0])

        distance_along_line = abs(self.runway_pos[1] - plane_position[1])
        
        distance_down_ILS = abs(self.runway_pos[0] - 550)
        
        total_distance = distance_to_line + distance_along_line + distance_down_ILS
        pygame.display.update()
        print(f"Total distance: {total_distance/50} nm") # 1 nm is 50px
        self.planes.append(Plane(id,mx,my,total_distance/50))


class Plane:
    def __init__ (self,cs, x, y, d):
        self.cs = cs
        self.x = x
        self.y = y 
        self.d = d
        

if __name__ == "__main__":
    bot = Bot()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx,my = pygame.mouse.get_pos()
                bot.test_planes(mx,my)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bot.get_landing_order()
            

    pygame.quit()