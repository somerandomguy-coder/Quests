import engine
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.namle.Quests")
        self.level = Gtk.Label(label = "1")
        self.xp = Gtk.Label(label = "50")

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_title("Quests")
        win.set_default_size(400,300)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)

        label = Gtk.Label(label = "Welcome, Adventurer!")
        box.append(label)

        
        level_up_btn = Gtk.Button(label="Level Up!")
        level_up_btn.connect('clicked',self._calculate_and_change_display) 
        box.append(self.level)
        box.append(self.xp)
        box.append(level_up_btn)


        btn = Gtk.Button(label="Hello, World!")
        btn.connect('clicked', lambda x: win.close())
        box.append(btn)

        win.set_content(box)
        win.present()
    def _calculate_and_change_display(self, widget):
        level = int(self.level.get_text())
        xp = int(self.xp.get_text())
        new_level, new_xp = engine.calculate_xp_gain(310, level, xp)
        self.level.set_text(str(new_level))
        self.xp.set_text(str(new_xp))

app = App()
app.run(sys.argv)
