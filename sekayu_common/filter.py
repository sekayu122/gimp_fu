#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi

gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gimp

def apply_gegl_filter(layer, operation, name, props):
    """レイヤーにGEGLフィルタを適用する関数"""

    f = Gimp.DrawableFilter.new(layer, operation, name)
    config = f.get_config()
    for key, value in props.items():
        config.set_property(key, value)
    layer.append_filter(f)
    layer.merge_filters()
    
    return f