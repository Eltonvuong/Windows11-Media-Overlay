import io
import asyncio
import urllib.request
import tkinter as tk
import threading
from PIL import Image, ImageTk
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    )
from winsdk.windows.storage.streams import DataReader, Buffer, InputStreamOptions


class MediaOverlay:
    def __init__(self, root, controller):

        self.root = root
        self.controller = controller

        self.root.overrideredirect(True)
        # This will remove the title bar and border of the winder

        self.root.wm_attributes("-topmost", True)
        # This will make the window always on top like an overlay, so on games or anyother application
        
        self.root.geometry("520x210+1995+25")
        # This is the position of the popup itself old 350x125+2190+20, this is set to a 2560 x 1440 resolution screen
        
        #Content Frame for Labels
        self.text_frame = tk.Frame(root, bg="#1e1e1e")
        self.text_frame.place(x=205, y=15, width=295, height=170)


        #This is the UI elements of the overlay window
        self.title_label = tk.Label(self.text_frame, text="", fg="white",bg ="#1e1e1e", font = ("Segoe UI", 14, "bold"), anchor="w")
        self.title_label.pack(fill="x", pady=(0, 2))
        #Old self.title_label.pack(pady=(15, 2))

        self.artist_label = tk.Label(self.text_frame, text="", fg = "#aaaaaa", bg = "#1e1e1e", font = ("Segoe UI", 12), anchor="w")
        self.artist_label.pack(fill="x", pady=(0,2))
        #This is new fill="x" to make it stretch across the overlay window



        self.root.config(bg="#1e1e1e")
        # This is the background color

        #IMage container for the art 
        self.art_image = None
        self.art_label = tk.Label(root, bg="#1e1e1e")
        self.art_label.place(x=20, y=20, width=170, height=170)

        

        #This is for the source of the media that is currently playing
        self.source_label = tk.Label(self.text_frame, text="", fg = "#666666", bg = "#1e1e1e", font = ("Segoe UI", 9), anchor="w")
        self.source_label.pack(fill="x", pady=(0, 2))


        # These two lines are for when you're 
        self.hide_timer_id = None
        self.is_hovered = False

        self.root.withdraw()
        #This starts it hidden


        #This chunk of code is for text scrolling
        self.title_text = ""
        self.artist_text = ""
        self.scroll_timer_id = None
        self.max_display_length = 28

        #THis is for the control buttons
        self.control_frame = tk.Frame(self.text_frame, bg="#1e1e1e")
        #This will pack to the bottom of the text frame
        self.control_frame.pack(fill = "x", pady=(0,2))

        btn_style = {
            "bg": "#2d2d2d",
            "fg": "white",
            "activebackground": "#3d3d3d",
            "activeforeground": "white",
            "bd": 0,
            "font": ("Segoe UI", 9),
            "pady": 3
            }

        #This is the control buttons for the overlay window
        self.playback_row = tk.Frame(self.control_frame, bg="#1e1e1e")
        self.playback_row.pack(fill = "x", pady=(0, 2))
        
        self.prev_button = tk.Button(self.playback_row, text="⏮️", command=self.on_prev_click, **btn_style)
        self.play_button = tk.Button(self.playback_row, text="⏯️", command=self.on_play_pause_click, **btn_style)
        self.next_button = tk.Button(self.playback_row, text="⏭️", command=self.on_next_click, **btn_style)

        for btn in (self.prev_button, self.play_button, self.next_button):
            btn.pack(side="left", expand=True, fill="x", padx=1)

            

        

        # Switching the source of media that's currently playing
        self.switch_btn = tk.Button(
            self.control_frame,
            text="🔄 Switch App",
            command=self.on_switch_click,
            **btn_style
            
        )
        
        

        self.switch_btn.pack(fill="x", padx=1)
        self.hide_timer = None

        self.root.bind("Escape", lambda e: self.root.destroy())
        
        # These two lines are for when the mouse hovers over the overlay, so it will cancel auto-hide
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)



        
    def update_thumbnail(self, image_bytes):

        #THis will convert bytes into TKinter PhotoIMage
        if image_bytes:
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
                pil_img = pil_img.convert("RGBA").resize((150, 150), Image.Resampling.LANCZOS)
                '''Format conversion pillow struggles to convert certain, 
                uncompressed or palette-based pixel streams into TKinter PhotoImage.
                This will translate pixel array into standard 32-bit color channels before handing it to TKinter.
                '''
                self.art_image = ImageTk.PhotoImage(pil_img)
                self.art_label.config(image=self.art_image, text="")
                return
            except Exception as e:
                print(f"Error loading image: {e}")

        self.art_image = None
        self.art_label.config(image="", text="🎵", fg="#555555", font=("Segoe UI", 52))

    def show_popup(self, title, artist, app_name="", image_bytes=None):
        
        self.update_thumbnail(image_bytes)

        # This will pad the strings with trailing spaces for smooth looping
        self.title_text = title if len(title) <= self.max_display_length else f"{title}   .    "
        self.artist_text = artist if len(artist) <= self.max_display_length else f"{artist}   .    "
        self.source_label.config(text=f"Source: {app_name}")

        # This will stop active marquee loops before starting a new one
        if self.scroll_timer_id is not None:
            self.root.after_cancel(self.scroll_timer_id)
            self.scroll_timer_id = None

        # This will reset label text diaplays
        self.title_label.config(text=self.title_text[:self.max_display_length])
        self.artist_label.config(text=self.artist_text[:self.max_display_length])

        #This line reverses .withdraw() to make hidden overlay visible again
        self.root.deiconify()
        # This just makes the overlay visibnle again and resets the auto-hide timer
        self.reset_hide_timer()
        # This starts the scrolling animation loops
        self.animate_scroll()

    def animate_scroll(self):

        if len(self.title_text) > self.max_display_length:
            self.title_text = self.title_text[1:] + self.title_text[0]

            self.title_label.config(text=self.title_text[:self.max_display_length])

        if len(self.artist_text) > self.max_display_length:
            self.artist_text = self.artist_text[1:] + self.artist_text[0]

            self.artist_label.config(text=self.artist_text[:self.max_display_length])

        #This will schedule the next frames (250ms = 4 steps per second)
        self.scroll_timer_id = self.root.after(250, self.animate_scroll)







    def on_switch_click(self):
        #TRigger the session switch in the background async loop
        asyncio.run_coroutine_threadsafe(self.controller.switch_to_next_session(), self.controller.loop)



   

    def reset_hide_timer(self):

        if self.hide_timer_id is not None:
            try:
                self.root.after_cancel(self.hide_timer_id)
            except (ValueError, KeyError):
                pass
            self.hide_timer_id = None

        #This is for when is you're not hovering, it will just bring the timer for 5 seconds back
        if not self.is_hovered:
            self.hide_timer_id = self.root.after(5000, self.hide_overlay)

    def on_mouse_enter(self, event):
        
        self.is_hovered = True
        if self.hide_timer_id is not None:
            try:
                self.root.after_cancel(self.hide_timer_id)
            except (ValueError, KeyError):
                pass
            self.hide_timer_id = None

    def on_mouse_leave(self, event):

        self.is_hovered = False
        self.reset_hide_timer()

    def hide_overlay(self):

        self.hide_timer_id = None
        #Clear timer ID since it completed execution
        if not self.is_hovered:
            self.root.withdraw()

    def on_play_pause_click(self):
        asyncio.run_coroutine_threadsafe(self.controller.toggle_play_pause(), self.controller.loop)

    def on_next_click(self):
        asyncio.run_coroutine_threadsafe(self.controller.skip_next(), self.controller.loop)

    def on_prev_click(self):
        asyncio.run_coroutine_threadsafe(self.controller.skip_previous(), self.controller.loop)

            

    




