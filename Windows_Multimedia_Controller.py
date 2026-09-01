from ast import Try
import asyncio
import tkinter as tk
import threading
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as SessionManager
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

        self.root.withdraw()
        #This starts it hidden

        
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

        def check_signals():
            self.root.after(500, check_signals)
        check_signals()


    def on_switch_click(self):
        #TRigger the session switch in the background async loop
        asyncio.run_coroutine_threadsafe(self.controller.switch_to_next_session(), self.controller.loop)



    def show_popup(self, title, artist, app_name=""):

        #This will update the text
        ## Injects the track name and artist into UI labels
        self.title_label.config(text = title)
        self.artist_label.config(text = artist)
        self.source_label.config(text=f"Source: {app_name}")



        #Reverses the .withdraw() to make hidden window visible
        self.root.deiconify()


        # This will reset the auto-hide countdown, I'm going to make it 2.5 seconds for now
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
            #So this will cancel any active hide timer when we go spam mode
        self.hide_timer = self.root.after(3000, self.root.withdraw)
        # This will start the 3 second timer and calls withdraw() to hide the overlay

    




class MediaController:
    def __init__(self):
        self.manager = None
        self.sessions = []
        self.current_index = 0
        self.overlay = None
        self.loop = None

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

    def attach_event_listener(self):
        current = self.manager.get_current_session()
        if current:
            current.add_media_properties_changed(self.on_media_properties_changed)

    def on_media_properties_changed(self, session, args=None):
        asyncio.run_coroutine_threadsafe(self.update_current_display(), self.loop)

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

        if info:
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