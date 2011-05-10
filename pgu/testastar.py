import pygame
from pygame.locals import *
import math
import random

#Use the PGU folder directly beneath game code folder (coz I've modified it slightly)
import sys; sys.path.insert(0, "pgu")
from pgu import tilevid, timer, algo

g = tilevid.Tilevid()
g.view.w,g.view.h = (SW-(4*TW)),SH
g.screen = pygame.display.set_mode((SW,SH),SWSURFACE)
g.tga_load_level('dj-level1.tga',0)




