from constants import *
from util import toRealTime
from gfxtheme import GFXTheme
from announcer import Announcer

from listener import Listener

from pygame.sprite import RenderUpdates, RenderClear

import fontfx, colors, steps, random, arrows
import lifebars, scores, combos, grades, judge, stats

# This class keeps an ordered list of sprites in addition to the dict,
# so we can draw in the order the sprites were added.
class OrderedRenderUpdates(RenderClear):
  def __init__(self, group = ()):
    self.spritelist = []
    RenderClear.__init__(self, group)

  def sprites(self):
    return list(self.spritelist)

  # A patch has been sent to Pete in the hopes that we can avoid overriding
  # this function, and only override add_internal (pygame 1.5.6)
  def add(self, sprite):
    has = self.spritedict.has_key
    if hasattr(sprite, '_spritegroup'):
      for sprite in sprite.sprites():
        if not has(sprite):
          self.add_internal(sprite)
          sprite.add_internal(self) 
    else:
      try: len(sprite)
      except (TypeError, AttributeError):
        if not has(sprite):
          self.add_internal(sprite)
          sprite.add_internal(self) 
      else:
        for sprite in sprite:
          if not has(sprite):
            self.add_internal(sprite)
            sprite.add_internal(self) 

  def add_internal(self, sprite):
    RenderClear.add_internal(self, sprite)
    self.spritelist.append(sprite)

  def remove_internal(self, sprite):
    RenderClear.remove_internal(self, sprite)
    self.spritelist.remove(sprite)

  def draw(self, surface):
    spritelist = self.spritelist
    spritedict = self.spritedict
    surface_blit = surface.blit
    dirty = self.lostsprites
    self.lostsprites = []
    dirty_append = dirty.append
    for s in spritelist:
      r = spritedict[s]
      newrect = surface_blit(s.image, s.rect)
      if r is 0:
        dirty_append(newrect)
      else:
        if newrect.colliderect(r):
          dirty_append(newrect.union(r))
        else:
          dirty_append(newrect)
      spritedict[s] = newrect
    return dirty

class HoldJudgeDisp(Listener, pygame.sprite.Sprite):
  def __init__(self, pid, player, game):
    pygame.sprite.Sprite.__init__(self)
    self.pid = pid
    self.game = game

    self.space = pygame.surface.Surface([48, 24])
    self.space.fill([0, 0, 0])

    self.image = pygame.surface.Surface([len(game.dirs) * game.width, 24])
    self.image.fill([0, 0, 0])
    self.image.set_colorkey([0, 0, 0], RLEACCEL)

    self.okimg = fontfx.shadefade("OK", 28, 3, [48, 24], [112, 224, 112])
    self.ngimg = fontfx.shadefade("NG", 28, 3, [48, 24], [224, 112, 112])

    self.rect = self.image.get_rect()
    if player.scrollstyle == 2: self.rect.top = 228
    elif player.scrollstyle == 1: self.rect.top = 400
    else: self.rect.top = 56

    self.rect.left = game.left_off(pid) + pid * game.player_offset
    self.len = len(game.dirs)

  def set_song(self, pid, bpm, difficulty, count, holds, feet):
    self.slotnow = [self.space] * self.len
    self.slotold = list(self.slotnow)
    self.slothit = [-1] * self.len

  def ok_hold(self, pid, curtime, direction, whichone):
    if pid != self.pid: return
    self.slothit[self.game.dirs.index(direction)] = curtime
    self.slotnow[self.game.dirs.index(direction)] = self.okimg

  def broke_hold(self, pid, curtime, direction, whichone):
    if pid != self.pid: return
    self.slothit[self.game.dirs.index(direction)] = curtime
    self.slotnow[self.game.dirs.index(direction)] = self.ngimg
    
  def update(self, curtime):
    for i in range(len(self.slotnow)):
      if (curtime - self.slothit[i] > 0.5):
        self.slotnow[i] = self.space
      if self.slotnow[i] != self.slotold[i]:
        x = (i * self.game.width)
        self.image.blit(self.slotnow[i], [x, 0])
        self.slotold[i] = self.slotnow[i]

