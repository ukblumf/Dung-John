"""<title>Dung, John - RetroRemakes competition</title>"""

import pygame
from pygame.locals import *
import math
import random

#Use the PGU folder directly beneath game code folder (coz I've modified tilevid ever so slightly)
import sys; sys.path.insert(0, "pgu")
from pgu import tilevid, timer, algo, ani

pygame.init()

#some global vars
SW,SH = 800,600
TW,TH = 32,32
SPEED = 4
FPS = 25
FACING=['up','down','left','right']
ANGLE=['0','180','90','270'] # the new array in town.
gameLevel=1
maxGameLevels=3
#global msgQ
#msgQ=[]
object_KEY=11
teleportTile=0x0E
spraySpeed=6

#now to the sound
pygame.mixer.stop()
spraySnd=pygame.mixer.Sound('sound/spray.wav')

debugMode=0

class Van(pygame.sprite.Sprite):

    def __init__(self):

        pygame.sprite.Sprite.__init__(self)
        self.image=pygame.image.load("graphics/vansprite.tga").convert_alpha()
        self.rect=self.image.get_rect()

        self.rect.y=371
        self.rect.x=0
        self.bump=0

    def update(self):

        self.rect.x += 2
        if self.rect.left>=SW:self.rect.left=0
        if not self.rect.left%50:
            self.image=pygame.image.load("graphics/vansprite2.tga").convert_alpha()
            self.bump=1
        else:
            if self.bump and not self.rect.left%10:
                self.image=pygame.image.load("graphics/vansprite.tga").convert_alpha()
                self.bump=0

def player_new(g,t,value):
    g.clayer[t.ty][t.tx] = 0
    if hasattr(g,"player"):
        s=g.player
        s.setimage(g.images['player_f0.'+ANGLE[s.facing-1]])
        s.spacebar=0
        s.animFrame=0
        s.rect=t.rect
        g.sprites.append(s)

    else:
        s = tilevid.Sprite(g.images['player_f0.'+ANGLE[3]],t.rect)

        g.sprites.append(s)
        s.loop = player_loop
        s.groups = g.string2groups('player')
        s.score = 0
        s.spriteName="player"
        s.facing=4 # 1=up, 2=down, 3=left, 4=right
        s.hitPoints=100
        s.movementType='player'
        s.msg=""
        s.msgDuration=0
        
        s.spray=1 # 1=detergent, 2=fungicides, 3=poison, 4=bleach
        s.detergent=1000 # full
        s.fungicide=1000
        s.poison=1000
        s.bleach=1000

        s.spacebar=0
        s.spriteNumber=sprite_count(g)
        s.animFrame=0
        s.inventory=[]
        s.isTeleporting=0
        
        g.player = s

