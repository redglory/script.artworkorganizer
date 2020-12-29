import os, shutil, re, unicodedata
import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import json
import lib.library as video_library
from collections import namedtuple

try:  # Kodi v19 or newer
    from xbmcvfs import translatePath
except ImportError:  # Kodi v18 and older
    from xbmc import translatePath

ADDON = xbmcaddon.Addon()
ADDONID = ADDON.getAddonInfo('id')
ADDONNAME = ADDON.getAddonInfo('name')
ADDONVERSION = ADDON.getAddonInfo('version')
LANGUAGE = ADDON.getLocalizedString

def log(txt, level=xbmc.LOGDEBUG):
    message = '%s: %s' % (ADDONID, txt)
    xbmc.log(msg=message, level=level)

def clean_filename(filename):
    illegal_char = '^<>:"/\|?*'
    for char in illegal_char:
        filename = filename.replace( char , '' )
    return filename

class Main:
    def __init__ ( self ):
        self._load_settings()
        self._init_variables()
        # make sure that "sources.xml" is already set
        if xbmcvfs.exists("special://masterprofile/sources.xml"):
            # only delete if it is safe!
            if not self._directory_in_sources():
                self._delete_directories()
                # get media sources if setting is defined
                if  self.split_media_sources == "true" and (self.split_movies_sources == "true" or self.split_tvshows_sources == "true"):
                    self._get_media_sources_and_content()
                self._create_directories()
                if self.directoriescreated == 'true':
                    self._copy_artwork()
            else:
                log("WARNING! The specified destination directory is defined as a media source. Please choose a different path!", level=xbmc.LOGINFO)
        else:
            log("You MUST set your media sources BEFORE running this addon.", level=xbmc.LOGINFO)

    def _load_settings( self ):
        self.moviefanart = ADDON.getSetting( "moviefanart" )
        self.tvshowfanart = ADDON.getSetting( "tvshowfanart" )
        self.musicvideofanart = ADDON.getSetting( "musicvideofanart" )
        self.artistfanart = ADDON.getSetting( "artistfanart" )
        self.moviethumbs = ADDON.getSetting( "moviethumbs" )
        self.tvshowbanners = ADDON.getSetting( "tvshowbanners" )
        self.tvshowposters = ADDON.getSetting( "tvshowposters" )
        self.seasonthumbs = ADDON.getSetting( "seasonthumbs" )
        self.episodethumbs = ADDON.getSetting( "episodethumbs" )
        self.musicvideothumbs = ADDON.getSetting( "musicvideothumbs" )
        self.artistthumbs = ADDON.getSetting( "artistthumbs" )
        self.albumthumbs = ADDON.getSetting( "albumthumbs" )
        self.source = ADDON.getSetting( "source" )
        if self.source == 'true':
            self.path = ADDON.getSetting( "path" )
        else:
            self.path = ''
        self.directory = ADDON.getSetting( "directory" )
        # Option to separate artwork by media sources types (movies, tvshows) by path
        self.split_media_sources = ADDON.getSetting( "split_media_sources" )
        if self.split_media_sources == "true":
            self.split_movies_sources = ADDON.getSetting( "split_movies_sources" )
            self.split_tvshows_sources = ADDON.getSetting( "split_tvshows_sources" )
        else:
            self.split_movies_sources = "false"
            self.split_tvshows_sources = "false"
        # Option to normalize names. Useful when using nfs file systems (accented names not supported!)
        self.normalize_names = ADDON.getSetting( "normalize_names" )

    def _init_variables( self ):
        self.moviefanartdir = 'MovieFanart'
        self.tvshowfanartdir = 'TVShowFanart'
        self.musicvideofanartdir = 'MusicVideoFanart'
        self.artistfanartdir = 'ArtistFanart'
        self.moviethumbsdir = 'MovieThumbs'
        self.tvshowbannersdir = 'TVShowBanners'
        self.tvshowpostersdir = 'TVShowPosters'
        self.seasonthumbsdir = 'SeasonThumbs'
        self.episodethumbsdir = 'EpisodeThumbs'
        self.musicvideothumbsdir = 'MusicVideoThumbs'
        self.artistthumbsdir = 'ArtistThumbs'
        self.albumthumbsdir = 'AlbumThumbs'
        self.directoriescreated = 'true'
        self.dialog = xbmcgui.DialogProgress()
        if self.directory == '':
            self.directory = translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        if self.path != '':
            path = os.path.split( os.path.dirname( self.path ) )[1]
            self.directory = os.path.join( self.directory, path )
        self.artworklist = []
        if self.moviefanart == 'true':
            self.moviefanartpath = os.path.join( self.directory, self.moviefanartdir )
            self.artworklist.append( self.moviefanartpath )
        if self.tvshowfanart == 'true':
            self.tvshowfanartpath = os.path.join( self.directory, self.tvshowfanartdir )
            self.artworklist.append( self.tvshowfanartpath )
        if self.musicvideofanart == 'true':
            self.musicvideofanartpath = os.path.join( self.directory, self.musicvideofanartdir )
            self.artworklist.append( self.musicvideofanartpath )
        if self.artistfanart == 'true':
            self.artistfanartpath = os.path.join( self.directory, self.artistfanartdir )
            self.artworklist.append( self.artistfanartpath )
        if self.moviethumbs == 'true':
            self.moviethumbspath = os.path.join( self.directory, self.moviethumbsdir )
            self.artworklist.append( self.moviethumbspath )
        if self.tvshowbanners == 'true':
            self.tvshowbannerspath = os.path.join( self.directory, self.tvshowbannersdir )
            self.artworklist.append( self.tvshowbannerspath )
        if self.tvshowposters == 'true':
            self.tvshowposterspath = os.path.join( self.directory, self.tvshowpostersdir )
            self.artworklist.append( self.tvshowposterspath )
        if self.seasonthumbs == 'true':
            self.seasonthumbspath = os.path.join( self.directory, self.seasonthumbsdir )
            self.artworklist.append( self.seasonthumbspath )
        if self.episodethumbs == 'true':
            self.episodethumbspath = os.path.join( self.directory, self.episodethumbsdir )
            self.artworklist.append( self.episodethumbspath )
        if self.musicvideothumbs == 'true':
            self.musicvideothumbspath = os.path.join( self.directory, self.musicvideothumbsdir )
            self.artworklist.append( self.musicvideothumbspath )
        if self.artistthumbs == 'true':
            self.artistthumbspath = os.path.join( self.directory, self.artistthumbsdir )
            self.artworklist.append( self.artistthumbspath )
        if self.albumthumbs == 'true':
            self.albumthumbspath = os.path.join( self.directory, self.albumthumbsdir )
            self.artworklist.append( self.albumthumbspath )

    def _directory_in_sources( self ):
        all_sources = video_library.get_all_sources()
        for source in [s.path for s in all_sources]:
            if video_library._normalize_path(self.directory) in source:
                return True
        return False

    def _delete_directories( self ):
        if xbmcvfs.exists( self.directory ):
            dirs, files = xbmcvfs.listdir( self.directory )
            for item in dirs:
                try:
                    shutil.rmtree( os.path.join(self.directory, item) )
                except:
                    pass

    def _get_media_sources_and_content ( self ):
        # retrieve both movies and tvshows sources
        if self.split_movies_sources == "true" and self.split_tvshows_sources == "true":
            self.movies_sources, self.tvshows_sources, self.movies_content, self.tvshows_content = video_library._identify_source_content()
        # retrieve movies sources
        elif self.split_movies_sources == "true":
            self.movies_sources = video_library.get_movie_sources()
            self.movies_content = video_library.get_movie_content()
        # retrieve tvshows sources
        elif self.split_tvshows_sources == "true":
            self.tvshows_sources = video_library.get_tv_sources()
            self.tvshows_content = video_library.get_tv_content()

    def _create_directories( self ):
        if not xbmcvfs.exists( self.directory ):
            try:
                xbmcvfs.mkdir( self.directory )
            except:
                self.directoriescreated = 'false'
                log( 'failed to create artwork directory' )
        if self.directoriescreated == 'true':
            for path in self.artworklist:
                try:
                    xbmcvfs.mkdir( path )
                except:
                    self.directoriescreated = 'false'
                    log( 'failed to create directories' )
        # Create media type based directories if defined by user (movies, tvshows)
        # media source format: [(name, path, content)]
        if self.directoriescreated == 'true':
            if self.split_movies_sources == "true" and (self.moviefanart == "true" or self.moviethumbs == 'true'):
                for ms_name in [m_s.name for m_s in self.movies_sources]:
                    try:
                        if self.normalize_names == "true":
                            ms_name = video_library._normalize_string(ms_name)
                        if self.moviefanart == "true":
                            xbmcvfs.mkdir( os.path.join( self.moviefanartpath, ms_name ) )
                        if self.moviethumbs == "true":
                            xbmcvfs.mkdir( os.path.join( self.moviethumbspath, ms_name ) )
                    except:
                        self.directoriescreated = 'false'
                        log( 'failed to create directories for movies content type' )
            if self.split_tvshows_sources == "true" and (self.tvshowfanart == 'true' or self.tvshowbanners == 'true' or self.tvshowposters == 'true' or self.seasonthumbs == 'true' or self.episodethumbs == 'true'):
                for tvs_name in [tv_s.name for tv_s in self.tvshows_sources]:
                    try:
                        if self.normalize_names == "true":
                            tvs_name = video_library._normalize_string(tvs_name)
                        if self.tvshowfanart == 'true':
                            xbmcvfs.mkdir( os.path.join( self.tvshowfanartpath, tvs_name ) )
                        if self.tvshowbanners == 'true':
                            xbmcvfs.mkdir( os.path.join( self.tvshowbannerspath, tvs_name ) )
                        if self.tvshowposters == 'true':
                            xbmcvfs.mkdir( os.path.join( self.tvshowposterspath, tvs_name ) )
                        if self.seasonthumbs == 'true':
                            xbmcvfs.mkdir( os.path.join( self.seasonthumbspath, tvs_name ) )
                        if self.episodethumbs == 'true':
                            xbmcvfs.mkdir( os.path.join( self.episodethumbspath, tvs_name ) )
                    except:
                        self.directoriescreated = 'false'
                        log( 'failed to create directories for tvshows content type' )

    def _copy_artwork( self ):
        self.dialog.create( ADDONNAME )
        self.dialog.update(0)
        if not self.dialog.iscanceled():
            if self.moviefanart == 'true':
                self._copy_moviefanart()
        if not self.dialog.iscanceled():
            if self.tvshowfanart == 'true':
                self._copy_tvshowfanart()
        if not self.dialog.iscanceled():
            if self.musicvideofanart == 'true':
                self._copy_musicvideofanart()
        if not self.dialog.iscanceled():
            if (self.artistfanart == 'true') and (self.path == ''):
                self._copy_artistfanart()
        if not self.dialog.iscanceled():
            if self.moviethumbs == 'true':
                self._copy_moviethumbs()
        if not self.dialog.iscanceled():
            if self.tvshowbanners == 'true':
                self._copy_tvshowbanners()
        if not self.dialog.iscanceled():
            if self.tvshowposters == 'true':
                self._copy_tvshowposters()
        if not self.dialog.iscanceled():
            if self.seasonthumbs == 'true':
                self._copy_seasonthumbs()
        if not self.dialog.iscanceled():
            if self.episodethumbs == 'true':
                self._copy_episodethumbs()
        if not self.dialog.iscanceled():
            if self.musicvideothumbs == 'true':
                self._copy_musicvideothumbs()
        if not self.dialog.iscanceled():
            if (self.artistthumbs == 'true') and (self.path == ''):
                self._copy_artistthumbs()
        if not self.dialog.iscanceled():
            if (self.albumthumbs == 'true') and (self.path == ''):
                self._copy_albumthumbs()
        self.dialog.close()

    def _copy_moviefanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "title", "fanart", "year"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('movies')):
            totalitems = len( json_response['result']['movies'] )
            for item in json_response['result']['movies']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32001) + ': ' + str( count + 1 ) )
                name = item['title']
                year = str(item['year'])
                artwork = item['fanart']
                tmp_filename = name + ' (' + year + ')' + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test file path with movie_content to find source name
                moviefanartpath = self.moviefanartpath
                if self.split_movies_sources == "true" and video_library._normalize_path(item['file']) in self.movies_content:
                    media_source = self.movies_content[video_library._normalize_path(item['file'])]
                    if self.normalize_names == "true":
                        media_source = video_library._normalize_string(media_source)
                    moviefanartpath = os.path.join( self.moviefanartpath, media_source )
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( moviefanartpath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy moviefanart' )
        log( 'moviefanart copied: %s' % count )

    def _copy_tvshowfanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "title", "fanart"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('tvshows')):
            totalitems = len( json_response['result']['tvshows'] )
            for item in json_response['result']['tvshows']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32002) + ': ' + str( count + 1 ) )
                name = item['title']
                artwork = item['fanart']
                tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test file path with tv_content to find source name
                tvshowfanartpath = self.tvshowfanartpath
                if self.split_tvshows_sources == "true":
                    for tv_file_path, source_name in self.tvshows_content.items():
                        if tv_file_path.startswith(video_library._normalize_path(item['file'])):
                            if self.normalize_names == "true":
                                source_name = video_library._normalize_string(source_name)
                            tvshowfanartpath = os.path.join( self.tvshowfanartpath, source_name )
                            break
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( tvshowfanartpath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy tvshowfanart' )
        log( 'tvshowfanart copied: %s' % count )

    def _copy_musicvideofanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["title", "fanart", "artist"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('musicvideos')):
            totalitems = len( json_response['result']['musicvideos'] )
            for item in json_response['result']['musicvideos']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32003) + ': ' + str( count + 1 ) )
                name = item['title']
                artwork = item['fanart']
                if item['artist']: # bug workaround, musicvideos can end up in the database without an artistname
                    artist = item['artist'][0]
                    tmp_filename = artist + ' - ' + name + '.jpg'
                else:
                    tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( self.musicvideofanartpath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy musicvideofanart' )
        log( 'musicvideofanart copied: %s' % count )

    def _copy_artistfanart( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["fanart"]}, "id": 1}')
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('artists')):
            totalitems = len( json_response['result']['artists'] )
            for item in json_response['result']['artists']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32004) + ': ' + str( count + 1 ) )
                name = item['label']
                artwork = item['fanart']
                tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( self.artistfanartpath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy artistfanart' )
        log( 'artistfanart copied: %s' % count )

    def _copy_moviethumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "title", "thumbnail", "year"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('movies')):
            totalitems = len( json_response['result']['movies'] )
            for item in json_response['result']['movies']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32005) + ': ' + str( count + 1 ) )
                name = item['title']
                year = str(item['year'])
                artwork = item['thumbnail']
                tmp_filename = name + ' (' + year + ')' + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test file path with movie_content to find source name
                moviethumbspath = self.moviethumbspath
                if self.split_movies_sources == "true" and video_library._normalize_path(item['file']) in self.movies_content:
                    media_source = self.movies_content[video_library._normalize_path(item['file'])]
                    if self.normalize_names == "true":
                        media_source = video_library._normalize_string(media_source)
                    moviethumbspath = os.path.join( self.moviethumbspath, media_source )
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( moviethumbspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy moviethumb' )
        log( 'moviethumbs copied: %s' % count )

    def _copy_tvshowbanners( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "title", "art"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('tvshows')):
            totalitems = len( json_response['result']['tvshows'] )
            for item in json_response['result']['tvshows']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32013) + ': ' + str( count + 1 ) )
                name = item['title']
                artwork = item['art'].get('banner')
                tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test tvshow path in tv_content to find source name
                tvshowbannerspath = self.tvshowbannerspath
                if self.split_tvshows_sources == "true":
                    for tv_file_path, source_name in self.tvshows_content.items():
                        if tv_file_path.startswith(video_library._normalize_path(item['file'])):
                            if self.normalize_names == "true":
                                source_name = video_library._normalize_string(source_name)
                            tvshowbannerspath = os.path.join( self.tvshowbannerspath, source_name )
                            break
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( tvshowbannerspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy tvshowbanner' )
        log( 'tvshowbanners copied: %s' % count )

    def _copy_tvshowposters( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "title", "art"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('tvshows')):
            totalitems = len( json_response['result']['tvshows'] )
            for item in json_response['result']['tvshows']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32014) + ': ' + str( count + 1 ) )
                name = item['title']
                artwork = item['art'].get('poster')
                tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test file path with tv_content to find source name
                tvshowposterspath = self.tvshowposterspath
                if self.split_tvshows_sources == "true":
                    for tv_file_path, source_name in self.tvshows_content.items():
                        if tv_file_path.startswith(video_library._normalize_path(item['file'])):
                            if self.normalize_names == "true":
                                source_name = video_library._normalize_string(source_name)
                            tvshowposterspath = os.path.join( self.tvshowposterspath, source_name )
                            break
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( tvshowposterspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy tvshowposter' )
        log( 'tvshowposters copied: %s' % count )

    def _copy_seasonthumbs( self ):
        _TVShow_ = namedtuple('TVShow', ['id', 'path'])
        count = 0
        tvshows = []
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('tvshows')):
            for item in json_response['result']['tvshows']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                tvshow = _TVShow_(int(item['tvshowid']), item['file'])
                tvshows.append(tvshow)
            for tvshow in tvshows:
                processeditems = 0
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetSeasons", "params": {"properties": ["thumbnail", "showtitle"], "tvshowid":%s}, "id": 1}' % tvshow.id )
                json_response = json.loads(json_query)
                if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('seasons')):
                    totalitems = len( json_response['result']['seasons'] )
                    for item in json_response['result']['seasons']:
                        if self.dialog.iscanceled():
                            log('script cancelled')
                            return
                        processeditems = processeditems + 1
                        self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32007) + ': ' + str( count + 1 ) )
                        name = item['label']
                        tvshow_title = item['showtitle']
                        artwork = item['thumbnail']
                        tmp_filename = tvshow_title + ' - ' + name + '.jpg'
                        filename = clean_filename( tmp_filename )
                        if self.normalize_names == "true":
                            filename = video_library._normalize_string(filename)
                        # test file path with tv_content to find source name
                        seasonthumbspath = self.seasonthumbspath
                        if self.split_tvshows_sources == "true":
                            for tv_file_path, source_name in self.tvshows_content.items():
                                if tv_file_path.startswith(video_library._normalize_path(tvshow.path)):
                                    if self.normalize_names == "true":
                                        source_name = video_library._normalize_string(source_name)
                                    seasonthumbspath = os.path.join( self.seasonthumbspath, source_name )
                                    break
                        if artwork != '':
                            try:
                                xbmcvfs.copy( translatePath( artwork ), os.path.join( seasonthumbspath, filename ) )
                                count += 1
                            except:
                                log( 'failed to copy seasonthumb' )
        log( 'seasonthumbs copied: %s' % count )

    def _copy_episodethumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params": {"properties": ["file", "title", "thumbnail", "season", "episode", "showtitle"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('episodes')):
            totalitems = len( json_response['result']['episodes'] )
            for item in json_response['result']['episodes']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32008) + ': ' + str( count + 1 ) )
                name = item['title']
                tvshow = item['showtitle']
                artwork = item['thumbnail']
                season = item['season']
                episode = item['episode']
                episodenumber = "s%.2d%.2d" % (int( season ), int( episode ))
                tmp_filename = tvshow + ' - ' + episodenumber + ' - ' + name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                # test file path with tv_content to find source name
                episodethumbspath = self.episodethumbspath
                if self.split_tvshows_sources == "true" and video_library._normalize_path(item['file']) in self.tvshows_content:
                    source_name = self.tvshows_content[video_library._normalize_path(item['file'])]
                    if self.normalize_names == "true":
                        source_name = video_library._normalize_string(source_name)
                    episodethumbspath = os.path.join( self.episodethumbspath, source_name)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( episodethumbspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy episodethumb' )
        log( 'episodethumbs copied: %s' % count )

    def _copy_musicvideothumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMusicVideos", "params": {"properties": ["title", "thumbnail", "artist"], "filter": {"field": "path", "operator": "contains", "value": "%s"}}, "id": 1}' % self.path)
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('musicvideos')):
            totalitems = len( json_response['result']['musicvideos'] )
            for item in json_response['result']['musicvideos']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32009) + ': ' + str( count + 1 ) )
                name = item['title']
                artwork = item['thumbnail']
                if item['artist']: # bug workaround, musicvideos can end up in the database without an artistname
                    artist = item['artist'][0]
                    tmp_filename = artist + ' - ' + name + '.jpg'
                else:
                    tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( self.musicvideothumbspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy musicvideothumb' )
        log( 'musicvideothumbs copied: %s' % count )

    def _copy_artistthumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetArtists", "params": {"properties": ["thumbnail"]}, "id": 1}')
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('artists')):
            totalitems = len( json_response['result']['artists'] )
            for item in json_response['result']['artists']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32010) + ': ' + str( count + 1 ) )
                name = item['label']
                artwork = item['thumbnail']
                tmp_filename = name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( self.artistthumbspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy artistthumb' )
        log( 'artistthumbs copied: %s' % count )

    def _copy_albumthumbs( self ):
        count = 0
        processeditems = 0
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "AudioLibrary.GetAlbums", "params": {"properties": ["title", "thumbnail", "artist"]}, "id": 1}')
        json_response = json.loads(json_query)
        if json_response.__contains__('result') and (json_response['result'] != None) and (json_response['result'].__contains__('albums')):
            totalitems = len( json_response['result']['albums'] )
            for item in json_response['result']['albums']:
                if self.dialog.iscanceled():
                    log('script cancelled')
                    return
                processeditems = processeditems + 1
                self.dialog.update( int( float( processeditems ) / float( totalitems ) * 100), LANGUAGE(32011) + ': ' + str( count + 1 ) )
                name = item['title']
                artist = item['artist'][0]
                artwork = item['thumbnail']
                tmp_filename = artist + ' - ' + name + '.jpg'
                filename = clean_filename( tmp_filename )
                if self.normalize_names == "true":
                    filename = video_library._normalize_string(filename)
                if artwork != '':
                    try:
                        xbmcvfs.copy( translatePath( artwork ), os.path.join( self.albumthumbspath, filename ) )
                        count += 1
                    except:
                        log( 'failed to copy albumthumb' )
        log( 'albumthumbs copied: %s' % count )

if ( __name__ == "__main__" ):
    log('script version %s started' % ADDONVERSION)
    Main()
log('script stopped')
