from __future__ import annotations

import logging
from typing import Any


class Visualization:

    def __init__(self, cfg: dict[str, Any] | None = None) -> None:
        self.plot_data: dict[str, Any] = {"data": [], "layout": {}}
        self.colors: list[str] = self.get_colors()
        self.current_color_index: int = 0
        self.cfg: dict[str, Any] | None = None
        self.default_cfg: dict[str, Any] = {}

        if cfg is not None:
            self.cfg = cfg

            self.default_cfg = {
                "data_source": None,
                "type": "scatter",
                "mode": "lines",
                "name": None,
                "x": [],
                "y": [],
                "line": {"color": None},
            }

        self.default_layout: dict[str, Any] = {
            "title": "Title",
            "xaxis": {"title": "X Label"},
            "yaxis": {"title": "Y Label"},
        }

    def get_plotly_data(self, cfg: dict[str, Any] | None) -> dict[str, Any] | str:
        import json

        import plotly

        if cfg is not None:
            self.cfg = cfg
        elif self.cfg is None:
            self.cfg = self.default_cfg

        if not self.cfg.__contains__("name_column_legend_groups"):
            plot_data = self.assign_simple_data_by_DataFrame_source()
            # data_source = type(self.cfg['data_source'])
            # self.assign_simple_data_by_array_source()
            self.plot_data["data"] = plot_data
        else:
            self.assign_grouped_data()
        self.assign_layout()

        if format in cfg.keys() and cfg["format"] == "json":
            plotly_data: str = json.dumps(
                self.plot_data, cls=plotly.utils.PlotlyJSONEncoder
            )
        else:
            plotly_data = self.plot_data

        return plotly_data

    def assign_simple_data_by_array_source(self) -> None:
        pass

    def assign_simple_data_by_DataFrame_source(self) -> list[dict[str, Any]] | None:

        def get_x_data(df: Any, column: str) -> list[Any]:
            data: list[Any] = []
            if column in df.columns.to_list():
                data = df[column]
            elif column == "index":
                data = df.index.to_list()
            else:
                logging.debug("X Data does not exist")
                raise Exception("X Data does not exist")
            return data

        def get_y_data(df: Any, column: str) -> list[Any]:
            data: list[Any] = []
            if column in df.columns.to_list():
                data = df[column]
            elif column == "index":
                data = df.index.to_list()
            else:
                logging.debug("Y Data does not exist")
                raise Exception("Y Data does not exist")
            return data

        def get_z_data(df: Any, column: str) -> list[Any]:
            data: list[Any] = []
            if column in df.columns.to_list():
                data = df[column]
            elif column == "index":
                data = df.index.to_list()
            else:
                logging.debug("Z Data does not exist")
                raise Exception("Z Data does not exist")
            return data

        def get_text_data(df: Any, column: str | None) -> list[Any]:
            data: list[Any] = []
            if column is not None:
                if column in df.columns.to_list():
                    data = df[column]
                elif column == "index":
                    data = df.index.to_list()
                else:
                    logging.debug("Text Data does not exist")
                    raise Exception("Text Data does not exist")

            return data

        def get_data_name(cfg: dict[str, Any]) -> None:
            pass

        def get_data_item(
            cfg: dict[str, Any],
            x_data: list[Any],
            y_data: list[Any],
            z_data: list[Any],
            series_name: str,
            text_data: list[Any] | None = None,
        ) -> dict[str, Any]:
            if text_data is None:
                text_data = []
            cfg.update({"x": x_data, "y": y_data, "z": z_data, "name": series_name})
            if cfg.__contains__("text"):
                cfg.update({"text": text_data})
            return cfg

        def get_data_cfg() -> dict[str, Any]:
            import copy

            cfg = copy.deepcopy(self.cfg)
            keys_to_drop = ["data_source", "x", "y"]
            for key in keys_to_drop:
                if key in cfg:
                    del cfg[key]
            return cfg

        try:
            plot_data: list[dict[str, Any]] = []
            x_data: list[Any] = []
            y_data: list[Any] = []
            z_data: list[Any] = []

            df = self.cfg["data_source"]

            if len(self.cfg["x"]) == 1:
                x_column: str = self.cfg["x"][0]
                x_data = get_x_data(df, column=x_column)

            if len(self.cfg["y"]) >= 1:
                for y_data_index in range(0, len(self.cfg["y"])):
                    y_column: str = self.cfg["y"][y_data_index]
                    y_data = get_y_data(df, y_column)
                    if self.cfg.__contains__("z"):
                        z_column: str = self.cfg["z"][y_data_index]
                        z_data = get_z_data(df, z_column)
                    if self.cfg.__contains__("text"):
                        text_column: str | None = self.cfg["text"][y_data_index]
                    else:
                        text_column = None
                    text_data = get_text_data(df, text_column)
                    series_name: str = self.cfg["name"][y_data_index]
                    cfg_temp = get_data_cfg()
                    if cfg_temp.__contains__("marker") and cfg_temp[
                        "marker"
                    ].__contains__("sizerefcolumn"):
                        sizecolumn = cfg_temp["marker"].get("sizecolumn", None)
                        sizedata = get_y_data(df, sizecolumn)
                        sizerefcolumn = cfg_temp["marker"].get("sizerefcolumn", None)
                        sizerefdata = get_y_data(df, sizerefcolumn)
                    else:
                        sizerefdata = []
                        sizedata = []
                    cfg_data = self.assign_custom_properties(
                        cfg_temp, sizedata, sizerefdata
                    )
                    data = get_data_item(
                        cfg_data, x_data, y_data, z_data, series_name, text_data
                    )
                    plot_data.append(data.copy())

            return plot_data
        except Exception:
            logging.debug("Data does not exist")
            return None

    def assign_grouped_data(self) -> None:
        try:
            df = self.cfg["data_source"]
            groupby_columns = self.cfg["name_column_legend_groups"]
            grouped_df = df.groupby(groupby_columns)
            names = list(grouped_df.groups.keys())
            plot_type = self.cfg["type"]

            for name in names:
                x_data = grouped_df.get_group(name)[self.cfg["x"][0]]
                y_data = grouped_df.get_group(name)[self.cfg["y"][0]]
                data: dict[str, Any] = {
                    "x": x_data,
                    "y": y_data,
                    "name": name,
                    "type": plot_type,
                }
                if "text" in list(df.columns):
                    text_data = grouped_df.get_group(name)[self.cfg["y"][0]]
                    data.update({"text": text_data})
                self.plot_data["data"].append(data.copy())
        except Exception:
            logging.debug("Data does not exist")

    def assign_custom_properties(
        self, cfg: dict[str, Any], sizedata: list[Any], sizerefdata: list[Any]
    ) -> dict[str, Any]:
        cfg = self.get_cfg_with_custom_color(cfg, sizedata)
        cfg = self.get_cfg_with_custom_marker(cfg, sizedata, sizerefdata)
        return cfg

    def get_cfg_with_custom_marker(
        self, cfg: dict[str, Any], sizedata: list[Any], sizerefdata: list[Any]
    ) -> dict[str, Any]:
        if cfg.__contains__("marker"):
            marker = cfg.get("marker", None)
            marker["size"] = sizedata
            sizeref = marker.get("sizeref", None)
            if sizeref is None:
                sizemax = marker["sizemax"]
                sizeref_max = sizerefdata.max()
                marker["sizeref"] = self.get_custom_size_ref(sizeref_max, sizemax)
                cfg["marker"] = marker

        return cfg

    def get_cfg_with_custom_color(
        self, cfg: dict[str, Any], sizedata: list[Any]
    ) -> dict[str, Any]:
        color: str | None = None
        if "marker" in self.cfg:
            color = self.cfg["marker"].get("color", None)
        if "line" in self.cfg:
            color = self.cfg["line"].get("color", None)
        if color is None:
            color = self.colors[self.current_color_index]
            self.current_color_index = self.current_color_index + 1

        if cfg.__contains__("line"):
            cfg["line"]["color"] = color
        elif cfg.__contains__("marker"):
            cfg["marker"]["color"] = color

        return cfg

    def assign_layout(self) -> None:
        layout = self.cfg.get("layout", self.default_layout)
        self.plot_data["layout"] = layout

    def get_colors(self, n: int = 15) -> list[str]:
        from webcolors import rgb_to_hex

        colors: list[str]
        if n <= 8:
            colors = [
                "#75968f",
                "#a5bab7",
                "#c9d9d3",
                "#e2e2e2",
                "#dfccce",
                "#ddb7b1",
                "#cc7878",
                "#933b41",
                "#550b1d",
            ]
        else:
            # Tableau 20 Colors
            color_tuples: list[tuple[int, int, int]] = [
                (31, 119, 180),
                (174, 199, 232),
                (255, 127, 14),
                (255, 187, 120),
                (44, 160, 44),
                (152, 223, 138),
                (214, 39, 40),
                (255, 152, 150),
                (148, 103, 189),
                (197, 176, 213),
                (140, 86, 75),
                (196, 156, 148),
                (227, 119, 194),
                (247, 182, 210),
                (127, 127, 127),
                (199, 199, 199),
                (188, 189, 34),
                (219, 219, 141),
                (23, 190, 207),
                (158, 218, 229),
            ]
            colors = [rgb_to_hex(color) for color in color_tuples]
        return colors

    def get_custom_size_ref(self, sizeref_max: float, sizemax: int = 40) -> float:
        sizeref: float = 2 * sizeref_max / (sizemax**2)

        return sizeref