class JudgingDisp(Listener, pygame.sprite.Sprite):
  def __init__(self, playernum, game):
    pygame.sprite.Sprite.__init__(self)

    self.sticky = mainconfig['stickyjudge']
    self.needsupdate = 1
    self.laststep = 0
    self.oldzoom = -1
    self.bottom = 320
    self.centerx = game.sprite_center + (playernum * game.player_offset)
        
    tx = FONTS[48].size("MARVELOUS")[0]+4
    self.marvelous = fontfx.shadefade("MARVELOUS", 48, 4,
                                      [tx, 40], [224, 224, 224])

    tx = FONTS[48].size("PERFECT")[0]+4
    self.perfect = fontfx.shadefade("PERFECT", 48, 4, [tx, 40], [224, 224, 32])

    tx = FONTS[48].size("GREAT")[0]+4
    self.great = fontfx.shadefade("GREAT", 48, 4, [tx, 40], [32, 224, 32])

    tx = FONTS[48].size("OKAY")[0]+4
    self.okay = fontfx.shadefade("OKAY", 48, 4, [tx, 40], [32, 32, 224])

    tx = FONTS[48].size("BOO")[0]+4
    self.boo = fontfx.shadefade("BOO", 48, 4, [tx, 40], [96, 64, 32])

    tx = FONTS[48].size("MISS")[0]+4
    self.miss = fontfx.shadefade("MISS", 48, 4, [tx, 40], [224, 32, 32])

    self.space = FONTS[48].render(" ", True, [0, 0, 0])

    self.marvelous.set_colorkey(self.marvelous.get_at([0, 0]), RLEACCEL)
    self.perfect.set_colorkey(self.perfect.get_at([0, 0]), RLEACCEL)
    self.great.set_colorkey(self.great.get_at([0, 0]), RLEACCEL)
    self.okay.set_colorkey(self.okay.get_at([0, 0]), RLEACCEL)
    self.boo.set_colorkey(self.boo.get_at([0, 0]), RLEACCEL)
    self.miss.set_colorkey(self.miss.get_at([0, 0]), RLEACCEL)
    
    self.image = self.space
    self.baseimage = self.space

  def stepped(self, pid, dir, curtime, rating, combo):
    if rating is None: return

    self.laststep = curtime
    self.rating = rating
    self.baseimage = { "V": self.marvelous, "P": self.perfect,
                       "G": self.great, "O": self.okay,
                       "B": self.boo, "M": self.miss }.get(rating, self.space)

  def update(self, curtime):
    self.laststep = min(curtime, self.laststep)
    steptimediff = curtime - self.laststep

    zoomzoom = 1 - min(steptimediff, 0.2) * 2

    if zoomzoom != self.oldzoom:
      self.oldzoom = zoomzoom
      self.needsupdate = True
      if (steptimediff > 0.36) and not self.sticky:
        self.image = self.space

    if self.needsupdate:
      self.image = pygame.transform.rotozoom(self.baseimage, 0, zoomzoom)
      self.rect = self.image.get_rect()
      self.rect.centerx = self.centerx
      self.rect.bottom = self.bottom
      self.image.set_colorkey(self.image.get_at([0, 0]), RLEACCEL)
      self.needsupdate = False

