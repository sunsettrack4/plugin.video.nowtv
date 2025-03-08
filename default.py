from datetime import datetime
import json
import requests
import urllib
import sys
import xbmc, xbmcaddon, xbmcgui, xbmcplugin, xbmcvfs


# Headers
headers = {
    "x-skyott-device": "TV",
    "x-skyott-platform": "ANDROIDTV",
    "x-skyott-proposition": "NOWTV",
    "x-skyott-provider": "NOWTV",
    "x-skyott-territory": "DE",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    'sec-ch-ua-platform': '"Windows"',
    "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
    "sec-ch-ua-Mobile": "?0"
}

# URL
graph_url = "https://graphql.ott.sky.com"
local_url = "http://localhost:4800"

# MD5
md5 = {
    "main": ("main", "cde8ff8cf3d3cad22071d05d305a88b1de761705a11a65b8ce26d39b652c7511"),
    "highlights": ("highlights", "fe425f9d865d8448261ebe06c9e966ae02087ecae53918ea3c23c70d5e3083ef"),
    "sub": ("sub", "20e9fa43bd56fe3f8e9caed6fec7dbf25decf0d1903e7280b239d3d6e11a3697"),
    "item": ("item", "b0f8096034e428db847e0c906f0207f7ee15ff05c853a51ef1fb410597d47b6a")
}

# Country Areas
ca = {
    "DE": ["HOME", "CINEMA", "ENTERTAINMENT", "SPORT", "KIDS"],
    "GB": ["HOME", "CINEMA", "ENTERTAINMENT", "SPORT", "KIDS"],
    "IT": ["HOME", "CINEMA", "ENTERTAINMENT", "SPORT", "KIDS"]
}


#
# KODI definitions and router
#

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
data_dir = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))
addonpath = xbmcvfs.translatePath(__addon__.getAddonInfo('path'))

base_url = sys.argv[0]
__addon_handle__ = int(sys.argv[1])
args = urllib.parse.parse_qs(sys.argv[2][1:])
lang = "de" if xbmc.getLanguage(xbmc.ISO_639_1) == "de" else "en"

xbmcplugin.setContent(__addon_handle__, 'videos')


def build_url(query):
    return f"{base_url}?{urllib.parse.urlencode(query)}"


