#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi

gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GimpUi, Gtk, Pango


COLOR_TEMPERATURE_PRESETS = (
    ("晴れた日の外", 5500.0, 6500.0),
    ("薄曇りの外", 6250.0, 7250.0),
    ("曇りの日の外", 7000.0, 8000.0),
    ("晴れた日の日陰", 8000.0, 9000.0),
)

DEFAULT_COLOR_TEMPERATURE_PRESET = 1


class MessageDialog(GimpUi.Dialog):
    def __init__(self, title, role, message, default_response=None):
        super().__init__(use_header_bar=False, title=title, role=role)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._box_settings(box)

        self._create_buttons()

        label = self._create_message_label(message, font_size=12)

        if default_response is not None:
            self.set_default_response(default_response)

        box.pack_start(label, True, True, 0)
        self.get_content_area().add(box)
        self.show_all()

    def _box_settings(self, box):
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

    def _create_buttons(self):
        self.add_button("キャンセル", Gtk.ResponseType.CANCEL)
        self.add_button("OK", Gtk.ResponseType.OK)

    def _create_message_label(self, message, font_size):
        label = Gtk.Label(label=message)
        label.set_line_wrap(True)

        if font_size is not None:
            attrs = Pango.AttrList()
            attrs.insert(Pango.attr_size_new(int(font_size * Pango.SCALE)))
            label.set_attributes(attrs)

        return label


class SakuraSettingsDialog(GimpUi.Dialog):
    """Sakura Retouchの簡単調整ダイアログ。"""

    def __init__(self, title, role, initial_settings, on_settings_changed=None):
        super().__init__(use_header_bar=False, title=title, role=role)

        self.on_settings_changed = on_settings_changed
        self.set_default_size(640, -1)
        self.add_button("キャンセル", Gtk.ResponseType.CANCEL)
        self.add_button("実行", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        self.environment_combo = Gtk.ComboBoxText()
        for name, _original, _intended in COLOR_TEMPERATURE_PRESETS:
            self.environment_combo.append_text(name)
        self.environment_combo.set_active(DEFAULT_COLOR_TEMPERATURE_PRESET)

        original_temperature_control, self.original_temperature = (
            self._create_numeric_control(1000.0, 12000.0, 100.0, 0)
        )
        intended_temperature_control, self.intended_temperature = (
            self._create_numeric_control(1000.0, 12000.0, 100.0, 0)
        )
        gamma_gp_control, self.gamma_gp = self._create_numeric_control(
            0.10, 5.00, 0.01, 2
        )
        white_clip_control, self.white_clip = self._create_numeric_control(
            0.01, 1.00, 0.01, 2
        )
        black_lift_control, self.black_lift = self._create_numeric_control(
            0.00, 0.25, 0.01, 2
        )

        self._attach_row(grid, 0, "撮影環境", self.environment_combo)
        self._attach_row(grid, 1, "元の色温度 (K)", original_temperature_control)
        self._attach_row(grid, 2, "仕上がり色温度 (K)", intended_temperature_control)
        self._attach_row(grid, 3, "GMA GP", gamma_gp_control)
        self._attach_row(grid, 4, "White Clip", white_clip_control)
        self._attach_row(grid, 5, "Black Lift", black_lift_control)

        self._on_environment_changed(self.environment_combo)
        self.original_temperature.set_value(initial_settings["original_temperature"])
        self.intended_temperature.set_value(initial_settings["intended_temperature"])
        self.gamma_gp.set_value(initial_settings["gamma_gp"])
        self.white_clip.set_value(initial_settings["white_clip"])
        self.black_lift.set_value(initial_settings["black_lift"])

        self.environment_combo.connect("changed", self._on_environment_changed)
        for widget, setting_name in (
            (self.original_temperature, "original_temperature"),
            (self.intended_temperature, "intended_temperature"),
            (self.gamma_gp, "gamma_gp"),
            (self.white_clip, "white_clip"),
            (self.black_lift, "black_lift"),
        ):
            widget.connect(
                "value-changed", self._on_setting_changed, setting_name
            )

        box.pack_start(grid, True, True, 0)
        self.get_content_area().add(box)
        self.show_all()

    def _create_numeric_control(self, lower, upper, step, digits):
        adjustment = Gtk.Adjustment(
            value=lower,
            lower=lower,
            upper=upper,
            step_increment=step,
            page_increment=step * 10,
            page_size=0.0,
        )

        scale = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, adjustment)
        scale.set_draw_value(False)
        scale.set_hexpand(True)

        spin = Gtk.SpinButton.new(adjustment, step, digits)
        spin.set_numeric(True)
        spin.set_width_chars(7)

        control = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        control.pack_start(scale, True, True, 0)
        control.pack_start(spin, False, False, 0)
        return control, spin

    def _attach_row(self, grid, row, text, widget):
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        widget.set_hexpand(True)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)

    def _on_environment_changed(self, combo):
        preset_index = combo.get_active()
        if preset_index < 0:
            return

        _name, original, intended = COLOR_TEMPERATURE_PRESETS[preset_index]
        self.original_temperature.set_value(original)
        self.intended_temperature.set_value(intended)

    def _on_setting_changed(self, _widget, setting_name):
        if self.on_settings_changed is not None:
            self.on_settings_changed(self.get_settings(), setting_name)

    def get_settings(self):
        return {
            "original_temperature": self.original_temperature.get_value(),
            "intended_temperature": self.intended_temperature.get_value(),
            "gamma_gp": self.gamma_gp.get_value(),
            "white_clip": self.white_clip.get_value(),
            "black_lift": self.black_lift.get_value(),
        }


def run_message_dialog( binary_name, title, role, message, default_response=None,):
    GimpUi.init(binary_name)

    dialog = MessageDialog( title=title, role=role, message=message, default_response=default_response,)

    response = dialog.run()
    dialog.destroy()

    return response


def confirm_selected_layer(binary_name, proc_name, layer):
    """選択中のレイヤーで処理していいか確認するダイアログを表示する関数"""

    response = run_message_dialog(
        binary_name,
        "Sakura Retouch",
        proc_name,
        f"選択中のレイヤー「{layer.get_name()}」に Sakura Retouch を実行しますか？",
        Gtk.ResponseType.OK,
    )

    return response == Gtk.ResponseType.OK


def run_sakura_settings_dialog(
    binary_name, proc_name, initial_settings, on_settings_changed=None
):
    """簡単調整ダイアログを表示し、キャンセル時はNoneを返す。"""

    GimpUi.init(binary_name)
    dialog = SakuraSettingsDialog(
        "Sakura Retouch - 画質調整",
        proc_name,
        initial_settings,
        on_settings_changed,
    )

    response = dialog.run()
    settings = dialog.get_settings() if response == Gtk.ResponseType.OK else None
    dialog.destroy()

    return settings
