from __future__ import annotations

from pathlib import Path
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw

import database
import engine
from parser import parse_markdown_quests
from ui_manager import QuestUIManager


class App(Adw.Application):
    """Application coordinator for Quests.

    UI construction lives in `ui_manager.py`, while persistence and progression
    stay in their own modules. This keeps `main.py` focused on orchestration.
    """

    def __init__(self):
        super().__init__(application_id="com.namle.Quests")

        self.project_root = Path(__file__).resolve().parent.parent
        self.database_path = Path(__file__).resolve().with_name("database.db")
        self.db = database.DatabaseConnection(self.database_path)
        self.ui = QuestUIManager(self.project_root)

        self.window = None
        self.player: dict | None = None
        self.player_id: str | None = None

    def do_activate(self):
        if self.window is None:
            self._bootstrap_app()
        self.window.present()

    def _bootstrap_app(self) -> None:
        self.db.bootstrap()
        self.window = self.ui.build_window(
            self,
            on_toggle_entry=self._toggle_task_entry,
            on_import=self._import_tasks,
            on_task_name_activate=self._toggle_task_description,
            on_task_description_activate=self._create_task,
            on_delete_character=self._open_delete_message_dialog,
            on_create_player=self._create_player,
        )
        self._refresh_app_state()

    def _refresh_app_state(self) -> None:
        self.player = self.db.fetch_player()
        if self.player is None:
            self.player_id = None
            self.ui.show_welcome_state()
            return

        self.player_id = str(self.player["playerID"])
        self.ui.show_main_state()
        self._load_player_state()
        self._load_task_list()

    def _load_player_state(self) -> None:
        self.player = self.db.fetch_player()
        if self.player is None:
            self.player_id = None
            self.ui.show_welcome_state()
            return

        self.player_id = str(self.player["playerID"])
        self.ui.update_player(self.player)

    def _load_task_list(self) -> None:
        if self.player_id is None:
            self.ui.render_tasks([], self._complete_task)
            return

        tasks = self.db.fetch_unfinished_tasks(self.player_id)
        self.ui.render_tasks(tasks, self._complete_task)

    def _create_player(self, _widget) -> None:
        name = self.ui.get_player_name().strip()
        if not name:
            self.ui.set_player_name_error_visible(True)
            return

        self.ui.set_player_name_error_visible(False)
        self.db.add_player(name)
        self._refresh_app_state()

    def _import_tasks(self, _widget) -> None:
        if self.player_id is None:
            return

        self.ui.clear_notice()
        self.ui.open_import_dialog(self._finish_import_tasks)

    def _finish_import_tasks(self, source, result) -> None:
        try:
            selected_file = source.open_finish(result)
            if selected_file is None:
                return

            file_path = selected_file.get_path()
            if not file_path:
                self.ui.show_notice(
                    "Import failed: the selected file has no local path.",
                    error=True,
                )
                return

            quests = parse_markdown_quests(file_path)
            imported_count = self.db.add_multiple_new_task(self.player_id, quests)

            if imported_count == 0:
                self.ui.show_notice(
                    "No valid quests were found in that markdown file.",
                    error=True,
                )
                return

            self._load_task_list()
            self.ui.show_notice(f"Imported {imported_count} quest(s).")
        except Exception as error:
            self.ui.show_notice(f"Import failed: {error}", error=True)

    def _toggle_task_entry(self, _widget) -> None:
        if self.player_id is None:
            return

        if self.ui.is_task_entry_visible():
            self.ui.set_task_editor_visible(show_entry=False, show_description=False)
            return

        self.ui.clear_notice()
        self.ui.set_task_editor_visible(show_entry=True, show_description=False)

    def _toggle_task_description(self, _widget) -> None:
        if self.player_id is None:
            return

        if not self.ui.get_task_name().strip():
            self.ui.show_notice("Quest name can not be empty.", error=True)
            return

        self.ui.clear_notice()
        self.ui.set_task_editor_visible(show_entry=True, show_description=True)

    def _create_task(self, _widget) -> None:
        if self.player_id is None:
            return

        raw_task_name = self.ui.get_task_name()
        cleaned_task_name, difficulty, reward_xp = self._resolve_difficulty(raw_task_name)
        description = self.ui.get_task_description().strip()

        if not cleaned_task_name:
            self.ui.show_notice("Quest name can not be empty.", error=True)
            return

        self.db.add_new_task(
            self.player_id,
            cleaned_task_name,
            difficulty=difficulty,
            description=description,
            reward_xp=reward_xp,
        )
        self.ui.clear_task_inputs()
        self.ui.set_task_editor_visible(show_entry=False, show_description=False)
        self._load_task_list()
        self.ui.show_notice("Quest added.")

    def _complete_task(self, widget) -> None:
        if self.player is None or self.player_id is None:
            return

        current_level = max(1, int(self.player.get("level") or 1))
        current_xp = max(0, int(self.player.get("XP") or 0))
        xp_gain = max(0, int(getattr(widget, "reward_xp", 0)))

        new_level, new_xp = engine.calculate_xp_gain(
            xp_gain,
            current_level,
            current_xp,
        )
        self.db.complete_task(widget.task_id, self.player_id, new_xp, new_level)
        self._load_player_state()
        self._load_task_list()
        self.ui.show_notice(f"Quest completed. You gained {xp_gain} XP.")

    def _open_delete_message_dialog(self, _widget) -> None:
        if self.player_id is None:
            return

        self.ui.present_delete_dialog(self._on_delete_response)

    def _on_delete_response(self, dialog, response_id, _data) -> None:
        response = dialog.choose_finish(response_id)
        if response != "delete" or self.player_id is None:
            return

        self.db.delete_character(self.player_id)
        self._refresh_app_state()

    def _resolve_difficulty(self, task_name: str) -> tuple[str, int, int]:
        trimmed_name = task_name.strip()

        # TODO: Replace these inline shortcuts with an explicit UI control later.
        if trimmed_name.endswith("/h"):
            return trimmed_name[:-2].strip(), 3, 100
        if trimmed_name.endswith("/m"):
            return trimmed_name[:-2].strip(), 2, 50
        return trimmed_name, 1, 10


if __name__ == "__main__":
    app = App()
    app.run(sys.argv)