def playback(stream_type, stream_id):
    """Get player infolabels"""

    title = xbmc.getInfoLabel("ListItem.Title")
    thumb = xbmc.getInfoLabel("ListItem.Thumb")
    plot = xbmc.getInfoLabel("ListItem.Plot")
    genre = xbmc.getInfoLabel("ListItem.Genre")
    year = xbmc.getInfoLabel("ListItem.Year")
    director = xbmc.getInfoLabel("ListItem.Director")
    duration = xbmc.getInfoLabel("ListItem.Duration")

    """Pass the urls and infolabels to the player"""

    stream_url = f"{local_url}/api/{stream_type}/{stream_id}/manifest.mpd"

    li = xbmcgui.ListItem(path=stream_url)

    if xbmc.getCondVisibility('system.platform.android'):

        li.setProperty('inputstream.adaptive.license_key', f"{local_url}/api/{stream_type}/{stream_id}/license" + "||R{SSM}|")
        li.setProperty('inputstream.adaptive.license_type', "com.widevine.alpha")

    else:

        try:
            requests.get(stream_url)
            key = requests.get(f"{local_url}/api/{stream_type}/{stream_id}/license").content.decode()
            
            if not key or key == "" or key == "None":
                raise Exception()
        except:
            return
        
        li.setProperty('inputstream.adaptive.drm_legacy', f'org.w3.clearkey|{key}')


    li.setProperty('inputstream', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.manifest_type', 'mpd')

    li.setInfo("video", {"title": title, 'genre': genre, 'year': year, 'director': director, 'duration': duration, 'plot': plot})
    li.setArt({'thumb': thumb})

    xbmcplugin.setResolvedUrl(__addon_handle__, True, li)


def router(item):
    
    try:
        cc = requests.get(f"{local_url}/api/file/status.json").json()["territory"]
    except:
        xbmcgui.Dialog().notification(__addonname__, "Unable to detect service instance, please enable the NOW TV Streamer.", xbmcgui.NOTIFICATION_ERROR)
        return

    params = dict(urllib.parse.parse_qsl(item[1:]))
    main_listing = []

    if params:
        if params.get("type", "") in ("live", "vod"):
            playback(params["type"], params["location"])
            return
        elif params.get("type", "") == "personalized":
            m = get_now_structure(params["location"], get_local_query(params["location"]), cc)
        else:
            m = get_now_structure(params["type"], get_now_query(md5[params["type"]], cc, params["location"]), cc)
    else:
        m = get_now_structure("main", get_now_query(md5["main"], cc), cc)
        
    for i in m:
        url = build_url({'location': i["location"], "type": i["type"]})
        li = xbmcgui.ListItem(i["title"])
        li.setArt({"thumb": i.get("t_img"), "fanart": i.get("f_img")})
        li.setInfo('video', 
                   {    
                       'director': i.get("director", []),
                       'cast': i.get("actor", []),
                       'duration': i.get("duration"),
                       'title': i["title"], 
                       'plot': i["desc"] if i.get("desc") else i["title"],
                       'genre': i.get("genre"),
                       'year': i.get("year")
                    })
        
        if i["type"] in ("live", "vod"):
            li.setProperty("IsPlayable", "true")
            main_listing.append((url, li, False))
        else:
            main_listing.append((url, li, True))

    xbmcplugin.addDirectoryItems(__addon_handle__, main_listing, len(main_listing))
    xbmcplugin.endOfDirectory(__addon_handle__)


#
# Now API functions
#

def get_local_query(menu_type):
    result = requests.get(f"http://localhost:4800/api/file/{menu_type}.json")
    return result.json()
        
def get_now_query(hash_level, country_code, id=None):

    r = requests.Session()
    r.headers = headers

    # Country Area
    cc = ca[country_code]
    r.headers.update({"x-skyott-territory": country_code})
    
    if hash_level[0] == "main":
        variables  = urllib.parse.quote(json.dumps({
            "navIdentifier": "|".join(cc)}).replace(" ", ""))      
        
    elif hash_level[0] == "highlights" and id:
        variables  = urllib.parse.quote(json.dumps({
            "id": id, 
            "idType": "SLUG", 
            "railItemLimit": 12, 
            "segment": "0000005", 
            "fullWidthHeroImages": False}).replace(" ", ""))
        
    elif hash_level[0] == "sub" and id:
        variables  = urllib.parse.quote(json.dumps({
            "id": id, 
            "idType": "SLUG"}).replace(" ", ""))
        
    elif hash_level[0] == "item" and id:
        variables  = urllib.parse.quote(json.dumps({
            "id": id, 
            "idType": "UUID",
            "includeProgrammeTrailer": False,
            "includeSeriesTrailer": False}).replace(" ", ""))


    extensions = urllib.parse.quote(json.dumps({
        "persistedQuery": {
            "version": 1, 
            "sha256Hash": hash_level[1]}}).replace(" ", ""))

    return json.loads(r.get(
            f'{graph_url}/graphql?extensions={extensions}&variables={variables}').content)


def get_now_structure(menu_level, result, country_code):

    def img_provider(item, c_type):
        d = {}
        if type(item) != list:
            return
        for i in item:
            d[i["type"]] = i["url"]
        if c_type == "portrait" and not d.get("portrait"):
            return d.get("landscape", d.get("highlights"))
        return d.get(c_type, d.get("highlights"))
    
    d = []

    # MAIN MENU SECTION
    if menu_level == "main":
        
        items = result["data"]["menu"]["items"]
        
        for i in items:
            if i["title"] == "TOP_LEVEL_MAIN":
                for j in i["items"]:
                    if j["sectionNavigation"] in ca[country_code]:
                        if j.get("items") and not j.get("location"):
                            d.append({
                                "title": j["title"], 
                                "t_img": f"{addonpath}/icon.png",
                                "f_img": f"{addonpath}/resources/fanart.png",
                                "location": j["items"][0]["location"],
                                "type": "highlights"})
                        else:
                            d.append({
                                "title": j["title"],
                                "t_img": f"{addonpath}/icon.png",
                                "f_img": f"{addonpath}/fanart.png",
                                "location": j["location"],
                                "type": "highlights"})
                            
        for i in [("watchlist", {"DE": "Merkliste", "GB": "Watchlist"}), ("continue", {"DE": "Weiterschauen", "GB": "Continue Watching"})]:
            d.append({
                "title": i[1].get(country_code, i[1]["GB"]),
                "t_img": f"{addonpath}/icon.png",
                "f_img": f"{addonpath}/resources/fanart.png",
                "location": i[0],
                "type": "personalized"
            })
                            
    # HIGHLIGHTS MENU SECTION
    if menu_level == "highlights":

        items = result["data"]["group"]["rails"]

        for i in items:
            if i["type"] == "CATALOGUE/COLLECTION":
                if i["items"][0]["__typename"] == "GroupLink":
                    d.append({
                        "title": i["title"],
                        "desc": i.get("description", i["title"]),
                        "t_img": i["items"][0].get("imageUrl"),
                        "f_img": i["items"][0].get("imageUrl"),
                        "location": i["items"][0]["linkInfo"]["slug"],
                        "type": "highlights"
                    })
                    continue
                d.append({
                    "title": i["title"],
                    "desc": i.get("description", i["title"]),
                    "t_img": img_provider(i["items"][0].get("images"), "portrait") if len(i.get("items", [])) > 0 else None,
                    "f_img": img_provider(i["items"][0].get("images"), "landscape") if len(i.get("items", [])) > 0 else None,
                    "location": i["slug"],
                    "type": "sub"
                })
            if i["type"] == "CATALOGUE/GROUP":
                for j in i["items"]:
                    if j["type"] == "CATALOGUE/COLLECTION":
                        d.append({
                            "title": f'[COLOR yellow][B]{i["title"]}[/B][/COLOR] / {j["title"]}',
                            "desc": j.get("description", j["title"]),
                            "t_img": j.get("imageUrl"),
                            "f_img": j.get("imageUrl"),
                            "location": j["slug"],
                            "type": "sub"
                        })

    # SUB MENU SECTION
    if menu_level in ["sub", "watchlist", "continue"]:

        data_type = "catalogue" if menu_level == "sub" else "continueWatching" if menu_level == "continue" else menu_level

        items = result["data"][data_type]["items"]

        for i in items:
            if i["type"] == "ASSET/LINEAR":
                d.append({
                    "title": f'[COLOR yellowgreen][B]{i["channel"]["name"].replace(" SD", "")}:[/B][/COLOR] {"[B]" + datetime.fromtimestamp(int(i["startTimeEpoch"])).strftime("%H:%M") + " | [/B]" if i.get("startTimeEpoch") else ""}{i["title"]}',
                    "location": i["serviceKey"],
                    "t_img": img_provider(i.get("images"), "highlights"),
                    "f_img": img_provider(i.get("images"), "landscape"),
                    "desc": i.get("synopsisLong"),
                    "type": "live"
                })
            elif i["type"] == "ASSET/PROGRAMME":
                d.append({
                    "title": i["title"],
                    "director": i.get("directors", []),
                    "actor": i.get("cast", []),
                    "desc": i.get("synopsisLong"),
                    "location": i["providerVariantId"],
                    "duration": i["durationSeconds"],
                    "t_img": img_provider(i.get("images"), "portrait"),
                    "f_img": img_provider(i.get("images"), "landscape"),
                    'year': i.get("year"), 
                    "genre": i["genres"][0]["title"] if len(i.get("genres", [])) > 0 else None,
                    "type": "vod"
                })
            else:
                d.append({
                    "title": i["title"],
                    "director": i.get("directors", []),
                    "actor": i.get("cast", []),
                    "desc": i.get("synopsisLong"),
                    "location": i["id"],
                    "t_img": img_provider(i.get("images"), "portrait"),
                    "f_img": img_provider(i.get("images"), "landscape"),
                    'year': i.get("year"), 
                    "genre": i["genres"][0]["title"] if len(i.get("genres", [])) > 0 else None,
                    "type": "item"
                })
    
    # SERIES/EPISODE MENU SECTION
    if menu_level == "item":

        seasons = result["data"]["showpage"]["hero"]["seasons"]

        for s in seasons:
            for i in s["episodes"]:
                d.append({
                    "title": f'[COLOR yellowgreen][B]S{i["seasonNumber"]} E{i["episodeNumber"]}:[/B][/COLOR] {i["title"]}',
                    "actor": result["data"]["showpage"]["hero"].get("cast", []),
                    "desc": i.get("synopsisLong"),
                    "location": i["providerVariantId"],
                    "duration": i["durationMilliseconds"] / 1000 if i.get("durationMilliseconds") else None,
                    "t_img": i.get("episodeImage"),
                    "f_img": i.get("episodeImage"),
                    "genre": result["data"]["showpage"]["hero"]["genres"][0]["title"] if len(result["data"]["showpage"]["hero"].get("genres", [])) > 0 else None,
                    "type": "vod"
                })

    return d


if __name__ == "__main__":
    router(sys.argv[2])