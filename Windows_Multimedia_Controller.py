
import asyncio
import tkinter as tk
import threading
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus
    )


class MediaOverlay:
    def __init__(self, root, controller):

        self.root = root
        self.controller = controller

        self.root.overrideredirect(True)
        # This will remove the title bar and border of the winder

        self.root.wm_attributes("-topmost", True)
        # This will make the window always on top like an overlay, so on games or anyother application
        
        self.root.geometry("350x125+2190+20")
        # This is the position of the popup itself

        self.root.config(bg="#1e1e1e")
        # This is the background color

        # These two lines are for when you're 
        self.hide_timer_id = None
        self.is_hovered = False

        self.root.withdraw()
        #This starts it hidden


        #This chunk of code is for text scrolling
        self.title_text = ""
        self.artist_text = ""
        self.scroll_timer_id = None
        self.max_display_length = 22

        
        #This is the UI elements of the overlay window
        self.title_label = tk.Label(root, text="", fg="white",bg ="#1e1e1e", font = ("Segoe UI", 12, "bold"))
        self.title_label.pack(pady=(15,2))


        self.artist_label = tk.Label(root, text="", fg = "#aaaaaa", bg = "#1e1e1e", font = ("Segoe UI", 10))
        self.artist_label.pack()

        self.source_label = tk.Label(root, text="", fg = "#666666", bg = "#1e1e1e", font = ("Segoe UI", 8))
        self.source_label.pack(pady=(2,5))

        # Switching the source of media that's currently playing
        self.switch_btn = tk.Button(
            root,
            text="🔄 Switch App",
            command=self.on_switch_click,
            bg="#2d2d2d",
            fg="white",
            activebackground="#3d3d3d",
            activeforeground="white",
            bd=0,
            font=("Segoe UI", 8)
        )

        self.switch_btn.pack(pady=(0, 8))
        self.hide_timer = None

        self.root.bind("Escape", lambda e: self.root.destroy())
        
        # These two lines are for when the mouse hovers over the overlay, so it will cancel auto-hide
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)

        def check_signals():
            self.root.after(500, check_signals)
        check_signals()

    def show_popup(self, title, artist, app_name=""):

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

        #This is for when is you're not hovering, it will just bring the timer for 3 seconds back
        if not self.is_hovered:
            self.hide_timer_id = self.root.after(3000, self.hide_overlay)

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
            

    




class MediaController:
    def __init__(self):
        self.manager = None
        self.sessions = []
        self.current_index = 0
        self.overlay = None
        self.loop = None
        self.attached_sessions = set()

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
        for session in self.sessions:
            app_id = session.source_app_user_model_id
            if app_id not in self.attached_sessions:

                #This line is for tracking metadata changes (Next/Previous track)
                session.add_media_properties_changed(self.on_media_properties_changed)

                session.add_playback_info_changed(self.on_playback_info_changed)

                self.attached_sessions.add(app_id)

    def on_media_properties_changed(self, session, args=None):
        asyncio.run_coroutine_threadsafe(self.update_current_display(), self.loop)

    def on_playback_info_changed(self, session, args=None):
        asyncio.run_coroutine_threadsafe(self.check_active_playback(session), self.loop)

    async def check_active_playback(self, session):
        # This is the auto-switch to the application playing media or that started to play audio
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
    async def update_current_display(self):
        if not self.sessions:
            return
        if self.current_index >= len(self.sessions):
            self.current_index = 0

        session = self.sessions[self.current_index]
        info = await session.try_get_media_properties_async()

        if info and info.title:
            #Get the app name(Spotify.exe or chrome)
            app_id = session.source_app_user_model_id.split("!")[0]
            self.overlay.show_popup(info.title, info.artist, app_id)
    async def switch_to_next_session(self):
        await self.refresh_sessions()
        if not self.sessions:
            return

        self.current_index = (self.current_index + 1) % len(self.sessions)
        await self.update_current_display()



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