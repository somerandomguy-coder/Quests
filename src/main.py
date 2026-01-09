import sys
from parser import parse_markdown_quests

import gi

import database
import engine

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.namle.Quests")


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.header = Adw.HeaderBar()

        self.add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self.add_btn.connect("clicked", self._toggle_entry)

        self.import_btn = Gtk.Button(icon_name="document-open-symbolic")
        self.import_btn.set_tooltip_text("Import Quest Log")
        self.import_btn.connect("clicked", self._import_file)

        self.level = Gtk.Label()
        self.level.level_num = None
        
        self.xp_label = Gtk.Label()

        self.xp = Gtk.ProgressBar()
        self.xp.xp_point = None
        
        self.player_id = None

        self.tasks_list = Gtk.ListBox()
        self.list_header = Gtk.Label(label="Task name")

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

        self.stack = Adw.ViewStack(enable_transitions=True)
        self.character_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.character_stats = Gtk.ScrolledWindow()
        self.character_stats.set_hexpand(True)

        self.character_stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.character_box_header = Gtk.Label(label = "DETAIL STATISTIC")
        self.identity_rank_row = Adw.ExpanderRow(title = "Identity and Rank: ")

        self.character_title = Gtk.Label() 

        self.character_class = Gtk.Label()
        self.character_class.char_class = None

        self.join_date = Gtk.Label()
        
        self.performance_stat= Adw.ExpanderRow(title = "Performance Stats: ")
        self.quest_complete = Gtk.Label()
        
        self.efficiency_rating = Gtk.Label()
        self.streak_count = Gtk.Label()
        self.skirmish = Gtk.Label()
        self.expedition = Gtk.Label()
        self.legendary = Gtk.Label()

        self.character_stats.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.character_visual = Gtk.Overlay()
        self.character_icon = Gtk.Image()
        self.character_icon.set_from_file("/home/nam/Documents/git-repos/quests/knight.png")
        self.character_icon.set_pixel_size(200)
        
        self.class_badge = Gtk.Label(label="Knight")
        self.class_badge.set_valign(Gtk.Align.START)
        # The "Overlay" (Level Badge sitting on top)
        self.level_badge = Gtk.Label(label="Lvl 1")
        self.level_badge.add_css_class("xp-badge") # Reuse your existing CSS!
        self.level_badge.set_valign(Gtk.Align.END)   # Position it at the bottom
        self.level_badge.set_halign(Gtk.Align.CENTER)

        self.view_switcher = Adw.ViewSwitcher(stack=self.stack)
        
        self._sync_player_stat()
    def do_activate(self):
