"""CHIMERA plotting, fitting and data-entry logic.

Extracted from ``main.py`` to keep the monolithic ``MainWindow`` class smaller.
Provided as a mixin whose methods run against a live ``MainWindow`` instance and
rely on its attributes and helpers (``self.master``, ``self.fig``, ``self.ax``,
``self.canvas``, ``self.update_parameter`` ...).

Fit expressions are evaluated via :func:`expr_eval.safe_eval` (never the built-in
``eval``); the actual regression lives in :func:`fitting.run_odr_fit`.
"""

import tkinter as tk
import tkinter.messagebox  # noqa: F401  (enables ``tk.messagebox`` access)
from io import StringIO
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from chimera_core import parser, process_params, read_file
from expr_eval import safe_eval
from fitting import run_odr_fit


class PlottingMixin:
    """Data-entry, compile, plot and fit methods for :class:`MainWindow`."""

    def check_databox(self):
        for x in range(len(self.dataset_text)):
            if self.dataset_text[x].replace(" ", "") == "" and self.datasets_to_plot_var[x].get():
                tk.messagebox.showwarning(
                    "ERROR", f"Dataset {x + 1} is empty. Insert your data or remove it."
                )
                return False

        for x in range(len(self.dataset_text)):
            split = self.dataset_text[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(" ")
                ponto = [p for p in ponto if p]
                if len(ponto) != 3 and len(ponto) != 4 and self.datasets_to_plot_var[x].get():
                    tk.messagebox.showwarning(
                        "ERROR",
                        f"Dataset {x + 1} has at least one point with an incorrect number of columns. Correct it.",
                    )
                    self.want_fit[self.selected_dataset].set(0)
                    return False

        for x in range(len(self.dataset_text)):
            split = self.dataset_text[x].split("\n")
            for i in range(len(split)):
                ponto = split[i].split(" ")
                ponto = [p for p in ponto if p]

                for k in ponto:
                    try:
                        float(k)
                    except ValueError:
                        tk.messagebox.showwarning(
                            "ERROR",
                            f"Dataset {x + 1} contains non-numerical input. Only numerical input is allowed.",
                        )
                        self.want_fit[self.selected_dataset].set(0)
                        return False
        return True

    def update_databox(self, event):
        # Keep the current one
        if event != "remove":
            self.dataset_text[self.current_selection] = self.data_entry.get(
                "1.0", "end-1c"
            ).replace("\t", " ")
        # This function shows the text for a dataset in the text box
        # The least messy way to do that is to destroy everything in the frame and put the information
        # for the new dataset
        self.update_combobox_values()
        select = self.data_list.index(self.data_list_var.get())
        self.selected_dataset = select
        self.current_selection = select

        self.function_entry.delete(0, tk.END)
        self.function_entry.insert(0, self.functions[self.selected_dataset])
        self.parameter_entry.delete(0, tk.END)
        self.parameter_entry.insert(0, self.params[self.selected_dataset])
        self.independent_entry.delete(0, tk.END)
        self.independent_entry.insert(0, self.indeps[self.selected_dataset])
        self.chisq_entry.delete(0, tk.END)
        self.r2_entry.delete(0, tk.END)

        self.update_parameter()

        self.plot_options.delete(0, tk.END)
        self.plot_options.add_checkbutton(
            label="Plot points",
            onvalue=1,
            offvalue=0,
            variable=self.want_points[self.selected_dataset],
        )
        self.plot_options.add_checkbutton(
            label="Connect points",
            onvalue=1,
            offvalue=0,
            variable=self.want_line[self.selected_dataset],
        )
        self.plot_options.add_checkbutton(
            label="Error bars",
            onvalue=1,
            offvalue=0,
            variable=self.want_error[self.selected_dataset],
        )
        self.plot_options.add_checkbutton(
            label="Plot fit", onvalue=1, offvalue=0, variable=self.want_fit[self.selected_dataset]
        )
        self.plot_options.add_checkbutton(
            label="Plot function",
            onvalue=1,
            offvalue=0,
            variable=self.want_function[self.selected_dataset],
        )

        self.subframe_left_2.destroy()
        self.data_entry.destroy()

        self.subframe_left_2 = tk.Frame(self.frame_left, bg="#E4E4E4")
        self.subframe_left_2.place(
            in_=self.frame_left, relwidth=1, relheight=0.38, relx=0, rely=0.55
        )

        # Create the text box with the corresponding information
        self.data_entry = ScrolledText(self.subframe_left_2)
        self.data_entry.pack(expand=1, fill=tk.X)
        self.data_entry.insert(tk.INSERT, self.dataset_text[select])

        # Same delete-and-recreate for the menus, so the right ones appear in the place corresponding
        # to the selected dataset
        self.marker_sizescale.destroy()
        self.line_width_scale.destroy()
        self.error_size_scale.destroy()
        self.func_fit_width_scale.destroy()
        self.func_plot_width_scale.destroy()

        self.marker_size_combo.destroy()
        self.line_style_combo.destroy()
        self.func_fit_style_combo.destroy()
        self.func_plot_style_combo.destroy()

        self.line_style_combo = ttk.Combobox(
            self.subframe_right_3,
            values=["Solid", "Dashed", "Dotted", "DashDot"],
            textvariable=self.line_option,
        )

        self.func_fit_style_combo = ttk.Combobox(
            self.subframe_right_3,
            values=["Solid", "Dashed", "Dotted", "DashDot"],
            textvariable=self.func_fit_option,
        )

        self.func_plot_style_combo = ttk.Combobox(
            self.subframe_right_3,
            values=["Solid", "Dashed", "Dotted", "DashDot"],
            textvariable=self.func_plot_option,
        )

        self.marker_size_combo = ttk.Combobox(
            self.subframe_right_3,
            values=["Triangle", "Square", "Circle", "Star", "Diamond", "X"],
            textvariable=self.marker_option,
        )

        if self.marker_option_translater[self.selected_dataset] == "x":
            self.marker_size_combo.current(5)
            self.marker_option.set("X")
        if self.marker_option_translater[self.selected_dataset] == "D":
            self.marker_size_combo.current(4)
            self.marker_option.set("Diamond")
        if self.marker_option_translater[self.selected_dataset] == "*":
            self.marker_size_combo.current(3)
            self.marker_option.set("Star")
        if self.marker_option_translater[self.selected_dataset] == "o":
            self.marker_size_combo.current(2)
            self.marker_option.set("Circle")
        if self.marker_option_translater[self.selected_dataset] == "s":
            self.marker_size_combo.current(1)
            self.marker_option.set("Square")
        if self.marker_option_translater[self.selected_dataset] == "^":
            self.marker_size_combo.current(0)
            self.marker_option.set("Triangle")

        if self.line_option_translater[self.selected_dataset] == "-":
            self.line_style_combo.current(0)
            self.line_option.set("Solid")
        if self.line_option_translater[self.selected_dataset] == "--":
            self.line_style_combo.current(1)
            self.line_option.set("Dashed")
        if self.line_option_translater[self.selected_dataset] == ":":
            self.line_style_combo.current(2)
            self.line_option.set("Dotted")
        if self.line_option_translater[self.selected_dataset] == "-.":
            self.line_style_combo.current(3)
            self.line_option.set("DashDot")

        if self.func_fit_option_translater[self.selected_dataset] == "-":
            self.func_fit_style_combo.current(0)
            self.func_fit_option.set("Solid")
        if self.func_fit_option_translater[self.selected_dataset] == "--":
            self.func_fit_style_combo.current(1)
            self.func_fit_option.set("Dashed")
        if self.func_fit_option_translater[self.selected_dataset] == ":":
            self.func_fit_style_combo.current(2)
            self.func_fit_option.set("Dotted")
        if self.func_fit_option_translater[self.selected_dataset] == "-.":
            self.func_fit_style_combo.current(3)
            self.func_fit_option.set("DashDot")

        if self.func_plot_option_translater[self.selected_dataset] == "-":
            self.func_plot_style_combo.current(0)
            self.func_plot_option.set("Solid")
        if self.func_plot_option_translater[self.selected_dataset] == "--":
            self.func_plot_style_combo.current(1)
            self.func_plot_option.set("Dashed")
        if self.func_plot_option_translater[self.selected_dataset] == ":":
            self.func_plot_style_combo.current(2)
            self.func_plot_option.set("Dotted")
        if self.func_plot_option_translater[self.selected_dataset] == "-.":
            self.func_plot_style_combo.current(3)
            self.func_plot_option.set("DashDot")

        self.marker_size_combo.place(
            in_=self.subframe_right_3, relwidth=0.15, relx=0.63, rely=0.64, relheight=0.05
        )
        self.marker_size_combo.bind("<<ComboboxSelected>>", self.marker_selector)

        self.line_style_combo.place(
            in_=self.subframe_right_3, relwidth=0.15, relx=0.63, rely=0.56, relheight=0.05
        )
        self.line_style_combo.bind("<<ComboboxSelected>>", self.line_selector)

        self.func_plot_style_combo.place(
            in_=self.subframe_right_3, relwidth=0.15, relx=0.63, rely=0.72, relheight=0.05
        )
        self.func_plot_style_combo.bind("<<ComboboxSelected>>", self.func_plot_selector)

        self.func_fit_style_combo.place(
            in_=self.subframe_right_3, relwidth=0.15, relx=0.63, rely=0.80, relheight=0.05
        )
        self.func_fit_style_combo.bind("<<ComboboxSelected>>", self.func_fit_selector)

        # Figure out which dataset is selected just to apply the correct colors and so on
        self.line_width_scale = tk.Scale(
            self.subframe_right_3,
            from_=1,
            to=5,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            troughcolor="#F21112",
            bg="#E4E4E4",
            highlightthickness=0,
            command=self.line_slider,
            showvalue=False,
            variable=self.line_width[self.selected_dataset],
        )
        self.line_width_scale.place(
            in_=self.subframe_right_3, relwidth=0.17, relx=0.34, rely=0.56, relheight=0.06
        )
        self.line_width_scale["width"] = 0.025 * self.master.winfo_width()

        self.marker_sizescale = tk.Scale(
            self.subframe_right_3,
            from_=1,
            to=5,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            troughcolor="#F21112",
            bg="#E4E4E4",
            highlightthickness=0,
            command=self.marker_slider,
            showvalue=False,
            variable=self.marker_size[self.selected_dataset],
        )
        self.marker_sizescale.place(
            in_=self.subframe_right_3, relwidth=0.17, relx=0.34, rely=0.64, relheight=0.06
        )
        self.marker_sizescale["width"] = 0.025 * self.master.winfo_width()

        self.func_plot_width_scale = tk.Scale(
            self.subframe_right_3,
            from_=1,
            to=5,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            troughcolor="#F21112",
            bg="#E4E4E4",
            highlightthickness=0,
            command=self.func_plot_slider,
            showvalue=False,
            variable=self.func_plot_width[self.selected_dataset],
        )
        self.func_plot_width_scale.place(
            in_=self.subframe_right_3, relwidth=0.17, relx=0.34, rely=0.72, relheight=0.06
        )
        self.func_plot_width_scale["width"] = 0.025 * self.master.winfo_width()

        self.func_fit_width_scale = tk.Scale(
            self.subframe_right_3,
            from_=1,
            to=5,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            troughcolor="#F21112",
            bg="#E4E4E4",
            highlightthickness=0,
            command=self.func_fit_slider,
            showvalue=False,
            variable=self.func_fit_width[self.selected_dataset],
        )
        self.func_fit_width_scale.place(
            in_=self.subframe_right_3, relwidth=0.17, relx=0.34, rely=0.80, relheight=0.06
        )
        self.func_fit_width_scale["width"] = 0.025 * self.master.winfo_width()

        self.error_size_scale = tk.Scale(
            self.subframe_right_3,
            from_=1,
            to=5,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            troughcolor="#F21112",
            bg="#E4E4E4",
            highlightthickness=0,
            command=self.error_slider,
            showvalue=False,
            variable=self.error_width[self.selected_dataset],
        )
        self.error_size_scale.place(
            in_=self.subframe_right_3, relwidth=0.17, relx=0.34, rely=0.88, relheight=0.06
        )
        self.error_size_scale["width"] = 0.025 * self.master.winfo_width()

        self.error_scale_label_value["text"] = self.error_width[self.selected_dataset].get()
        self.marker_scale_label_value["text"] = self.marker_size[self.selected_dataset].get()
        self.line_scale_label_value["text"] = self.line_width[self.selected_dataset].get()
        self.func_fit_scale_label_value["text"] = self.func_fit_width[self.selected_dataset].get()
        self.func_plot_scale_label_value["text"] = self.func_plot_width[self.selected_dataset].get()

        if self.count_plots == 0:
            self.line_width_scale["state"] = tk.DISABLED
            self.marker_sizescale["state"] = tk.DISABLED
            self.error_size_scale["state"] = tk.DISABLED
            self.func_fit_width_scale["state"] = tk.DISABLED
            self.func_plot_width_scale["state"] = tk.DISABLED

    def compile_function(self):
        # clean the fit parameters
        for x in range(self.box_number):
            self.param_err_boxes[x].config(state="normal")
            self.param_err_boxes[x].delete(0, tk.END)
            self.param_err_boxes[x].config(state="readonly")

            self.param_res_boxes[x].config(state="normal")
            self.param_res_boxes[x].delete(0, tk.END)
            self.param_res_boxes[x].config(state="readonly")
        # clean r2 and chisq
        self.chisq_entry.config(state="normal")
        self.chisq_entry.delete(0, tk.END)
        self.chisq_entry.config(state="readonly")
        self.r2_entry.config(state="normal")
        self.r2_entry.delete(0, tk.END)
        self.r2_entry.config(state="readonly")
        # erase the graph
        self.want_fit[self.selected_dataset].set(0)
        try:
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        except Exception:
            pass

        parsed_input = parser(
            self.function_entry.get(), self.parameter_entry.get(), self.independent_entry.get()
        )
        self.functions[self.selected_dataset] = self.function_entry.get()

        for x in range(len(self.param_boxes)):
            try:
                self.init_values[self.selected_dataset][x] = float(self.param_boxes[x].get())
            except ValueError:
                if self.param_boxes[x].get().replace(" ", "") == "":
                    tk.messagebox.showwarning(
                        "ERROR",
                        "Empty input found in initial guesses. Provide an initial guess for every parameter.",
                    )
                    self.want_fit[self.selected_dataset].set(0)
                else:
                    tk.messagebox.showwarning(
                        "ERROR",
                        "Non-numerical input found in initial guesses. Only numerical input allowed.",
                    )
                    self.want_fit[self.selected_dataset].set(0)
        if parsed_input[0]:
            self.clean_functions[self.selected_dataset] = parsed_input[1]
        else:
            tk.messagebox.showwarning("ERROR", parsed_input[1])
            self.clean_functions[self.selected_dataset] = ""

    # Function to plot the function with numeric parameters given by the user
    def plot_fitted_function(self, dataset):
        self.x_fitted_func[dataset] = [0] * 10000
        self.y_fitted_func[dataset] = [0] * 10000

        x_max = float(self.x_axis_max_entry.get().replace(" ", ""))
        x_min = float(self.x_axis_min_entry.get().replace(" ", ""))
        amp = x_max - x_min

        B = self.fit_params[dataset]
        expr = self.clean_functions[dataset]
        for j in range(10000):
            _x = x_min + j * amp / 9999
            self.x_fitted_func[dataset][j] = _x
            self.y_fitted_func[dataset][j] = safe_eval(expr, {"np": np, "B": B, "_x": _x})

    def plot_function(self):
        parsed_input = parser(
            self.function_entry.get(), self.parameter_entry.get(), self.independent_entry.get()
        )
        if parsed_input[0]:
            expr = parsed_input[1]
        else:
            tk.messagebox.showwarning("ERROR", parsed_input[1])
            self.want_function[self.selected_dataset].set(0)
            return parsed_input

        B = []

        for i in range(len(self.plot_param_boxes)):
            param_boxes = self.plot_param_boxes[i].get()
            param_boxes = param_boxes.replace(" ", "")
            if param_boxes == "":
                tk.messagebox.showwarning("ERROR", "No parameter values were provided for plot.")
                self.want_function[self.selected_dataset].set(0)
                return False
            try:
                float(param_boxes)
            except ValueError:
                tk.messagebox.showwarning(
                    "ERROR",
                    "A non-numerical parameter value was detected. Only numerical values are allowed.",
                )
                self.want_function[self.selected_dataset].set(0)
                return False
            B.append(float(param_boxes))

        x_max = float(self.x_axis_max_entry.get().replace(",", ".").replace(" ", ""))
        x_min = float(self.x_axis_min_entry.get().replace(",", ".").replace(" ", ""))
        amp = x_max - x_min

        self.x_func[self.selected_dataset] = _x = [x_min + i * amp / 9999 for i in range(10000)]
        self.y_func[self.selected_dataset] = []

        for i in range(10000):
            self.y_func[self.selected_dataset].append(
                safe_eval(expr.replace("_x", "_x[i]"), {"np": np, "B": B, "_x": _x, "i": i})
            )

        self.want_function[self.selected_dataset].set(1)
        self.plot_dataset()

    def plot_dataset(self):
        # we don't want to remove autoscale while in here
        self.remove_autoscale = False

        # Test whether the limits are well defined. If not, we can skip all of this
        info_x = [
            (self.x_axis_max_entry, "Max value of x"),
            (self.x_axis_min_entry, "Min value of x"),
            (self.x_axis_tick_space_entry, "X axis tick spacing"),
        ]
        info_y = [
            (self.y_axis_max_entry, "Max value of y"),
            (self.y_axis_min_entry, "Min value of y"),
            (self.y_axis_tick_space_entry, "Y axis tick spacing"),
        ]

        if not self.autoscale_x.get():
            for var in info_x:
                try:
                    float(var[0].get().replace(",", ".").replace(" ", ""))
                except ValueError:
                    if var[0].get().replace(" ", "") == "":
                        tk.messagebox.showwarning("ERROR", var[1] + " contains no input.")
                    else:
                        tk.messagebox.showwarning(
                            "ERROR",
                            var[1] + " contains non-numerical input. Only numerical input allowed.",
                        )
                    return False
            # Also check that the max values are not smaller than the min
            if float(self.x_axis_max_entry.get().replace(",", ".").replace(" ", "")) <= float(
                self.x_axis_min_entry.get().replace(",", ".").replace(" ", "")
            ):
                tk.messagebox.showwarning(
                    "ERROR", "Upper limit for X axis is not greater that lower limit."
                )
                return False
            # And that the tick spacings are positive
            if float(self.x_axis_tick_space_entry.get().replace(",", ".").replace(" ", "")) <= 0:
                tk.messagebox.showwarning(
                    "ERROR", "Tick spacing must be a positive non-zero number."
                )
                return False
            # And that we do not have too many ticks
            x_max = float(self.x_axis_max_entry.get().replace(",", ".").replace(" ", ""))
            x_min = float(self.x_axis_min_entry.get().replace(",", ".").replace(" ", ""))
            amp = x_max - x_min
            n_ticks = int(
                amp / float(self.x_axis_tick_space_entry.get().replace(",", ".").replace(" ", ""))
            )
            if n_ticks > 100:
                tk.messagebox.showwarning(
                    "ERROR",
                    f"Having {n_ticks} ticks will make your plot unreabable. Adjust X tick spacing.",
                )
                return False

        if not self.autoscale_y.get():
            for var in info_y:
                try:
                    float(var[0].get().replace(",", ".").replace(" ", ""))
                except ValueError:
                    if var[0].get().replace(" ", "") == "":
                        tk.messagebox.showwarning("ERROR", var[1] + " contains no input.")
                    else:
                        tk.messagebox.showwarning(
                            "ERROR",
                            var[1] + " contains non-numerical input. Only numerical input allowed.",
                        )
                    return False
            # Also check that the max values are not smaller than the min
            if float(self.y_axis_max_entry.get().replace(",", ".").replace(" ", "")) <= float(
                self.y_axis_min_entry.get().replace(",", ".").replace(" ", "")
            ):
                tk.messagebox.showwarning(
                    "ERROR", "Upper limit for Y axis is not greater that lower limit."
                )
                return False
            # And that the tick spacings are positive
            if float(self.y_axis_tick_space_entry.get().replace(",", ".").replace(" ", "")) <= 0:
                tk.messagebox.showwarning(
                    "ERROR", "Tick spacing must be a positive non-zero number."
                )
                return False
            y_max = float(self.y_axis_max_entry.get().replace(",", ".").replace(" ", ""))
            y_min = float(self.y_axis_min_entry.get().replace(",", ".").replace(" ", ""))
            amp = y_max - y_min
            n_ticks = int(
                amp / float(self.y_axis_tick_space_entry.get().replace(",", ".").replace(" ", ""))
            )
            if n_ticks > 100:
                tk.messagebox.showwarning(
                    "ERROR",
                    f"Having {n_ticks} ticks will make your plot unreabable. Adjust Y tick spacing.",
                )
                return False

        # Test whether the data is fine. If not, we can skip all of this
        self.update_combobox_values()
        select = self.data_list.index(self.data_list_var.get())
        self.dataset_text[select] = self.data_entry.get("1.0", "end-1c").replace("\t", " ")

        if not self.check_databox():
            return False

        # set the data to plot=true
        self.datasets_to_plot_var[select].set(1)

        if self.count_plots == 0:
            self.line_width_scale["state"] = tk.NORMAL
            self.marker_sizescale["state"] = tk.NORMAL
            self.error_size_scale["state"] = tk.NORMAL
            self.func_fit_width_scale["state"] = tk.NORMAL
            self.func_plot_width_scale["state"] = tk.NORMAL
            self.count_plots = 1

        for x in range(self.number_datasets):
            if self.datasets_to_plot_var[x].get():
                self.abcissas[x] = []
                self.err_abcissas[x] = []
                self.ordenadas[x] = []
                self.err_ordenadas[x] = []
                self.datastring = self.dataset_text[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                if data_sets == -2:
                    tk.messagebox.showwarning(
                        "ERROR",
                        f"Dataset {select} has at least one point defined incorrectly. Make sure all points have the same number of columns.",
                    )
                    self.dataset_text[select] = ""
                    self.datasetring = ""
                    return False
                for i in range(len(data_sets[0])):
                    if len(data_sets[0][i]) == 4:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.err_abcissas[x].append(data_sets[0][i][1])
                        self.ordenadas[x].append(data_sets[0][i][2])
                        self.err_ordenadas[x].append(data_sets[0][i][3])

                    if len(data_sets[0][i]) == 3:
                        self.abcissas[x].append(data_sets[0][i][0])
                        self.err_abcissas[x].append(0)
                        self.ordenadas[x].append(data_sets[0][i][1])
                        self.err_ordenadas[x].append(data_sets[0][i][2])

                self.abc[x] = np.array(self.abcissas[x])
                self.err_abc[x] = np.array(self.err_abcissas[x])
                self.ord[x] = np.array(self.ordenadas[x])
                self.err_ord[x] = np.array(self.err_ordenadas[x])

        if 5 * self.width_ratio / self.height_ratio > 10:
            figsize = (10, 10 * self.height_ratio / self.width_ratio)
        else:
            figsize = (5 * self.width_ratio / self.height_ratio, 5)

        self.fig = Figure(figsize=figsize, tight_layout=True)

        data_for_fit = []
        for x in range(self.number_datasets):
            if self.datasets_to_plot_var[x].get():
                self.datastring = self.dataset_text[x]
                data = StringIO(self.datastring)
                data_sets = read_file(data, float, False, 0)
                data_for_fit.append(data_sets[0])
            else:
                data_for_fit.append("")
        a = []
        for dataset in data_for_fit:
            for point in dataset:
                a.append(point)

        if not self.autoscale_x.get():
            max_abc = float(self.x_axis_max_entry.get().replace(",", ".").replace(" ", ""))
            min_abc = float(self.x_axis_min_entry.get().replace(",", ".").replace(" ", ""))
            amp_x = float(self.x_axis_tick_space_entry.get().replace(",", ".").replace(" ", ""))
        if self.autoscale_x.get():
            all_abc = []
            for x in range(len(a)):
                all_abc.append(a[x][0])

            min_abc = min(all_abc)
            max_abc = max(all_abc)

            if len(a[0]) == 4:
                min_indexes = []
                max_indexes = []
                for point in a:
                    if point[0] == min_abc and len(point) == 4:
                        min_indexes.append(point[1])
                    if point[0] == max_abc and len(point) == 4:
                        max_indexes.append(point[1])

                max_abc += max(max_indexes)
                min_abc -= max(min_indexes)

            amp_x = max_abc - min_abc

            max_abc += 0.05 * amp_x
            min_abc -= 0.05 * amp_x

            self.x_axis_max_entry.delete(0, "end")
            self.x_axis_min_entry.delete(0, "end")

            self.x_axis_max_entry.insert(0, f"{max_abc:.3e}")
            self.x_axis_min_entry.insert(0, f"{min_abc:.3e}")

            amp_x = amp_x / 8
            self.x_axis_tick_space_entry.delete(0, "end")
            self.x_axis_tick_space_entry.insert(0, f"{amp_x:.3e}")

        if not self.autoscale_y.get():
            max_ord = float(self.y_axis_max_entry.get().replace(",", ".").replace(" ", ""))
            min_ord = float(self.y_axis_min_entry.get().replace(",", ".").replace(" ", ""))
            amp_y = float(self.y_axis_tick_space_entry.get().replace(",", ".").replace(" ", ""))

        if self.autoscale_y.get():
            all_ord = []
            for x in range(len(a)):
                all_ord.append(a[x][-2])
                all_ord.append(a[x][-2])

            min_ord = min(all_ord)
            max_ord = max(all_ord)

            min_indexes = []
            max_indexes = []
            for point in a:
                if point[-2] == min_ord:
                    min_indexes.append(point[-1])
                if point[-2] == max_ord:
                    max_indexes.append(point[-1])

            min_ord -= max(min_indexes)
            max_ord += max(max_indexes)

            amp_y = max_ord - min_ord
            max_ord += 0.05 * amp_y
            min_ord -= 0.05 * amp_y

            self.y_axis_max_entry.delete(0, "end")
            self.y_axis_min_entry.delete(0, "end")

            self.y_axis_max_entry.insert(0, f"{max_ord:.3e}")
            self.y_axis_min_entry.insert(0, f"{min_ord:.3e}")

            amp_y = amp_y / 8
            self.y_axis_tick_space_entry.delete(0, "end")
            self.y_axis_tick_space_entry.insert(0, f"{amp_y:.3e}")

        x_ticks = []
        y_ticks = []

        x_max = max_abc
        x_min = min_abc
        x_space = amp_x
        y_max = max_ord
        y_min = min_ord
        y_space = amp_y

        # determine the ticks for the x-axis
        if len(self.x_ticks_ref) == 0:
            x_tick_number = 1 + int((x_max - x_min) / x_space)
            for x in range(x_tick_number):
                x_ticks.append(x * x_space + x_min)

        if len(self.x_ticks_ref) == 1:
            x_tick_number = 1 + int((x_max - x_min) / x_space)
            temp = self.x_ticks_ref[0]
            if self.x_ticks_ref[0] < x_min:
                while temp < x_min:
                    temp += x_space
            if self.x_ticks_ref[0] > x_min:
                while temp - x_space > x_min:
                    temp -= x_space
            for x in range(x_tick_number):
                x_ticks.append(x * x_space + temp)

        if len(self.x_ticks_ref) > 1:
            x_ticks = self.x_ticks_ref

        # determine the ticks for the y-axis
        if len(self.y_ticks_ref) == 0:
            y_tick_number = 1 + int((y_max - y_min) / y_space)
            for y in range(y_tick_number):
                y_ticks.append(y * y_space + y_min)

        if len(self.y_ticks_ref) == 1:
            y_tick_number = 1 + int((y_max - y_min) / y_space)
            temp = self.y_ticks_ref[0]
            if self.y_ticks_ref[0] < y_min:
                while temp < y_min:
                    temp += y_space
            if self.y_ticks_ref[0] > y_min:
                while temp - y_space > y_min:
                    temp -= y_space
            for y in range(y_tick_number):
                y_ticks.append(y * y_space + temp)

        if len(self.y_ticks_ref) > 1:
            y_ticks = self.y_ticks_ref

        self.a = self.fig.add_subplot(
            111,
            projection=None,
            xlim=(x_min, x_max),
            ylim=(y_min, y_max),
            xticks=x_ticks,
            yticks=y_ticks,
            ylabel=self.y_axis_title_entry.get(),
            xlabel=self.x_axis_title_entry.get(),
        )

        self.subframe_left_1.destroy()
        self.subframe_left_1 = tk.Frame(self.frame_left, bg="#E4E4E4")
        self.subframe_left_1.place(in_=self.frame_left, relwidth=1, relheight=0.5, relx=0, rely=0)

        # first we see what scale we are using
        if self.log_x.get():
            if float(self.x_axis_min_entry.get().replace(",", ".").replace(" ", "")) > 0:
                self.a.set_xscale("log")
            else:
                self.a.set_xscale("symlog")
            self.a.set_xticks(x_ticks)
        if self.log_y.get():
            if float(self.y_axis_min_entry.get().replace(",", ".").replace(" ", "")) > 0:
                self.a.set_yscale("log")
            else:
                self.a.set_yscale("symlog")
            self.a.set_yticks(y_ticks)

        if self.check_databox():
            for i in range(self.number_datasets):
                if self.datasets_to_plot_var[i].get():
                    if self.want_error[i].get():
                        self.a.errorbar(
                            self.abc[i],
                            self.ord[i],
                            xerr=self.err_abc[i],
                            yerr=self.err_ord[i],
                            fmt="none",
                            zorder=-1,
                            lw=0,
                            ecolor=self.error_color_var[i],
                            elinewidth=self.error_width[i].get(),
                        )
                    if self.want_points[i].get():
                        if self.data_labels[i]:
                            self.a.plot(
                                self.abc[i],
                                self.ord[i],
                                label=self.data_labels[i],
                                marker=self.marker_option_translater[i],
                                color=str(self.marker_color_var[i]),
                                zorder=1,
                                lw=0,
                                ms=self.marker_size[i].get() * 2,
                            )
                        else:
                            self.a.plot(
                                self.abc[i],
                                self.ord[i],
                                marker=self.marker_option_translater[i],
                                color=str(self.marker_color_var[i]),
                                zorder=1,
                                lw=0,
                                ms=self.marker_size[i].get() * 2,
                            )
                    if self.want_line[i].get():
                        self.a.plot(
                            self.abc[i],
                            self.ord[i],
                            color=self.line_color_var[i],
                            lw=self.line_width[i].get(),
                            ls=str(self.line_option_translater[i]),
                        )
                    if self.want_function[i].get():
                        if self.plot_labels[i]:
                            self.a.plot(
                                self.x_func[i],
                                self.y_func[i],
                                label=self.plot_labels[i],
                                lw=self.func_plot_width[0].get(),
                                ls=str(self.func_plot_option_translater[i]),
                                color=self.func_plot_color_var[i],
                            )
                        else:
                            self.a.plot(
                                self.x_func[i],
                                self.y_func[i],
                                lw=self.func_plot_width[0].get(),
                                ls=str(self.func_plot_option_translater[i]),
                                color=self.func_plot_color_var[i],
                            )
                    if self.want_fit[i].get():
                        (
                            self.fit_params[i],
                            self.fit_uncert[i],
                            self.fit_chi[i],
                            self.fit_r2[i],
                        ) = self.fit_data(data_for_fit[i], self.init_values[i], 2000, i)
                        self.plot_fitted_function(i)
                        if self.fit_labels[i]:
                            self.a.plot(
                                self.x_fitted_func[i],
                                self.y_fitted_func[i],
                                label=self.fit_labels[i],
                                lw=self.func_fit_width[i].get(),
                                ls=str(self.func_fit_option_translater[i]),
                                color=self.func_fit_color_var[i],
                            )
                        else:
                            self.a.plot(
                                self.x_fitted_func[i],
                                self.y_fitted_func[i],
                                lw=self.func_fit_width[i].get(),
                                ls=str(self.func_fit_option_translater[i]),
                                color=self.func_fit_color_var[i],
                            )
                        if i == self.selected_dataset:
                            for x in range(len(self.param_res_boxes)):
                                self.param_res_boxes[x].config(state="normal")
                                self.param_res_boxes[x].delete(0, tk.END)
                                self.param_res_boxes[x].insert(
                                    0, f"{self.fit_params[self.selected_dataset][x]:.7e}"
                                )
                                self.param_res_boxes[x].config(state="readonly")
                                self.param_err_boxes[x].config(state="normal")
                                self.param_err_boxes[x].delete(0, tk.END)
                                self.param_err_boxes[x].insert(
                                    0, f"{self.fit_uncert[self.selected_dataset][x]:.7e}"
                                )
                                self.param_err_boxes[x].config(state="readonly")

                            self.chisq_entry.config(state="normal")
                            self.chisq_entry.delete(0, tk.END)
                            self.chisq_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.3e}")
                            self.chisq_entry.config(state="readonly")
                            self.r2_entry.config(state="normal")
                            self.r2_entry.delete(0, tk.END)
                            self.r2_entry.insert(0, f"{self.fit_r2[self.selected_dataset]:.6f}")
                            self.r2_entry.config(state="readonly")
        # Maybe also add a condition to check whether the user wants a grid
        self.a.grid(True)

        # Write the texts on the plot
        for i in range(len(self.plot_text)):
            self.a.text(
                self.text_pos[i][0],
                self.text_pos[i][1],
                self.plot_text[i],
                fontsize=self.text_size[i],
            )

        if (
            np.any(np.array(self.data_labels) != "")
            or np.any(np.array(self.plot_labels) != "")
            or np.any(np.array(self.fit_labels) != "")
        ):
            self.a.legend()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.subframe_left_1)
        self.canvas.get_tk_widget().pack()
        self.canvas.draw()

        # we don't want to remove autoscale while in here
        self.remove_autoscale = True

    def update_parameter(self):
        self.want_fit[self.selected_dataset].set(0)
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().pack_forget()
            del self.canvas
            del self.fig
        # Same reasoning: destroy the box holding the parameters and initial guesses to put the new ones
        self.params[self.selected_dataset] = self.parameter_entry.get()
        self.indeps[self.selected_dataset] = self.independent_entry.get()

        if hasattr(self, "param_boxes"):
            for x in range(len(self.param_boxes)):
                try:
                    self.init_values[self.selected_dataset][x] = float(self.param_boxes[x].get())
                except ValueError:
                    if self.param_boxes[x].get().replace(" ", "") == "":
                        tk.messagebox.showwarning(
                            "ERROR",
                            "Empty input found in initial guesses. Provide an initial guess for every parameter.",
                        )
                        self.want_fit[self.selected_dataset].set(0)
                    else:
                        tk.messagebox.showwarning(
                            "ERROR",
                            "Non-numerical input found in initial guesses. Only numerical input allowed.",
                        )
                        self.want_fit[self.selected_dataset].set(0)

        process = process_params(self.parameter_entry.get(), self.independent_entry.get())
        if not process[0]:
            self.count = 1
            self.box_number = 0

            self.param_label = []
            self.param_boxes = []
            self.plot_param_label = []
            self.plot_param_boxes = []

            self.param_scroll_y.destroy()
            self.another_frame.destroy()
            self.param_canvas.destroy()
            self.initial_guess_label.destroy()
            tk.messagebox.showwarning("ERROR", process[1])
        else:
            self.process_params = process[1]
            clean_split = process[1]
            if self.count == 2:
                self.subframe_right_2.destroy()

                self.subframe_right_2 = tk.Frame(self.frame_right, bg="#E4E4E4")
                self.subframe_right_2.place(
                    in_=self.frame_right, relwidth=1, relheight=0.2, relx=0, rely=0.25
                )

                self.box_number = len(clean_split)

                self.param_scroll_y.destroy()
                self.another_frame.destroy()
                self.param_canvas.destroy()

                self.param_label = []
                self.param_boxes = []
                self.param_res_boxes = []
                self.param_res_label = []
                self.param_err_label = []
                self.param_err_boxes = []
                self.plot_param_label = []
                self.plot_param_boxes = []

                self.box_number = len(clean_split)
                if len(self.init_values[self.selected_dataset]) > self.box_number:
                    self.init_values[self.selected_dataset] = [1.0] * self.box_number
                else:
                    while len(self.init_values[self.selected_dataset]) != self.box_number:
                        self.init_values[self.selected_dataset].append(1.0)

                self.param_canvas = tk.Canvas(
                    self.subframe_right_2, highlightthickness=0, bg="#E4E4E4"
                )
                self.param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

                self.another_frame = tk.Frame(self.param_canvas, bg="#E4E4E4")

                self.param_scroll_y = ttk.Scrollbar(
                    self.subframe_right_2, orient="vertical", command=self.param_canvas.yview
                )
                self.param_scroll_y.pack(side=tk.RIGHT, fill="y")

                self.param_canvas.configure(yscrollcommand=self.param_scroll_y.set)
                self.param_canvas.bind("<Configure>", self.adjust_canvas)

                self.another_frame.columnconfigure(0, weight=1)
                self.another_frame.columnconfigure(1, weight=3)
                self.another_frame.columnconfigure(2, weight=1)
                self.another_frame.columnconfigure(3, weight=3)
                self.another_frame.columnconfigure(4, weight=1)
                self.another_frame.columnconfigure(5, weight=3)
                self.another_frame.columnconfigure(6, weight=1)
                self.another_frame.columnconfigure(7, weight=3)

                self.chisq_entry.config(state="normal")
                self.chisq_entry.delete(0, tk.END)
                self.chisq_entry.config(state="readonly")

                self.r2_entry.config(state="normal")
                self.r2_entry.delete(0, tk.END)
                self.r2_entry.config(state="readonly")
                for x in range(self.box_number):
                    self.param_err_label.append(
                        tk.Label(self.another_frame, text="\u03b4" + clean_split[x], bg="#E4E4E4")
                    )
                    self.param_err_label[x].grid(column=6, row=x, pady=10, sticky=tk.E)
                    self.param_err_boxes.append(
                        tk.Entry(self.another_frame, cursor="arrow", takefocus=0)
                    )
                    self.param_err_boxes[x].grid(
                        column=7, row=x, pady=10, padx=(0, 10), sticky=tk.W + tk.E
                    )
                    self.param_err_boxes[x].config(state="readonly")
                    self.param_res_label.append(
                        tk.Label(self.another_frame, text=clean_split[x], bg="#E4E4E4")
                    )
                    self.param_res_label[x].grid(column=4, row=x, pady=10, sticky=tk.E)
                    self.param_res_boxes.append(
                        tk.Entry(self.another_frame, cursor="arrow", takefocus=0)
                    )
                    self.param_res_boxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_res_boxes[x].config(state="readonly")
                    self.param_boxes.append(tk.Entry(self.another_frame))
                    try:
                        self.param_boxes[x].insert(
                            0, f"{self.init_values[self.selected_dataset][x]:e}"
                        )
                    except Exception:
                        pass
                    self.param_boxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_label.append(
                        tk.Label(
                            self.another_frame,
                            text=clean_split[x] + "\N{SUBSCRIPT ZERO}",
                            bg="#E4E4E4",
                        )
                    )
                    self.param_label[x].grid(column=2, row=x, pady=10, padx=(15, 0), sticky=tk.E)
                    self.plot_param_label.append(
                        tk.Label(self.another_frame, text=clean_split[x], bg="#E4E4E4")
                    )
                    self.plot_param_label[x].grid(column=0, row=x, pady=10, sticky=tk.E)
                    self.plot_param_boxes.append(tk.Entry(self.another_frame))
                    self.plot_param_boxes[x].grid(column=1, row=x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(
                    self.another_frame,
                    text="GET FULL OUTPUT",
                    fg="white",
                    bg="#F21112",
                    activebackground="white",
                    activeforeground="#F21112",
                )
                output["command"] = self.show_output
                output["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
                self._add_hover(output)
                output.grid(row=x + 1, column=5)

                self.windows_item = self.param_canvas.create_window(
                    (0, 0), window=self.another_frame, anchor="nw"
                )

            if self.count == 1:
                self.param_label = []
                self.param_boxes = []
                self.param_res_boxes = []
                self.param_res_label = []
                self.param_err_label = []
                self.param_err_boxes = []
                self.plot_param_label = []
                self.plot_param_boxes = []

                self.box_number = len(clean_split)

                self.result_label = tk.Label(self.subframe_right_1, text="Results", bg="#E4E4E4")
                self.result_label.place(rely=0.4, relwidth=0.25, relheight=0.1, relx=0.5)

                self.error_label = tk.Label(self.subframe_right_1, text="Errors", bg="#E4E4E4")
                self.error_label.place(rely=0.4, relwidth=0.25, relheight=0.1, relx=0.75)

                self.initial_guess_label = tk.Label(
                    self.subframe_right_1, text="Initial Guess", bg="#E4E4E4"
                )
                self.initial_guess_label.place(rely=0.4, relwidth=0.25, relheight=0.1, relx=0.25)

                self.func_plot_label = tk.Label(
                    self.subframe_right_1, text="Plot Function", bg="#E4E4E4"
                )
                self.func_plot_label.place(rely=0.4, relwidth=0.25, relheight=0.1, relx=-0.03)

                self.param_canvas = tk.Canvas(
                    self.subframe_right_2, highlightthickness=0, bg="#E4E4E4"
                )
                self.param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

                self.another_frame = tk.Frame(self.param_canvas, bg="#E4E4E4")

                self.param_scroll_y = ttk.Scrollbar(
                    self.subframe_right_2, orient="vertical", command=self.param_canvas.yview
                )
                self.param_scroll_y.pack(side=tk.RIGHT, fill="y")

                self.param_canvas.configure(yscrollcommand=self.param_scroll_y.set)
                self.param_canvas.bind("<Configure>", self.adjust_canvas)

                self.another_frame.columnconfigure(0, weight=1)
                self.another_frame.columnconfigure(1, weight=3)
                self.another_frame.columnconfigure(2, weight=1)
                self.another_frame.columnconfigure(3, weight=3)
                self.another_frame.columnconfigure(4, weight=1)
                self.another_frame.columnconfigure(5, weight=3)
                self.another_frame.columnconfigure(6, weight=1)
                self.another_frame.columnconfigure(7, weight=3)

                self.chisq_entry.config(state="normal")
                self.chisq_entry.delete(0, tk.END)
                try:
                    self.chisq_entry.insert(0, f"{self.fit_chi[self.selected_dataset]:.3e}")
                except Exception:
                    pass
                self.chisq_entry.config(state="readonly")

                self.r2_entry.config(state="normal")
                self.r2_entry.delete(0, tk.END)
                try:
                    self.r2_entry.insert(0, f"{self.fit_r2[self.selected_dataset]:.6f}")
                except Exception:
                    pass
                self.r2_entry.config(state="readonly")
                for x in range(self.box_number):
                    self.param_err_label.append(
                        tk.Label(self.another_frame, text="\u03b4" + clean_split[x], bg="#E4E4E4")
                    )
                    self.param_err_label[x].grid(column=6, row=x, pady=10, sticky=tk.E)
                    self.param_err_boxes.append(
                        tk.Entry(self.another_frame, cursor="arrow", takefocus=0)
                    )
                    try:
                        self.param_err_boxes[x].insert(
                            0, f"{self.fit_uncert[self.selected_dataset][x]:.7e}"
                        )
                    except Exception:
                        pass
                    self.param_err_boxes[x].grid(
                        column=7, row=x, pady=10, padx=(0, 10), sticky=tk.W + tk.E
                    )
                    self.param_err_boxes[x].config(state="readonly")
                    self.param_res_label.append(
                        tk.Label(self.another_frame, text=clean_split[x], bg="#E4E4E4")
                    )
                    self.param_res_label[x].grid(column=4, row=x, pady=10, sticky=tk.E)
                    self.param_res_boxes.append(
                        tk.Entry(self.another_frame, cursor="arrow", takefocus=0)
                    )
                    try:
                        self.param_res_boxes[x].insert(
                            0, f"{self.fit_params[self.selected_dataset][x]:.7e}"
                        )
                    except Exception:
                        pass
                    self.param_res_boxes[x].grid(column=5, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_res_boxes[x].config(state="readonly")
                    self.param_boxes.append(tk.Entry(self.another_frame))
                    try:
                        self.param_boxes[x].insert(
                            0, f"{self.init_values[self.selected_dataset][x]:e}"
                        )
                    except Exception:
                        pass
                    self.param_boxes[x].grid(column=3, row=x, pady=10, sticky=tk.W + tk.E)
                    self.param_label.append(
                        tk.Label(
                            self.another_frame,
                            text=clean_split[x] + "\N{SUBSCRIPT ZERO}",
                            bg="#E4E4E4",
                        )
                    )
                    self.param_label[x].grid(column=2, row=x, pady=10, padx=(15, 0), sticky=tk.E)
                    self.plot_param_label.append(
                        tk.Label(self.another_frame, text=clean_split[x], bg="#E4E4E4")
                    )
                    self.plot_param_label[x].grid(column=0, row=x, pady=10, sticky=tk.E)
                    self.plot_param_boxes.append(tk.Entry(self.another_frame))
                    self.plot_param_boxes[x].grid(column=1, row=x, pady=10, sticky=tk.W + tk.E)
                output = tk.Button(
                    self.another_frame,
                    text="GET FULL OUTPUT",
                    fg="white",
                    bg="#F21112",
                    activebackground="white",
                    activeforeground="#F21112",
                )
                output["command"] = self.show_output
                output["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
                self._add_hover(output)
                output.grid(row=x + 1, column=5)

            self.count = 2

            self.windows_item = self.param_canvas.create_window(
                (0, 0), window=self.another_frame, anchor="nw"
            )

            sep2_plot = ttk.Separator(self.frame_right, orient=tk.VERTICAL)
            sep2_plot.place(in_=self.frame_right, relx=0.24, relheight=0.245, rely=0.20)
            sep3_plot = ttk.Separator(self.frame_right, orient=tk.HORIZONTAL)
            sep3_plot.place(in_=self.frame_right, relwidth=1, rely=0.2)
            sep4_plot = ttk.Separator(self.frame_right, orient=tk.HORIZONTAL)
            sep4_plot.place(in_=self.frame_right, relwidth=1, rely=0.445)
            sep5_plot = ttk.Separator(self.frame_right, orient=tk.VERTICAL)
            sep5_plot.place(in_=self.frame_right, relx=0, relheight=1, rely=0)

            self.param_canvas.update()

    def show_output(self):
        if self.full_output[self.selected_dataset]:
            tk.messagebox.showinfo("FULL OUTPUT", self.full_output[self.selected_dataset])
        else:
            tk.messagebox.showwarning("ERROR", "Fit not yet done.")

    def adjust_canvas(self, event):
        canvas_width = event.width
        self.param_canvas.itemconfig(self.windows_item, width=canvas_width)
        self.param_canvas.configure(scrollregion=self.param_canvas.bbox("all"))

    def update(self):
        "Update the canvas and the scrollregion"
        self.update_idletasks()
        self.param_canvas.config(scrollregion=self.param_canvas.bbox(self.windows_item))

    def fit_data(self, data, init_params, max_iter, dataset_number):
        """
        Parameters
        ----------
        data : array of array
            Points, in the format [[x1,ex1,y1,ey1],[x2,ex2,y2,ey2],...]

        init_params: array
            Initial estimates for the parameter values

        Returns
        -------
        fit.beta: fitted parameters
        fit.sd_beta: parameter uncertainties
        fit.res_var: reduced chi-squared
        r2: R^2 of the fit
        """
        for i in range(len(self.clean_functions)):
            if self.clean_functions[i] == "":
                tk.messagebox.showwarning(
                    "ERROR",
                    f"Fitting function for dataset {i + 1} is not defined. Make sure it is compiled without errors.",
                )
                return 0

        x_points = []
        y_points = []
        x_err = []
        y_err = []

        # start by testing that all points have the same dimensions and that there are no repeated points
        dims = len(data[0])
        for point in data:
            if len(point) != dims:
                tk.messagebox.showwarning(
                    "ERROR",
                    "There are points with x uncertainty and points without. All points need to match before a fit can be done.",
                )
                return False
            if point[0] in x_points:
                tk.messagebox.showwarning(
                    "ERROR", "There are repeated points. Remove them before fitting."
                )
                return False
            x_points.append(point[0])
            y_points.append(point[-2])
            y_err.append(point[-1])
            if dims == 4:
                x_err.append(point[1])

        if x_err and np.any(np.array(x_err) == 0):
            tk.messagebox.showwarning(
                "ERROR",
                f"At least one point in dataset {self.current_selection} has a null x uncertainty. It is not possible to fit data with null uncertainty.",
            )
            return 0
        if y_err and np.any(np.array(y_err) == 0):
            tk.messagebox.showwarning(
                "ERROR",
                f"At least one point in dataset {self.current_selection} has a null y uncertainty. It is not possible to fit data with null uncertainty.",
            )
            return 0

        beta, sd_beta, res_var, r2, output = run_odr_fit(
            self.clean_functions[dataset_number],
            x_points,
            y_points,
            x_err,
            y_err,
            init_params,
            max_iter,
        )
        self.full_output[dataset_number] = output
        return (beta, sd_beta, res_var, r2)
