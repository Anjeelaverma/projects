import streamlit as st
import requests as r
import re
import urllib.parse
from pytubefix import YouTube as yt
from io import BytesIO

def song_data(name:str):
    '''Function to get info of given song from jiosavaan'''
    url="https://www.jiosaavn.com/api.php?__call=autocomplete.get&query="+name+"&_format=json&_marker=0&ctx=wap6dot0"
    info=r.get(url)
    info=info.json()["songs"]["data"]
    return info

def get_dl(link):
    song_id = re.findall(r'song/(.*?)/(.*)',link)[0]
    url = f'https://www.jiosaavn.com/api.php?__call=webapi.get&api_version=4&_format=json&_marker=0&ctx=wap6dot0&token={song_id[1]}&type=song'
    resp = r.get(url)
    response = resp.json()
    final_url = urllib.parse.quote(response['songs'][0]['more_info']['encrypted_media_url'])
    dwn_url = f'https://www.jiosaavn.com/api.php?__call=song.generateAuthToken&url={final_url}&bitrate=320&api_version=4&_format=json&ctx=wap6dot0&_marker=0'
    dwn_r = r.get(dwn_url)
    dl_lnk = re.findall(r"(.+?(?=Expires))",dwn_r.json()['auth_url'])[0].replace('.cf.','.').replace('?','').replace('ac','aac')
    dl_items = [dl_lnk, song_id[0]]
    return dl_items

def on_progress_callback(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = int(bytes_downloaded / total_size * 100)
    st.session_state.progress_bar.progress(percentage_of_completion)
def download(url):
    if 'youtube.com' in url:
        yt_video = yt(url, on_progress_callback=on_progress_callback)
        chc = yt_video.streams.filter(only_audio=True)[-1]
        titl = yt_video.title
        buffer = BytesIO()
        st.session_state.progress_bar = st.progress(0)
        chc.stream_to_buffer(buffer)
        buffer.seek(0)
        return buffer, titl
    else:
        try:
            response = r.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            content = b""
            bytes_downloaded = 0
            chunk_size = 1024
            progress_bar = st.progress(0)
            for data in response.iter_content(chunk_size=chunk_size):
                content += data
                bytes_downloaded += len(data)
                progress = bytes_downloaded / total_size
                progress_bar.progress(progress)
            return content
        except Exception as e:
            st.error(f"Error: {e}")


st.title(":red[Song Downloader]")
st.subheader(":green[Easily download your favourite songs in highest quality(320kbps)]")
name = st.text_input('Enter song name')
titles = []
description = []
urls = []

if "urls" not in st.session_state:
    st.session_state["urls"] = None

if 'Download' not in st.session_state:
    st.session_state['Download'] = False

if st.button('Done'):
    a =  song_data(name)
    for i in a:
        titles.append(i['title'])
        urls.append(i['url'])
        description.append(i['description'])
    st.write('Available results are: ') 
    for i in range(len(titles)):
        st.text(f'{i+1}. {titles[i]} : {description[i]}')
    st.session_state["urls"]=urls

num = st.number_input("Enter index of song to download", value=0, max_value=3)

if st.button("Download"):
    url = st.session_state["urls"]
    lnk = url[int(num)-1]
    down = get_dl(lnk)
    st.success("please wait....")
    content=download(down[0])
    st.download_button(label="Download", data=content, key="audio_file", file_name=f"{down[1]}.mp3", mime='audio/mp3')
