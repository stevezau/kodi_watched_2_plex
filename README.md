# Kodi Watched Status to Plex
This script will sync the kodi watched status for Movies and TVShows into Plex

`**WARNING: This was only minimally tested.**
`
# Install
```
git clone https://github.com/stevezau/kodi_watched_2_plex.git
cd kodi_watched_2_plex
pip install -r requirements.txt
```

# Usage
Example is below. Kodi API URl looks like `http://<KODI_IP>:KODI_PORT/`
```
python kodi_watched_2_plex.py kodi_api_url plex_username plex_password plex_server_name
```