def player_loop(g,s):
    keys = pygame.key.get_pressed()
    dx,dy = 0,0
    if keys[K_UP]:
        dy=-spriteData['player']['moveSpeed']
        s.facing=1
    if keys[K_DOWN]:
        dy=spriteData['player']['moveSpeed']
        s.facing=2
    if keys[K_LEFT]:
        dx=-spriteData['player']['moveSpeed']
        s.facing=3
    if keys[K_RIGHT]:
        dx=spriteData['player']['moveSpeed']
        s.facing=4

    #check to see if new position will hit any other sprite
    myRect=pygame.Rect(s.rect.x,s.rect.y,s.rect.width,s.rect.height)
    myRect.x += dx
    myRect.y += dy
    as_=g.sprites[:]
    for spr in as_:
        if s.spriteNumber != spr.spriteNumber and spr.rect.colliderect(myRect) and spr.spriteName != 'spray' and spr.spriteName != 'watertrap':
            if spr.hitPoints>0: #final check
                dx=dx/2
                dy=dy/2
                break

    if dx or dy:
        #I like to move it,move it,I like to ...
        update_anim(s)
        s.setimage(g.images['player_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])
        s.rect.x += dx
        s.rect.y += dy
        s.rect.clamp_ip(g.view)

    ##In player_loop(), check to see if spacebar is pressed for the first time.
    if keys[K_SPACE] and s.spacebar==0:    
        spray_new(g,s,None)

def spray_new(g,t,value):
    #decide which spray to use
    spray_name='' # expand this to use all sprays
    if t.spray==1:
        if t.detergent>0:
            spray_name='spray_detergent'
        else:
            return
    if t.spray==2:
        if t.fungicide>0:
            spray_name='spray_fungicide'
        else:
            return
    if t.spray==3:
        if t.poison>0:
            spray_name='spray_poison'
        else:
            return
    if t.spray==4:
        if t.bleach>0:
            spray_name='spray_bleach'
        else:
            return

    #facing - not really important now, because I load a blank image to start spray and
    #let spray_loop handle positioning and image
    startX,startY=0,0
    s = tilevid.Sprite(g.images['blank'],(startX,startY))
    s.facing=t.facing
    s.spriteName="spray"
    s.sprayName=spray_name
    s.spraySize=1
    s.originalImage=pygame.image.load('graphics/'+spray_name+'_' + str(t.facing) + '.tga').convert_alpha()
    s.spriteNumber=sprite_count(g)
    s.movementType='spray'
    s.msg=""
    s.msgDuration=0        
    
    g.sprites.append(s)
    s.groups=g.string2groups(s.spriteName)
    s.agroups = g.string2groups('small_rat,small_spider,sewer_dweller,dire_tortoise,small_croc,slime,pennyvice')
    s.hit = spray_hit
    s.loop = spray_loop

    #begin sound
    spraySnd.play(-1)

def spray_loop(g,s):
    #Dudes, this is a big lump o' code now.
    #the longer the spacebar is pressed the longer the spray becomes
    #it unfurls to a maximum of 128px
    #also stops upon contact with a non zero tile
    keys = pygame.key.get_pressed()
    if keys[K_SPACE]:
        
        g.player.spacebar=1
        s.spraySize +=spraySpeed
        if s.spraySize>128: s.spraySize=128

        if s.facing<>g.player.facing:
            s.originalImage=pygame.image.load('graphics/'+s.sprayName+'_' + str(g.player.facing) + '.tga').convert_alpha()
            s.facing=g.player.facing

        spX,spY,spWidth,spHeight=0,0,0,0
        if g.player.facing==1:
            #spray up
            spY=128-s.spraySize # spray is going up, so start unfurling from bottom of image
            spWidth=32
            spHeight=s.spraySize
            s.rect.x=g.player.rect.centerx-7
            s.rect.y=g.player.rect.top-s.spraySize-5
        if g.player.facing==2:
            #spray down
            spWidth=32
            spHeight=s.spraySize
            s.rect.x=g.player.rect.centerx-5
            s.rect.y=g.player.rect.bottom+4
        if g.player.facing==3:
            #spray left
            spX=128-s.spraySize
            spWidth=s.spraySize
            spHeight=32
            s.rect.x=g.player.rect.left-s.spraySize-4
            s.rect.y=g.player.rect.centery-23
        if g.player.facing==4:
            #spray right
            spWidth=s.spraySize
            spHeight=32
            s.rect.x=g.player.rect.right+3
            s.rect.y=g.player.rect.centery-7

        #if spray is empty delete spray sprite
        sprayEmpty=0
        if g.player.spray==1:
            g.player.detergent -=1
            if s.spraySize==128:g.player.detergent -=1 #at max length uses double rate
            if g.player.detergent<1:sprayEmpty=1

        if g.player.spray==2:
            g.player.fungicide -=1
            if s.spraySize==128:g.player.fungicide -=1
            if g.player.fungicide<1:sprayEmpty=1

        if g.player.spray==3:
            g.player.poison -=1
            if s.spraySize==128:g.player.poison -=1
            if g.player.poison<1:sprayEmpty=1

        if g.player.spray==4:
            g.player.bleach -=1
            if s.spraySize==128:g.player.bleach -=1
            if g.player.bleach<1:sprayEmpty=1

        if not sprayEmpty:
            #check if spray collides with a tile
            #if so,truncate spray
            if g.player.facing==1:
                cY=0
                cX=(s.rect.x+16)/TW
                while (s.rect.bottom-cY)>(s.rect.bottom-spHeight):
                    if g.tlayer[(s.rect.bottom-cY-spraySpeed)/TH][cX]:
                        spY=128-cY
                        s.spraySize=cY
                        spHeight=cY
                        break
                    cY+=spraySpeed
            elif g.player.facing==2:
                cY=0
                cX=(s.rect.x+16)/TW
                while (s.rect.top+cY)<(s.rect.top+spHeight):
                    if g.tlayer[(s.rect.top+cY+spraySpeed)/TH][cX]:
                        s.spraySize=cY
                        spHeight=cY
                        break
                    cY+=spraySpeed
            elif g.player.facing==3:
                cY=(s.rect.y+16)/TH
                cX=0
                while (s.rect.right-cX)>(s.rect.right-spWidth):
                    if g.tlayer[cY][(s.rect.right-cX-spraySpeed)/TW]:
                        spX=128-cX
                        s.spraySize=cX
                        spWidth=cX
                        break
                    cX+=spraySpeed
            elif g.player.facing==4:
                cY=(s.rect.y+16)/TH
                cX=0
                while (s.rect.left+cX)<(s.rect.left+spWidth):
                    if g.tlayer[cY][(s.rect.left+cX+spraySpeed)/TW]:
                        s.spraySize=cX
                        spWidth=cX
                        break
                    cX+=spraySpeed

            sprayImage=pygame.Surface((spWidth,spHeight))
            sprayImage.blit(s.originalImage,(0,0),[spX,spY,spWidth,spHeight])
            sprayImage.set_colorkey(0)
            s.setimage(sprayImage)
        else:
            if g.sprites.count(s): g.sprites.remove(s)
            g.player.spacebar=0
    else:
        if g.sprites.count(s): g.sprites.remove(s)
        g.player.spacebar=0
        spraySnd.stop()

def spray_hit(g,s,a):
    if a.hitPoints<1: return #don't kick it when its down.
    
    if not sprayDmg[s.sprayName][a.spriteName]: # no damage
        a.msg="No Effect"
        a.msgDuration=g.frames+(FPS/2)
    else:
        a.hitPoints -= sprayDmg[s.sprayName][a.spriteName] # consult the matrix of doom.
        if a.hitPoints<1:
            if a in g.sprites:
                a.spriteName = a.spriteName + '_dead' #sorry ol' boy
                a.animFrame=0
        else:
            if sprayDmg[s.sprayName][a.spriteName]<0:

                monsterRnd=random.randrange(1,3)
                if monsterRnd==1:
                    a.msg="Hmmm,that tastes good"
                elif monsterRnd==2:
                    a.msg="Yum,yum. I'm feeling better"
                else:
                    a.msg="Its not working"
                a.msgDuration=g.frames+(FPS/2)

#generic monster instantiation routine
def monster_factory(g,t,value):
    g.clayer[t.ty][t.tx] = 0 # clear code from code layer

    monsterName,hitPoints,movementType,facing=value
    s = tilevid.Sprite(g.images[monsterName + '_f0.0'],t.rect)
    g.sprites.append(s)

    if movementType == 'simple':
        s.loop = simple_player_chase
    elif movementType == 'astar':
        s.loop = astar_player_chase
        s.refreshRoute=0
        s.playerCoords=(0,0)
        s.astarRoute=[]
    elif movementType =='facing':
        s.loop = move_in_facing_direction
    elif movementType == 'pounce':
        s.loop=pounce
        s.isPouncing=0
        s.isReturningHome=0
        s.homeLocation=(t.tx,t.ty)
        s.refreshRoute=0
        s.playerCoords=(0,0)
        s.astarRoute=[]
    elif movementType == 'spawn_chase':
        s.loop=spawn_chase
        s.maxSpawns=random.randrange(4,10)
        s.spawnCount=0
    elif movementType == 'pennyvice':
        s.loop=pennyvice_loop
        s.sidewaysDir=1
        s.lastFired=0

    s.groups = g.string2groups(monsterName)
    if not facing:#randomly determine facing
        s.facing=random.randrange(1,4)
    else:
        s.facing=facing
    s.spriteName=monsterName
    s.hitdelay=0
    s.hitPoints=hitPoints
    s.movementType=movementType
    s.msg=""
    s.msgDuration=0    
    
    s.animFrame=random.randrange(0,spriteData[s.spriteName]['maxframes'])
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])

    s.agroups = g.string2groups('player')
    s.hit = enemy_hit
    s.spriteNumber=sprite_count(g)
    s.tileCollide=0

#the trap spawner
def trap_factory(g,t,value):

    trapName,movementAngle,trapStart=value

    if (random.randrange(1,200)==1 and trapStart) or not trapStart:
        #g.clayer[t.ty][t.tx] = 0 # clear code from code layer

        #final check, make sure this trap is not already started
        if trapStart:
            for spr in g.sprites:
                if spr.spriteName==trapName:
                    if spr.trapSpawnTile==t:
                        return # already started

        s = tilevid.Sprite(g.images[trapName + '_f0.'+str(movementAngle)],t.rect)
        if not trapStart:
            #adjust positioning of trap tail to cater for movement gap
            if movementAngle==0:
                s.rect.y -= spriteData[trapName]['moveSpeed']
            if movementAngle==180:
                s.rect.y += spriteData[trapName]['moveSpeed']
            if movementAngle==90:
                s.rect.x -= spriteData[trapName]['moveSpeed']
            if movementAngle==270:
                s.rect.x += spriteData[trapName]['moveSpeed']
        g.sprites.append(s)
        s.loop = moving_trap
        s.groups = g.string2groups(trapName)
        s.angle=movementAngle
        s.facing=1
        s.spriteName=trapName
        s.hitdelay=0
        s.hitPoints=1
        s.movementType='trap'
        s.msg=""
        s.msgDuration=0        
        s.animFrame=0

        s.agroups = g.string2groups('player,small_rat,small_spider,small_croc')
        s.hit = enemy_hit # reuse monster hit routine
        s.spriteNumber=sprite_count(g)
        s.tileCollide=0
        s.trapStart=trapStart
        if trapStart:
            s.trapSpawnTile=t
            s.trapLastTilePos=(t.tx,t.ty)
            s.trapLength=random.randrange(1,6)
        else:
            s.trapSpawnTile=0
            s.trapLength=0

