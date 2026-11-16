# Outside tools and services used by Amber's MSC Hub

| What | Why | Cost | Licence / terms |
|---|---|---|---|
| YouTube Data API v3 (Google) | Lets the Music tab list the songs of a YouTube playlist so Amber can tick some and save them | Free. 10,000 free units a day; a playlist of 300 songs uses 6 units | Google APIs Terms of Service and YouTube API Services Terms |
| YouTube IFrame Player API (Google) | Plays YouTube songs inside the app with our own song list, queue and buttons | Free | Google APIs Terms of Service and YouTube API Services Terms |
| Spotify iFrame API (Spotify) | Plays songs from a Spotify file inside the app with our own skip and rewind buttons | Free | Spotify Developer Terms and Spotify Platform Rules |
| Google Fonts (fonts.googleapis.com) | Font search in My Look | Free | Open font licences (mostly SIL OFL) |
| GitHub Pages | Hosts the app | Free | GitHub Terms |
| Mammoth, read-excel-file, PDF.js | Read Word, Excel and PDF files on the phone | Free | Open source (see licences in source/assets/lib) |

## YouTube key notes
- The key is a browser key. It is visible in the public page code, which is normal for this kind of key.
- It is restricted to the YouTube Data API only and to the website https://silverwolf5636.github.io/* only.
- It lives in Google Cloud project "meta-agent-factory" (Wolf's account). It can be deleted or regenerated at console.cloud.google.com, APIs & Services, Credentials.
- If it is ever replaced: change `YT_KEY` in source/src.html, run build.py, publish.
