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
        self.list_header = Gtk.Label(label="Task name")
        self.tasks_list.append(self.list_header)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.content_box.set_margin_top(10)
        self.content_box.set_margin_bottom(10)
        self.content_box.set_margin_start(10)
        self.content_box.set_margin_end(10)
        
    def do_activate(self):
        win = Adw.ApplicationWindow(application=self)
        win.set_title("Quests")
        win.set_default_size(400,300)
        Gtk.Window.set_default_icon_name("task-due-symbolic")

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)

        header = Adw.HeaderBar()
        
        add_btn = Gtk.Button(icon_name="list-add-symbolic")
        add_btn.connect("clicked", self._add_task)
        header.pack_start(add_btn)

        main_box.append(header)

        main_box.append(self.content_box)

        label = Gtk.Label(label = "Welcome, Adventurer!")
        self.content_box.append(label)


        self.content_box.append(self.level)
        self.content_box.append(self.xp_label)
        self.content_box.append(self.xp)

        self._load_task_and_display()
            
        win.set_content(main_box)
        win.present()

    def _check_and_display_empty_list(self):
        # if the last row is also the header then the list is empty
        if self.tasks_list.get_last_child().get_child() == self.list_header:
            self.tasks_list.append(Gtk.Label(label="No active quests. Take a rest, Adventurer!"))

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

        self.con.update_player_stat(new_xp, new_level, self.player_id)

        self.con.update_complete_task(widget.id)
        
        row = widget.get_ancestor(Adw.ActionRow)
        if row:
            self.tasks_list.remove(row)
        self._check_and_display_empty_list()

    def _load_task_and_display(self):
        tasks = self.con.fetch_unfinished_tasks()
        if tasks == []:
            self.tasks_list.append(Gtk.Label(label="No active quests. Take a rest, Adventurer!"))
        else:
            for task in tasks:
                row = Adw.ActionRow(title=task[1])
                finish_btn = Gtk.Button(icon_name="object-select-symbolic", label = str(task[6]))
                finish_btn.xp_point = task[6]
                finish_btn.id = task[0]
                finish_btn.connect("clicked", self._calculate_and_change_display)
                row.add_suffix(finish_btn)
                self.tasks_list.append(row)
        self.content_box.append(self.tasks_list)
    
    def _remove_task(self):
        self.content_box.remove(self.tasks_list)
        self.tasks_list = Gtk.ListBox()
        self.list_header = Gtk.Label(label="Task name")
        self.tasks_list.append(self.list_header)
        

    def _add_task(self, widget):
        task_name = "shower"
        self.con.add_new_task(self.player_id, task_name, reward_xp=20)
        self._remove_task()
        self._load_task_and_display() 
app = App()
app.run(sys.argv)