def simple_player_chase(g,s):
    #This is your classic move directly towards player type movement
    if spriteCheck(g,s): return

    dx,dy=0,0
    #head directly for player based upon x/y coords
    if g.player.rect.x <s.rect.x:
        dx -= spriteData[s.spriteName]['moveSpeed']
    if g.player.rect.x >s.rect.x:
        dx += spriteData[s.spriteName]['moveSpeed']
    if g.player.rect.y <s.rect.y:
        dy -= spriteData[s.spriteName]['moveSpeed']
    if g.player.rect.y >s.rect.y:
        dy += spriteData[s.spriteName]['moveSpeed']

    dx,dy=spriteCollisionHandler(s,dx,dy)

    if dx or dy:
        #update position
        s.rect.x +=dx
        s.rect.y +=dy
        if abs(s.rect.x-g.player.rect.x)<spriteData[s.spriteName]['moveSpeed']:
            s.rect.x=g.player.rect.x
        if abs(s.rect.y-g.player.rect.y)<spriteData[s.spriteName]['moveSpeed']:
            s.rect.y=g.player.rect.y

    #work out facing based on greatest difference between x and y
    #oldFacing=s.facing
    if abs(g.player.rect.y-s.rect.y)>abs(g.player.rect.x-s.rect.x):
        #vertical facing
        if g.player.rect.y<s.rect.y:
            s.facing=1
        else:
            s.facing=2
    else:
        #horizontal facing
        if g.player.rect.x<s.rect.x:
            s.facing=3
        else:
            s.facing=4

    #if oldFacing<>s.facing:
    update_anim(s)
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])

def move_in_facing_direction(g,s):
    #dumb movement, rebound if collide

    if spriteCheck(g,s): return

    dx,dy=0,0
    if s.facing==1:
        dy -= spriteData[s.spriteName]['moveSpeed']
    if s.facing==2:
        dy += spriteData[s.spriteName]['moveSpeed']
    if s.facing==3:
        dx -= spriteData[s.spriteName]['moveSpeed']
    if s.facing==4:
        dx += spriteData[s.spriteName]['moveSpeed']
    
    if s.spriteName !='pennyvice_tears':
        dx,dy=spriteCollisionHandler(s,dx,dy)

    if dx or dy:
        #update position
        s.rect.x +=dx
        s.rect.y +=dy

    update_anim(s)
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])

def moving_trap(g,s):
    #simplified moving_in_facing_direction
    #but with the added twist of adding a 'tail'

    if s.trapStart:
        #special rules
        #a trap, such as the watertrap, can be a chain of upto 6 sprites
        if (s.rect.x/TW<> s.trapLastTilePos[0] or s.rect.y/TH<>s.trapLastTilePos[1]) and s.trapLength>1:
            s.trapLength -=1
            s.trapLastTilePos=(s.rect.x/TW,s.rect.y/TH)
            trap_factory(g,s.trapSpawnTile,(s.spriteName,s.angle,0))

    dx,dy=0,0
    if s.angle==0:
        dy -= spriteData[s.spriteName]['moveSpeed']
    if s.angle==180:
        dy += spriteData[s.spriteName]['moveSpeed']
    if s.angle==90:
        dx -= spriteData[s.spriteName]['moveSpeed']
    if s.angle==270:
        dx += spriteData[s.spriteName]['moveSpeed']

    #update position
    s.rect.x +=dx
    s.rect.y +=dy

    update_anim(s)
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+str(s.angle)])

def astar_player_chase(g,s):
    #the clever movement type
    #to add further 'AI' I will pass in the refreshRoute as a param
    #so 'cleverer' creatures update their paths more frequently
    if spriteCheck(g,s): return

    updateFacing=0

    #only refresh astar path every couple of seconds and only if player has moved out of position
    if (s.refreshRoute<=g.frames) or not s.astarRoute:
        updateRoute=1
        destTX=g.player.rect.x/TW
        destTY=g.player.rect.y/TH
        if hasattr(s,'isPouncing'):
            if s.astarRoute: #route already set, stay on target
                updateRoute=0
            elif s.isReturningHome and not s.astarRoute:
                #monster is going home
                destTX,destTY=s.homeLocation
        if updateRoute:
            s.refreshRoute=g.frames+(FPS*2)
            tx,ty=s.playerCoords
            if tx<>destTX or ty<>destTY:
                #refresh the route
                s.astarRoute=algo.astar((s.rect.x/TW,s.rect.y/TH),(destTX,destTY),g.tlayer)
                s.playerCoords=(destTX,destTY)
                updateFacing=1

    if not s.astarRoute: return

    txPx,tyPx=s.astarRoute[0]
    txPx *= TW
    tyPx *= TH

    dx,dy=0,0
    if txPx <s.rect.x:
        dx -= spriteData[s.spriteName]['moveSpeed']
    if txPx >s.rect.x:
        dx += spriteData[s.spriteName]['moveSpeed']
    if tyPx <s.rect.y:
        dy -= spriteData[s.spriteName]['moveSpeed']
    if tyPx >s.rect.y:
        dy += spriteData[s.spriteName]['moveSpeed']

    #check to see if move will collide with any other sprite other than self
    dx,dy=spriteCollisionHandler(s,dx,dy)

    if dx or dy:
        #update position
        s.rect.x +=dx
        s.rect.y +=dy
        if abs(s.rect.x-txPx)<spriteData[s.spriteName]['moveSpeed']:
            s.rect.x=txPx
        if abs(s.rect.y-tyPx)<spriteData[s.spriteName]['moveSpeed']:
            s.rect.y=tyPx

        #remove astar coordinate.
        if txPx == s.rect.x and tyPx == s.rect.y:
            s.astarRoute.pop(0)
            if s.astarRoute:
                updateFacing=1
                txPx,tyPx=s.astarRoute[0]
                txPx *= TW
                tyPx *= TH
            elif hasattr(s,'isPouncing'):
                if s.isPouncing:
                    s.isPouncing=0
                    s.isReturningHome=1
                elif s.isReturningHome:
                    #in theory the pouncer should be at home square
                    s.isReturningHome=0

    if updateFacing:
        if abs(s.rect.x-txPx)>abs(s.rect.y-tyPx):
            if txPx<s.rect.x:
                s.facing=3
            else:
                s.facing=4
        else:
            if tyPx<s.rect.y:
                s.facing=1
            else:
                s.facing=2

    update_anim(s)
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])

def pounce(g,s):

    if spriteCheck(g,s): return

    if s.isPouncing or s.isReturningHome:
        astar_player_chase(g,s)

    if not s.isPouncing and not s.isReturningHome:
        if algo.dist((s.rect.x/TW,s.rect.y/TH),(g.player.rect.x/TW,g.player.rect.y/TH))<6:
            s.isPouncing=1

def spawn_chase(g,s):

    if spriteCheck(g,s): return

    if s.spawnCount<s.maxSpawns:
        #check if slime wants to spawn
        if random.randrange(1,25)==1:
            #at this rate it will be the size of the planet.
            #find an available tile space
            slimeTX=s.rect.x/TW
            slimeTY=s.rect.y/TH
            for dx,dy in [(0,-1),(1,0),(0,1),(-1,0)]:
                if g.tlayer[dy+slimeTY][dx+slimeTX]:continue # occupied by a tile
                #found empty tile
                t=tilevid.Tile()
                t.tx=dx+slimeTX
                t.ty=dy+slimeTY
                t.rect=pygame.Rect(t.tx*TW,t.ty*TH,s.rect.width,s.rect.height)
                if dx==-1:t.rect.left=s.rect.right
                if dx==1:t.rect.right=s.rect.left
                if dy==-1:t.rect.bottom=s.rect.top
                if dy==1:t.rect.top=s.rect.bottom
                monster_factory(g,t,('slime',60,'simple',s.facing))
                s.spawnCount +=1
                break

    simple_player_chase(g,s)

