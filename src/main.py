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

        self.character_title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 

        self.character_title_title = Gtk.Label(label="Adventurer Title:", halign=Gtk.Align.START) 
        self.character_title_title.set_hexpand(True)
        self.character_title_value = Gtk.Label() 
        self.character_title_row.append(self.character_title_title)
        self.character_title_row.append(self.character_title_value)


        
        self.character_class_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.character_class_title = Gtk.Label(label = "Class:", halign=Gtk.Align.START)
        self.character_class_title.set_hexpand(True)
        self.character_class_value = Gtk.Label()
        self.character_class_value.char_class = None

        self.character_class_row.append(self.character_class_title)
        self.character_class_row.append(self.character_class_value)

        self.join_date_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.join_date_title = Gtk.Label(label =  "Join Date:", halign=Gtk.Align.START)
        self.join_date_title.set_hexpand(True)
        self.join_date_value = Gtk.Label()

        self.join_date_row.append(self.join_date_title)
        self.join_date_row.append(self.join_date_value)

        
        self.performance_stat= Adw.ExpanderRow(title = "Performance Stats: ")
        self.quest_complete_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.quest_complete_title = Gtk.Label(label = "Total Quests Completed: ", halign=Gtk.Align.START)
        self.quest_complete_title.set_hexpand(True)
        self.quest_complete_value = Gtk.Label()
        self.quest_complete_row.append(self.quest_complete_title)
        self.quest_complete_row.append(self.quest_complete_value)
        
        self.efficiency_rating_row= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.efficiency_rating_title = Gtk.Label(label = "Efficiency Rating: ", halign=Gtk.Align.START)
        self.efficiency_rating_title.set_hexpand(True)
        self.efficiency_rating_value = Gtk.Label()
        self.efficiency_rating_row.append(self.efficiency_rating_title)
        self.efficiency_rating_row.append(self.efficiency_rating_value)

        self.streak_count_row= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.streak_count_title = Gtk.Label(label = "Streak Count: ", halign=Gtk.Align.START)
        self.streak_count_title.set_hexpand(True)
        self.streak_count_value = Gtk.Label()
        self.streak_count_row.append(self.streak_count_title)
        self.streak_count_row.append(self.streak_count_value)

        self.skirmish_row= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.skirmish_title = Gtk.Label(label="Number of Skirmish Quests (easy) Finished: ", halign=Gtk.Align.START)
        self.skirmish_title.set_hexpand(True)
        self.skirmish_value = Gtk.Label()
        self.skirmish_row.append(self.skirmish_title)
        self.skirmish_row.append(self.skirmish_value)

        self.expedition_row= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.expedition_title= Gtk.Label(label="Number of Expedition Quests (medium) Finished: ", halign=Gtk.Align.START)
        self.expedition_title.set_hexpand(True)
        self.expedition_value = Gtk.Label()
        self.expedition_row.append(self.expedition_title)
        self.expedition_row.append(self.expedition_value)

        self.legendary_row= Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL) 
        self.legendary_title = Gtk.Label(label ="Number of Legendary Quests (hard) Finished: " , halign=Gtk.Align.START)
        self.legendary_title.set_hexpand(True)
        self.legendary_value = Gtk.Label()
        self.legendary_row.append(self.legendary_title)
        self.legendary_row.append(self.legendary_value)

        self.character_stats.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.character_visual = Gtk.Overlay()
        self.character_icon = Gtk.Image()
        self.character_icon.set_from_file("/home/nam/Documents/git-repos/quests/knight.png")
        self.character_icon.set_pixel_size(200)
        
        self.class_badge = Gtk.Label()
        self.class_badge.set_valign(Gtk.Align.START)
        # The "Overlay" (Level Badge sitting on top)
        self.level_badge = Gtk.Label(label=f"Lvl {self.level.level_num}")
        self.level_badge.add_css_class("xp-badge") # Reuse your existing CSS!
        self.level_badge.set_valign(Gtk.Align.END)   # Position it at the bottom
        self.level_badge.set_halign(Gtk.Align.CENTER)

        self.view_switcher = Adw.ViewSwitcher(stack=self.stack)
        self.stat_size_group_identity= Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        self.stat_size_group_identity.add_widget(self.character_title_value)
        self.stat_size_group_identity.add_widget(self.character_class_value)
        self.stat_size_group_identity.add_widget(self.join_date_value)

        self.stat_size_group_performance= Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self.stat_size_group_performance.add_widget(self.quest_complete_value)
        self.stat_size_group_performance.add_widget(self.efficiency_rating_value)
        self.stat_size_group_performance.add_widget(self.streak_count_value)
        self.stat_size_group_performance.add_widget(self.skirmish_value)
        self.stat_size_group_performance.add_widget(self.expedition_value)
        self.stat_size_group_performance.add_widget(self.legendary_value)
        
       
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

        self._check_and_display_starting_point()

        self.main_box.append(self.stack)

        self.tasks_list.append(self.list_header)


        self.content_box.append(self.label)
        self.content_box.append(self.level)
        self.content_box.append(self.xp_label)
        self.content_box.append(self.xp)

        self.identity_rank_row.add_row(self.character_title_row)
        self.identity_rank_row.add_row(self.character_class_row)
        self.identity_rank_row.add_row(self.join_date_row)

        self.performance_stat.add_row(self.quest_complete_row)
        self.performance_stat.add_row(self.efficiency_rating_row)
        self.performance_stat.add_row(self.streak_count_row)
        self.performance_stat.add_row(self.skirmish_row)
        self.performance_stat.add_row(self.expedition_row)
        self.performance_stat.add_row(self.legendary_row)

        self.character_stats_box.append(self.character_box_header)
        self.character_stats_box.append(self.identity_rank_row)
        self.character_stats_box.append(self.performance_stat)

        self.character_stats.set_child(self.character_stats_box)

        self.character_visual.set_child(self.character_icon)
        self.character_visual.add_overlay(self.class_badge)
        self.character_visual.add_overlay(self.level_badge)

        self.character_box.append(self.character_stats)
        self.character_box.append(self.character_visual)

        self.setting_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.delete_btn = Gtk.Button(label="Delete Character!")
        self.delete_btn.connect("clicked", self._open_delete_message_dialog)
        self.delete_btn.set_valign(Gtk.Align.CENTER)
        self.delete_btn.set_halign(Gtk.Align.CENTER)
        self.setting_box.append(self.delete_btn)
        
        self._load_task_and_display()

        self.win.set_content(self.main_box)
        self.win.present()
