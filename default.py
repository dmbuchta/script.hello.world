import xbmc
import xbmcaddon
import xbmcgui
import dropbox
import sys
from os import listdir, remove
from subprocess import call

__addon__         = xbmcaddon.Addon()
__addonname__     = __addon__.getAddonInfo('name')
__addonversion__  = __addon__.getAddonInfo('version')
__icon__  = __addon__.getAddonInfo('icon')

ACCESS_TOKEN      = __addon__.getSetting('access_token')
APP_KEY           = __addon__.getSetting('app_key')
APP_SECRET        = __addon__.getSetting('app_secret')
REMOTE_FILES      = __addon__.getSetting('remote_dir')
LOCAL_FILES       = __addon__.getSetting('local_dir')
REFS              = __addon__.getAddonInfo('path').decode('utf-8') + "/" + __addon__.getSetting('refs_dir')
WAIT              = int(__addon__.getSetting('sync_freq'))


def log(txt):
    message = '%s: %s' % (__addonname__, txt.encode('ascii', 'ignore'))
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def __configure__():
    log("Attempting to configure access token")

    flow = dropbox.client.DropboxOAuth2FlowNoRedirect(APP_KEY,APP_SECRET)

    authorize_url = flow.start()

    ret = xbmcgui.Dialog().yesno("Dropbox Authorization", "You'll need to authorize our app before continuing.", "Doing so will give this app full access to your dropbox account.", "Visit the URL in the next dialog and enter the access code.", nolabel="Cancel", yeslabel="Continue")

    if ret:
        code = xbmcgui.Dialog().input(authorize_url, type=xbmcgui.INPUT_ALPHANUM )
        log( "CODE: " + code )

        #code = raw_input("Enter the authorization code here: ").strip()
        #access_token, user_id = flow.finish(code)

        __addon__.setSetting('access_token', code)


def main():    

    def safely_delete(path_, file_, reason=''):
        file_ = path_ + "/" + file_
        try:
            log('Deleting ' + file_ + reason)
            remove(file_)
        except:
            log(file_ + ' does not exist')

    def wake_up():
        log( "Doing hack to trigger click command" )
        call(["xbmc-send", "--action='SendClick()'"])


    client = dropbox.client.DropboxClient(ACCESS_TOKEN)

    folder_metadata = client.metadata(REMOTE_FILES)

    old_files=[ref for ref in listdir(REFS)]
    current_files=[(file_['path'].replace(REMOTE_FILES + "/", ''),str(file_['revision'])) for file_ in folder_metadata['contents']]
    change_made = False

    ############################################
    # delete all picture/references that are no longer in the remote directory
    ############################################
    for file_name in [name for name in old_files if name not in [item[0] for item in current_files]]:
        old_files.remove(file_name)
        safely_delete(REFS, file_name, ' because it does not exist in dropbox (1)')
        safely_delete(LOCAL_FILES, file_name, ' because it does not exist in dropbox (2)')
        change_made = True

    ############################################
    # delete all picture/references that are stale. Then remove if from the list
    ############################################
    for old_file_ref in [item for item in current_files if item[0] in old_files]:
        try:
            with open(REFS + "/" + old_file_ref[0], 'r') as file_:
                old_ref=file_.read().strip()
                if not old_ref == old_file_ref[1]:
                    safely_delete(REFS, old_file_ref[0], ' because it is stale [new=' + old_file_ref[1]  + ',current=' + old_ref + ']')                
                    safely_delete(LOCAL_FILES, old_file_ref[0], ' because it is stale')                
                    old_files.remove(old_file_ref[0])
                    change_made = True
        except:
            log( REFS + "/" + old_file_ref[0] + ' cannot be found' )
    

    ############################################
    # download any new files
    ############################################
    for file_ref in [item for item in current_files if item[0] not in old_files]:
        log("I need to download " + file_ref[0])
        remote_file, metadata = client.get_file_and_metadata(REMOTE_FILES + "/" + file_ref[0])

        with open(LOCAL_FILES + "/" + file_ref[0], 'wb') as file_:
            log( "Saving new picture: " + LOCAL_FILES + "/" + file_ref[0])
            file_.write(remote_file.read())
            change_made = True

        with open(REFS + "/" + file_ref[0], 'wb') as file_:
            log( "Saving new reference: " + REFS + "/" + file_ref[0])
            file_.write(str(metadata['revision']))

    if change_made:
        log("A change has been found so we have to wake up...")
        wake_up()
        xbmc.executebuiltin('Notification(%s, %s, %d, %s)'%(__addonname__, "Pictures directory has been synced", 15000, __icon__))
            

if (__name__ == "__main__"):

    args = sys.argv[1:]
    if len(args) and args[0] == 'config':
        __configure__()
    else:
        monitor = xbmc.Monitor()

        while not monitor.abortRequested():
            if monitor.waitForAbort( WAIT ):
                break

            log('script version %s started' % __addonversion__)
            main()
            log('script version %s stopped' % __addonversion__)
    




