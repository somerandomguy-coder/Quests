
"""GTK widget composition helpers for the Quests app."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
        self._task_list_mode = "flat"
        self._matrix_tasks: list[dict[str, Any]] = []
        self._matrix_points: list[dict[str, Any]] = []
        self._matrix_hover_task_id: str | None = None

    def build_window(
        self,
        application: Adw.Application,
        *,
        on_toggle_entry,
        on_import,
        on_copy_prompt,
        on_task_name_activate,
        on_task_description_activate,
        on_delete_character,
        on_create_player,
        on_magical_sort,
        on_tag_batch,
    ) -> Adw.ApplicationWindow:
        self._install_css()
        self.window = Adw.ApplicationWindow(application=application)
        self.window.set_icon_name("task-due-symbolic")
        self.window.set_title("Quests")
        self.window.set_default_size(860, 680)

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
            on_copy_prompt,
            on_task_name_activate,
            on_task_description_activate,
        )
        self._build_welcome_page(on_create_player)
        self._build_list_page(on_magical_sort, on_tag_batch)
        self._page_cache["matrix"] = self._build_matrix_page()
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
        self.prompt_btn.set_sensitive(True)
        self.magical_sort_btn.set_sensitive(False)
        self.tag_batch_btn.set_sensitive(False)
        self.delete_btn.set_sensitive(False)
        self.set_task_editor_visible(show_editor=False)
        self.clear_notice()
        self._set_task_list_mode("flat")
        self.player_name.grab_focus()
        self.stack.set_visible_child(self.welcome_box)

    def show_main_state(self) -> None:
        self._ensure_welcome_page(is_visible=False)
        self._ensure_lazy_pages()
        self.view_switcher.set_visible(True)
        self.add_btn.set_sensitive(True)
        self.import_btn.set_sensitive(True)
        self.prompt_btn.set_sensitive(True)
        self.magical_sort_btn.set_sensitive(True)
        self.tag_batch_btn.set_sensitive(True)
        self.delete_btn.set_sensitive(True)
        self.stack.set_visible_child(self.content_box)

    def update_player(self, player: dict) -> None:
        self._update_progress_display(player)
        self._update_character_identity(player)
        self._update_character_metrics(player)

    def render_tasks(self, tasks: list[dict], on_complete_task) -> None:
        self._set_task_list_mode("flat")
        self._clear_list_box(self.tasks_list)
        if not tasks:
            self._set_focus_card(None, message="Take a break, or add one gentle quest to restart momentum.")
            self.tasks_list.append(self._build_empty_state_row("No active quests. Take a rest, Adventurer!"))
            return
        self._set_focus_card(tasks[0], message="Start with the top quest to reduce choice overload, then keep the streak going.")
        for index, task in enumerate(tasks):
            self.tasks_list.append(self._build_task_row(task, on_complete_task, is_focus=index == 0))

    def render_mission_tasks(self, mission_tasks: list[dict], backlog_tasks: list[dict], on_complete_task) -> None:
        self._set_task_list_mode("mission")
        self._clear_list_box(self.current_mission_list)
        self._clear_list_box(self.quest_backlog_list)
        if mission_tasks:
            self._set_focus_card(mission_tasks[0], message="Work through this mission set at your own pace, then refresh when you are ready for the next batch.")
            for index, task in enumerate(mission_tasks):
                self.current_mission_list.append(self._build_task_row(task, on_complete_task, is_focus=index == 0))
        else:
            self._set_focus_card(None, message="No active mission right now. Press magical sorting whenever you want a fresh batch.")
            self.current_mission_list.append(self._build_empty_state_row("No quests selected for the current mission."))
        if backlog_tasks:
            for task in backlog_tasks:
                self.quest_backlog_list.append(self._build_task_row(task, on_complete_task, is_focus=False))
        else:
            self.quest_backlog_list.append(self._build_empty_state_row("No quests waiting in the backlog."))

    def render_tag_batches(self, tag_batches: list[tuple[str, list[dict]]], on_complete_task) -> None:
        self._set_task_list_mode("tags")
        while child := self.tag_batches_box.get_first_child():
            self.tag_batches_box.remove(child)
        if not tag_batches:
            self._set_focus_card(None, message="No quests available to batch right now.")
            self.tag_batches_box.append(self._build_empty_state_row("No active quests available for tag batches."))
            return
        first_tag, first_tasks = tag_batches[0]
        first_task = first_tasks[0] if first_tasks else None
        if first_task is None:
            self._set_focus_card(None, message="No quests available to batch right now.")
        else:
            self._set_focus_card(first_task, message=f"Grouped by primary tag. Current leading batch: {first_tag}.")
        for tag_name, tasks in tag_batches:
            section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            list_box = Gtk.ListBox()
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            for index, task in enumerate(tasks):
                list_box.append(self._build_task_row(task, on_complete_task, is_focus=index == 0 and tag_name == first_tag))
            section.append(list_box)
            expander = Gtk.Expander(label=f"{tag_name} ({len(tasks)})")
            expander.set_expanded(True)
            expander.set_child(section)
            self.tag_batches_box.append(expander)
    def update_matrix(self, tasks: list[dict]) -> None:
        self._matrix_tasks = list(tasks)
        self._matrix_points = []
        self._matrix_hover_task_id = None
        self.matrix_hover_label.set_label("Hover over a quest dot to inspect it.")
        self.matrix_drawing.set_tooltip_text(None)
        self.matrix_drawing.queue_draw()

    def copy_text_to_clipboard(self, text: str) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            raise RuntimeError("Clipboard is unavailable without a display.")
        display.get_clipboard().set(text)

    def get_player_name(self) -> str:
        return self.player_name.get_text()

    def set_player_name_error_visible(self, visible: bool) -> None:
        self.player_name_error.set_visible(visible)

    def get_task_name(self) -> str:
        return self.task_name_entry.get_text()

    def get_task_description(self) -> str:
        return self.task_description_entry.get_text()

    def get_task_tags(self) -> list[str]:
        raw_tags = self.task_tags_entry.get_text().strip()
        if not raw_tags:
            return []
        return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]

    def get_task_deadline(self) -> str | None:
        deadline = self.task_deadline_entry.get_text().strip()
        return deadline or None

    def get_task_importance(self) -> int:
        return self.importance_spin.get_value_as_int()

    def get_selected_difficulty(self) -> int:
        return int(self.difficulty_dropdown.get_selected()) + 1

    def clear_task_inputs(self) -> None:
        self.task_name_entry.set_text("")
        self.task_description_entry.set_text("")
        self.task_tags_entry.set_text("")
        self.task_deadline_entry.set_text("")
        self.importance_spin.set_value(50)
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
        dialog.set_body("Deleting your character will erase all your levels and legendary deeds. This cannot be undone!")
        dialog.add_response("cancel", "Keep Fighting")
        dialog.add_response("delete", "Give Up (Delete)")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.choose(self.window, None, callback, None)

    def _build_header(self, on_toggle_entry, on_import, on_copy_prompt, on_task_name_activate, on_task_description_activate) -> None:
        self.header = Adw.HeaderBar()
        self.add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self.add_btn.set_tooltip_text("Add a quest")
        self.add_btn.connect("clicked", on_toggle_entry)

        self.import_btn = Gtk.Button(icon_name="document-open-symbolic")
        self.import_btn.set_tooltip_text("Import Quest Log")
        self.import_btn.connect("clicked", on_import)

        self.prompt_btn = Gtk.Button(label="?")
        self.prompt_btn.set_tooltip_text("Click to get the prompt")
        self.prompt_btn.connect("clicked", on_copy_prompt)

        self.theme_toggle = Gtk.ToggleButton()
        self.theme_toggle.set_tooltip_text("Toggle light and dark theme")
        self.theme_toggle.connect("toggled", self._toggle_theme)

        self.task_name_entry = Gtk.Entry(placeholder_text="Enter new quest...")
        self.task_name_entry.connect("activate", on_task_name_activate)
        self.task_name_entry.set_hexpand(True)
        self.task_description_entry = Gtk.Entry(placeholder_text="Add a quick description (optional)")
        self.task_description_entry.connect("activate", on_task_description_activate)
        self.task_description_entry.set_hexpand(True)
        self.task_tags_entry = Gtk.Entry(placeholder_text="Tags: study, chores, admin")
        self.task_tags_entry.set_hexpand(True)
        self.task_deadline_entry = Gtk.Entry(placeholder_text="Deadline: YYYY-MM-DD")
        self.task_deadline_entry.set_hexpand(True)

        self.difficulty_store = Gtk.StringList.new(["Skirmish (Easy)", "Expedition (Medium)", "Legendary (Hard)"])
        self.difficulty_dropdown = Gtk.DropDown.new(self.difficulty_store, None)
        self.difficulty_dropdown.set_selected(0)
        self.importance_spin = Gtk.SpinButton.new_with_range(0, 100, 5)
        self.importance_spin.set_value(50)
        self.importance_spin.set_numeric(True)
        self.importance_spin.set_tooltip_text("How important is this quest? 0 to 100")

        importance_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        importance_label = Gtk.Label(label="Importance", xalign=0)
        importance_box.append(importance_label)
        importance_box.append(self.importance_spin)

        self.quick_add_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        row_one = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_one.append(self.task_name_entry)
        row_one.append(self.difficulty_dropdown)
        row_one.append(importance_box)
        row_two = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_two.append(self.task_description_entry)
        row_three = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_three.append(self.task_tags_entry)
        row_three.append(self.task_deadline_entry)
        self.quick_add_box.append(row_one)
        self.quick_add_box.append(row_two)
        self.quick_add_box.append(row_three)

        helper = Gtk.Label(label="Set difficulty, importance, deadline, and tags up front so magical sorting has enough signal.", xalign=0)
        helper.add_css_class("helper-text")
        self.quick_add_box.append(helper)

        self.header.pack_start(self.add_btn)
        self.header.pack_end(self.theme_toggle)
        self.header.pack_end(self.prompt_btn)
        self.header.pack_end(self.import_btn)
        self.header_box.append(self.header)
        self._sync_theme_toggle_icon()
    def _build_welcome_page(self, on_create_player) -> None:
        self.welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.welcome_box.set_margin_top(24)
        self.welcome_box.set_margin_bottom(24)
        self.welcome_box.set_margin_start(24)
        self.welcome_box.set_margin_end(24)
        self.welcome_box.set_valign(Gtk.Align.CENTER)

        title = Gtk.Label(label="Quests")
        title.set_halign(Gtk.Align.CENTER)
        subtitle = Gtk.Label(label="Start your legendary tale today, Adventurer!")
        subtitle.set_halign(Gtk.Align.CENTER)
        self.player_name = Gtk.Entry(placeholder_text="Enter your name...")
        self.player_name.connect("activate", on_create_player)
        self.player_name_error = Gtk.Label(label="Name can not be empty")
        self.player_name_error.add_css_class("error")
        self.player_name_error.set_halign(Gtk.Align.CENTER)
        self.player_name_error.set_visible(False)
        self.create_char_btn = Gtk.Button(label="Confirm")
        self.create_char_btn.set_halign(Gtk.Align.CENTER)
        self.create_char_btn.connect("clicked", on_create_player)

        self.welcome_box.append(title)
        self.welcome_box.append(subtitle)
        self.welcome_box.append(self.player_name)
        self.welcome_box.append(self.player_name_error)
        self.welcome_box.append(self.create_char_btn)

    def _build_list_page(self, on_magical_sort, on_tag_batch) -> None:
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.content_box.set_margin_top(16)
        self.content_box.set_margin_bottom(16)
        self.content_box.set_margin_start(16)
        self.content_box.set_margin_end(16)

        self.hero_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.hero_box.set_halign(Gtk.Align.CENTER)
        self.label = Gtk.Label(label="Welcome, Adventurer!")
        self.label.set_halign(Gtk.Align.CENTER)
        self.level_value = Gtk.Label()
        self.level_value.set_halign(Gtk.Align.CENTER)
        self.level_value.level_num = 1
        self.level_value.add_css_class("level-text")
        self.xp_label = Gtk.Label()
        self.xp_label.set_halign(Gtk.Align.CENTER)
        self.xp_bar = Gtk.ProgressBar()
        self.xp_bar.xp_point = 0
        self.xp_bar.set_size_request(320, -1)
        self.xp_bar.set_halign(Gtk.Align.CENTER)
        self.hero_box.append(self.label)
        self.hero_box.append(self.level_value)
        self.hero_box.append(self.xp_label)
        self.hero_box.append(self.xp_bar)

        self.notice_label = Gtk.Label(wrap=True, xalign=0)
        self.notice_label.set_visible(False)
        self.focus_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.focus_card.add_css_class("focus-card")
        self.focus_title = Gtk.Label(label="Focus quest: None yet", xalign=0)
        self.focus_detail = Gtk.Label(label="Pick one quest and finish it before switching context.", xalign=0, wrap=True)
        self.focus_detail.add_css_class("helper-text")
        self.focus_card.append(self.focus_title)
        self.focus_card.append(self.focus_detail)

        task_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.tasks_header = Gtk.Label(label="Quest Log", xalign=0)
        self.tasks_header.set_hexpand(True)
        self.magical_sort_btn = Gtk.Button(label="Magical Sorting")
        self.magical_sort_btn.connect("clicked", on_magical_sort)
        self.tag_batch_btn = Gtk.Button(label="Batch by Tags")
        self.tag_batch_btn.connect("clicked", on_tag_batch)
        task_header_box.append(self.tasks_header)
        task_header_box.append(self.tag_batch_btn)
        task_header_box.append(self.magical_sort_btn)

        self.tasks_list = Gtk.ListBox()
        self.tasks_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.current_mission_list = Gtk.ListBox()
        self.current_mission_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.quest_backlog_list = Gtk.ListBox()
        self.quest_backlog_list.set_selection_mode(Gtk.SelectionMode.NONE)

        mission_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        mission_inner.append(self.current_mission_list)
        self.current_mission_expander = Gtk.Expander(label="Current Mission")
        self.current_mission_expander.set_expanded(True)
        self.current_mission_expander.set_child(mission_inner)
        backlog_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        backlog_inner.append(self.quest_backlog_list)
        self.quest_backlog_expander = Gtk.Expander(label="Quest Backlog")
        self.quest_backlog_expander.set_expanded(True)
        self.quest_backlog_expander.set_child(backlog_inner)

        self.flat_tasks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.flat_tasks_box.append(self.tasks_list)
        self.mission_sections_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.mission_sections_box.append(self.current_mission_expander)
        self.mission_sections_box.append(self.quest_backlog_expander)
        self.tag_batches_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        self.task_scroll_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.task_scroll_content.append(self.flat_tasks_box)
        self.task_scroll_content.append(self.mission_sections_box)
        self.task_scroll_content.append(self.tag_batches_box)
        self.task_scroll = Gtk.ScrolledWindow()
        self.task_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.task_scroll.set_vexpand(True)
        self.task_scroll.set_child(self.task_scroll_content)

        self.content_box.append(self.hero_box)
        self.content_box.append(self.notice_label)
        self.content_box.append(self.focus_card)
        self.content_box.append(task_header_box)
        self.content_box.append(self.task_scroll)
        self._set_task_list_mode("flat")

    def _build_matrix_page(self) -> Gtk.Widget:
        self.matrix_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.matrix_box.set_margin_top(16)
        self.matrix_box.set_margin_bottom(16)
        self.matrix_box.set_margin_start(16)
        self.matrix_box.set_margin_end(16)
        title = Gtk.Label(label="Eisenhower Matrix", xalign=0)
        title.add_css_class("matrix-title")
        helper = Gtk.Label(label="Urgency increases from left to right. Importance increases from bottom to top.", xalign=0, wrap=True)
        helper.add_css_class("helper-text")
        self.matrix_hover_label = Gtk.Label(label="Hover over a quest dot to inspect it.", xalign=0, wrap=True)
        self.matrix_hover_label.add_css_class("helper-text")
        self.matrix_drawing = Gtk.DrawingArea()
        self.matrix_drawing.set_content_width(720)
        self.matrix_drawing.set_content_height(460)
        self.matrix_drawing.set_draw_func(self._draw_matrix)
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_matrix_motion)
        motion.connect("leave", self._on_matrix_leave)
        self.matrix_drawing.add_controller(motion)
        frame = Gtk.Frame()
        frame.set_child(self.matrix_drawing)
        self.matrix_box.append(title)
        self.matrix_box.append(helper)
        self.matrix_box.append(frame)
        self.matrix_box.append(self.matrix_hover_label)
        return self.matrix_box
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
        self.character_title_value = self._build_stat_row(identity_rank_row, "Adventurer Title:")
        self.character_class_value = self._build_stat_row(identity_rank_row, "Class:")
        self.join_date_value = self._build_stat_row(identity_rank_row, "Join Date:")
        performance_row = Adw.ExpanderRow(title="Performance Stats")
        self.quest_complete_value = self._build_stat_row(performance_row, "Total Quests Completed:")
        self.efficiency_rating_value = self._build_stat_row(performance_row, "Efficiency Rating:")
        self.streak_count_value = self._build_stat_row(performance_row, "Streak Count:")
        self.completed_today_value = self._build_stat_row(performance_row, "Quests Finished Today:")
        self.skirmish_value = self._build_stat_row(performance_row, "Number of Skirmish Quests (easy) Finished:")
        self.expedition_value = self._build_stat_row(performance_row, "Number of Expedition Quests (medium) Finished:")
        self.legendary_value = self._build_stat_row(performance_row, "Number of Legendary Quests (hard) Finished:")
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
        self.level_value.set_label(str(level))
        self.level_value.level_num = level
        self.xp_label.set_label(f"{xp}/{xp_full}")
        self.xp_bar.set_fraction(min(xp / xp_full, 1.0))
        self.xp_bar.xp_point = xp
        self.level_badge.set_label(f"Lvl {level}")

    def _update_character_identity(self, player: dict) -> None:
        name = str(player.get("name") or "Adventurer")
        level = max(1, int(player.get("level") or 1))
        char_class = str(player.get("character_class") or "Peasant")
        self.label.set_label(f"Welcome, {name}!")
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

    def _build_task_row(self, task: dict, on_complete_task, *, is_focus: bool) -> Adw.ExpanderRow:
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
        row.set_subtitle(self._build_task_meta_line(task))
        description_text = str(task.get("description") or "No description for this task")
        recurrence = task.get("recurrence", "none")
        if recurrence and recurrence != "none":
            description_text = f"{description_text}\n\nRepeats: {recurrence}"
        description = Gtk.Label(label=description_text, wrap=True, xalign=0)
        description.set_margin_top(10)
        description.set_margin_bottom(10)
        description.set_margin_start(10)
        description.set_margin_end(10)
        row.add_row(description)
        finish_btn = Gtk.Button(icon_name="object-select-symbolic", label=f"+{int(task.get('reward_xp') or 0)} XP")
        finish_btn.task_id = str(task.get("task_id"))
        finish_btn.reward_xp = int(task.get("reward_xp") or 0)
        finish_btn.task_difficulty = difficulty
        finish_btn.connect("clicked", on_complete_task)
        row.add_suffix(finish_btn)
        return row
    def _build_task_meta_line(self, task: dict) -> str:
        bits: list[str] = []
        bits.append(f"Importance {int(task.get('important_level') or 0)}")
        bits.append(f"Difficulty {self._difficulty_label(int(task.get('difficulty') or 1))}")
        deadline = task.get("deadline")
        days_until_deadline = task.get("days_until_deadline")
        if deadline:
            if days_until_deadline is None:
                bits.append(f"Due {deadline}")
            elif days_until_deadline < 0:
                bits.append(f"Overdue by {abs(int(days_until_deadline))}d")
            elif days_until_deadline == 0:
                bits.append("Due today")
            else:
                bits.append(f"Due in {int(days_until_deadline)}d")
        else:
            bits.append("No deadline")
        tags = task.get("tags") or []
        if tags:
            bits.append(f"Tags {', '.join(tags)}")
        return "  |  ".join(bits)

    def _difficulty_label(self, difficulty: int) -> str:
        if difficulty == 3:
            return "Hard"
        if difficulty == 2:
            return "Medium"
        return "Easy"

    def _set_focus_card(self, task: dict | None, *, message: str) -> None:
        if task is None:
            self.focus_title.set_label("No active quests")
            self.focus_detail.set_label(message)
            return
        self.focus_title.set_label(f"Focus quest: {task.get('name', 'Untitled Quest')}")
        self.focus_detail.set_label(message)

    def _build_empty_state_row(self, message: str) -> Gtk.Label:
        empty_label = Gtk.Label(label=message, wrap=True, xalign=0)
        empty_label.set_margin_top(8)
        empty_label.set_margin_bottom(8)
        return empty_label

    def _clear_list_box(self, list_box: Gtk.ListBox) -> None:
        while child := list_box.get_first_child():
            list_box.remove(child)

    def _set_task_list_mode(self, mode: str) -> None:
        self._task_list_mode = mode
        self.flat_tasks_box.set_visible(mode == "flat")
        self.mission_sections_box.set_visible(mode == "mission")
        self.tag_batches_box.set_visible(mode == "tags")
        if mode == "mission":
            self.tasks_header.set_label("Mission Board")
            self.magical_sort_btn.set_label("Back to Flat View")
            self.tag_batch_btn.set_label("Batch by Tags")
        elif mode == "tags":
            self.tasks_header.set_label("Tag Batches")
            self.magical_sort_btn.set_label("Magical Sorting")
            self.tag_batch_btn.set_label("Back to Flat View")
        else:
            self.tasks_header.set_label("Quest Log")
            self.magical_sort_btn.set_label("Magical Sorting")
            self.tag_batch_btn.set_label("Batch by Tags")

    def _toggle_theme(self, _widget) -> None:
        style_manager = Adw.StyleManager.get_default()
        if self.theme_toggle.get_active():
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        self._sync_theme_toggle_icon()

    def _sync_theme_toggle_icon(self) -> None:
        icon_name = "weather-clear-symbolic" if self.theme_toggle.get_active() else "weather-clear-night-symbolic"
        self.theme_toggle.set_icon_name(icon_name)

    def _draw_matrix(self, _area, cr, width: int, height: int) -> None:
        left, top, right_pad, bottom_pad = 72.0, 30.0, 30.0, 56.0
        plot_width = max(1.0, float(width) - left - right_pad)
        plot_height = max(1.0, float(height) - top - bottom_pad)
        right = left + plot_width
        bottom = top + plot_height
        mid_x = left + (plot_width / 2.0)
        mid_y = top + (plot_height / 2.0)
        cr.set_source_rgb(0.98, 0.98, 0.97)
        cr.paint()
        for color, rx, ry in [((0.93, 0.78, 0.36, 0.12), left, top), ((0.88, 0.43, 0.33, 0.10), mid_x, top), ((0.26, 0.62, 0.56, 0.10), left, mid_y), ((0.18, 0.30, 0.44, 0.08), mid_x, mid_y)]:
            cr.set_source_rgba(*color)
            cr.rectangle(rx, ry, plot_width / 2.0, plot_height / 2.0)
            cr.fill()
        cr.set_source_rgb(0.35, 0.35, 0.35)
        cr.set_line_width(2.0)
        cr.rectangle(left, top, plot_width, plot_height)
        cr.stroke()
        cr.move_to(mid_x, top)
        cr.line_to(mid_x, bottom)
        cr.move_to(left, mid_y)
        cr.line_to(right, mid_y)
        cr.stroke()
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(13)
        for tx, ty, label in [(left + 12, top + 22, "Schedule"), (mid_x + 12, top + 22, "Do Now"), (left + 12, mid_y + 22, "Delegate"), (mid_x + 12, mid_y + 22, "Reduce")]:
            cr.move_to(tx, ty)
            cr.show_text(label)
        cr.set_font_size(12)
        cr.move_to(left, top - 8)
        cr.show_text("Importance")
        cr.move_to(right - 70, bottom + 28)
        cr.show_text("Urgency")
        self._matrix_points = []
        for task in self._matrix_tasks:
            urgency = max(0, min(100, int(task.get("urgency_score") or 0)))
            importance = max(0, min(100, int(task.get("important_level") or 0)))
            x = left + (urgency / 100.0) * plot_width
            y = bottom - (importance / 100.0) * plot_height
            radius = 8.0 if str(task.get("task_id")) == self._matrix_hover_task_id else 6.0
            self._matrix_points.append({"task_id": str(task.get("task_id")), "name": str(task.get("name") or "Untitled Quest"), "x": x, "y": y, "radius": radius})
            self._draw_matrix_dot(cr, task, x, y, radius)

    def _draw_matrix_dot(self, cr, task: dict, x: float, y: float, radius: float) -> None:
        difficulty = int(task.get("difficulty") or 1)
        color = (0.91, 0.43, 0.32) if difficulty == 3 else (0.91, 0.77, 0.42) if difficulty == 2 else (0.16, 0.62, 0.56)
        cr.set_source_rgb(*color)
        cr.new_sub_path()
        cr.arc(x, y, radius, 0, 6.28318530718)
        cr.fill_preserve()
        cr.set_source_rgb(1, 1, 1)
        cr.set_line_width(1.5)
        cr.stroke()
    def _on_matrix_motion(self, _controller, x: float, y: float) -> None:
        hovered = None
        for point in self._matrix_points:
            dx = float(point["x"]) - x
            dy = float(point["y"]) - y
            threshold = float(point["radius"]) + 5.0
            if (dx * dx) + (dy * dy) <= threshold * threshold:
                hovered = point
                break
        hovered_task_id = hovered["task_id"] if hovered else None
        if hovered_task_id == self._matrix_hover_task_id:
            return
        self._matrix_hover_task_id = hovered_task_id
        if hovered is None:
            self.matrix_hover_label.set_label("Hover over a quest dot to inspect it.")
            self.matrix_drawing.set_tooltip_text(None)
        else:
            self.matrix_hover_label.set_label(f"Hovering: {hovered['name']}")
            self.matrix_drawing.set_tooltip_text(str(hovered["name"]))
        self.matrix_drawing.queue_draw()

    def _on_matrix_leave(self, _controller) -> None:
        if self._matrix_hover_task_id is None:
            return
        self._matrix_hover_task_id = None
        self.matrix_hover_label.set_label("Hover over a quest dot to inspect it.")
        self.matrix_drawing.set_tooltip_text(None)
        self.matrix_drawing.queue_draw()

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
        if self._page_cache["matrix"].get_parent() is None:
            self.stack.add_titled(self._page_cache["matrix"], "matrix", "Matrix")
        if self._page_cache["character"].get_parent() is None:
            self.stack.add_titled(self._page_cache["character"], "character", "Character")
        if self._page_cache["settings"].get_parent() is None:
            self.stack.add_titled(self._page_cache["settings"], "settings", "Settings")

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        css_path = self.asset_dir / "src" / "styles.css"
        provider.load_from_path(str(css_path))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