##############################

    def _open_delete_message_dialog(self, widget):
        dialog = Adw.AlertDialog()
        dialog.set_heading("Abandon Adventure?")
        dialog.set_body("Deleting your character will erase all your levels and legendary deeds. This cannot be undone!")
        dialog.add_response("cancel", "Keep Fighting")
        dialog.add_response("delete", "Give Up (Delete)")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.choose(self.win, None, self._on_delete_response, None)


    def _on_delete_response(self, dialog, response_id, _data):
        response = dialog.choose_finish(response_id)
        if response == "delete":
            self.con.delete_character(self.player_id) 
            self._check_and_display_starting_point()
        




    def _check_and_display_starting_point(self):

        self.con = database.Database_Connection()
        char = self.con.fetch_player()

        if char == None:
            label = Gtk.Label(label="Quests")
            small_text = Gtk.Label(label="Start your legendary tale today, Adventurer!")
            self.player_name = Gtk.Entry(placeholder_text="Enter your name...")
            self.player_name.connect("activate",self._get_name_and_create_player)
            self.player_name.grab_focus()
            self.create_char_btn = Gtk.Button(label="Confirm")
            self.warning = 0
            self.create_char_btn.connect("clicked", self._get_name_and_create_player)

            self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing = 10)
            self.welcome_box.append(label)
            self.welcome_box.append(small_text)
            self.welcome_box.append(self.player_name)
            self.welcome_box.append(self.create_char_btn)

            self.stack.add_titled(child=self.welcome_box, title="Welcome")

        else:
            self.stack.add_titled(child=self.content_box, title="List")
            self.stack.add_titled(child=self.character_box, title="Character")
            self.stack.add_titled(child=self.setting_box, title="Settings")
            self.stack.remove(self.welcome_box)
            self.main_box.append(self.view_switcher)
            self._sync_player_stat()

    def _get_name_and_create_player(self, widget):
        warning_text = Gtk.Label(label="Name can not be empty")
        warning_text.add_css_class("error")
        name = self.player_name.get_text()
        if name:
            self.con.add_player(name) 
            self._check_and_display_starting_point()
        else:
            if self.warning == 0:
                self.welcome_box.insert_child_after(warning_text, self.player_name)
                self.warning = 1

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

        self.name = res[1]

        self.level.set_label(str(res[3]))
        self.level.level_num = res[3]
        
        self.xp_label.set_label(f"{res[4]}/{res[5]}")

        self.xp.set_fraction(res[4]/res[5])
        self.xp.xp_point = res[4]
        
        self.player_id = res[0]

        self.character_title_value.set_label(f"Level {self.level.level_num} - Depression fighter") 

        self.character_class_value.char_class = res[2]
        self.character_class_value.set_label(f"{self.character_class_value.char_class}")
        self.join_date_value.set_label(f"{res[13]}")
        
        self.quest_complete_value.set_label(f"{res[7]}")
        self.efficiency_rating_value.set_label(f"{0} tasks/day")
        self.streak_count_value.set_label(f"{res[11]}")
        self.skirmish_value.set_label(f"{res[8]}")
        self.expedition_value.set_label(f"{res[9]}")
        self.legendary_value.set_label(f"{res[10]}")

        self.level_badge.set_label(f"Lvl {self.level.level_num}")
        self.class_badge.set_label(f"{self.name}")
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