def fungus_new(g,t,value):
    g.clayer[t.ty][t.tx] = 0
    s = tilevid.Sprite(g.images['fungus'],t.rect)
    g.sprites.append(s)
    s.spriteName="fungus"
    s.groups = g.string2groups('fungus')
    s.agroups = g.string2groups('player')
    s.hit = bonus_collect
    s.spriteNumber=sprite_count(g)
    s.movementType='fungus'
    s.msg=""
    s.msgDuration=""
    s.hitPoints=0

def bonus_collect(g,s,a):
    if s.spriteName=='fungus':
        a.hitPoints +=50
        if a.hitPoints>100:a.hitPoints=100

    if g.sprites.count(s): g.sprites.remove(s)

def enemy_hit(g,s,a):
    if s.hitdelay<g.frames:
        s.hitdelay=g.frames+(FPS/2)
        if not debugMode: a.hitPoints -= spriteData[s.spriteName]['attackDmg']
        if a.spriteName=='player' and a.hitPoints>0 and spriteData[s.spriteName]['attackDmg']>0:
            if spriteData[s.spriteName]['attackDmg']<=10:
                a.msg="Come on yer wuss"
            elif spriteData[s.spriteName]['attackDmg']<=20:
                a.msg="Ouch"
            elif spriteData[s.spriteName]['attackDmg']<=30:
                a.msg="That smarts"
            elif spriteData[s.spriteName]['attackDmg']<=50:
                a.msg="That really really hurts"
            else:
                a.msg="ARGHHHHHH!"
            a.msgDuration=g.frames+(FPS/2)
            
        if a.hitPoints<1:
            if a.spriteName=='player':
                g.quit = 1
            else:
                if g.sprites.count(a):
                    g.sprites.remove(a)
        
        if s.spriteName=='pennyvice_tears':
            if g.sprites.count(s): g.sprites.remove(s)

def spriteCheck(g,s):
    #standard function that all sprite movers call
    #checks whether sprite is in 'dead' phase
    #or latched onto player
    functionReturn=0
    if s.hitPoints<1:
        update_anim(s)
        if s.animFrame==-1:# end of death animation
            if g.sprites.count(s): g.sprites.remove(s)
        else:
            s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])
        functionReturn=1

    #if in collision with player then exit
    if s.rect.colliderect(g.player.rect): functionReturn=1

    return functionReturn

def spriteCollisionHandler(s,dx,dy):
    #check to see if move will collide with any other sprite other than self and spray
    if not hasattr(s,'maxSpawns'):
        myRect=pygame.Rect(s.rect.x,s.rect.y,s.rect.width,s.rect.height)
        myRect.x += dx
        myRect.y += dy
        as_=g.sprites[:]
        for spr in as_:
            if spr.spriteNumber != s.spriteNumber and spr.rect.colliderect(myRect) and spr.spriteName != 'spray' and spr.spriteName != 'player':
                if s.movementType=='facing' and s.spriteName in g.bossList:
                    s.tileCollide +=1
                    if s.tileCollide>=10:
                        s.tileCollide=0
                        s.facing=change_facing(s.facing)
                elif s.movementType=='facing':
                    dx,dy=0,0
                    s.facing=change_facing(s.facing)
                else:
                    myRect.x -= dx
                    myRect.y -= dy
                    if spr.rect.colliderect(myRect) and s.spriteNumber<spr.spriteNumber: #if already in collision keep moving,and hope it sorts itself out :)
                        break
                    elif spr.rect.colliderect(myRect) and s.spriteNumber>spr.spriteNumber and spr.hitPoints>1:
                        dx,dy=0,0
                        break
                    elif s.spriteNumber<spr.spriteNumber or spr.hitPoints<1:
                        break
                    else:
                        dx,dy=0,0
                break
    return dx,dy

def update_anim(s):
    if not g.frames%spriteData[s.spriteName]['animSpeed']:
        s.animFrame+=1
        if s.animFrame>spriteData[s.spriteName]['maxframes']:
            if s.hitPoints<1: # if sprite has less than 1 hitpoint, it is dead,no more, deceased
                s.animFrame=-1# so alert movement routine that death animation has finished
            else:
                s.animFrame=0

def tile_block(g,t,a):
    c = t.config
    if (c['top'] == 1 and a._rect.bottom <= t._rect.top and a.rect.bottom > t.rect.top):
        a.rect.bottom = t.rect.top
    if (c['left'] == 1 and a._rect.right <= t._rect.left and a.rect.right > t.rect.left):
        a.rect.right = t.rect.left
    if (c['right'] == 1 and a._rect.left >= t._rect.right and a.rect.left < t.rect.right):
        a.rect.left = t.rect.right
    if (c['bottom'] == 1 and a._rect.top >= t._rect.bottom and a.rect.top < t.rect.bottom):
        a.rect.top = t.rect.bottom

    # deal with boss/tile collisions differently because they are bigger than TW and TH
    if a.spriteName in g.bossList:
        a.tileCollide +=1
        if a.tileCollide>=10:
            a.tileCollide=0
            if a.spriteName=='pennyvice':#more rules
                #all bosses need special rules
                if a.sidewaysDir>0:
                    a.sidewaysDir=-1
                else:
                    a.sidewaysDir=1
            else:
                a.facing=change_facing(a.facing)
                a.setimage(g.images[a.spriteName+'_f0.'+ANGLE[a.facing-1]])

    if a.movementType=='facing':
        a.facing=change_facing(a.facing)
        a.setimage(g.images[a.spriteName+'_f0.'+ANGLE[a.facing-1]])

    if a.spriteName =='watertrap' or a.spriteName=='pennyvice_tears':
        if g.sprites.count(a):
            g.sprites.remove(a)

def gate(g,t,a):
    #ah!!, them sneaky monsters are using the players keys to open gates
    #the cheek of it! need to add spriteName check.
    if g.player.inventory.count(object_KEY) and a.spriteName=='player':
         g.tlayer[t.ty][t.tx] = 0
         g.player.inventory.remove(object_KEY)
    else:
        tile_block(g,t,a)

def key_pickup(g,t,a):
    #add to inventory
    if len(a.inventory)<3:
        a.inventory.append(g.tlayer[t.ty][t.tx]) # add item to inventory
        g.tlayer[t.ty][t.tx] = 0

def change_facing(f):
    #crikey, I wish had started out with 1=up,2=right,3=down and 4=left.Would have been so much simpler
    if f==1:
        f=2
    elif f==2:
         f=1
    elif f==3:
         f=4
    else:
         f=3
    return f

def sprite_count(g):
    g.spriteCount += 1
    return g.spriteCount

#player has reached escape exit of level
def exit_level(g,t,a):
    g.quit=1
    g.nextLevel=1

def teleport(g,t,a):

    if a.spriteName<>'player': return

    #how many teleports?
    teleportCount=len(g.teleports)-1

    #find teleporters position
    currentTeleporter=0
    while g.teleports[currentTeleporter] != (t.tx,t.ty):
        currentTeleporter +=1
        if currentTeleporter >teleportCount:break #somethings gone wrong
       
    if currentTeleporter<=teleportCount: #somethings gone right
        g.player.isTeleporting=1
        g.teleportIndex=currentTeleporter+1
        if g.teleportIndex>teleportCount: g.teleportIndex=0

