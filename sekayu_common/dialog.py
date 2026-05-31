#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi

gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import GimpUi, Gtk, Pango


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