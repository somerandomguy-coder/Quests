"""GTK widget composition helpers for the Quests app."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk


class QuestUIManager:
    """Build and update the app's pages while keeping business logic elsewhere."""

    def __init__(self, asset_dir: str | Path):
        self.asset_dir = Path(asset_dir)
        self.window: Adw.ApplicationWindow | None = None
        self._page_cache: dict[str, Gtk.Widget] = {}

    def build_window(
        self,
        application: Adw.Application,
        *,
        on_toggle_entry,
        on_import,
        on_task_name_activate,
        on_task_description_activate,
        on_delete_character,
        on_create_player,
    ) -> Adw.ApplicationWindow:
        self._install_css()

        self.window = Adw.ApplicationWindow(application=application)
        self.window.set_icon_name("task-due-symbolic")
        self.window.set_title("Quests")
        self.window.set_default_size(720, 560)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.stack = Adw.ViewStack(enable_transitions=True)
        self.stack.set_vexpand(True)
        self.view_switcher = Adw.ViewSwitcher()
        self.view_switcher.set_stack(self.stack)
        self.view_switcher.set_visible(False)

        self._build_header(
            on_toggle_entry,
            on_import,
            on_task_name_activate,
            on_task_description_activate,
        )
        self._build_welcome_page(on_create_player)
        self._build_list_page()
        self._page_cache["character"] = self._build_character_page()
        self._page_cache["settings"] = self._build_settings_page(on_delete_character)

        self.stack.add_titled(self.welcome_box, "welcome", "Welcome")
        self.stack.add_titled(self.content_box, "list", "List")

        self.main_box.append(self.header_box)
        self.main_box.append(self.view_switcher)
        self.main_box.append(self.stack)

        self.window.set_content(self.main_box)
        return self.window

    def show_welcome_state(self) -> None:
        self._ensure_welcome_page(is_visible=True)
        self.view_switcher.set_visible(False)
        self.add_btn.set_sensitive(False)
        self.import_btn.set_sensitive(False)
        self.delete_btn.set_sensitive(False)
        self.set_task_editor_visible(show_editor=False)
        self.clear_notice()
        self.player_name.grab_focus()
        self.stack.set_visible_child(self.welcome_box)

    def show_main_state(self) -> None:
        self._ensure_welcome_page(is_visible=False)
        self._ensure_lazy_pages()
        self.view_switcher.set_visible(True)
        self.add_btn.set_sensitive(True)
        self.import_btn.set_sensitive(True)
        self.delete_btn.set_sensitive(True)
        self.stack.set_visible_child(self.content_box)

    def update_player(self, player: dict) -> None:
        self._update_progress_display(player)
        self._update_character_identity(player)
        self._update_character_metrics(player)

    def render_tasks(self, tasks: list[dict], on_complete_task) -> None:
        while child := self.tasks_list.get_first_child():
            self.tasks_list.remove(child)

        if not tasks:
            self.focus_title.set_label("No active quests")
            self.focus_detail.set_label("Take a break, or add one gentle quest to restart momentum.")
            self.tasks_list.append(
                self._build_empty_state_row("No active quests. Take a rest, Adventurer!")
            )
            return

        suggested_task = tasks[0]
        self.focus_title.set_label(f"Focus quest: {suggested_task.get('name', 'Untitled Quest')}")
        self.focus_detail.set_label(
            "Start with the top quest to reduce choice overload, then keep the streak going."
        )

        for index, task in enumerate(tasks):
            self.tasks_list.append(self._build_task_row(task, on_complete_task, is_focus=index == 0))

    def get_player_name(self) -> str:
        return self.player_name.get_text()

    def set_player_name_error_visible(self, visible: bool) -> None:
        self.player_name_error.set_visible(visible)

    def get_task_name(self) -> str:
        return self.task_name_entry.get_text()

    def get_task_description(self) -> str:
        return self.task_description_entry.get_text()

    def get_selected_difficulty(self) -> int:
        return int(self.difficulty_dropdown.get_selected()) + 1

    def clear_task_inputs(self) -> None:
        self.task_name_entry.set_text("")
        self.task_description_entry.set_text("")
        self.difficulty_dropdown.set_selected(0)

    def set_task_editor_visible(self, *, show_editor: bool) -> None:
        self._set_optional_widget_visible(self.quick_add_box, show_editor)
        if show_editor:
            self.task_name_entry.grab_focus()

    def is_task_entry_visible(self) -> bool:
        return self.quick_add_box.get_parent() is not None

    def show_notice(self, message: str, *, error: bool = False) -> None:
        self.notice_label.set_label(message)
        if error:
            self.notice_label.add_css_class("error")
        else:
            self.notice_label.remove_css_class("error")
        self.notice_label.set_visible(True)

    def clear_notice(self) -> None:
        self.notice_label.set_label("")
        self.notice_label.remove_css_class("error")
        self.notice_label.set_visible(False)

    def open_import_dialog(self, callback) -> None:
        chooser = Gtk.FileDialog()
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern("*.md")
        chooser.set_default_filter(file_filter)
        chooser.open(parent=self.window, callback=callback)

    def present_delete_dialog(self, callback) -> None:
        dialog = Adw.AlertDialog()
        dialog.set_heading("Abandon Adventure?")
        dialog.set_body(
            "Deleting your character will erase all your levels and legendary deeds. "
            "This cannot be undone!"
        )
        dialog.add_response("cancel", "Keep Fighting")
        dialog.add_response("delete", "Give Up (Delete)")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.choose(self.window, None, callback, None)

    def _build_header(
        self,
        on_toggle_entry,
        on_import,
        on_task_name_activate,
        on_task_description_activate,
    ) -> None:
        self.header = Adw.HeaderBar()
        self.add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self.add_btn.connect("clicked", on_toggle_entry)

        self.import_btn = Gtk.Button(icon_name="document-open-symbolic")
        self.import_btn.set_tooltip_text("Import Quest Log")
        self.import_btn.connect("clicked", on_import)

        self.task_name_entry = Gtk.Entry(placeholder_text="Enter new quest...")
        self.task_name_entry.connect("activate", on_task_name_activate)
        self.task_name_entry.set_hexpand(True)

        self.task_description_entry = Gtk.Entry(
            placeholder_text="Enter description (optional)"
        )
        self.task_description_entry.connect("activate", on_task_description_activate)
        self.task_description_entry.set_hexpand(True)

        self.difficulty_store = Gtk.StringList.new(
            ["Skirmish (Easy)", "Expedition (Medium)", "Legendary (Hard)"]
        )
        self.difficulty_dropdown = Gtk.DropDown.new(self.difficulty_store, None)
        self.difficulty_dropdown.set_selected(0)

        self.quick_add_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row_one = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_one.append(self.task_name_entry)
        row_one.append(self.difficulty_dropdown)
        self.quick_add_box.append(row_one)
        self.quick_add_box.append(self.task_description_entry)

        helper = Gtk.Label(
            label="Choose a quest difficulty directly instead of typing command suffixes.",
            xalign=0,
        )
        helper.add_css_class("helper-text")
        self.quick_add_box.append(helper)

        self.header.pack_start(self.add_btn)
        self.header.pack_end(self.import_btn)

        self.header_box.append(self.header)

    def _build_welcome_page(self, on_create_player) -> None:
        self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.welcome_box.set_margin_top(24)
        self.welcome_box.set_margin_bottom(24)
        self.welcome_box.set_margin_start(24)
        self.welcome_box.set_margin_end(24)

        title = Gtk.Label(label="Quests")
        subtitle = Gtk.Label(label="Start your legendary tale today, Adventurer!")

        self.player_name = Gtk.Entry(placeholder_text="Enter your name...")
        self.player_name.connect("activate", on_create_player)

        self.player_name_error = Gtk.Label(label="Name can not be empty")
        self.player_name_error.add_css_class("error")
        self.player_name_error.set_visible(False)

        self.create_char_btn = Gtk.Button(label="Confirm")
        self.create_char_btn.connect("clicked", on_create_player)

        self.welcome_box.append(title)
        self.welcome_box.append(subtitle)
        self.welcome_box.append(self.player_name)
        self.welcome_box.append(self.player_name_error)
        self.welcome_box.append(self.create_char_btn)

    def _build_list_page(self) -> None:
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.content_box.set_margin_top(16)
        self.content_box.set_margin_bottom(16)
        self.content_box.set_margin_start(16)
        self.content_box.set_margin_end(16)

        self.label = Gtk.Label(label="Welcome, Adventurer!")
        self.level_value = Gtk.Label()
        self.level_value.level_num = 1
        self.level_value.add_css_class("level-text")

        self.xp_label = Gtk.Label()
        self.xp_bar = Gtk.ProgressBar()
        self.xp_bar.xp_point = 0

        self.notice_label = Gtk.Label(wrap=True, xalign=0)
        self.notice_label.set_visible(False)

        self.focus_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.focus_card.add_css_class("focus-card")
        self.focus_title = Gtk.Label(label="Focus quest: None yet", xalign=0)
        self.focus_detail = Gtk.Label(
            label="Pick one quest and finish it before switching context.",
            xalign=0,
            wrap=True,
        )
        self.focus_detail.add_css_class("helper-text")
        self.focus_card.append(self.focus_title)
        self.focus_card.append(self.focus_detail)

        self.tasks_header = Gtk.Label(label="Task name", xalign=0)
        self.tasks_list = Gtk.ListBox()
        self.tasks_list.set_selection_mode(Gtk.SelectionMode.NONE)

        self.content_box.append(self.label)
        self.content_box.append(self.level_value)
        self.content_box.append(self.xp_label)
        self.content_box.append(self.xp_bar)
        self.content_box.append(self.notice_label)
        self.content_box.append(self.focus_card)
        self.content_box.append(self.tasks_header)
        self.content_box.append(self.tasks_list)

    def _build_character_page(self) -> Gtk.Widget:
        self.character_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self.character_box.set_margin_top(16)
        self.character_box.set_margin_bottom(16)
        self.character_box.set_margin_start(16)
        self.character_box.set_margin_end(16)

        self.character_stats = Gtk.ScrolledWindow()
        self.character_stats.set_hexpand(True)
        self.character_stats.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        character_stats_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        character_box_header = Gtk.Label(label="DETAIL STATISTIC")

        identity_rank_row = Adw.ExpanderRow(title="Identity and Rank")
        self.character_title_value = self._build_stat_row(
            identity_rank_row, "Adventurer Title:"
        )
        self.character_class_value = self._build_stat_row(identity_rank_row, "Class:")
        self.join_date_value = self._build_stat_row(identity_rank_row, "Join Date:")

        performance_row = Adw.ExpanderRow(title="Performance Stats")
        self.quest_complete_value = self._build_stat_row(
            performance_row, "Total Quests Completed:"
        )
        self.efficiency_rating_value = self._build_stat_row(
            performance_row, "Efficiency Rating:"
        )
        self.streak_count_value = self._build_stat_row(
            performance_row, "Streak Count:"
        )
        self.completed_today_value = self._build_stat_row(
            performance_row, "Quests Finished Today:"
        )
        self.skirmish_value = self._build_stat_row(
            performance_row, "Number of Skirmish Quests (easy) Finished:"
        )
        self.expedition_value = self._build_stat_row(
            performance_row, "Number of Expedition Quests (medium) Finished:"
        )
        self.legendary_value = self._build_stat_row(
            performance_row, "Number of Legendary Quests (hard) Finished:"
        )

        character_stats_box.append(character_box_header)
        character_stats_box.append(identity_rank_row)
        character_stats_box.append(performance_row)
        self.character_stats.set_child(character_stats_box)

        self.character_visual = Gtk.Overlay()
        self.character_icon = Gtk.Image()
        character_asset = self.asset_dir / "knight.png"
        if character_asset.exists():
            self.character_icon.set_from_file(str(character_asset))
        else:
            self.character_icon.set_icon_name("avatar-default-symbolic")
        self.character_icon.set_pixel_size(200)

        self.class_badge = Gtk.Label()
        self.class_badge.set_valign(Gtk.Align.START)
        self.class_badge.set_halign(Gtk.Align.CENTER)

        self.level_badge = Gtk.Label(label="Lvl 1")
        self.level_badge.set_valign(Gtk.Align.END)
        self.level_badge.set_halign(Gtk.Align.CENTER)

        self.character_visual.set_child(self.character_icon)
        self.character_visual.add_overlay(self.class_badge)
        self.character_visual.add_overlay(self.level_badge)

        self.character_box.append(self.character_stats)
        self.character_box.append(self.character_visual)
        return self.character_box

    def _build_settings_page(self, on_delete_character) -> Gtk.Widget:
        self.setting_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.setting_box.set_margin_top(24)
        self.setting_box.set_margin_bottom(24)
        self.setting_box.set_margin_start(24)
        self.setting_box.set_margin_end(24)

        self.delete_btn = Gtk.Button(label="Delete Character!")
        self.delete_btn.set_valign(Gtk.Align.CENTER)
        self.delete_btn.set_halign(Gtk.Align.CENTER)
        self.delete_btn.connect("clicked", on_delete_character)

        self.setting_box.append(self.delete_btn)
        return self.setting_box

    def _update_progress_display(self, player: dict) -> None:
        level = max(1, int(player.get("level") or 1))
        xp = max(0, int(player.get("xp") or 0))
        xp_full = max(1, int(player.get("xp_full") or 100))
        xp_fraction = min(xp / xp_full, 1.0)

        self.level_value.set_label(str(level))
        self.level_value.level_num = level
        self.xp_label.set_label(f"{xp}/{xp_full}")
        self.xp_bar.set_fraction(xp_fraction)
        self.xp_bar.xp_point = xp
        self.level_badge.set_label(f"Lvl {level}")

    def _update_character_identity(self, player: dict) -> None:
        name = str(player.get("name") or "Adventurer")
        level = max(1, int(player.get("level") or 1))
        char_class = str(player.get("character_class") or "Peasant")

        self.character_title_value.set_label(f"Level {level} - Momentum Builder")
        self.character_class_value.set_label(char_class)
        self.join_date_value.set_label(str(player.get("join_date") or "Unknown"))
        self.class_badge.set_label(name)

    def _update_character_metrics(self, player: dict) -> None:
        self.quest_complete_value.set_label(str(player.get("total_quest_completed") or 0))
        self.efficiency_rating_value.set_label(f"{player.get('efficiency_rating', 0)} quests/day")
        self.streak_count_value.set_label(str(player.get("streak_count") or 0))
        self.completed_today_value.set_label(str(player.get("completed_today") or 0))
        self.skirmish_value.set_label(str(player.get("easy_quests_completed") or 0))
        self.expedition_value.set_label(str(player.get("medium_quests_completed") or 0))
        self.legendary_value.set_label(str(player.get("hard_quests_completed") or 0))

    def _build_stat_row(self, expander_row: Adw.ExpanderRow, label_text: str) -> Gtk.Label:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title = Gtk.Label(label=label_text, halign=Gtk.Align.START)
        title.set_hexpand(True)
        value = Gtk.Label()
        row.append(title)
        row.append(value)
        expander_row.add_row(row)
        return value

    def _build_task_row(
        self, task: dict, on_complete_task, *, is_focus: bool
    ) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow(title=str(task.get("name") or "Untitled Quest"))
        difficulty = int(task.get("difficulty") or 1)

        if difficulty == 3:
            row.add_css_class("task-hard")
        elif difficulty == 2:
            row.add_css_class("task-medium")
        else:
            row.add_css_class("task-easy")

        if is_focus:
            row.add_css_class("task-focus")

        tags = ", ".join(task.get("tags", []))
        recurrence = task.get("recurrence", "none")
        details = [str(task.get("description") or "No description for this task")]
        if task.get("deadline"):
            details.append(f"Deadline: {task['deadline']}")
        if recurrence and recurrence != "none":
            details.append(f"Recurs: {recurrence}")
        if tags:
            details.append(f"Tags: {tags}")

        description = Gtk.Label(
            label="\n".join(details),
            wrap=True,
            xalign=0,
        )
        description.set_margin_top(10)
        description.set_margin_bottom(10)
        description.set_margin_start(10)
        description.set_margin_end(10)
        row.add_row(description)

        finish_btn = Gtk.Button(
            icon_name="object-select-symbolic",
            label=f"+{int(task.get('reward_xp') or 0)} XP",
        )
        finish_btn.task_id = str(task.get("task_id"))
        finish_btn.reward_xp = int(task.get("reward_xp") or 0)
        finish_btn.task_difficulty = difficulty
        finish_btn.connect("clicked", on_complete_task)
        row.add_suffix(finish_btn)

        return row

    def _build_empty_state_row(self, message: str) -> Gtk.Label:
        empty_label = Gtk.Label(label=message, wrap=True, xalign=0)
        empty_label.set_margin_top(8)
        empty_label.set_margin_bottom(8)
        return empty_label

    def _set_optional_widget_visible(self, widget: Gtk.Widget, visible: bool) -> None:
        if visible and widget.get_parent() is None:
            self.header_box.append(widget)
        elif not visible and widget.get_parent() is not None:
            self.header_box.remove(widget)

    def _ensure_welcome_page(self, *, is_visible: bool) -> None:
        if is_visible:
            if self.welcome_box.get_parent() is None:
                self.stack.add_titled(self.welcome_box, "welcome", "Welcome")
            return

        if self.welcome_box.get_parent() is not None:
            self.stack.remove(self.welcome_box)

    def _ensure_lazy_pages(self) -> None:
        if self._page_cache["character"].get_parent() is None:
            self.stack.add_titled(self._page_cache["character"], "character", "Character")
        if self._page_cache["settings"].get_parent() is None:
            self.stack.add_titled(self._page_cache["settings"], "settings", "Settings")

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        css_path = self.asset_dir / "src" / "styles.css"
        provider.load_from_path(str(css_path))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