def powerup_new(g,t,value):
    #go go power uppers
    g.clayer[t.ty][t.tx] = 0
    powerUpName=value
    s = tilevid.Sprite(g.images['powerup_'+powerUpName],t.rect)
    g.sprites.append(s)
    s.spriteName='powerup_'+powerUpName
    s.groups = g.string2groups(s.spriteName)
    s.agroups = g.string2groups('player')
    s.hit = powerup_collect
    s.spriteNumber=sprite_count(g)
    s.movementType='powerup'
    s.msg=""
    s.msgDuration=""
    s.hitPoints=0

def powerup_collect(g,s,a):
    #the reward
    if s.spriteName=='powerup_detergent':
        g.player.detergent +=500
        if g.player.detergent>1000:g.player.detergent=1000
    elif s.spriteName=='powerup_fungicide':
        g.player.fungicide +=500
        if g.player.fungicide>1000:g.player.fungicide=1000
    elif s.spriteName=='powerup_poison':
        g.player.poison +=500
        if g.player.poison>1000:g.player.poison=1000
    elif s.spriteName=='powerup_bleach':
        g.player.bleach +=500
        if g.player.bleach>1000:g.player.bleach=1000

    if g.sprites.count(s): g.sprites.remove(s)

def pennyvice_loop(g,s):
    #custom movement routine for the clown <shiver>
    if spriteCheck(g,s): return
    
    #sprite will move sideways, this may be left/right or up/down depending on facing
    #if player is within 10 squares he fires tears every couple of seconds
    dx,dy=0,0    
    if s.facing==1 or s.facing==3:
        if s.sidewaysDir>0:
            dx = spriteData[s.spriteName]['moveSpeed']
        else:        
            dx -= spriteData[s.spriteName]['moveSpeed']
    else:
        if s.sidewaysDir>0:
            dy = spriteData[s.spriteName]['moveSpeed']
        else:
            dy -= spriteData[s.spriteName]['moveSpeed']

    dx,dy=spriteCollisionHandler(s,dx,dy)

    if dx or dy:
        #update position
        s.rect.x +=dx
        s.rect.y +=dy

    update_anim(s)
    s.setimage(g.images[s.spriteName+'_f'+str(s.animFrame)+'.'+ANGLE[s.facing-1]])
    
    if algo.dist(((s.rect.x/TW)+1,(s.rect.y/TH)+1),(g.player.rect.x/TW,g.player.rect.y/TH))<10 and s.lastFired<g.frames:
        #unleash the tears
        if s.facing==1:
            ctRect=Rect(s.rect.x+26,s.rect.y+14,TW,TH)
        elif s.facing==2:
            ctRect=Rect(s.rect.x+26,s.rect.y+48,TW,TH)
        elif s.facing==3:
            ctRect=Rect(s.rect.x+18,s.rect.y+28,TW,TH)
        else:
            ctRect=Rect(s.rect.x+47,s.rect.y+27,TW,TH)
            
        ct = tilevid.Sprite(g.images['pennyvice_tears_f0.0'],ctRect)
        g.sprites.append(ct)
        ct.loop = move_in_facing_direction
        ct.groups = g.string2groups('pennyvice_tears')
        ct.facing=s.facing
        ct.spriteName='pennyvice_tears'
        ct.hitdelay=0
        ct.hitPoints=1
        ct.movementType='facing'
        ct.msg=""
        ct.msgDuration=0    
        ct.animFrame=0
        ct.setimage(g.images[ct.spriteName+'_f0.'+ANGLE[ct.facing-1]])

        ct.agroups = g.string2groups('player')
        ct.hit = enemy_hit
        ct.spriteNumber=sprite_count(g)
        ct.tileCollide=0
        s.lastFired=g.frames+(FPS)
    
#wait for a key to be pressed
def pressKey():
    pygame.event.clear()
    pressAnyKey=0
    gameLoopQuit=0
    while not pressAnyKey:
        for e in pygame.event.get():
            if e.type is QUIT:
                pressAnyKey=1
                gameLoopQuit=1
            if e.type is KEYDOWN and e.key == K_ESCAPE:
                pressAnyKey=1
                gameLoopQuit=1
            if e.type is KEYDOWN:
                pressAnyKey=1
    return gameLoopQuit
    
# Codes layer, when code is encountered run appropriate instantiation routine
cdata = {
    1:(player_new,None),
    2:(monster_factory,('small_rat',20,'simple',0)),
    3:(monster_factory,('small_spider',40,'facing',0)),
    4:(monster_factory,('sewer_dweller',60,'astar',0)),
    5:(fungus_new,None),
    6:(monster_factory,('dire_tortoise',150,'facing',3)),
    7:(monster_factory,('small_croc',50,'pounce',0)),
    8:(monster_factory,('slime',60,'spawn_chase',0)),
    9:(monster_factory,('pennyvice',200,'pennyvice',1)),
    10:(powerup_new,('detergent')),
    11:(powerup_new,('fungicide')),
    12:(powerup_new,('poison')),
    13:(powerup_new,('bleach')),
    24:(trap_factory,('watertrap',0,1)),
    25:(trap_factory,('watertrap',180,1)),
    26:(trap_factory,('watertrap',90,1)),
    27:(trap_factory,('watertrap',270,1)),
    }

# image data
idata = [
    ('fungus','graphics/fungus.tga',(1,4,27,25)),
    ('spray_detergent_1','graphics/spray_detergent_1.tga',(1,4,27,25)),
    ('spray_detergent_2','graphics/spray_detergent_2.tga',(1,4,27,25)),
    ('spray_detergent_3','graphics/spray_detergent_3.tga',(1,4,27,25)),
    ('spray_detergent_4','graphics/spray_detergent_4.tga',(1,4,27,25)),
    ('blank','graphics/empty.tga',(1,1,1,1)),
    ('powerup_detergent','graphics/powerup_detergent.tga',(1,4,27,25)),
    ('powerup_fungicide','graphics/powerup_fungicide.tga',(1,4,27,25)),
    ('powerup_poison','graphics/powerup_poison.tga',(1,4,27,25)),
    ('powerup_bleach','graphics/powerup_bleach.tga',(1,4,27,25)),
    ]

#Tile data, how do the tiles interact with players and meanies
tdata = {
    0x01:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x02:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x03:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x04:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x05:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x06:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x07:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x08:('player,small_rat,sewer_dweller,small_spider,dire_tortoise,watertrap',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x09:('player',exit_level,{'top':1,'bottom':0,'left':0,'right':1}),
    0x0B:('player',key_pickup,{'top':1,'bottom':0,'left':0,'right':1}),
    0x0C:('player,small_rat,small_croc,slime,small_spider,sewer_dweller,watertrap',gate,{'top':1,'bottom':1,'left':1,'right':1}),
    0x0D:('player,small_rat,small_croc,slime,small_spider,sewer_dweller,watertrap',gate,{'top':1,'bottom':1,'left':1,'right':1}),
    0x0E:('player',teleport,{'top':1,'bottom':1,'left':1,'right':1}),
    0x10:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x11:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x12:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x13:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x14:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x15:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x16:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x17:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x10:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x1C:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x1D:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x20:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x21:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x22:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x23:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x24:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x28:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x29:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x2A:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x2B:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x2C:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x30:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x31:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1}),
    0x32:('player,small_rat,small_croc,slime,watertrap,sewer_dweller,pennyvice,pennyvice_tears',tile_block,{'top':1,'bottom':1,'left':1,'right':1})
    }

