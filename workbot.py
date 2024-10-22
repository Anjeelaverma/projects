import streamlit as st
import webbrowser
import random
import requests as r
import re
import urllib.parse
from tqdm import tqdm

st.title(":green[hi]")
st.subheader(":blue[A speech-powered virtual assistant to ease your life]")

def song_data(name:str):
    '''Function to get info of given song from jiosavaan'''
    url="https://www.jiosaavn.com/api.php?__call=autocomplete.get&query="+name+"&_format=json&_marker=0&ctx=wap6dot0"
    resp=r.get(url).text
    info = re.findall(r'songs\":{\"data\":\[(.*?)\]',resp)[0]
    data = re.findall(r'id\":\"(.*?)\".*?:\"(.*?)\".*?url\":\"(.*?)\".*?description\":\"(.*?)\"',info)
    return data


def get_dl(link):
    song_id = re.findall(r'song/(.*?)/(.*)',link)[0]
    # Get direct download link of song from savaan server
    url = f'https://www.jiosaavn.com/api.php?__call=webapi.get&api_version=4&_format=json&_marker=0&ctx=wap6dot0&token={song_id[1]}&type=song'
    resp = r.get(url)
    response = resp.json()
    final_url = urllib.parse.quote(response['songs'][0]['more_info']['encrypted_media_url'])
    dwn_url = f'https://www.jiosaavn.com/api.php?__call=song.generateAuthToken&url={final_url}&bitrate=320&api_version=4&_format=json&ctx=wap6dot0&_marker=0'
    dwn_r = r.get(dwn_url)
    dl_lnk = re.findall(r"(.+?(?=Expires))",dwn_r.json()['auth_url'])[0].replace('.cf.','.').replace('?','').replace('ac','aac')
    dl_items = [dl_lnk, song_id[0]]
    return dl_items


def download_mp3(link, progress_bar):
    try:
        response = r.get(link, stream=True)

        # Get the total file size in bytes
        total_size = int(response.headers.get('content-length', 0))
        content = b""
        with tqdm(
            desc="Downloading",
            total=total_size,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=1024):
                size = len(data)
                content += data
                bar.update(size)
                progress_bar.progress(bar.n / bar.total)
        return content
    
    except Exception as e:
        st.error(f"Error: {e}")

def down_song():
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
            titles.append(i[1])
            urls.append(i[2].replace("\\/","/"))
            description.append(i[3].replace("\\u00b7",""))
        st.write('Available results are: ')    # Show the available results to user and ask for user's choice
        for i in range(len(titles)):
            st.text(f'{i+1}. {titles[i]} : {description[i]}')
        st.session_state["urls"]=urls

    num = st.number_input("Enter index of song to download",value =0, max_value=3)

    if st.button("Download"):
        url = st.session_state["urls"]
        lnk = url[int(num)-1]
        down = get_dl(lnk)
        st.write(":green[Downloading....]")
        progress_bar = st.progress(0)
        content=download_mp3(down[0], progress_bar)
        st.success("Downloaded successfully!")
        st.download_button(label="Save Audio File", data=content, key="audio_file", file_name=f"{down[1]}.mp3", mime='audio/mp3')


def play_game():
    st.markdown("<h1 style='text-align: center; color: #ff5733;'>Let's play Rock-Paper-Scissors!</h1>", unsafe_allow_html=True)
    
    user_choice = st.selectbox("Select your move:", ("Rock", "Paper", "Scissors"))
    choices = ["Rock", "Paper", "Scissors"]
    computer_choice = random.choice(choices)

    st.write(f"You chose: **{user_choice}**")
    st.write(f"Computer chose: **{computer_choice}**")

    if user_choice == computer_choice:
        st.markdown("<h2 style='text-align: center; color: #ffa07a;'>It's a tie!</h2>", unsafe_allow_html=True)
    elif (user_choice == "Rock" and computer_choice == "Scissors") or \
         (user_choice == "Paper" and computer_choice == "Rock") or \
         (user_choice == "Scissors" and computer_choice == "Paper"):
        st.markdown("<h2 style='text-align: center; color: #00ff00;'>You win!</h2>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align: center; color: #ff0000;'>You lose!</h2>", unsafe_allow_html=True)


def fetch_news(api_key):
    url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}"
    response = r.get(url)
    news_data = response.json()
    news_headlines = [article['title'] for article in news_data['articles']]
    return news_headlines
