import engine, database
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.namle.Quests")
        con = database.Database_Connection()
        res = con.fetch_player()
        self.level = Gtk.Label(label = res[2])
        self.xp = Gtk.ProgressBar()
        self.xp.set_fraction(res[3]/res[4])
        
        self.con = database.Database_Connection().con 

    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_title("Quests")
        win.set_default_size(400,300)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
        btn = Gtk.Button(label="X")
        btn.connect('clicked', lambda x: win.close())
        box.append(btn)

        label = Gtk.Label(label = "Welcome, Adventurer!")
        box.append(label)

        
        level_up_btn = Gtk.Button(label="Level Up!")
        level_up_btn.connect('clicked',self._calculate_and_change_display) 
        box.append(self.level)
        box.append(self.xp)
        box.append(level_up_btn)

        tasks_list = Gtk.ListBox()
        tasks = self.load_task()
        if tasks == []:
            tasks_list.set_text("No active quests. Take a rest, Adventurer!")
        else:
            header = Gtk.Label(label="Task name")
            tasks_list.append(header)
            for task in tasks:
                row = Adw.ActionRow(title=task[1])
                finish_btn = Gtk.Button(icon_name="object-select-symbolic", label = str(task[6]))
                finish_btn.connect("clicked", self._calculate_and_change_display)
                row.add_suffix(finish_btn)
                tasks_list.append(row)

        box.append(tasks_list)
        
        win.set_content(box)
        win.present()

    def _calculate_and_change_display(self, widget):
        level = int(self.level.get_text())
        xp_fraction = self.xp.get_fraction()
        xp = xp_fraction * level * 100
        xp_gain = int(widget.get_child().get_text()) 
        
        new_level, new_xp = engine.calculate_xp_gain(xp_gain, level, xp)
        self.level.set_text(str(new_level))
        new_xp_fraction = (new_xp/new_level)/100
        self.xp.set_fraction(new_xp_fraction)

    def load_task(self):
        con = database.Database_Connection()
        tasks = con.fetch_unfinished_tasks()
        return tasks

app = App()
app.run(sys.argv)