#Matrix of spray damage against meanies, Python is really cool at this stuff
sprayDmg = {
    'spray_detergent':{
                       'small_rat': 0,
                       'small_spider': 0,
                       'sewer_dweller':2,
                       'dire_tortoise':1,
                       'small_croc':2,
                       'slime':0,
                       'pennyvice':1
                       },
    'spray_fungicide':{
                       'small_rat': 0,
                       'small_spider': 0,
                       'sewer_dweller':2,
                       'dire_tortoise':1,
                       'small_croc':0,
                       'slime':-1,
                       'pennyvice':0
                       },
    'spray_poison':{
                    'small_rat': 2,
                    'small_spider': 2,
                    'sewer_dweller':0,
                    'dire_tortoise':0,
                    'small_croc':0,
                    'slime':0,
                    'pennyvice':-1
                    },
    'spray_bleach':{
                    'small_rat': 0,
                    'small_spider': 1,
                    'sewer_dweller':0,
                    'dire_tortoise':0,
                    'small_croc':0,
                    'slime':2,
                    'pennyvice':1
                    },
    }

#spriteData
#details animation data,moveSpeed and damage (amalgamating various other dict lists into one source)
#animSpeed=higher the number the slower the animation
#maxframes is zero based
spriteData = {
    'small_rat':{'animSpeed':2,'maxframes':3,'moveSpeed':2,'attackDmg':10},
    'small_spider':{'animSpeed':4,'maxframes':3,'moveSpeed':3,'attackDmg':20},
    'sewer_dweller':{'animSpeed':4,'maxframes':3,'moveSpeed':2,'attackDmg':30},
    'dire_tortoise':{'animSpeed':4,'maxframes':3,'moveSpeed':4,'attackDmg':50},
    'player':{'animSpeed':2,'maxframes':3,'moveSpeed':5,'attackDmg':0},
    'watertrap':{'animSpeed':6,'maxframes':1,'moveSpeed':8,'attackDmg':30},
    'small_rat_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},
    'small_spider_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},
    'sewer_dweller_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},
    'dire_tortoise_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},

    'small_croc':{'animSpeed':4,'maxframes':3,'moveSpeed':8,'attackDmg':30},
    'slime':{'animSpeed':4,'maxframes':2,'moveSpeed':2,'attackDmg':25},
    'small_croc_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},
    'slime_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':0},
    'pennyvice':{'animSpeed':4,'maxframes':3,'moveSpeed':4,'attackDmg':50},
    'pennyvice_dead':{'animSpeed':20,'maxframes':1,'moveSpeed':0,'attackDmg':20},
    'pennyvice_tears':{'animSpeed':100,'maxframes':0,'moveSpeed':6,'attackDmg':25},

    }

