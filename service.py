# -*- coding: utf-8 -*-

from requests import post as requests_post
from xbmc import Monitor as xbmc_Monitor, Player as xbmc_Player, getInfoLabel, log as xbmc_log, LOGERROR


class service_monitor(xbmc_Monitor):


    def __init__(self, player):
        from xbmcaddon import Addon

        self.player = player
        self.last_tracked_position = None
        self.last_played_file = None
        self.content_id = None
        self.duration = None
        self.start_tracking = False
        self.addon_id = Addon().getAddonInfo('id')
        self.addon_path = 'plugin://' + self.addon_id
        xbmc_Monitor.__init__(self)


    def onNotification(self, sender, method, data):
        if method == 'Player.OnPlay':
            from xbmcgui import Window, getCurrentWindowId
            window_id = getCurrentWindowId()

            if getInfoLabel('Container.FolderPath').startswith(self.addon_path):
                self.start_tracking = True
                content_id = Window(window_id).getProperty('nowtv_content_id')
                if content_id is not None and len(content_id) != 0:
                    self.content_id = content_id
                    xbmc_log(f"[{self.addon_id}] track content: {self.content_id}")
            else:
                self.reset_tracking()
            Window(window_id).clearProperty('nowtv_content_id')

        elif method == 'Player.OnStop':
            if self.start_tracking is True and self.content_id is not None and self.last_tracked_position is not None and self.duration is not None:
                xbmc_log(f"[{self.addon_id}] track position: cid = {self.content_id} - pos = {self.last_tracked_position}")
                track_url = f"http://localhost:4800/api/{self.content_id}/playback/{self.last_tracked_position}"
                requests_post(track_url)

            self.reset_tracking()


    def track_position(self):

        if self.player.isPlayingVideo():
            try:
                self.last_played_file = str(self.player.getPlayingFile())
                cur_pos = int(self.player.getTime())
                if self.start_tracking is True and self.content_id is not None and self.last_played_file.find(
                        self.content_id) != -1:
                    self.last_tracked_position = cur_pos
                    self.duration = int(self.player.getTotalTime())
            except Exception as e:
                xbmc_log(f"[{self.addon_id}] exception when trying to set last_tracked_position: {e}", LOGERROR)
                pass


    def reset_tracking(self):
        self.start_tracking = False
        self.last_played_file = None
        self.content_id = None
        self.last_tracked_position = None
        self.duration = None


if __name__ == '__main__':
    servicemonitor = service_monitor(xbmc_Player())

    while not servicemonitor.abortRequested():
        servicemonitor.track_position()
        if servicemonitor.waitForAbort(2):
            break

    service_monitor = None