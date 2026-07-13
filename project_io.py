"""CHIMERA project I/O: save/open ``.chi`` projects and LaTeX export.

Extracted from ``main.py`` to keep the monolithic ``MainWindow`` class smaller.
Provided as a mixin whose methods run against a live ``MainWindow`` instance and
rely on its attributes and helpers (``self.master``, ``self.database``,
``self.create_scatter``, ``self.update_databox`` ...).

The load path deliberately re-derives ``clean_functions`` from the raw fit
functions via the validating parser rather than trusting the stored value, so a
tampered project cannot smuggle in an expression to evaluate (see
``chimera_core.rederive_clean_functions`` and ``tests/test_project_roundtrip.py``).
"""

import json
import tkinter as tk
import tkinter.filedialog  # noqa: F401  (enables ``tk.filedialog`` access)
import tkinter.messagebox  # noqa: F401  (enables ``tk.messagebox`` access)

import numpy as np
import pymongo
import pyperclip

from chimera_core import latexify_data, math_2_latex, rederive_clean_functions


class ProjectIOMixin:
    """Save, open and LaTeX-export methods for :class:`MainWindow`."""

    def _serialize_project(self):
        """Collect the current project state into a plain dict for saving.

        Shared by :meth:`save_online` (database) and :meth:`save_everything`
        (local ``.chi`` file).
        """
        data = {}
        data["plot_text"] = self.plot_text
        data["text_pos"] = self.text_pos
        data["text_size"] = self.text_size
        data["width_ratio"] = self.width_ratio
        data["height_ratio"] = self.height_ratio
        data["x_ticks_ref"] = self.x_ticks_ref
        data["y_ticks_ref"] = self.y_ticks_ref
        data["x_axis_max"] = self.x_axis_max_entry.get()
        data["x_axis_min"] = self.x_axis_min_entry.get()
        data["x_axis_tick_space"] = self.x_axis_tick_space_entry.get()
        data["x_axis_title"] = self.x_axis_title_entry.get()
        data["y_axis_max"] = self.y_axis_max_entry.get()
        data["y_axis_min"] = self.y_axis_min_entry.get()
        data["y_axis_tick_space"] = self.y_axis_tick_space_entry.get()
        data["y_axis_title"] = self.y_axis_title_entry.get()
        data["data_list"] = self.data_list
        data["dataset_text"] = self.dataset_text
        data["indeps"] = self.indeps
        data["params"] = self.params
        data["functions"] = self.functions
        data["clean_functions"] = self.clean_functions
        data["data_labels"] = self.data_labels
        data["plot_labels"] = self.plot_labels
        data["fit_labels"] = self.fit_labels
        data["init_values"] = self.init_values
        data["marker_color_var"] = self.marker_color_var
        data["line_color_var"] = self.line_color_var
        data["error_color_var"] = self.error_color_var
        data["func_fit_color_var"] = self.func_fit_color_var
        data["func_plot_color_var"] = self.func_plot_color_var
        data["marker_option_translater"] = self.marker_option_translater
        data["line_option_translater"] = self.line_option_translater
        data["func_fit_option_translater"] = self.func_fit_option_translater
        data["func_plot_option_translater"] = self.func_plot_option_translater
        data["marker_size"] = [var.get() for var in self.marker_size]
        data["line_width"] = [var.get() for var in self.line_width]
        data["error_width"] = [var.get() for var in self.error_width]
        data["func_fit_width"] = [var.get() for var in self.func_fit_width]
        data["func_plot_width"] = [var.get() for var in self.func_plot_width]
        return data

    def save_online(self):
        data = self._serialize_project()
        data["owner"] = self.user["username"]
        data["name"] = "TEMPORARY"

        try:
            self.database.insert_project(data)
        except pymongo.errors.PyMongoError:
            tk.messagebox.showwarning(
                "ERROR", "Could not save project. Please try again or create local copy."
            )
            return

        tk.messagebox.showinfo("SAVED TO DATABASE", "Project has been saved to the database.")

    def save_as(self, event=None):
        new_file = tk.filedialog.asksaveasfilename(
            filetypes=(("*CHIMERA Project (.chi)", "*.chi"),), defaultextension=".chi"
        )
        if new_file:
            self.file = new_file
            self.save_everything()

    def save_everything(self, event=None):
        if not hasattr(self, "file"):
            self.file = tk.filedialog.asksaveasfilename(
                filetypes=(("*CHIMERA Project (.chi)", "*.chi"),), defaultextension=".chi"
            )
        if self.file:
            file = open(self.file, "w")
        else:
            del self.file
            return

        data = self._serialize_project()

        json.dump(data, file)
        file.close()
        tk.messagebox.showinfo("File Saved", f"File {self.file.split('/')[-1]} has been saved")

    def open_project(self, event=None, data=None):
        if data is None:
            self.file = tk.filedialog.askopenfilename(
                filetypes=(("*CHIMERA Project (.chi)", "*.chi"),), defaultextension=".chi"
            )
            if not self.file:
                del self.file
                return
        self.create_scatter()
        try:
            if data is None:
                file = open(self.file, "r")
                data = json.load(file)
                file.close()
            self.plot_text = data["plot_text"]
            self.text_pos = data["text_pos"]
            self.text_size = data["text_size"]
            self.width_ratio = data["width_ratio"]
            self.height_ratio = data["height_ratio"]
            self.x_ticks_ref = data["x_ticks_ref"]
            self.y_ticks_ref = data["y_ticks_ref"]

            self.x_axis_max_entry.delete(0, tk.END)
            self.x_axis_max_entry.insert(0, data["x_axis_max"])
            self.x_axis_min_entry.delete(0, tk.END)
            self.x_axis_min_entry.insert(0, data["x_axis_min"])
            self.x_axis_tick_space_entry.delete(0, tk.END)
            self.x_axis_tick_space_entry.insert(0, data["x_axis_tick_space"])
            self.x_axis_title_entry.delete(0, tk.END)
            self.x_axis_title_entry.insert(0, data["x_axis_title"])

            self.y_axis_max_entry.delete(0, tk.END)
            self.y_axis_max_entry.insert(0, data["y_axis_max"])
            self.y_axis_min_entry.delete(0, tk.END)
            self.y_axis_min_entry.insert(0, data["y_axis_min"])
            self.y_axis_tick_space_entry.delete(0, tk.END)
            self.y_axis_tick_space_entry.insert(0, data["y_axis_tick_space"])
            self.y_axis_title_entry.delete(0, tk.END)
            self.y_axis_title_entry.insert(0, data["y_axis_title"])

            self.fit_params = []
            self.fit_uncert = []
            self.fit_chi = []
            self.fit_r2 = []
            self.x_func = []
            self.y_func = []
            self.y_fitted_func = []
            self.x_fitted_func = []
            self.full_output = []

            self.want_fit = []
            self.want_points = []
            self.want_line = []
            self.want_error = []
            self.want_function = []

            self.abcissas = []
            self.err_abcissas = []
            self.ordenadas = []
            self.err_ordenadas = []
            self.abc = []
            self.err_abc = []
            self.ord = []
            self.err_ord = []

            self.line_width = []
            self.marker_size = []
            self.error_width = []
            self.func_fit_width = []
            self.func_plot_width = []

            self.datasets_to_plot_var = []
            self.data_list = data["data_list"]
            self.number_datasets = len(self.data_list)

            for i in range(self.number_datasets):
                # We start by adding all the empty lists
                self.fit_params.append([])
                self.fit_uncert.append([])
                self.fit_chi.append("")
                self.fit_r2.append("")
                self.x_func.append([])
                self.y_func.append([])
                self.y_fitted_func.append([])
                self.x_fitted_func.append([])
                self.full_output.append("")
                self.want_fit.append(tk.BooleanVar())
                self.want_fit[-1].set(0)
                self.want_points.append(tk.BooleanVar())
                self.want_points[-1].set(1)
                self.want_line.append(tk.BooleanVar())
                self.want_line[-1].set(0)
                self.want_error.append(tk.BooleanVar())
                self.want_error[-1].set(1)
                self.want_function.append(tk.BooleanVar())
                self.want_function[-1].set(0)
                self.abcissas.append([0, 0, 0, 0])
                self.err_abcissas.append([0, 0, 0, 0])
                self.ordenadas.append([0, 0, 0, 0])
                self.err_ordenadas.append([0, 0, 0, 0])
                self.abc.append(np.array(self.abcissas[-1]))
                self.err_abc.append(np.array(self.err_abcissas[-1]))
                self.ord.append(np.array(self.ordenadas[-1]))
                self.err_ord.append(np.array(self.err_ordenadas[-1]))
                self.line_width.append(tk.DoubleVar())
                self.marker_size.append(tk.DoubleVar())
                self.error_width.append(tk.DoubleVar())
                self.func_fit_width.append(tk.DoubleVar())
                self.func_plot_width.append(tk.DoubleVar())
                self.datasets_to_plot_var.append(tk.BooleanVar())
                self.datasets_to_plot_var[-1].set(1)
                self.datasets_to_plot.add_checkbutton(
                    label="Plot Dataset " + str(i + 1),
                    onvalue=1,
                    offvalue=0,
                    variable=self.datasets_to_plot_var[-1],
                )

            self.dataset_text = data["dataset_text"]
            self.indeps = data["indeps"]
            self.params = data["params"]
            self.functions = data["functions"]
            # Never trust the pre-compiled expression stored in the file/record:
            # re-derive it from the (validated) raw function so a tampered
            # project cannot smuggle in an arbitrary expression to evaluate.
            self.clean_functions = rederive_clean_functions(
                self.functions, self.params, self.indeps
            )
            self.data_labels = data["data_labels"]
            self.plot_labels = data["plot_labels"]
            self.fit_labels = data["fit_labels"]
            self.init_values = data["init_values"]
            self.marker_color_var = data["marker_color_var"]
            self.line_color_var = data["line_color_var"]
            self.error_color_var = data["error_color_var"]
            self.func_fit_color_var = data["func_fit_color_var"]
            self.func_plot_color_var = data["func_plot_color_var"]
            self.marker_option_translater = data["marker_option_translater"]
            self.line_option_translater = data["line_option_translater"]
            self.func_fit_option_translater = data["func_fit_option_translater"]
            self.func_plot_option_translater = data["func_plot_option_translater"]
            for i in range(self.number_datasets):
                self.marker_size[i].set(data["marker_size"][i])
                self.line_width[i].set(data["line_width"][i])
                self.error_width[i].set(data["error_width"][i])
                self.func_fit_width[i].set(data["error_width"][i])
                self.func_plot_width[i].set(data["func_plot_width"][i])

            del self.param_boxes
            self.data_entry.delete("1.0", tk.END)
            self.data_entry.insert(tk.INSERT, self.dataset_text[0])
            self.data_list_var.set(self.data_list[0])
            self.dataset_selector.config(values=self.data_list)
            self.autoscale_x.set(1)
            self.autoscale_y.set(1)
            self.update_databox("")
            self.update_parameter()
        except Exception:
            # Broad on purpose: any malformed field in an untrusted .chi file
            # (KeyError, ValueError, TclError from a bad widget value, ...) should
            # surface as a single "file corrupted" message rather than a traceback.
            self.create_scatter()
            tk.messagebox.showwarning("ERROR", "Unable to open. File corrupted.")
            del self.file
            return

    def latexify(self):
        self.erase_all_windows()

        self.export_window = tk.Toplevel(self.master)
        self.export_window.title("LaTeX-ify")
        self.export_window.geometry("400x200")
        self.export_window.configure(background="#E4E4E4")
        self.export_window.resizable(False, False)
        self.focus_window(self.export_window)

        # Place the various export options
        function = tk.Label(self.export_window, text="Fitting Function")
        function["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        function.configure(background="#E4E4E4")

        data_same_x = tk.Label(self.export_window, text="Datasets (share x)")
        data_same_x["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        data_same_x.configure(background="#E4E4E4")

        data_diff_x = tk.Label(self.export_window, text="Datasets (split x)")
        data_diff_x["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        data_diff_x.configure(background="#E4E4E4")

        # Place the buttons to copy the text
        self.function_button = tk.Button(
            self.export_window,
            text="COPY",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        self.function_button["command"] = self.export_function
        self.function_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(self.function_button)

        self.data_same_x_button = tk.Button(
            self.export_window,
            text="COPY",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        self.data_same_x_button["command"] = self.export_data_same_x
        self.data_same_x_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(self.data_same_x_button)

        self.data_diff_x_button = tk.Button(
            self.export_window,
            text="COPY",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        self.data_diff_x_button["command"] = self.export_data_diff_x
        self.data_diff_x_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(self.data_diff_x_button)

        # Set the positions of the various elements on screen
        function.place(relx=0.05, rely=0.15, anchor="w")
        data_same_x.place(relx=0.05, rely=0.5, anchor="w")
        data_diff_x.place(relx=0.05, rely=0.85, anchor="w")
        self.function_button.place(relx=0.85, rely=0.15, anchor="c")
        self.data_same_x_button.place(relx=0.85, rely=0.5, anchor="c")
        self.data_diff_x_button.place(relx=0.85, rely=0.85, anchor="c")

    def export_function(self):
        # If the function has already been compiled
        try:
            self.functions[self.selected_dataset]
        except (AttributeError, IndexError):
            tk.messagebox.showwarning(
                "ERROR", "The function has not been compiled yet! Compile before exporting."
            )
            self.export_window.destroy()
            return
        if self.functions[self.selected_dataset]:
            # Some cosmetic operations
            self.function_button.configure(text="COPIED!", fg="#F21112", bg="white")
            self.data_same_x_button.configure(text="COPY", fg="white", bg="#F21112")
            self.data_diff_x_button.configure(text="COPY", fg="white", bg="#F21112")

            self.function_button.bind("<Enter>", func=lambda e: "")
            self.function_button.bind("<Leave>", func=lambda e: "")
            self._add_hover(self.data_same_x_button)
            self._add_hover(self.data_diff_x_button)

            text = math_2_latex(
                self.functions[self.selected_dataset],
                self.params[self.selected_dataset],
                self.indeps[self.selected_dataset],
            )
            pyperclip.copy(text)
        else:
            tk.messagebox.showwarning(
                "ERROR",
                "The function was compiled with errors! Make sure it compiles correctly before exporting.",
            )
            self.export_window.destroy()

    def export_data_same_x(self):
        # Some cosmetic operations
        self.function_button.configure(text="COPY", fg="white", bg="#F21112")
        self.data_same_x_button.configure(text="COPIED!", fg="#F21112", bg="white")
        self.data_diff_x_button.configure(text="COPY", fg="white", bg="#F21112")

        self._add_hover(self.function_button)
        self.data_same_x_button.bind("<Enter>", func=lambda e: "")
        self.data_same_x_button.bind("<Leave>", func=lambda e: "")
        self._add_hover(self.data_diff_x_button)
        text = latexify_data(self.dataset_text, 0)
        pyperclip.copy(text)

    def export_data_diff_x(self):
        # Some cosmetic operations
        self.function_button.configure(text="COPY", fg="white", bg="#F21112")
        self.data_same_x_button.configure(text="COPY", fg="white", bg="#F21112")
        self.data_diff_x_button.configure(text="COPIED!", fg="#F21112", bg="white")

        self._add_hover(self.function_button)
        self._add_hover(self.data_same_x_button)
        self.data_diff_x_button.bind("<Enter>", func=lambda e: "")
        self.data_diff_x_button.bind("<Leave>", func=lambda e: "")
        text = latexify_data(self.dataset_text, 0)
        pyperclip.copy(text)