def init():
    g = tilevid.Tilevid()
    g.view.w,g.view.h = (SW-(4*TW)),SH
    if not debugMode:
        g.screen = pygame.display.set_mode((SW,SH),SWSURFACE)
    else:
        g.screen = pygame.display.set_mode((SW,SH),SWSURFACE)
        
    g.spriteCount=0
    g.quit=0

    # Load game images
    g.load_images(idata)

    #animated hero, big step forward (or rather a waddle forward)
    sprite=pygame.image.load("graphics/player_frame0.tga").convert_alpha()
    ani.image_rotate(g,'player_f0',sprite,(3,11,21,14),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/player_frame1.tga").convert_alpha()
    ani.image_rotate(g,'player_f1',sprite,(3,11,21,14),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/player_frame0.tga").convert_alpha()
    ani.image_rotate(g,'player_f2',sprite,(3,11,21,14),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/player_frame2.tga").convert_alpha()
    ani.image_rotate(g,'player_f3',sprite,(3,11,21,14),[0,90,180,270],0)

    #the multitudinous horde, moving!
    sprite=pygame.image.load("graphics/small_rat_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_f0',sprite,(7,1,13,25),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_rat_frame1.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_f1',sprite,(7,1,13,25),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_rat_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_f2',sprite,(7,1,13,25),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_rat_frame2.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_f3',sprite,(7,1,13,25),[0,90,180,270],0)

    #the horde, deceased.
    sprite=pygame.image.load("graphics/small_rat_dead0.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_dead_f0',sprite,(7,1,13,25),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_rat_dead1.tga").convert_alpha()
    ani.image_rotate(g,'small_rat_dead_f1',sprite,(7,1,13,25),[0,90,180,270],0)

    #animated sewer dweller
    sprite=pygame.image.load("graphics/sewer_dweller_frame0.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_f0',sprite,(4,4,25,15),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/sewer_dweller_frame1.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_f1',sprite,(4,4,25,15),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/sewer_dweller_frame0.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_f2',sprite,(4,4,25,15),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/sewer_dweller_frame2.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_f3',sprite,(4,4,25,15),[0,90,180,270],0)

    #dead dwellers.
    sprite=pygame.image.load("graphics/sewer_dweller_dead0.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_dead_f0',sprite,(4,4,25,15),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/sewer_dweller_dead1.tga").convert_alpha()
    ani.image_rotate(g,'sewer_dweller_dead_f1',sprite,(4,4,25,15),[0,90,180,270],0)

    #Spider animated
    sprite=pygame.image.load("graphics/small_spider_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_f0',sprite,(1,7,27,22),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_spider_frame1.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_f1',sprite,(1,7,27,22),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_spider_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_f2',sprite,(1,7,27,22),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_spider_frame2.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_f3',sprite,(1,7,27,22),[0,90,180,270],0)

    #spidey diedy
    sprite=pygame.image.load("graphics/small_spider_dead0.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_dead_f0',sprite,(1,7,27,22),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_spider_dead1.tga").convert_alpha()
    ani.image_rotate(g,'small_spider_dead_f1',sprite,(1,7,27,22),[0,90,180,270],0)

    #Dire tortoise, arghh the horror!
    sprite=pygame.image.load("graphics/dire_tortoise_frame0.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_f0',sprite,(30,4,34,84),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/dire_tortoise_frame1.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_f1',sprite,(30,4,34,84),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/dire_tortoise_frame0.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_f2',sprite,(30,4,34,84),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/dire_tortoise_frame2.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_f3',sprite,(30,4,34,84),[0,90,180,270],0)

    #tortoise shell
    sprite=pygame.image.load("graphics/dire_tortoise_dead0.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_dead_f0',sprite,(30,4,34,84),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/dire_tortoise_dead1.tga").convert_alpha()
    ani.image_rotate(g,'dire_tortoise_dead_f1',sprite,(30,4,34,84),[0,90,180,270],0)

    #Water trap
    sprite=pygame.image.load("graphics/watertrap_frame0.tga").convert_alpha()
    ani.image_rotate(g,'watertrap_f0',sprite,(2,2,28,28),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/watertrap_frame1.tga").convert_alpha()
    ani.image_rotate(g,'watertrap_f1',sprite,(2,2,28,28),[0,90,180,270],0)

    #small crocs
    sprite=pygame.image.load("graphics/small_croc_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_f0',sprite,(5,2,19,27),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_croc_frame1.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_f1',sprite,(5,2,19,27),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_croc_frame0.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_f2',sprite,(5,2,19,27),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_croc_frame2.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_f3',sprite,(5,2,19,27),[0,90,180,270],0)

    #croc croaked
    sprite=pygame.image.load("graphics/small_croc_dead0.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_dead_f0',sprite,(5,2,19,27),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/small_croc_dead1.tga").convert_alpha()
    ani.image_rotate(g,'small_croc_dead_f1',sprite,(5,2,19,27),[0,90,180,270],0)

    #I've been slimed
    sprite=pygame.image.load("graphics/slime_frame0.tga").convert_alpha()
    ani.image_rotate(g,'slime_f0',sprite,(3,1,26,29),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/slime_frame1.tga").convert_alpha()
    ani.image_rotate(g,'slime_f1',sprite,(3,1,26,29),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/slime_frame2.tga").convert_alpha()
    ani.image_rotate(g,'slime_f2',sprite,(3,1,26,29),[0,90,180,270],0)

    #slime dead
    sprite=pygame.image.load("graphics/slime_dead0.tga").convert_alpha()
    ani.image_rotate(g,'slime_dead_f0',sprite,(3,1,26,29),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/slime_dead1.tga").convert_alpha()
    ani.image_rotate(g,'slime_dead_f1',sprite,(3,1,26,29),[0,90,180,270],0)

    #pennyvice, clown <shudder>
    sprite=pygame.image.load("graphics/pennyvice_frame0.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_f0',sprite,(0,10,91,65),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/pennyvice_frame1.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_f1',sprite,(0,10,91,65),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/pennyvice_frame0.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_f2',sprite,(0,10,91,65),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/pennyvice_frame2.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_f3',sprite,(0,10,91,65),[0,90,180,270],0)

    #clown tears
    sprite=pygame.image.load("graphics/pennyvice_tears.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_tears_f0',sprite,(3,0,28,29),[0,90,180,270],0)

    #stop clowning about
    sprite=pygame.image.load("graphics/pennyvice_dead0.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_dead_f0',sprite,(0,10,91,65),[0,90,180,270],0)
    sprite=pygame.image.load("graphics/pennyvice_dead1.tga").convert_alpha()
    ani.image_rotate(g,'pennyvice_dead_f1',sprite,(0,10,91,65),[0,90,180,270],0)
    
    #title screen - van sprite
    sprite=pygame.image.load("graphics/vansprite.tga").convert_alpha()

    ##set a font
    g.font = pygame.font.SysFont('helvetica',16)
    g.hitPointFont=pygame.font.SysFont('helvetica',24)

    #boss list
    g.bossList=['dire_tortoise','pennyvice']

    global statusBar1Percent
    statusBar1Percent=154.0/1000.0 # 1% of the status bar in pixels
    pygame.display.set_caption('2D Top Down Dungeon - Well Dungeon might be stretching it a bit, more a sewer really')

    return g

def next_level(g,level):
    #initialise in game vars
    g.frames=0
    g.nextLevel=0 # used to determine if player has escaped level
    g.sprites=[] # clear sprite array

    # only one set of tiles, though could easily be changed to allow a tileset per level
    g.tga_load_tiles('level/simple01_gimp.tga',(TW,TH),tdata)
    g.tga_load_level('level/dj-level' + str(level) + '.tga',0)

    #find players start position
    w,h=g.size    
    vx,vy=0,0
    foundPlayer=0
    for y in range(0,h-1):
        for x in range (0,w-1):
            if g.clayer[y][x]==1:#found him
                vx=x*TW
                vy=y*TH
                foundPlayer=1
                break
        if foundPlayer:break

    halfScreenWidth=((SW/TW)-4)/2
    halfScreenHeight=(SH/TH)/2
    if vx-halfScreenWidth<0:vx=0
    if vy-halfScreenHeight<0:vy=0
    g.view.x=vx

    #initialise codes
    g.run_codes(cdata,(vx/TW,vy/TH,(SW/TW)-5,(SH/TH)-1))

    #Set the bounds of the level.  The view will never go
    #outside the bounds of the level.
    g.bounds = pygame.Rect(0,0,(len(g.tlayer[0])-2)*TW,(len(g.tlayer)-2)*TH)

    #find teleports if they exist for level
    g.teleports=[]
    g.teleportIndex=0

    for y in range(0,h-1):
        for x in range (0,w-1):
            if g.tlayer[y][x]==teleportTile:g.teleports.append((x,y))

def runLevel(g):
    statusPanel=pygame.image.load("graphics/status_panel.jpg").convert()
    panelReset=pygame.Surface((128,480)).convert()
    panelReset.blit(statusPanel,(0,0),[0,120,128,480])
    clock = pygame.time.Clock()
    gameLoopQuit=0
    #global msgQ
    #inner game loop - where the action is
    halfScreenWidth=((SW/TW)-4)/2
    halfScreenHeight=(SH/TH)/2
    mapWidth=128
    mapHeight=64

    while not g.quit:
        dx,dy = 0,0
        for e in pygame.event.get():
            if e.type is QUIT:
                g.quit = 1
                gameLoopQuit=1
            if e.type is KEYDOWN and e.key == K_ESCAPE:g.quit = 1
            if e.type is KEYDOWN and (e.key==K_1 or e.key==K_2 or e.key==K_3 or e.key==K_4):
                g.player.spray = e.key-48

        if g.player.isTeleporting: #apparently, the player is being fancy
            for dx,dy in [(0,-1),(1,0),(0,1),(-1,0)]:
                if g.tlayer[dy+g.teleports[g.teleportIndex][1]][dx+g.teleports[g.teleportIndex][0]]:continue # occupied by a tile
                g.player.rect.x=(dx+g.teleports[g.teleportIndex][0])*TW
                g.player.rect.y=(dy+g.teleports[g.teleportIndex][1])*TH
                break
            g.player.isTeleporting=0

        # Derive view from players coords
        g.view.x = g.player.rect.x - (halfScreenWidth*TW)
        g.view.y = g.player.rect.y- (halfScreenHeight*TH)

        #activating run codes
        #need to activate the codes 1 row and 1 col out of view, as this makes sprites appear smoothly
        #also need to run all codes in viewable area for the traps to work
        rcX,rcY,rcW,rcH=0,0,0,0
        playerTX=(g.player.rect.x/TW)-1
        if playerTX<0:playerTX=0
        playerTY=(g.player.rect.y/TH)-1

        if playerTX<halfScreenWidth:
            rcX=0
            rcW=(halfScreenWidth*2)+2
        elif playerTX>(mapWidth-halfScreenWidth):
            rcX=mapWidth-((SW/TW)-4)
            rcW=halfScreenWidth*2
        else:
            rcX=(g.player.rect.x/TW)-halfScreenWidth
            rcW=(halfScreenWidth*2)+2
            if rcX+rcW>mapWidth: rcW=mapWidth-rcX
        if (g.player.rect.y/TH)<halfScreenHeight:
            rcY=0
            rcH=(halfScreenHeight*2)+2
        elif (g.player.rect.y/TW)>(mapHeight-halfScreenHeight):
            rcY=mapHeight-(SH/TH)
            rcH=halfScreenHeight*2
        else:
            rcY=(g.player.rect.y/TH)-halfScreenHeight
            rcH=(halfScreenHeight*2)+2
            if rcY+rcH>mapHeight:rcH=mapHeight-rcY

        g.run_codes(cdata,(rcX,rcY,rcW,rcH))

        g.loop()
        g.screen.fill((0,0,0))
        g.paint(g.screen) # draw the level and the sprites

        #Player Hit Points
        statusPanel.blit(panelReset,(0,120)) # Reset status panel
        if g.player.hitPoints<100:
            pygame.draw.rect(statusPanel,(32,32,32),[4+(g.player.hitPoints*1.2),160,120-(g.player.hitPoints*1.2),33],0)

        #update inventory
        itemCount=0
        for item in g.player.inventory:
            statusPanel.blit(g.tiles[item].image,(4+(itemCount*TW),128))
            itemCount+=1

        #spray levels
        if g.player.detergent<1000:pygame.draw.rect(statusPanel,(32,32,32),[11,245,40,155-(statusBar1Percent*g.player.detergent)],0)
        if g.player.fungicide<1000:pygame.draw.rect(statusPanel,(32,32,32),[77,245,40,155-(statusBar1Percent*g.player.fungicide)],0)
        if g.player.poison<1000:pygame.draw.rect(statusPanel,(32,32,32),[11,433,40,155-(statusBar1Percent*g.player.poison)],0)
        if g.player.bleach<1000:pygame.draw.rect(statusPanel,(32,32,32),[78,432,40,155-(statusBar1Percent*g.player.bleach)],0)
        if g.player.spray==1:
            pygame.draw.rect(statusPanel,(255,255,0),(1,222,64,13),1)
        elif g.player.spray==2:
            pygame.draw.rect(statusPanel,(255,255,0),(69,222,58,13),1)
        elif g.player.spray==3:
            pygame.draw.rect(statusPanel,(255,255,0),(8,414,48,13),1)
        else:
            pygame.draw.rect(statusPanel,(255,255,0),(75,414,48,13),1)

        #blit the status panel to game screen
        g.screen.blit(statusPanel,(SW-(4*TW),0))

        #write out messages
        vx,vy=g.view.x,g.view.y
        if vx<0:vx=0
        if vy<0:vy=0
        for spr in g.sprites[:]:
            if spr.msg:
                msg = g.font.render(spr.msg,1,(198,198,198))
                g.screen.blit(msg,(spr.rect.x+16-vx,spr.rect.y+16-vy))
                if g.frames>spr.msgDuration:
                    spr.msg="" # clear message
                    

        pygame.display.flip()
        g.frames += 1

        #Lock frame rate
        clock.tick(FPS)

    return gameLoopQuit

#outer gameloop - display title screen
random.seed()
g=init() # one time only
gameLoopQuit=0

while not gameLoopQuit and gameLevel<=3:
    gameLevel=1 # reset global var
    if hasattr(g,"player"):
        delattr(g,"player") # stops player object being carried over into next game

    #start title music
    titleMusic=pygame.mixer.Sound('sound/Dung_John_Theme.ogg')
    titleMusic.play()

    #load titlescreen
    titleScreen=pygame.image.load("graphics/titlescreen03.jpg").convert()
    g.screen.blit(titleScreen,(0,0))
    g.quit=0
    titleFont=pygame.font.SysFont('sansserif',64)
    titleMsg=titleFont.render('   Dung John, Sewer Maintenance. Use Cursor Keys to move.  To change Sprays: 1=Detergent, 2=Fungicide, 3=Poison, 4=Bleach. Press Spacebar to Fire, keep pressed to make spray longer.   Hint1: Some sprays are useless against certain creatures. Hint2: Rats really do not like poision.',1,(104,21,5))

    titleMsgY=516
    titleMsgPos=0
    titleMsgDisp=0

    #display van sprite
    vanSprite=Van()
    vanGroup=pygame.sprite.RenderClear(vanSprite)
    pressAnyKey=0
    pygame.event.clear()
    clock = pygame.time.Clock()
    while not pressAnyKey:
        vanGroup.clear(g.screen, titleScreen)
        vanGroup.update()
        vanGroup.draw(g.screen)

        #move text
        if titleMsgPos>=titleMsg.get_width():
            titleMsgPos=0
            titleMsgDisp=0
        if titleMsgDisp >= SW:
            titleMsgPos +=4
        else:
            titleMsgDisp +=4

        #clear background
        g.screen.blit(titleScreen,(0,titleMsgY),(0,titleMsgY,SW,66))
        #write text to screen
        g.screen.blit(titleMsg,(SW-titleMsgDisp,titleMsgY),(titleMsgPos,0,titleMsgDisp,titleMsg.get_height()))
        pygame.display.flip()
        clock.tick(50)

        for e in pygame.event.get():
            if e.type is QUIT:
                pressAnyKey=1
                gameLoopQuit=1
            if e.type is KEYDOWN and e.key == K_ESCAPE:
                pressAnyKey=1
                gameLoopQuit=1
            if e.type is KEYDOWN:
                pressAnyKey=1

    #wait until player has read message.
    #gameLoopQuit=pressKey()
    pygame.mixer.stop()

    while not gameLoopQuit and gameLevel<=maxGameLevels and not g.quit:
        next_level(g,gameLevel) #initialise level
        gameLoopQuit=runLevel(g)
        spraySnd.stop()
        if gameLoopQuit: break # immediately end game

        #did player die or did he get to the end of the level
        if not g.nextLevel:
            g.font = pygame.font.SysFont('helvetica',24)
            clearMsg= pygame.Surface((550,100)).convert()
            clearMsg.fill((0,0,0))
            g.screen.blit(clearMsg,(100,275))
            g.quit=1
            if g.player.hitPoints<1:
                #msg = g.font.render('THE MEANIES HAVE GOT YOU. SORRY. BETTER LUCK NEXT TIME',1,(255,32,32))
                #g.screen.blit(msg,(100,300))
                #loop the screen
                deadScreen=pygame.image.load("graphics/poppedhisclogs.jpg").convert()
                startLoop=0
                maxLoop=SW/2
                while startLoop<=maxLoop:
                    lh=pygame.Surface((startLoop,200)).convert()
                    rh=pygame.Surface((startLoop,200)).convert()
                    lh.blit(deadScreen,(0,0),(maxLoop-startLoop,0,startLoop,200))
                    rh.blit(deadScreen,(0,0),(maxLoop,0,startLoop,200))
                    g.screen.blit(lh,(0,200))
                    g.screen.blit(rh,(SW-startLoop,200))
                    pygame.display.flip()
                    startLoop += 10
            else:
                msg = g.font.render('YOU HAVE QUIT THE GAME. SEE YOU LATER',1,(255,32,32))
                g.screen.blit(msg,(100,300))
        elif gameLevel == maxGameLevels:
            #game is complete
            endScreen=pygame.image.load("graphics/endscreen.jpg").convert()
            g.screen.blit(endScreen,(0,0))
        else:
            #load next screen
            nextLevel=pygame.image.load("graphics/nextLevel.jpg").convert()
            g.screen.blit(nextLevel,(0,0))
            g.quit=0
            gameLevel+= 1

        #display message
        pygame.display.flip()

        #Wait until player has read message.
        gameLoopQuit=pressKey()

pygame.display.quit()

