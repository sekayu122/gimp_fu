#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi

gi.require_version("GimpUi", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gimp

def apply_gegl_filter(layer, operation, name, props, merge=True):
    """レイヤーにGEGLフィルタを適用する関数"""

    f = Gimp.DrawableFilter.new(layer, operation, name)
    config = f.get_config()
    for key, value in props.items():
        try:
            config.set_property(key, value)
        except Exception as error:
            raise RuntimeError(f"{operation}.{key}: {error}") from error
    layer.append_filter(f)
    if merge:
        layer.merge_filters()
    
    return f


def build_gamma_curve(gamma, samples, white_point=1.0, black_lift=0.0):
    """黒点と中間調を持ち上げ、指定した白点以上をクリップするGMAカーブを作成する。"""

    curve = Gimp.Curve.new()
    curve.set_curve_type(Gimp.CurveType.FREE)
    curve.set_n_samples(samples)

    for i in range(samples):
        x = i / (samples - 1)
        gamma_value = min(1.0, (x / white_point) ** (1.0 / gamma))
        value = black_lift + (1.0 - black_lift) * gamma_value
        curve.set_sample(x, value)

    return curve


def add_filter(layer, curve):
    """フィルタオブジェクトを作成する関数"""
    filter = Gimp.DrawableFilter.new(layer, "gimp:curves", "Highkey GMA curve")
    cfg = filter.get_config()
    cfg.set_property("curve", curve)
    cfg.set_property("channel", Gimp.HistogramChannel.VALUE)
    cfg.set_property("trc", Gimp.TRCType.NON_LINEAR)
    layer.append_filter(filter)
    return filter