class Player(object):

  def __init__(self, pid, config, songconf, game):
    self.theme = GFXTheme(mainconfig.get("%s-theme" % game.theme, "default"),
                          pid, game)
    self.pid = pid
    self.failed = False

    self.__dict__.update(config)

    self.game = game

    if self.scrollstyle == 2: self.top = 240 - game.width / 2
    elif self.scrollstyle == 1: self.top = 352
    else: self.top = 64

    self.secret_kind = songconf["secret"]

    self.score = scores.scores[songconf["scoring"]](pid, "NONE", game)
    self.combos = combos.combos[songconf["combo"]](pid, game)
    self.grade = grades.grades[songconf["grade"]]()
    Lifebar = lifebars.bars[songconf["lifebar"]]
    self.lifebar = Lifebar(pid, self.theme, songconf, game)
    self.judging_disp = JudgingDisp(self.pid, game)
    self.stats = stats.Stats()
    self.announcer = Announcer(mainconfig["djtheme"])

    self.listeners = [self.combos, self.score, self.grade, self.lifebar,
                      self.judging_disp, self.stats, self.announcer]

    if not game.double:
      self.judge = judge.judges[songconf["judge"]](self.pid, songconf)
      self.listeners.append(self.judge)
      arr, arrfx = self.theme.toparrows(self.top, self.pid)
      self.toparr = arr
      self.toparrfx = arrfx
      self.listeners.extend(arr.values() + arrfx.values())
      self.holdtext = HoldJudgeDisp(self.pid, self, self.game)
      self.listeners.append(self.holdtext)
    else:
      Judge = judge.judges[songconf["judge"]]
      self.judge = [Judge(self.pid * 2, songconf),
                    Judge(self.pid * 2 + 1, songconf)]
      self.listeners.extend(self.judge)
      arr1, arrfx1 = self.theme.toparrows(self.top, self.pid * 2)
      arr2, arrfx2 = self.theme.toparrows(self.top, self.pid * 2 + 1)
      self.arrows = [self.theme.arrows(self.pid * 2),
                     self.theme.arrows(self.pid * 2 + 1)]
      self.toparr = [arr1, arr2]
      self.toparrfx = [arrfx1, arrfx2]
      self.listeners.extend(arr1.values() + arr2.values() +
                            arrfx1.values() + arrfx2.values())
      self.holdtext = [HoldJudgeDisp(self.pid * 2, self, self.game),
                       HoldJudgeDisp(self.pid * 2 + 1, self, self.game)]
      self.listeners.extend(self.holdtext)

  def set_song(self, song, diff, lyrics):
    self.difficulty = diff

    if self.game.double:
      self.holding = [[-1] * len(self.game.dirs), [-1] * len(self.game.dirs)]
      if self.transform == 1:
        # In double mirror mode, we have to swap the step sets for this
        # player's pids. This ensures, e.g., 1R becomes 2L, rather than 1L.
        self.steps = [steps.Steps(song, diff, self, self.pid * 2 + 1,
                                  lyrics, self.game.name),
                      steps.Steps(song, diff, self, self.pid * 2,
                                  lyrics, self.game.name)]
      else:
        self.steps = [steps.Steps(song, diff, self, self.pid * 2,
                                  lyrics, self.game.name),
                      steps.Steps(song, diff, self, self.pid * 2 + 1,
                                  lyrics, self.game.name)]
      self.length = max(self.steps[0].length, self.steps[1].length)
      self.ready = min(self.steps[0].ready, self.steps[1].ready)
      self.bpm = self.steps[0].bpm

      count = self.steps[0].totalarrows + self.steps[1].totalarrows

      total_holds = 0
      for i in range(2):  total_holds += len(self.steps[i].holdref)

      args = (self.pid, self.bpm, diff, count, total_holds,
              self.steps[0].feet)
      for l in self.listeners: l.set_song(*args)

    else:
      self.holding = [-1] * len(self.game.dirs)
      self.steps = steps.Steps(song, diff, self, self.pid, lyrics,
                               self.game.name)
      self.length = self.steps.length
      self.ready = self.steps.ready
      self.bpm = self.steps.bpm
      self.arrows = self.theme.arrows(self.pid)

      holds = len(self.steps.holdref)

      args = (self.pid, self.bpm, diff, self.steps.totalarrows,
              holds, self.steps.feet)
      for l in self.listeners: l.set_song(*args)

  def start_song(self):
    self.toparr_group = RenderUpdates()
    self.fx_group = RenderUpdates()
    self.text_group = RenderUpdates()
    self.text_group.add([self.score, self.lifebar, self.judging_disp])
    self.text_group.add(self.holdtext)

    if mainconfig["showcombo"]: self.text_group.add(self.combos)

    if self.game.double:
      self.arrow_group = [OrderedRenderUpdates(),
                          OrderedRenderUpdates()]

      for i in range(2):
        self.steps[i].play()
        for d in self.game.dirs:
          if mainconfig["explodestyle"] > -1:
            self.toparrfx[i][d].add(self.fx_group)
          if not self.dark: self.toparr[i][d].add(self.toparr_group)
      self.sprite_groups = [self.toparr_group, self.arrow_group[0],
                            self.arrow_group[1], self.fx_group,
                            self.text_group]
    else:
      self.steps.play()
      self.arrow_group = OrderedRenderUpdates()
      for d in self.game.dirs:
        if mainconfig["explodestyle"] > -1: self.toparrfx[d].add(self.fx_group)
        if not self.dark: self.toparr[d].add(self.toparr_group)
      self.sprite_groups = [self.toparr_group, self.arrow_group,
                            self.fx_group, self.text_group]

  def get_next_events(self, song):
    if self.game.double:
      self.fx_data = [[], []]
      for i in range(2):
        self._get_next_events(song, self.arrow_group[i], self.arrows[i],
                              self.steps[i], self.judge[i])
    else:
      self.fx_data = []
      self._get_next_events(song, self.arrow_group, self.arrows, self.steps,
                            self.judge)

  def _get_next_events(self, song, arrow_grp, arrow_gfx, steps, judge):
    evt = steps.get_events()
    if evt is not None:
      events, nevents, time, bpm = evt
      for ev in events:
        if ev.feet:
          for (dir, num) in zip(self.game.dirs, ev.feet):
            if num & 1: judge.handle_arrow(dir, ev.when, num & 4)

      newsprites = []
      for ev in nevents:
        if ev.feet:
          for (dir, num) in zip(self.game.dirs, ev.feet):
            # Don't make hidden arrow sprites if we have hidden arrows
            # off entirely, or have them set not to display.
            if not num & 4 or self.secret_kind == 2:
              dirstr = dir + repr(int(ev.color) % self.colortype)
              if num & 1 and not num & 2:
                ns = arrows.ArrowSprite(arrow_gfx[dirstr], time, num & 4,
                                        ev.when, self, song)
                newsprites.append(ns)
              elif num & 2:
                holdindex = steps.holdref.index((self.game.dirs.index(dir),
                                                 ev.when))
                ns = arrows.HoldArrowSprite(arrow_gfx[dirstr], time, num & 4,
                                            steps.holdinfo[holdindex],
                                            self, song)
                newsprites.append(ns)

      arrow_grp.add(newsprites)

  def check_sprites(self, curtime, arrows, steps, fx_data, judge):
    misses = judge.expire_arrows(curtime)
    for d in misses:
      for l in self.listeners:
        l.stepped(self.pid, d, curtime, "M", self.combos.combo)
    for rating, dir, time in fx_data:
      if (rating == "V" or rating == "P" or rating == "G"):
        for spr in arrows.sprites():
          if spr.endtime == time and spr.dir == dir:
            if spr.hold: spr.broken = False
            else: spr.kill()

    arrows.update(curtime, self.bpm, steps.lastbpmchangetime)
    self.toparr_group.update(curtime, steps.offset)

  def should_hold(self, steps, direction, curtime):
    l = steps.holdinfo
    for i in range(len(l)):
      if l[i][0] == self.game.dirs.index(direction):
        if ((curtime - 15.0/steps.playingbpm > l[i][1])
            and (curtime < l[i][2])):
          return i

  def check_holds(self, pid, curtime, arrows, steps, judge, toparrfx, holding):
    # FIXME THis needs to go away
    keymap_kludge = { "u": E_UP, "k": E_UPLEFT, "z": E_UPRIGHT,
                      "d": E_DOWN, "l": E_LEFT, "r": E_RIGHT,
                      "g": E_DOWNRIGHT, "w": E_DOWNLEFT, "c": E_CENTER }

    for dir in self.game.dirs:
      toparrfx[dir].holding(0)
      current_hold = self.should_hold(steps, dir, curtime)
      dir_idx = self.game.dirs.index(dir)
      if current_hold is not None:
        if event.states[(pid, keymap_kludge[dir])]:
          if judge.holdsub.get(holding[dir_idx]) != -1:
            toparrfx[dir].holding(1)
          holding[dir_idx] = current_hold
        else:
          if judge.holdsub.get(current_hold) != -1:
            args = (pid, curtime, dir, current_hold)
            for l in self.listeners: l.broke_hold(*args)
            botchdir, timef1, timef2 = steps.holdinfo[current_hold]
            for spr in arrows.sprites():
              if (spr.endtime == timef1 and spr.dir == dir):
                  spr.broken = True
                  break
      else:
        if holding[dir_idx] > -1:
          if judge.holdsub.get(holding[dir_idx]) != -1:
            args = (pid, curtime, dir, holding[dir_idx])
            for l in self.listeners: l.ok_hold(*args)
            holding[dir_idx] = -1

  def handle_key(self, ev, time):
    if ev[1] not in self.game.dirs: return

    # Note that we can't pack up the listener arguments ahead of time
    # here, because otherwise we use the old values for combos.combo.

    if self.game.double:
      pid = ev[0] & 1
      rating, dir, etime = self.judge[pid].handle_key(ev[1], time)
      for l in self.listeners:
        l.stepped(ev[0], dir, time, rating, self.combos.combo)
      self.fx_data[pid].append((rating, dir, etime))
    else:
      rating, dir, etime = self.judge.handle_key(ev[1], time)
      for l in self.listeners:
        l.stepped(ev[0], dir, time, rating, self.combos.combo)
      self.fx_data.append((rating, dir, etime))

  def check_bpm_change(self, pid, time, steps, judge):
    if len(steps.lastbpmchangetime) > 0:
      if time >= steps.lastbpmchangetime[0][0]:
        newbpm = steps.lastbpmchangetime[0][1]
        self.bpm = newbpm
        for l in self.listeners: l.change_bpm(pid, time, newbpm)
        steps.lastbpmchangetime.pop(0)

  def clear_sprites(self, screen, bg):
    for g in self.sprite_groups: g.clear(screen, bg)

  def game_loop(self, time, screen):
    if self.game.double:
      for i in range(2):
        self.check_holds(self.pid * 2 + i, time, self.arrow_group[i],
                         self.steps[i], self.judge[i], self.toparrfx[i],
                         self.holding[i])
        self.check_bpm_change(self.pid * 2 + i, time, self.steps[i],
                              self.judge[i])
        self.check_sprites(time, self.arrow_group[i], self.steps[i],
                           self.fx_data[i],
                           self.judge[i])

    else:
      self.check_holds(self.pid, time, self.arrow_group, self.steps,
                       self.judge, self.toparrfx, self.holding)
      self.check_bpm_change(self.pid, time, self.steps, self.judge)
      self.check_sprites(time, self.arrow_group, self.steps, self.fx_data,
                         self.judge)


    self.fx_group.update(time)
    self.text_group.update(time)
    if self.lifebar.gameover == lifebars.FAILED and not self.failed:
      self.failed = True

    rects = []
    for g in self.sprite_groups: rects.extend(g.draw(screen))
    return rects