def present_news(news_headlines):
    st.markdown("<h1 style='text-align: center; color: #0066ff;'>Latest News Headlines</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    for headline in news_headlines:
        st.markdown(f"<p style='font-size: 18px; margin-bottom: 10px;'>📰 {headline}</p>", unsafe_allow_html=True)
        st.markdown("---")

def text_to_speech():
    import requests as r
    from tqdm import tqdm
    import streamlit as st

    def download_mp3(link, progress_bar):
        try:
            response = r.get(link, stream=True)

            # Get the total file size in bytes
            total_size = int(response.headers.get('content-length', 0))
            content = b""
            with tqdm(
                desc="Downloading",
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
            ) as bar:
                for data in response.iter_content(chunk_size=1024):
                    size = len(data)
                    content += data
                    bar.update(size)
                    progress_bar.progress(bar.n / bar.total)
            return content
        
        except Exception as e:
            st.error(f"Error: {e}")
            return None

    # Apply custom CSS for styling
    st.markdown("""
        <style>
            .main {
                background-color: #0A0607 ;
                padding: 20px;
                border-radius: 10px;
                color: white;
            }
            .stButton>button {
                background-color: #1e90ff;
                color: white;
                border-radius: 5px;
                border: none;
                padding: 10px 20px;
                cursor: pointer;
            }
            .stButton>button:hover {
                background-color: #1c86ee;
            }
            .stTextInput>div>div>input {
                border-radius: 5px;
                border: 1px solid #ddd;
                padding: 10px;
                background-color: #374151;
                color: white;
            }
            .stTextArea>div>div>textarea {
                border-radius: 5px;
                border: 1px solid #ddd;
                padding: 10px;
                background-color: #374151;
                color: white;
            }
            .stAudio>audio {
                width: 100%;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='main'>", unsafe_allow_html=True)

    st.title("🎤 Text to Speech and Audio Downloader")

    txt = st.text_area("Enter text to get speech:", height=150)

    if st.button('🔊 Convert to Speech'):
        with st.spinner('Processing...'):
            url = 'https://ttsmp3.com/makemp3_new.php'
            post = {'msg': txt, 'lang': 'Aditi', 'source': 'ttsmp3'}
            
            try:
                resp = r.post(url=url, data=post).json()
                url_b = resp['URL']
                
                progress_bar = st.progress(0)
                content = download_mp3(url_b, progress_bar)
                
                if content:
                    st.audio(content, format='audio/mp3')
                    st.download_button(label="💾 Save Audio File", data=content, file_name="audio.mp3", mime='audio/mp3')
                else:
                    st.error("Failed to download audio content.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)


def yt_down():
    import os
    import streamlit as st
    from pytubefix import YouTube

    def down_vid(url, res):
        yt = YouTube(url)
        title = yt.title
        title = title.replace('|', ' ').replace(':', " ").replace(" ", "_")

        video_stream = yt.streams.filter(subtype='mp4', res=res, only_video=True).first()
        video_path = video_stream.download(filename="video.mp4")

        audio_stream = yt.streams.filter(only_audio=True).first()
        audio_path = audio_stream.download(filename="audio.mp3")

        final_output_path = f"{title}.mp4"
        os.system(f'ffmpeg -i {video_path} -i {audio_path} -c:v copy -c:a aac {final_output_path}')

        os.remove(video_path)
        os.remove(audio_path)

        return final_output_path

    st.title('YouTube Downloader')

    with st.sidebar:
        st.title('YouTube Downloader')
        add_selectbox = st.selectbox("Select what you want to download:", ("Video", "Audio"))
        st.markdown('''
        ## About 
        Download your favorite media from YouTube by providing the YouTube link;
        and selecting to download the video or audio file of the media provided:            
        ''')

    if add_selectbox == 'Video':
        st.header("Download Video")

        youtube_url = st.text_input("Enter the YouTube URL:")
        res = st.selectbox("Select Resolution:", ["360p", "480p", "720p", "1080p"])

        if st.button("Download Video"):
            if youtube_url and res:
                try:
                    output_path = down_vid(youtube_url, res)
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="Download Video",
                            data=file,
                            file_name=output_path,
                            mime="video/mp4"
                        )
                except Exception as e:
                    st.error(f"An error occurred: {e}")
            else:
                st.warning("Please enter a valid URL and select a resolution.")

    elif add_selectbox == 'Audio':
        st.header("Download Audio")

        youtube_url = st.text_input("Enter the YouTube URL:")

        if st.button("Download Audio"):
            if youtube_url:
                try:
                    yt = YouTube(youtube_url)
                    titl = yt.title
                    titl = titl.replace('|', ' ').replace(':', " ").replace(" ", "_")
                    audio_stream = yt.streams.filter(only_audio=True)[-1]
                    audio_path = audio_stream.download(filename=f"{titl}.mp3")

                except Exception as e:
                    print(e)
            else:
                st.warning("Please enter a valid URL.")

 

def main():
    command = st.text_input("Enter command (/help for list of all cmds): ")
    if command == "/help":
        st.write("List of available commands:")
        st.write("- `videos`: download audio/video from youtube.")
        st.write("- `Insta`: Download Insta posts with links.")
        st.write("- `game`: Let's play some games.")
        st.write("- `news`: Top headlines currently")
        st.write("- `song`: download High quality song")
        st.write("- `txtaud`: want someone to speak your words.")
    elif command == "videos":
        yt_down()
    elif command == "game":
        st.write("wannna play Rock, paper, scissors or head to site with huge collection of games u can play")
        gm_command = st.text_input("A for RPS B or other games: ")
        if gm_command == "A":
            play_game()
        elif gm_command == "B":
            webbrowser.open_new_tab("https://www.poki.com/")
    elif command == "news":
        NEWS_API_KEY = "a0e7243221fd4fc5bd414013288b8526"
        news_headlines = fetch_news(NEWS_API_KEY)
        present_news(news_headlines)
    elif command == "song":
        down_song()
    elif command == "txtaud":
        text_to_speech()
    elif command == "Insta":
        webbrowser.open_new_tab("https://snapinsta.app/")
    elif command.strip() != "":
        st.write("Unknown command. Type `/help` for available commands.")


if __name__ == "__main__":
    main()
