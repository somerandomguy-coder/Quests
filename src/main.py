from abc import abstractmethod, ABC
import engine, database
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw



class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.namle.Quests")
        self.con = database.Database_Connection()
        res = self.con.fetch_player()

        self.level = Gtk.Label(label = res[2])
        self.level.level_num = res[2]
        
        self.xp_label = Gtk.Label(label = f"{res[3]}/{res[4]}")

        self.xp = Gtk.ProgressBar()
        self.xp.set_fraction(res[3]/res[4])
        self.xp.xp_point = res[3]
        
        self.player_id = res[0]

        self.tasks_list = Gtk.ListBox()
    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_title("Quests")
        win.set_default_size(400,300)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)

        header = Adw.HeaderBar()
        main_box.append(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content_box.set_margin_top(10)
        content_box.set_margin_bottom(10)
        content_box.set_margin_start(10)
        content_box.set_margin_end(10)
        main_box.append(content_box)

        label = Gtk.Label(label = "Welcome, Adventurer!")
        content_box.append(label)

        
        content_box.append(self.level)
        content_box.append(self.xp_label)
        content_box.append(self.xp)

        tasks = self._load_task()
        if tasks == []:
            self.tasks_list.append(Gtk.Label(label="No active quests. Take a rest, Adventurer!"))
        else:
            header = Gtk.Label(label="Task name")
            self.tasks_list.append(header)
            for task in tasks:
                row = Adw.ActionRow(title=task[1])
                finish_btn = Gtk.Button(icon_name="object-select-symbolic", label = str(task[6]))
                finish_btn.xp_point = task[6]
                finish_btn.id = task[0]
                finish_btn.connect("clicked", self._calculate_and_change_display)
                row.add_suffix(finish_btn)
                self.tasks_list.append(row)
        content_box.append(self.tasks_list)
        
        win.set_content(main_box)
        win.present()

    def _calculate_and_change_display(self, widget):
        level = self.level.level_num

        # ProgressBar only work with fraction
        xp = self.xp.xp_point
        xp_gain = widget.xp_point
        new_level, new_xp = engine.calculate_xp_gain(xp_gain, level, xp)

        self.level.set_text(str(new_level))
        self.level.level_num = new_level

        new_xp_fraction = (new_xp/new_level)/100
        self.xp.set_fraction(new_xp_fraction)
        self.xp.xp_point = new_xp

        self.xp_label.set_text(f"{int(new_xp)}/{new_level*100}")

        if new_level != level:
            self.con.update_player_level(new_level, self.player_id)
        self.con.update_player_xp(new_xp, self.player_id)

        self.con.update_complete_task(widget.id)

        # Remove the row
        self.tasks_list.remove(widget.get_parent().get_parent().get_parent())
    def _load_task(self):
        tasks = self.con.fetch_unfinished_tasks()
        return tasks


app = App()
app.run(sys.argv)
