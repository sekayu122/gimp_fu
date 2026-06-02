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

from sekayu_common.dialog import confirm_selected_layer
from sekayu_common.filter import apply_gegl_filter

# GIMPに登録するprocedureの名前
PROC_NAME = "plug-in-sakura"

# 実行ファイル名（UIの初期化用）
BINARY_NAME = "sakura.py"

HIGHKEY_GAMMA = 1.45
HIGHKEY_CURVE_SAMPLES = 256


def build_gamma_curve(gamma, samples):
    """GMAカーブ用の明るめトーンカーブオブジェクトを作成する。"""

    curve = Gimp.Curve.new()
    curve.set_curve_type(Gimp.CurveType.FREE)
    curve.set_n_samples(samples)

    for i in range(samples):
        x = i / (samples - 1)
        curve.set_sample(x, x ** (1.0 / gamma))

    return curve


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
    position = image.get_item_position(drawables[0])
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

    #################################
    # レイヤー処理
    #################################
    
    ### 1. 全体を明るくハイキーに ###
    # GMAカーブで明るくしたレイヤーを通常合成で重ねる
    bright_layer = base_layer.copy()
    bright_layer.set_name("Highkey brightness")
    image.insert_layer(bright_layer, parent, position)

    highkey_curve = build_gamma_curve(HIGHKEY_GAMMA, HIGHKEY_CURVE_SAMPLES)
    highkey_filter = Gimp.DrawableFilter.new(bright_layer, "gimp:curves", "Highkey GMA curve")
    highkey_config = highkey_filter.get_config()
    highkey_config.set_property("curve", highkey_curve)
    highkey_config.set_property("channel", Gimp.HistogramChannel.VALUE)
    highkey_config.set_property("trc", Gimp.TRCType.NON_LINEAR)
    bright_layer.append_filter(highkey_filter)

    bright_layer.set_mode(Gimp.LayerMode.NORMAL)
    bright_layer.set_opacity(25.0) # 不透明度
    
    ### 2. ふわっとした桜の光 ###
    # Gaussioan Blurでぼかしたレイヤーを作成
    glow_layer = base_layer.copy()
    glow_layer.set_name("Soft sakura glow")
    image.insert_layer(glow_layer, base_layer.get_parent(), image.get_item_position(bright_layer))

    apply_gegl_filter(
        glow_layer,
        "gegl:focus-blur",
        "Soft focus glow blur",
        {
            "blur-type": "lens",
            "blur-radius": 34.0,
            "x": 0.5,
            "y": 0.5,
            "radius": 0.62,
            "focus": 0.16,
            "midpoint": 0.32,
            "highlight-factor": 1.7,
            "highlight-threshold-low": 0.72,
            "highlight-threshold-high": 1.0,
        },
        merge=False,
    )

    glow_layer.set_mode(Gimp.LayerMode.SCREEN)
    glow_layer.set_opacity(20.0)

    ### 3. 青空を青く戻す ###
    sky_layer = base_layer.copy()
    sky_layer.set_name("Blue sky restore")
    image.insert_layer(sky_layer, base_layer.get_parent(), image.get_item_position(glow_layer))

    apply_gegl_filter(
        sky_layer,
        "gegl:hue-chroma",
        "Blue sky boost",
        { "hue": 0.0, "chroma": 20.0, "lightness": -8.0, },
        merge=False,
    )

    sky_layer.set_mode(Gimp.LayerMode.NORMAL)
    sky_layer.set_opacity(20.0)
    

    ### 処理終了 ###
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
