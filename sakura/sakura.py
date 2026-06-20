#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

# Gitのバージョン指定
import gi
gi.require_version("Gimp", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gimp, GLib, Gtk

# プラグインのルートディレクトリをsys.pathに追加(commonモジュールのインポートのため)
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from sekayu_common.dialog import (
    COLOR_TEMPERATURE_PRESETS,
    DEFAULT_COLOR_TEMPERATURE_PRESET,
    run_sakura_settings_dialog,
)
from sekayu_common.filter import add_filter, apply_gegl_filter, build_gamma_curve

# GIMPに登録するprocedureの名前
PROC_NAME = "plug-in-sakura"

# 実行ファイル名（UIの初期化用）
BINARY_NAME = "sakura.py"

DEFAULT_GAMMA_GP = 1.50
DEFAULT_WHITE_CLIP = 0.85
DEFAULT_BLACK_LIFT = 0.03
GAMMA_CURVE_SAMPLES = 256
DEFAULT_DETAIL_ENHANCE_SETTINGS = {
    "std-dev": 1.2,
    "scale": 0.35,
    "threshold": 0.02,
}
DEFAULT_FOCUS_BLUR_SETTINGS = {
    "blur_radius": 40.0,
    "x": 0.5,
    "y": 0.5,
    "radius": 0.7,
    "focus": 0.25,
    "midpoint": 0.45,
    "highlight_factor": 0.5,
    "highlight_threshold_low": 0.8,
    "highlight_threshold_high": 1.0,
    "opacity": 60.0,
}


def get_default_settings():
    """非対話実行時に利用する初期設定を返す。"""

    _name, original, intended = COLOR_TEMPERATURE_PRESETS[
        DEFAULT_COLOR_TEMPERATURE_PRESET
    ]
    return {
        "original_temperature": original,
        "intended_temperature": intended,
        "gamma_gp": DEFAULT_GAMMA_GP,
        "white_clip": DEFAULT_WHITE_CLIP,
        "black_lift": DEFAULT_BLACK_LIFT,
    }


def create_effect_layer(image, source_layer, parent, name, insert_above=None):
    """複製元のfxを焼き込み、新しいfxグループ用レイヤーを作成する。"""

    layer = source_layer.copy()
    layer.set_name(name)
    insert_above = insert_above or source_layer
    image.insert_layer(layer, parent, image.get_item_position(insert_above))
    if layer.get_filters():
        layer.merge_filters()
    return layer


def add_background_adjustments(layer, settings):
    """背景色レイヤーへ画質調整フィルタを追加し、ライブ更新対象を返す。"""

    curve = build_gamma_curve(
        settings["gamma_gp"],
        GAMMA_CURVE_SAMPLES,
        white_point=settings["white_clip"],
        black_lift=settings["black_lift"],
    )
    curve_filter = add_filter(layer, curve)

    temperature_filter = apply_gegl_filter(
        layer,
        "gegl:color-temperature",
        "Spring warm color temperature",
        {
            "original-temperature": settings["original_temperature"],
            "intended-temperature": settings["intended_temperature"],
        },
        merge=False,
    )
    apply_gegl_filter(
        layer,
        "gimp:hue-saturation",
        "Spring master hue saturation",
        {
            "range": Gimp.HueRange.ALL,
            "hue": 0.0,
            "lightness": 0.0,
            "saturation": -5.0,
            "overlap": 0.0,
        },
        merge=False,
    )
    apply_gegl_filter(
        layer,
        "gimp:hue-saturation",
        "Spring green hue saturation",
        {
            "range": Gimp.HueRange.GREEN,
            "hue": 0.0,
            "lightness": 10.0,
            "saturation": -25.0,
            "overlap": 0.0,
        },
        merge=False,
    )
    return curve_filter, temperature_filter


def add_detail_enhance(layer):
    """確定後の背景色レイヤーへ細部強調フィルターを追加する。"""

    apply_gegl_filter(
        layer,
        "gegl:unsharp-mask",
        "Spring detail enhance",
        DEFAULT_DETAIL_ENHANCE_SETTINGS,
        merge=False,
    )


def update_background_preview(
    curve_filter, temperature_filter, settings, setting_name
):
    """変更された項目に対応する背景フィルターだけを更新する。"""

    if setting_name in {"gamma_gp", "white_clip", "black_lift"}:
        curve = build_gamma_curve(
            settings["gamma_gp"],
            GAMMA_CURVE_SAMPLES,
            white_point=settings["white_clip"],
            black_lift=settings["black_lift"],
        )
        curve_filter.get_config().set_property("curve", curve)
        curve_filter.update()
    elif setting_name in {"original_temperature", "intended_temperature"}:
        temperature_config = temperature_filter.get_config()
        temperature_config.set_property(
            "original-temperature", settings["original_temperature"]
        )
        temperature_config.set_property(
            "intended-temperature", settings["intended_temperature"]
        )
        temperature_filter.update()

    Gimp.displays_flush()


def add_focus_blur(layer, settings):
    """背景ぼかしレイヤーへ焦点ぼかしフィルタを追加する。"""

    apply_gegl_filter(
        layer,
        "gegl:focus-blur",
        "Background gentle focus blur",
        {
            "blur-type": "lens",
            "blur-radius": settings["blur_radius"],
            "x": settings["x"],
            "y": settings["y"],
            "radius": settings["radius"],
            "focus": settings["focus"],
            "midpoint": settings["midpoint"],
            "highlight-factor": settings["highlight_factor"],
            "highlight-threshold-low": settings["highlight_threshold_low"],
            "highlight-threshold-high": settings["highlight_threshold_high"],
        },
        merge=False,
    )
    layer.set_mode(Gimp.LayerMode.SOFTLIGHT)
    layer.set_opacity(settings["opacity"])


def create_derived_effect_layers(image, background_color_layer, parent):
    """背景色レイヤーから、ぼかしと光の派生レイヤーを作成する。"""

    background_blur_layer = create_effect_layer(
        image,
        background_color_layer,
        parent,
        "02 Background blur",
    )
    focus_blur_settings = DEFAULT_FOCUS_BLUR_SETTINGS.copy()
    add_focus_blur(background_blur_layer, focus_blur_settings)

    light_layer = create_effect_layer(
        image,
        background_color_layer,
        parent,
        "03 soft glow(gauussian + screen)",
        insert_above=background_blur_layer,
    )
    apply_gegl_filter(
        light_layer,
        "gegl:gaussian-blur",
        "Soft glow gaussian blur",
        {"std-dev-x": 18.0, "std-dev-y": 18.0},
        merge=False,
    )
    light_layer.set_mode(Gimp.LayerMode.SCREEN)
    light_layer.set_opacity(10.0)

    return [background_blur_layer, light_layer]


def run(procedure, run_mode, image, drawables, config, data):
    """
    GIMPのprocedureが呼び出されたときに実行される関数
    [args]
    procedure: 実行中のGimp.Procedureオブジェクト, return生成に利用
    run_mode: Gimp.RunMode
        - INTERACTIVE: 通常のGIMPメニューからの呼び出し
        - NONINTERACTIVE: コマンド、スクリプトからの呼び出しなど
        - WITH_LAST_VALS: "前回の値で実行"の呼び出し
    image: 処理対象のGimp.Imageオブジェクト
    drawables: 処理対象のGimp.Drawableオブジェクトのリスト
        - 選択中のレイヤー等
    config: procedureの設定値
        - フォント設定など
    data: procedureの追加データ
        - 今回はNoneを指定
    """
    
    #################################
    # 呼び出し状況確認
    #################################
    
    # 選択したdrawablesがない場合
    if len(drawables) == 0:
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Procedure '{PROC_NAME}' requires one selected layer."),
        )
    # 選択したdrawablesが複数個ある場合
    if len(drawables) > 1:
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Procedure '{PROC_NAME}' works with one layer only."),
        )
    # 選択したdrawablesがレイヤーではない場合
    if not isinstance(drawables[0], Gimp.Layer):
        return procedure.new_return_values(
            Gimp.PDBStatusType.CALLING_ERROR,
            GLib.Error(f"Procedure '{PROC_NAME}' works with layers only."),
        )
    parent = drawables[0].get_parent()
    # 通常の呼び出し
    # if run_mode == Gimp.RunMode.INTERACTIVE:
    #     # 選択したレイヤーで処理していいか確認
    #     if not confirm_selected_layer(BINARY_NAME, PROC_NAME, drawables[0]):
    #         return procedure.new_return_values(
    #             Gimp.PDBStatusType.CANCEL,
    #             GLib.Error("ユーザーが処理をキャンセルしました。")
    #         )
            
    # 処理対象レイヤー
    base_layer = drawables[0]

    settings = get_default_settings()
    image.undo_group_start()
    try:

        #################################
        # レイヤー処理
        #################################

        ### 01. 背景の明るさと春らしい色味をまとめて調整 ###
        background_color_layer = create_effect_layer(
            image, base_layer, parent, "01 Background color"
        )
        curve_filter, temperature_filter = add_background_adjustments(
            background_color_layer, settings
        )

        if run_mode != Gimp.RunMode.INTERACTIVE:
            add_detail_enhance(background_color_layer)

        ### 02・03. 軽量プレビューを作ってから画質調整ダイアログを表示 ###
        derived_layers = create_derived_effect_layers(
            image, background_color_layer, parent
        )
        Gimp.displays_flush()

        if run_mode == Gimp.RunMode.INTERACTIVE:
            settings = run_sakura_settings_dialog(
                BINARY_NAME,
                PROC_NAME,
                settings,
                lambda changed_settings, setting_name: update_background_preview(
                    curve_filter,
                    temperature_filter,
                    changed_settings,
                    setting_name,
                ),
            )
            if settings is None:
                for layer in reversed(derived_layers):
                    image.remove_layer(layer)
                image.remove_layer(background_color_layer)
                Gimp.displays_flush()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, None)

            add_detail_enhance(background_color_layer)

            # プレビュー中は重い派生処理を行わず、確定後に一度だけ作り直す。
            for layer in reversed(derived_layers):
                image.remove_layer(layer)
            derived_layers[:] = create_derived_effect_layers(
                image, background_color_layer, parent
            )
    except Exception as error:
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error(f"Procedure '{PROC_NAME}' failed: {error}"),
        )
    finally:
        image.undo_group_end()

    Gimp.displays_flush()

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, None)


class SakuraRetouch(Gimp.PlugIn):
    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        
        # 正しい呼び出しのみ処理を実施
        if not name == PROC_NAME:
            return None

        # procedure生成
        procedure = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, run, None
        )
        
        # プラグインを有効にする条件を指定
        procedure.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE # レイヤーなどが選択されているときのみ有効
            # | Gimp.ProcedureSensitivityMask.NO_DRAWABLES # ORで条件を追加可能
        )
        
        # プラグイン設定
        procedure.set_menu_label("Sekayu Retouch")
        procedure.set_attribution("Sekayu", "Sekayu GIMP Retouch project", "2026")
        procedure.add_menu_path("<Image>/Filters/Sekayu")
        procedure.set_documentation(
            "桜の写真をエモい雰囲気にする。",
            "スクリーン合成、ソフトグロー、青空強調を行います。",
            None,
        )

        return procedure


Gimp.main(SakuraRetouch.__gtype__, sys.argv)
