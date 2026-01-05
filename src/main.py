from abc import abstractmethod, ABC
import engine, database
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk



class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.namle.Quests")


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.header = Adw.HeaderBar()

        self.add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self.add_btn.connect("clicked", self._toggle_entry)

        self.level = Gtk.Label()
        self.level.level_num = None
        
        self.xp_label = Gtk.Label()

        self.xp = Gtk.ProgressBar()
        self.xp.xp_point = None
        
        self.player_id = None
        self._sync_player_stat()

        self.tasks_list = Gtk.ListBox()
        self.list_header = Gtk.Label(label="Task name")
        self.tasks_list.append(self.list_header)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.content_box.set_margin_top(10)
        self.content_box.set_margin_bottom(10)
        self.content_box.set_margin_start(10)
        self.content_box.set_margin_end(10)

        self.label = Gtk.Label(label = "Welcome, Adventurer!")
        
        self.entry = Gtk.Entry(placeholder_text="Enter new quest...")
        self.entry.connect("activate", self._toggle_description)

        self.description_entry = Gtk.Entry(placeholder_text="Enter description (optional)")
        self.description_entry.connect("activate", self._add_task)
    def do_activate(self):
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_icon_name("task-due-symbolic")
        self.win.set_title("Quests")
        self.win.set_default_size(400,300)
        
        self.header.pack_start(self.add_btn)

        self.header_box.append(self.header)

        self.main_box.append(self.header_box)
        self.main_box.append(self.content_box)

        self.content_box.append(self.label)
        self.content_box.append(self.level)
        self.content_box.append(self.xp_label)
        self.content_box.append(self.xp)

        self._load_task_and_display()

        self.win.set_content(self.main_box)
        self.win.present()

############################## CSS
        provider = Gtk.CssProvider()
        provider.load_from_data("""
            label.level-text { font-size: 24pt; font-weight: bold; color: red; }
            progressbar trough { min-height: 10px; border-radius: 5px; }
            progressbar progress { background-color: #3584e4; }
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.level.add_css_class("level-text")

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
        
        row = widget.get_ancestor(Adw.ExpanderRow)
        if row:
            self.tasks_list.remove(row)
        self._check_and_display_empty_list()

    def _sync_player_stat(self):
        self.con = database.Database_Connection()
        res = self.con.fetch_player()

        self.level.set_label(str(res[2]))
        self.level.level_num = res[2]
        
        self.xp_label.set_label(f"{res[3]}/{res[4]}")

        self.xp.set_fraction(res[3]/res[4])
        self.xp.xp_point = res[3]
        
        self.player_id = res[0]
        

    def _load_task_and_display(self):
        tasks = self.con.fetch_unfinished_tasks()
        if tasks == []:
            self.tasks_list.append(Gtk.Label(label="No active quests. Take a rest, Adventurer!"))
        else:
            for task in tasks:
                row = Adw.ExpanderRow(title=task[1])
                if task[2] == 3: # Hard
                    row.add_css_class("error") 
                elif task[2] == 2: # Medium
                    row.add_css_class("warning")
                print("diffuculty is",task[2])
                description_text = task[3]
                if description_text == "":
                    description_text= "No description for this task"
                description = Gtk.Label(label=description_text)
                row.add_row(description)
                finish_btn = Gtk.Button(icon_name="object-select-symbolic", label = str(task[6]))
                finish_btn.xp_point = task[6]
                finish_btn.id = task[0]
                finish_btn.connect("clicked", self._calculate_and_change_display)
                row.add_suffix(finish_btn)
                self.tasks_list.append(row)
                
        self.content_box.append(self.tasks_list)
    
    def _toggle_entry(self, widget):
        if self.entry.get_ancestor(Gtk.Box):
            self.header_box.remove(self.entry)
            if self.description_entry.get_ancestor(Gtk.Box):
                self.header_box.remove(self.description_entry)
        else:
            self.header_box.append(self.entry)
            self.entry.grab_focus()
            
    
    def _toggle_description(self, widget):
        if self.description_entry.get_ancestor(Gtk.Box) == None:
            self.header_box.append(self.description_entry)
            self.description_entry.grab_focus()

    def _remove_task(self):
        # Instead of recreating the ListBox, just empty it
        while child := self.tasks_list.get_first_child():
            self.tasks_list.remove(child)
    
        # Put the header back
        self.list_header = Gtk.Label(label="Task name")
        self.tasks_list.append(self.list_header)        

    def _add_task(self, widget):
        task_name = self.entry.get_text()
        description = self.description_entry.get_text()
        difficulty, xp = self._resolve_difficulty(task_name)
        if task_name != "":
            self.entry.set_text("")
            self.description_entry.set_text("")
            self.con.add_new_task(self.player_id, task_name, difficulty=difficulty, description=description, reward_xp=xp)
            self._remove_task()
            self._load_task_and_display() 
            self._toggle_description(None)

    def _resolve_difficulty(self, task_name):
        task_name = task_name.strip()
        if task_name.endswith("/h"):
            return 3, 100 
        elif task_name.endswith("/m"):
            return 2, 50
        else:
            return 1, 10
        

app = App()
app.run(sys.argv)
