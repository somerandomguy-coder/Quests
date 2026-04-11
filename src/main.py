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
    """Application coordinator for Quests."""

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

        self.player_id = str(self.player["player_id"])
        self.ui.show_main_state()
        self._load_player_state()
        self._load_task_list()

    def _load_player_state(self) -> None:
        self.player = self.db.fetch_player()
        if self.player is None:
            self.player_id = None
            self.ui.show_welcome_state()
            return

        self.player_id = str(self.player["player_id"])
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

            import_result = parse_markdown_quests(file_path)
            imported_count = self.db.add_multiple_new_task(self.player_id, import_result.quests)

            if imported_count == 0:
                if import_result.issues:
                    self.ui.show_notice(import_result.issues[0].message, error=True)
                else:
                    self.ui.show_notice(
                        "No valid quests were found in that markdown file.",
                        error=True,
                    )
                return

            self._load_task_list()
            if import_result.warning_count:
                self.ui.show_notice(
                    f"Imported {imported_count} quest(s) with {import_result.warning_count} warning(s)."
                )
            else:
                self.ui.show_notice(f"Imported {imported_count} quest(s).")
        except Exception as error:
            self.ui.show_notice(f"Import failed: {error}", error=True)

    def _toggle_task_entry(self, _widget) -> None:
        if self.player_id is None:
            return

        if self.ui.is_task_entry_visible():
            self.ui.set_task_editor_visible(show_editor=False)
            return

        self.ui.clear_notice()
        self.ui.set_task_editor_visible(show_editor=True)

    def _toggle_task_description(self, _widget) -> None:
        if self.player_id is None:
            return

        if not self.ui.get_task_name().strip():
            self.ui.show_notice("Quest name can not be empty.", error=True)
            return

        self._create_task(_widget)

    def _create_task(self, _widget) -> None:
        if self.player_id is None:
            return

        task_name = self.ui.get_task_name().strip()
        description = self.ui.get_task_description().strip()
        difficulty = self.ui.get_selected_difficulty()
        reward_xp = self._reward_for_difficulty(difficulty)

        if not task_name:
            self.ui.show_notice("Quest name can not be empty.", error=True)
            return

        self.db.add_new_task(
            self.player_id,
            task_name,
            difficulty=difficulty,
            description=description,
            reward_xp=reward_xp,
        )
        self.ui.clear_task_inputs()
        self.ui.set_task_editor_visible(show_editor=False)
        self._load_task_list()
        self.ui.show_notice("Quest added.")

    def _complete_task(self, widget) -> None:
        if self.player is None or self.player_id is None:
            return

        current_level = max(1, int(self.player.get("level") or 1))
        current_xp = max(0, int(self.player.get("xp") or 0))
        streak_count = max(0, int(self.player.get("streak_count") or 0))
        completed_today = max(0, int(self.player.get("completed_today") or 0))

        xp_gain = engine.calculate_reward_xp(
            int(getattr(widget, "reward_xp", 0)),
            difficulty=int(getattr(widget, "task_difficulty", 1)),
            streak_count=streak_count,
            completed_today=completed_today,
        )
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

    def _reward_for_difficulty(self, difficulty: int) -> int:
        if difficulty == 3:
            return 100
        if difficulty == 2:
            return 50
        return 10


if __name__ == "__main__":
    app = App()
    app.run(sys.argv)