class MediaController:
    def __init__(self):
        self.manager = None
        self.sessions = []
        self.current_index = 0
        self.overlay = None
        self.loop = None
        self.attached_sessions = set()


    async def extract_thumbnail(self, stream_ref):
        #This is just for async exraction of stream bytes from WinSDK IRandomAccessStreamReference

        if not stream_ref:
            return None
        try:
            stream = await stream_ref.open_read_async()
            if not stream or stream.size == 0:
                return None

          

            reader = DataReader(stream.get_input_stream_at(0))
            #Load the data into the reader asynchronously
            await reader.load_async(stream.size)

            byte_array = bytearray(stream.size)
            reader.read_bytes(byte_array)
            return bytes(byte_array)
        except Exception as e:
            print(f"Error extracting thumbnail: {e}")
            return None

    async def update_current_display(self):

        #This function will update the overlay with the current session's media info and thumbnail
        if not self.sessions:
            return
        if self.current_index >= len(self.sessions):
            self.current_index = 0

        session = self.sessions[self.current_index]
        info = await session.try_get_media_properties_async()

        if info and info.title:
            app_id = session.source_app_user_model_id
            if "!" in app_id:
                app_id = app_id.split("!")[0]
            clean_app_name = app_id.split("\\")[-1].replace(".exe", "").capitalize()

            image_bytes = await self.extract_thumbnail(info.thumbnail)
            self.overlay.show_popup(info.title, info.artist, clean_app_name, image_bytes)

    async def start(self, overlay, loop):
        self.overlay = overlay
        self.loop = loop
        self.manager = await SessionManager.request_async()

        await self.refresh_sessions()

        self.attach_event_listener()

        while True:
            await asyncio.sleep(2)
            # This continuously check if sessions changed (apps opened/closed)
            await self.refresh_sessions()
            self.attach_event_listener()

    def attach_event_listener(self):

        #This will attach event listeners to all sessions that haven't been attached yet
        for session in self.sessions:
            app_id = session.source_app_user_model_id
            if app_id not in self.attached_sessions:

                #This line is for tracking metadata changes (Next/Previous track)
                session.add_media_properties_changed(self.on_media_properties_changed)

                session.add_playback_info_changed(self.on_playback_info_changed)

                self.attached_sessions.add(app_id)

    def on_media_properties_changed(self, session, args=None):

        #This will trigger the update of the overlay when media properties change (like track change)
        asyncio.run_coroutine_threadsafe(self.update_current_display(), self.loop)

    def on_playback_info_changed(self, session, args=None):

        #This will trigger the check for active playback when playback info changes (like play/pause)
        asyncio.run_coroutine_threadsafe(self.check_active_playback(session), self.loop)

    async def check_active_playback(self, session):
        # This is the auto-switch to the application playing media or that started to play audio 
        #THis is still buggy I got to work on this 
        playback_info = session.get_playback_info()
        if playback_info and playback_info.playback_status == PlaybackStatus.PLAYING:
            #This finds if the index of the session that is actively playing media
            for idx, s in enumerate(self.sessions):
                if s.source_app_user_model_id == session.source_app_user_model_id:
                    self.current_index = idx
                    break

        await self.update_current_display()
       
    async def update_current_session(self):
        if not self.sessions:
            return

        #This makes sure that the current index is valid and within the range of the sessions list
        if self.current_index >= len(self.sessions):
            self.current_index = 0

            session = self.sessions[self.current_index]
            info = await session.try_get_media_properties_async()

            if info and info.title:

                app_id = session.source_app_user_model_id.split("!")[0]

                clean_app_name = app_id.split("\\")[-1].replace(".exe", "").capitalize()

                self.overlay.show_popup(info.title, info.artist, clean_app_name)


    async def refresh_sessions(self):
        # Get list of all open players sending media info
        raw_sessions = self.manager.get_sessions()
        self.sessions = list(raw_sessions)

    '''async def update_current_display(self):

        # This function will update the overlay with the current session's media info and thumbnail
        if not self.sessions:
            return
        if self.current_index >= len(self.sessions):
            self.current_index = 0

        session = self.sessions[self.current_index]
        info = await session.try_get_media_properties_async()

        if info and info.title:
            #Get the app name(Spotify.exe or chrome)
            app_id = session.source_app_user_model_id.split("!")[0]
            self.overlay.show_popup(info.title, info.artist, app_id)'''
    async def switch_to_next_session(self):
        await self.refresh_sessions()
        if not self.sessions:
            return

        self.current_index = (self.current_index + 1) % len(self.sessions)
        await self.update_current_display()

    async def toggle_play_pause(self):
        if not self.sessions:
            return
        session = self.sessions[self.current_index]
        playback_info = session.get_playback_info()
        if playback_info and playback_info.playback_status == PlaybackStatus.PLAYING:
            await session.try_pause_async()
        else:
            await session.try_play_async()
    
    async def skip_next(self):
        if not self.sessions:
            return
        session = self.sessions[self.current_index]
        await session.try_skip_next_async()

    async def skip_previous(self):
        if not self.sessions:
            return
        session = self.sessions[self.current_index]
        await session.try_skip_previous_async()


if __name__ == "__main__":
    root = tk.Tk()
    controller = MediaController()
    overlay = MediaOverlay(root, controller)


    # Run asyncio loop with Tkinter GUI loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)


    def run_asyncio():
        try:

            loop.run_until_complete(controller.start(overlay, loop))
        except asyncio.CancelledError:
            pass

    
    threading.Thread(target=run_asyncio, daemon=True).start()


    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()