############################## CSS
        provider = Gtk.CssProvider()
        provider.load_from_data("""
            label.level-text { font-size: 24pt; font-weight: bold; color: red; }
            progressbar trough { min-height: 10px; border-radius: 5px; }
            progressbar progress { background-color: #3584e4; }
            row.task-hard { background-color: rgba(255, 0, 0, 0.1); border-left: 5px solid red; }
            row.task-medium { background-color: rgba(255, 165, 0, 0.1); border-left: 5px solid orange; }
            row.task-easy { border-left: 5px solid green; }
            
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.level.add_css_class("level-text")
##############################
        self.win = Adw.ApplicationWindow(application=self)
        self.win.set_icon_name("task-due-symbolic")
        self.win.set_title("Quests")
        self.win.set_default_size(400,300)
        
        self.header.pack_start(self.add_btn)

        self.header.pack_end(self.import_btn)

        self.header_box.append(self.header)

        self.main_box.append(self.header_box)
        self.main_box.append(self.view_switcher)
        self.main_box.append(self.stack)

        self.tasks_list.append(self.list_header)

        self.stack.add_titled(child=self.content_box, title="List")

        self.content_box.append(self.label)
        self.content_box.append(self.level)
        self.content_box.append(self.xp_label)
        self.content_box.append(self.xp)

        self.stack.add_titled(child=self.character_box, title="Character")

        self.identity_rank_row.add_row(self.character_title)
        self.identity_rank_row.add_row(self.character_class)
        self.identity_rank_row.add_row(self.join_date)

        self.performance_stat.add_row(self.quest_complete)
        self.performance_stat.add_row(self.efficiency_rating)
        self.performance_stat.add_row(self.streak_count)
        self.performance_stat.add_row(self.skirmish)
        self.performance_stat.add_row(self.expedition)
        self.performance_stat.add_row(self.legendary)

        self.character_stats_box.append(self.character_box_header)
        self.character_stats_box.append(self.identity_rank_row)
        self.character_stats_box.append(self.performance_stat)

        self.character_stats.set_child(self.character_stats_box)

        self.character_visual.set_child(self.character_icon)
        self.character_visual.add_overlay(self.class_badge)
        self.character_visual.add_overlay(self.level_badge)

        self.character_box.append(self.character_stats)
        self.character_box.append(self.character_visual)
        
        self._load_task_and_display()

        self.win.set_content(self.main_box)
        self.win.present()
##############################

    def _import_file(self, widget):
        self.chooser = Gtk.FileDialog()
        self.filter = Gtk.FileFilter()
        self.filter.add_pattern("*md")

        self.chooser.set_default_filter(self.filter)
        self.chooser.open(parent = self.win, callback = self._get_the_import_file)
    
    def _get_the_import_file(self, source, res):
        try: 
            file = source.open_finish(res)

            if file:
                file_path = file.get_path()
            else: 
                raise Exception("There's no file")

            quests = parse_markdown_quests(file_path)
            self.con.add_multiple_new_task(self.player_id, quests) 
            self._remove_task()
            self._load_task_and_display() 
            
        except Exception as e:
            print("Some error happens during reading file:", e)
        
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

        self.level.set_label(str(res[3]))
        self.level.level_num = res[3]
        
        self.xp_label.set_label(f"{res[4]}/{res[5]}")

        self.xp.set_fraction(res[4]/res[5])
        self.xp.xp_point = res[4]
        
        self.player_id = res[0]

        self.character_title.set_label(f"Adventurer Title: Level {self.level.level_num} - Depression fighter") 

        self.character_class.char_class = res[2]
        self.character_class.set_label(f"Class: {self.character_class.char_class}")
        self.join_date.set_label(f"Join Date: {res[13]}")
        
        self.quest_complete.set_label(f"Total Quests Completed: {res[7]}")
        self.efficiency_rating.set_label(f"Efficiency Rating: {0} tasks/day")
        self.streak_count.set_label(f"Streak Count: {res[11]}")
        self.skirmish.set_label(f"Number of Skirmish Quests (easy) Finished: {res[8]}")
        self.expedition.set_label(f"Number of Expedition Quests (medium) Finished: {res[9]}")
        self.legendary.set_label(f"Number of Legendary Quests (hard) Finished: {res[10]}")

    def _load_task_and_display(self):
        tasks = self.con.fetch_unfinished_tasks()
        if tasks == []:
            self.tasks_list.append(Gtk.Label(label="No active quests. Take a rest, Adventurer!"))
        else:
            for task in tasks:
                row = Adw.ExpanderRow(title=task[1])
                
                # Apply our custom CSS classes based on difficulty
                if task[2] == 3:
                    row.add_css_class("task-hard")
                elif task[2] == 2:
                    row.add_css_class("task-medium")
                else:
                    row.add_css_class("task-easy")

                description_text = task[3] or "No description for this task"
                description = Gtk.Label(label=description_text)
                description.set_margin_top(10) # Make it look nicer
                description.set_margin_bottom(10) # Make it look nicer
                description.set_margin_start(10) # Make it look nicer
                description.set_margin_end(10) # Make it look nicer
                row.add_row(description)
                
                finish_btn = Gtk.Button(icon_name="object-select-symbolic", label=str(task[6]))
                finish_btn.xp_point = task[6]
                finish_btn.id = task[0]
                finish_btn.connect("clicked", self._calculate_and_change_display)
                row.add_suffix(finish_btn)
                
                self.tasks_list.append(row)
        
        # Check if tasks_list is already in content_box to avoid "already has a parent" error
        if self.tasks_list.get_parent() is None:
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
        else:
            self.header_box.remove(self.description_entry)

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
