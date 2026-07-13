"""CHIMERA Online UI: login, account, project, connection and group management.

These Tkinter windows were extracted verbatim from ``main.py`` to shrink the
monolithic ``MainWindow`` class. They are provided as a mixin whose methods run
against a live ``MainWindow`` instance, so they rely on attributes and helper
methods (``self.master``, ``self.online``, ``self.focus_window``,
``self._add_hover``, ``self.erase_all_windows`` ...) defined there.
"""

import hashlib
import hmac
import os
import re
import secrets
import tkinter as tk
import tkinter.messagebox  # noqa: F401  (enables ``tk.messagebox`` access)
from tkinter import ttk

import pymongo

from db import ChimeraDB


class OnlineUIMixin:
    """Tkinter windows for the optional CHIMERA Online features."""

    def create_login(self, event=None):
        self.erase_all_windows()

        if hasattr(self, "username_entry"):
            del self.username_entry
        if hasattr(self, "password_entry"):
            del self.password_entry

        self.login_window = tk.Toplevel(self.master)
        self.login_window.title("Login CHIMERA Online")
        self.login_window.geometry("500x300")
        self.login_window.configure(background="#E4E4E4")
        self.login_window.resizable(False, False)
        self.focus_window(self.login_window)

        text = """
        Welcome to CHIMERA Online! Before you can access our database you need
        to login below. Don't have an account yet? You can create one through
        the button at the bottom of the page.
        Please insert your username and password below.
        """
        intro = tk.Label(self.login_window, text=text, bg="#E4E4E4", justify="left")
        intro["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        intro.place(relwidth=0.9, relx=0.05, rely=0.02)

        frame_username = tk.Frame(self.login_window, bg="#E4E4E4")

        label_username = tk.Label(frame_username, text="Username:", bg="#E4E4E4", anchor="w")
        label_username["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_username.place(relx=0.32, rely=0.0)

        self.username_entry = tk.Entry(frame_username, width=20, justify="left")
        self.username_entry.place(relx=0.48, rely=0.0)
        self.username_entry.focus_set()

        frame_username.place(relwidth=1, relheight=0.2, relx=0, rely=0.35)

        frame_password = tk.Frame(self.login_window, bg="#E4E4E4")

        label_password = tk.Label(frame_password, text="Password:", bg="#E4E4E4", anchor="w")
        label_password["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_password.place(relx=0.32, rely=0)

        self.password_entry = tk.Entry(frame_password, show="*", width=20, justify="left")
        self.password_entry.place(relx=0.48, rely=0)

        self.button_show = tk.Button(
            frame_password,
            text="Show",
            bg="#E4E4E4",
            activebackground="#E4E4E4",
            highlightthickness=0,
            borderwidth=0,
            command=self.toggle_pass,
            cursor="hand2",
            takefocus=0,
        )
        self.button_show["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        self.button_show.place(relx=0.75, rely=0)

        frame_password.place(relwidth=1, relheight=0.2, relx=0, rely=0.55)

        login_button = tk.Button(
            self.login_window,
            text="LOGIN",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        login_button["command"] = self.login
        login_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(login_button)
        login_button.place(rely=0.7, relx=0.45)

        new_account_button = tk.Button(
            self.login_window,
            text="Create new account",
            bg="#E4E4E4",
            fg="blue",
            activebackground="#E4E4E4",
            activeforeground="blue",
            highlightthickness=0,
            borderwidth=0,
            cursor="hand2",
            takefocus=0,
        )
        new_account_button["command"] = self.setup_account
        new_account_button["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        new_account_button.place(rely=0.85, relx=0.4)
        # self.password_entry.bind('<Return>', lambda e: self.login_button.invoke())

    def load_db_credentials(self):
        """Read the CHIMERA Online database credentials from the environment.

        Returns True on success; on a build/environment where they are not
        configured it warns the user and returns False instead of crashing with
        a KeyError.
        """
        try:
            self.database_username = os.environ["CHIMERA_USERNAME"]
            self.database_password = os.environ["CHIMERA_PASSWORD"]
        except KeyError:
            tk.messagebox.showwarning(
                "ONLINE UNAVAILABLE",
                "CHIMERA Online is not configured in this build, so the database "
                "cannot be reached.",
            )
            return False
        return True

    def login(self, event=None):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not self.load_db_credentials():
            self.login_window.destroy()
            return

        if not hasattr(self, "database"):
            try:
                self.database = ChimeraDB.connect(self.database_username, self.database_password)
            except pymongo.errors.PyMongoError:
                tk.messagebox.showwarning(
                    "CONNECTION ERROR",
                    "Connection timed out after 5 seconds. Make sure you have a stable internet connection.",
                )
                self.login_window.destroy()
                return

        try:
            temp_user = self.database.find_user(username)
        except pymongo.errors.PyMongoError:
            tk.messagebox.showwarning(
                "CONNECTION ERROR",
                "Connection timed out after 5 seconds. Make sure you have a stable internet connection.",
            )
            self.login_window.destroy()
            return

        # first we check if the user exists
        if temp_user is None:
            tk.messagebox.showwarning(
                "INVALID LOGIN", "The username and/or the password are incorrect."
            )
            self.create_login()
            return

        # now we check if the password matches, using a constant-time comparison
        salt = temp_user["password"][:32]
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        if not hmac.compare_digest(key, temp_user["password"][32:]):
            tk.messagebox.showwarning(
                "INVALID LOGIN", "The username and/or the password are incorrect."
            )
            self.create_login()
            return

        # Keep the stored account document, but never retain the plaintext
        # password in memory.
        self.user = temp_user
        self.login_window.destroy()
        tk.messagebox.showinfo("LOGIN SUCCESSFUL", f"Welcome to CHIMERA, {self.user['username']}!")
        self.online.delete("Login")
        self.master.unbind("<Control-L>")
        self.master.unbind("<Control-l>")
        self.online.delete("Create Account")
        self.online.add_command(label="Manage Projects", command=self.view_projects)
        self.online.add_command(label="Manage Connections", command=self.view_connections)
        self.online.add_command(label="Manage Groups", command=self.view_groups)
        self.online.add_command(label="Manage Account", command=self.edit_account)
        self.online.add_command(label="Logout", command=self.logout)
        self.file_options.delete("Open Project")
        self.file_options.delete("Export Image")
        self.file_options.add_command(
            label="Save to Database", command=self.save_online, accelerator="Ctrl+D"
        )
        self.file_options.add_command(
            label="Open Project", command=self.open_project, accelerator="Ctrl+O"
        )
        self.file_options.add_command(
            label="Export Image", command=self.export_image, accelerator="Ctrl+Shift+E"
        )
        self.master.bind("<Control-D>", self.save_online)
        self.master.bind("<Control-d>", self.save_online)

    def toggle_pass(self):
        if self.button_show["text"] == "Show":
            self.button_show.config(text="Hide")
            self.password_entry.config(show="")
        else:
            self.button_show.config(text="Show")
            self.password_entry.config(show="*")

    def view_projects(self):
        self.erase_all_windows()
        projects = self.database.projects
        groups = self.database.groups
        all_projects = [project for project in projects.find({})]
        me_projects = []

        for project in all_projects:
            if project["owner"] == self.user["username"]:
                me_projects.append(project)
            else:
                if groups.find_one(
                    {"projects": {"$in": [project["_id"]]}, "members": {"$in": [self.user["_id"]]}}
                ):
                    me_projects.append(project)

        self.projects_window = tk.Toplevel(self.master)
        self.projects_window.title("Manage CHIMERA Projects")
        self.projects_window.geometry("1000x600")
        self.projects_window.configure(background="#E4E4E4")
        self.projects_window.resizable(False, False)
        self.focus_window(self.projects_window)

        self.projects_window.columnconfigure(0, weight=1, minsize=100)
        self.projects_window.columnconfigure(1, weight=1, minsize=120)
        self.projects_window.columnconfigure(2, weight=1, minsize=120)
        self.projects_window.columnconfigure(3, weight=1, minsize=120)
        self.projects_window.columnconfigure(4, weight=1, minsize=110)
        self.projects_window.columnconfigure(5, weight=1, minsize=110)
        self.projects_window.columnconfigure(6, weight=1, minsize=110)
        self.projects_window.columnconfigure(7, weight=1, minsize=110)
        self.projects_window.columnconfigure(8, weight=1, minsize=100)

        frame_data = tk.Frame(self.projects_window, bg="white")
        frame_data.grid(row=0, column=0, columnspan=9, pady=5, sticky=tk.N + tk.S)
        label1 = tk.Label(frame_data, text="Name", bg="white", fg="red")
        label1["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label1.grid(row=0, column=1)
        label2 = tk.Label(frame_data, text="Owner", bg="white", fg="red")
        label2["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label2.grid(row=0, column=2)
        label3 = tk.Label(frame_data, text="Groups In", bg="white", fg="red")
        label3["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label3.grid(row=0, column=3)
        label4 = tk.Label(frame_data, text="Actions", bg="white", fg="red")
        label4["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label4.grid(row=0, column=4, columnspan=4)
        data_area = tk.Canvas(frame_data, background="white", width=800, height=550)
        vscroll = tk.Scrollbar(frame_data, orient=tk.VERTICAL, command=data_area.yview)
        data_area["yscrollcommand"] = vscroll.set
        scrollable_frame = tk.Frame(data_area, bg="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: data_area.configure(scrollregion=data_area.bbox("all"))
        )
        data_area.create_window((0, 0), window=scrollable_frame, width=800)
        data_area.grid(row=1, column=1, columnspan=7, sticky=tk.N + tk.S + tk.E + tk.W)
        vscroll.grid(row=1, column=8, sticky=tk.N + tk.S + tk.E + tk.W)

        scrollable_frame.columnconfigure(0, weight=1, minsize=135)
        scrollable_frame.columnconfigure(1, weight=1, minsize=135)
        scrollable_frame.columnconfigure(2, weight=1, minsize=135)
        scrollable_frame.columnconfigure(3, weight=1, minsize=100)
        scrollable_frame.columnconfigure(4, weight=1, minsize=100)
        scrollable_frame.columnconfigure(5, weight=1, minsize=100)
        scrollable_frame.columnconfigure(6, weight=1, minsize=100)

        open_buttons = [
            tk.Button(
                scrollable_frame,
                text="OPEN\nPROJECT",
                fg="white",
                bg="#F21112",
                activebackground="white",
                activeforeground="#F21112",
            )
            for i in range(len(me_projects))
        ]
        add_buttons = [
            tk.Button(
                scrollable_frame,
                text="ADD TO\nGROUP",
                fg="white",
                bg="#F21112",
                activebackground="white",
                activeforeground="#F21112",
            )
            for i in range(len(me_projects))
        ]
        remove_buttons = [
            tk.Button(
                scrollable_frame,
                text="TAKE FROM\nGROUP",
                fg="white",
                bg="#F21112",
                activebackground="white",
                activeforeground="#F21112",
            )
            for i in range(len(me_projects))
        ]
        delete_buttons = [
            tk.Button(
                scrollable_frame,
                text="DELETE",
                fg="white",
                bg="#F21112",
                activebackground="white",
                activeforeground="#F21112",
            )
            for i in range(len(me_projects))
        ]

        self.new_groups = [
            [group for group in groups.find({}) if project["_id"] not in group["projects"]]
            for project in me_projects
        ]
        self.new_groups_name = [[group["name"] for group in project] for project in self.new_groups]
        self.new_groups_var = [tk.StringVar() for project in me_projects]
        self.new_group_selector = [
            ttk.Combobox(
                scrollable_frame,
                textvariable=self.new_groups_var[i],
                values=self.new_groups_name[i],
                font=("Roboto", 8),
            )
            for i in range(len(me_projects))
        ]

        self.current_groups = [
            [group for group in groups.find({}) if project["_id"] in group["projects"]]
            for project in me_projects
        ]
        self.current_groups_name = [
            [group["name"] for group in project] for project in self.current_groups
        ]
        self.current_groups_var = [tk.StringVar() for project in me_projects]
        self.current_group_selector = [
            ttk.Combobox(
                scrollable_frame,
                textvariable=self.current_groups_var[i],
                values=self.current_groups_name[i],
                font=("Roboto", 8),
            )
            for i in range(len(me_projects))
        ]

        # users = self.database.users
        for i in range(len(me_projects)):
            label_name = tk.Label(
                scrollable_frame, text=me_projects[i]["name"], bg="white", borderwidth=0
            )
            label_name["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_name.grid(row=2 * i, column=0, rowspan=2, pady=10)

            label_owner = tk.Label(
                scrollable_frame, text=me_projects[i]["owner"], bg="white", borderwidth=0
            )
            label_owner["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_owner.grid(row=2 * i, column=1, rowspan=2, pady=10)

            # now we find the groups it is in
            groups = self.database.groups
            groups_in = groups.find(
                {"projects": {"$in": [me_projects[i]["_id"]]}}, max_time_ms=5000
            )
            groups_in = [group for group in groups_in]

            groups = ""
            for group in groups_in:
                groups += group["name"] + "\n"
            groups = groups[:-1]
            if groups == "":
                groups = "N/A"

            label_groups = tk.Label(scrollable_frame, text=groups, bg="white", borderwidth=0)
            label_groups["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_groups.grid(row=2 * i, column=2, rowspan=2, pady=10)

            if me_projects[i]["owner"] == self.user["username"]:
                open_buttons[i]["command"] = lambda pos=i: self.open_from_database(
                    me_projects[pos]["_id"]
                )
                add_buttons[i]["command"] = lambda pos=i: self.add_project_to_group(
                    me_projects[pos]["_id"], self.new_groups_var[pos]
                )
                remove_buttons[i]["command"] = lambda pos=i: self.remove_project_from_group(
                    me_projects[pos]["_id"], self.current_groups_var[pos]
                )
                delete_buttons[i]["command"] = lambda pos=i: self.delete_project(
                    me_projects[pos]["_id"], me_projects[pos]["name"]
                )
                # Change the colors on enter and leave
                self._add_hover(open_buttons[i])
                open_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                open_buttons[i].grid(row=2 * i, column=3, rowspan=2, pady=10)
                self._add_hover(add_buttons[i])
                add_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                add_buttons[i].grid(row=2 * i + 1, column=4, pady=(0, 10))
                self.new_group_selector[i].grid(row=2 * i, column=4, pady=(10, 0))
                self._add_hover(remove_buttons[i])
                remove_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                remove_buttons[i].grid(row=2 * i + 1, column=5, pady=(0, 10))
                self.current_group_selector[i].grid(row=2 * i, column=5, pady=(10, 0))
                self._add_hover(delete_buttons[i])
                delete_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                delete_buttons[i].grid(row=2 * i, rowspan=2, column=6, pady=10)
            else:
                open_buttons[i]["command"] = lambda pos=i: self.open_from_database(
                    me_projects[pos]["_id"]
                )
                # Change the colors on enter and leave
                self._add_hover(open_buttons[i])
                open_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                open_buttons[i].grid(row=2 * i, column=3, rowspan=2, columnspan=4, pady=10)

    def delete_project(self, project_id, project_name):
        if tk.messagebox.askyesno(
            f"DELETE PROJECT {project_name}",
            "Are you sure you want to delete this project? This action is immediate and irreversible.",
        ):
            projects = self.database.projects
            projects.delete_one({"_id": project_id})

            groups = self.database.groups
            match_groups = groups.find({"$in": {"projects": project_id}})
            for group in match_groups:
                groups.update_one({"_id": group["_id"]}, {"$pull": {"projects": project_id}})

            self.view_projects()

    def open_from_database(self, project_id):
        projects = self.database.projects
        data = projects.find_one({"_id": project_id})
        self.open_project(data=data)
        self.erase_all_windows()

    def add_project_to_group(self, project_id, group):
        if not group.get():
            tk.messagebox.showwarning(
                "NO GROUP SELECTED", "Select a group in which to insert this project."
            )
        else:
            groups = self.database.groups
            groups.update_one({"name": group.get()}, {"$push": {"projects": project_id}})
        self.erase_all_windows()
        self.view_projects()

    def remove_project_from_group(self, project_id, group):
        if not group.get():
            tk.messagebox.showwarning(
                "NO GROUP SELECTED", "Select the group from which to remove this project."
            )
        else:
            groups = self.database.groups
            groups.update_one({"name": group.get()}, {"$pull": {"projects": project_id}})
        self.erase_all_windows()
        self.view_projects()

    def view_connections(self):
        self.erase_all_windows()

        self.connections_window = tk.Toplevel(self.master)
        self.connections_window.title("Manage CHIMERA Connections")
        self.connections_window.geometry("600x500")
        self.connections_window.configure(background="#E4E4E4")
        self.connections_window.resizable(False, False)
        self.focus_window(self.connections_window)

        self.connections_window.columnconfigure(0, weight=1, minsize=50)
        self.connections_window.columnconfigure(1, weight=1, minsize=167)
        self.connections_window.columnconfigure(2, weight=1, minsize=167)
        self.connections_window.columnconfigure(3, weight=1, minsize=167)
        self.connections_window.columnconfigure(4, weight=1, minsize=50)

        frame_data = tk.Frame(self.connections_window, bg="white")
        frame_data.grid(row=0, column=0, columnspan=5, pady=7, sticky=tk.N + tk.S)
        label1 = tk.Label(frame_data, text="Username", bg="white", fg="red")
        label1["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label1.grid(row=0, column=1)
        label2 = tk.Label(frame_data, text="Shared Groups", bg="white", fg="red")
        label2["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label2.grid(row=0, column=2)
        label3 = tk.Label(frame_data, text="Actions", bg="white", fg="red")
        label3["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label3.grid(row=0, column=3)
        data_area = tk.Canvas(frame_data, background="white", width=500, height=400)
        vscroll = tk.Scrollbar(frame_data, orient=tk.VERTICAL, command=data_area.yview)
        data_area["yscrollcommand"] = vscroll.set
        scrollable_frame = tk.Frame(data_area, bg="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: data_area.configure(scrollregion=data_area.bbox("all"))
        )
        data_area.create_window((0, 0), window=scrollable_frame, width=500)
        data_area.grid(row=1, column=1, columnspan=3, sticky=tk.N + tk.S + tk.E + tk.W)
        vscroll.grid(row=1, column=4, sticky=tk.N + tk.S + tk.E + tk.W)

        scrollable_frame.columnconfigure(0, weight=1, minsize=167)
        scrollable_frame.columnconfigure(1, weight=1, minsize=167)
        scrollable_frame.columnconfigure(2, weight=1, minsize=167)

        action_buttons = [
            tk.Button(
                scrollable_frame,
                text="REMOVE",
                fg="white",
                bg="#F21112",
                activebackground="white",
                activeforeground="#F21112",
            )
            for i in range(len(self.user["connections"]))
        ]

        users = self.database.users
        for i in range(len(self.user["connections"])):
            label_username = tk.Label(
                scrollable_frame,
                text=users.find_one({"_id": self.user["connections"][i]})["username"],
                bg="white",
                borderwidth=0,
            )
            label_username["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_username.grid(row=i + 1, column=0, pady=5)

            # now we find shared groups
            groups = self.database.groups
            shared_groups = groups.find(
                {"members": {"$all": [self.user["_id"], self.user["connections"][i]]}},
                max_time_ms=5000,
            )
            shared_groups = [group for group in shared_groups]

            groups = ""
            for group in shared_groups:
                groups += group["name"] + "\n"
            groups = groups[:-1]

            label_groups = tk.Label(scrollable_frame, text=groups, bg="white", borderwidth=0)
            label_groups["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_groups.grid(row=i + 1, column=1, pady=5)

            action_buttons[i]["command"] = lambda pos=i: self.disconnect_user(
                self.user["connections"][pos]
            )
            # Change the colors on enter and leave
            self._add_hover(action_buttons[i])
            action_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            action_buttons[i].grid(row=i + 1, column=2, pady=5)

        new_connection_button = tk.Button(
            self.connections_window,
            text="ADD CONNECTION",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        new_connection_button["command"] = self.add_connection
        new_connection_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(new_connection_button)
        new_connection_button.grid(row=2, column=2)

    def disconnect_user(self, user):
        users = self.database.users
        users.update_one({"username": self.user["username"]}, {"$pull": {"connections": user}})
        users.update_one({"_id": user}, {"$pull": {"connections": self.user["_id"]}})

        groups = self.database.groups
        groups.update_many(
            {"owner": self.user["username"], "members": {"$in": [user]}},
            {"$pull": {"members": user}},
        )

        self.user = users.find_one({"username": self.user["username"]}, max_time_ms=5000)
        self.view_connections()

    def add_connection(self):
        self.erase_all_windows()

        self.new_connect_window = tk.Toplevel(self.master)
        self.new_connect_window.title("Add CHIMERA Connections")
        self.new_connect_window.geometry("600x300")
        self.new_connect_window.configure(background="#E4E4E4")
        self.new_connect_window.resizable(False, False)
        self.focus_window(self.new_connect_window)

        text = """
        To add a connection, insert their username and their connection code.
        This connection code can be found under 'CHIMERA Online > Manage
        Account > Connection Code'.
        Only one person needs to perform this connection. Once it is done, the
        connection has been established for both users.
        """
        intro = tk.Label(self.new_connect_window, text=text, bg="#E4E4E4", justify="left")
        intro["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        intro.place(relwidth=0.9, relx=0.05, rely=0.01)

        frame_username = tk.Frame(self.new_connect_window, bg="#E4E4E4")
        label_username = tk.Label(frame_username, text="Username:", bg="#E4E4E4", anchor="w")
        label_username["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_username.place(relx=0.30, rely=0.0)
        self.username_entry = tk.Entry(frame_username, width=20, justify="left")
        self.username_entry.place(relx=0.50, rely=0.0)
        frame_username.place(relwidth=1, relheight=0.2, relx=0, rely=0.35)

        frame_code = tk.Frame(self.new_connect_window, bg="#E4E4E4")
        label_code = tk.Label(frame_code, text="Connection Code:", bg="#E4E4E4", anchor="w")
        label_code["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_code.place(relx=0.30, rely=0)
        self.code_entry = tk.Entry(frame_code, width=20, justify="left")
        self.code_entry.place(relx=0.50, rely=0)
        frame_code.place(relwidth=1, relheight=0.2, relx=0, rely=0.55)

        save_connection_button = tk.Button(
            self.new_connect_window,
            text="ADD CONNECTION",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        save_connection_button["command"] = self.finish_connection
        save_connection_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(save_connection_button)
        save_connection_button.place(relx=0.4, rely=0.8)

    def finish_connection(self):
        username = self.username_entry.get()
        connect_code = self.code_entry.get()

        users = self.database.users
        # finally we just check for repeated usernames
        try:
            other_user = users.find_one(
                {"username": username, "connect_code": connect_code}, max_time_ms=5000
            )
        except pymongo.errors.PyMongoError:
            tk.messagebox.showwarning(
                "CONNECTION ERROR",
                "Connection timed out. Make sure you have a stable internet connection.",
            )
            self.new_connect_window.destroy()
            return
        if other_user is None:
            tk.messagebox.showwarning(
                "INVALID CONNECTION",
                "The username and/or the connection code provided are incorrect.",
            )
            self.add_connection()
            return
        if other_user["_id"] in self.user["connections"]:
            tk.messagebox.showwarning(
                "REPEATED CONNECTION",
                f"A connection between you and {username} already exists.",
            )
            self.new_connect_window.destroy()
            return

        try:
            # update my account
            users.update_one(
                {"username": self.user["username"]}, {"$push": {"connections": other_user["_id"]}}
            )
            # update the other person's account
            users.update_one({"username": username}, {"$push": {"connections": self.user["_id"]}})
            self.user = users.find_one({"username": self.user["username"]}, max_time_ms=5000)
        except pymongo.errors.PyMongoError:
            tk.messagebox.showwarning(
                "CONNECTION ERROR",
                "Connection timed out. Make sure you have a stable internet connection.",
            )
            self.new_connect_window.destroy()
            return

        tk.messagebox.showinfo(
            "CONNECTION ESTABLISHED",
            f"Your connection with {username} has been stablished successfully.",
        )
        self.new_connect_window.destroy()

    def view_groups(self):
        self.erase_all_windows()

        self.groups_window = tk.Toplevel(self.master)
        self.groups_window.title("Manage CHIMERA Groups")
        self.groups_window.geometry("800x600")
        self.groups_window.configure(background="#E4E4E4")
        self.groups_window.resizable(False, False)
        self.focus_window(self.groups_window)

        self.groups_window.columnconfigure(0, weight=1, minsize=100)
        self.groups_window.columnconfigure(1, weight=1, minsize=150)
        self.groups_window.columnconfigure(2, weight=1, minsize=150)
        self.groups_window.columnconfigure(3, weight=1, minsize=150)
        self.groups_window.columnconfigure(4, weight=1, minsize=150)
        self.groups_window.columnconfigure(5, weight=1, minsize=100)

        frame_data = tk.Frame(self.groups_window, bg="white")
        frame_data.grid(row=0, column=0, columnspan=6, pady=7, sticky=tk.N + tk.S)
        label1 = tk.Label(frame_data, text="Name", bg="white", fg="red")
        label1["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label1.grid(row=0, column=1)
        label2 = tk.Label(frame_data, text="Members", bg="white", fg="red")
        label2["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label2.grid(row=0, column=2)
        label3 = tk.Label(frame_data, text="Projects", bg="white", fg="red")
        label3["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label3.grid(row=0, column=3)
        label4 = tk.Label(frame_data, text="Actions", bg="white", fg="red")
        label4["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label4.grid(row=0, column=4)
        data_area = tk.Canvas(frame_data, background="white", width=600, height=500)
        vscroll = tk.Scrollbar(frame_data, orient=tk.VERTICAL, command=data_area.yview)
        data_area["yscrollcommand"] = vscroll.set
        scrollable_frame = tk.Frame(data_area, bg="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: data_area.configure(scrollregion=data_area.bbox("all"))
        )
        data_area.create_window((0, 0), window=scrollable_frame, width=600)
        data_area.grid(row=1, column=1, columnspan=4, sticky=tk.N + tk.S + tk.E + tk.W)
        vscroll.grid(row=1, column=5, sticky=tk.N + tk.S + tk.E + tk.W)

        scrollable_frame.columnconfigure(0, weight=1, minsize=150)
        scrollable_frame.columnconfigure(1, weight=1, minsize=150)
        scrollable_frame.columnconfigure(2, weight=1, minsize=150)
        scrollable_frame.columnconfigure(3, weight=1, minsize=150)

        # now we need to find the all the groups this user is in
        groups = self.database.groups
        users = self.database.users
        projects = self.database.projects

        match_groups = groups.find({"members": {"$in": [self.user["_id"]]}}, max_time_ms=5000)

        match_groups = [group for group in match_groups]

        for i in range(len(match_groups)):
            match_groups[i]["members_name"] = [
                users.find_one({"_id": member})["username"] for member in match_groups[i]["members"]
            ]
            match_groups[i]["projects_name"] = [
                projects.find_one({"_id": project})["name"]
                for project in match_groups[i]["projects"]
            ]

        action_buttons = []
        for group in match_groups:
            if group["owner"] == self.user["username"]:
                action_buttons.append(
                    tk.Button(
                        scrollable_frame,
                        text="GROUP SETTINGS",
                        fg="white",
                        bg="#F21112",
                        activebackground="white",
                        activeforeground="#F21112",
                    )
                )
            else:
                action_buttons.append(
                    tk.Button(
                        scrollable_frame,
                        text="LEAVE GROUP",
                        fg="white",
                        bg="#F21112",
                        activebackground="white",
                        activeforeground="#F21112",
                    )
                )

        for i in range(len(action_buttons)):
            if action_buttons[i]["text"] == "LEAVE GROUP":
                action_buttons[i]["command"] = lambda pos=i: self.leave_group(
                    match_groups[pos]["_id"]
                )
            if action_buttons[i]["text"] == "GROUP SETTINGS":
                action_buttons[i]["command"] = lambda pos=i: self.group_settings(
                    match_groups[pos]["_id"], match_groups[pos]["name"]
                )
            # Change the colors on enter and leave
            self._add_hover(action_buttons[i])
            action_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))

        for i in range(len(match_groups)):
            label_name = tk.Label(
                scrollable_frame, text=match_groups[i]["name"], bg="white", borderwidth=0
            )
            label_name["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_name.grid(row=i + 1, column=0, pady=5)

            members = ""
            for member in match_groups[i]["members_name"]:
                if member == match_groups[i]["owner"]:
                    member += " (owner)"
                members += member + "\n"
            members = members[:-1]
            label_members = tk.Label(scrollable_frame, text=members, bg="white", borderwidth=0)
            label_members["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_members.grid(row=i + 1, column=1, pady=5)

            projects_names = ""
            for project in match_groups[i]["projects_name"]:
                projects_names += project + "\n"
            projects_names = projects_names[:-1]
            if projects_names == "":
                projects_names = "N/A"
            label_projects = tk.Label(
                scrollable_frame, text=projects_names, bg="white", borderwidth=0
            )
            label_projects["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_projects.grid(row=i + 1, column=2, pady=5)

            action_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            action_buttons[i].grid(row=i + 1, column=3, pady=5)

        new_connection_button = tk.Button(
            self.groups_window,
            text="CREATE GROUP",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        new_connection_button["command"] = self.add_connection
        new_connection_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(new_connection_button)
        new_connection_button.grid(row=2, column=2, columnspan=2)

    def leave_group(self, group_id):
        groups = self.database.groups
        groups.update_one({"_id": group_id}, {"$pull": {"members": self.user["_id"]}})
        self.view_groups()

    def group_settings(self, group_id, group_name):
        self.erase_all_windows()

        self.group_settings_window = tk.Toplevel(self.master)
        self.group_settings_window.title(f'Manage Group "{group_name}"')
        self.group_settings_window.geometry("800x600")
        self.group_settings_window.configure(background="#E4E4E4")
        self.group_settings_window.resizable(False, False)
        self.focus_window(self.group_settings_window)

        self.group_settings_window.columnconfigure(0, weight=1, minsize=100)
        self.group_settings_window.columnconfigure(1, weight=1, minsize=150)
        self.group_settings_window.columnconfigure(2, weight=1, minsize=150)
        self.group_settings_window.columnconfigure(3, weight=1, minsize=150)
        self.group_settings_window.columnconfigure(4, weight=1, minsize=150)
        self.group_settings_window.columnconfigure(5, weight=1, minsize=100)

        frame_data = tk.Frame(self.group_settings_window, bg="white")
        frame_data.grid(row=0, column=0, columnspan=6, pady=7, sticky=tk.N + tk.S)
        label1 = tk.Label(frame_data, text="Members", bg="white", fg="red")
        label1["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label1.grid(row=0, column=1)
        label2 = tk.Label(frame_data, text="Actions", bg="white", fg="red")
        label2["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label2.grid(row=0, column=2)
        label3 = tk.Label(frame_data, text="Projects", bg="white", fg="red")
        label3["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label3.grid(row=0, column=3)
        label4 = tk.Label(frame_data, text="Actions", bg="white", fg="red")
        label4["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label4.grid(row=0, column=4)
        data_area = tk.Canvas(frame_data, background="white", width=600, height=500)
        vscroll = tk.Scrollbar(frame_data, orient=tk.VERTICAL, command=data_area.yview)
        data_area["yscrollcommand"] = vscroll.set
        scrollable_frame = tk.Frame(data_area, bg="white")
        scrollable_frame.bind(
            "<Configure>", lambda e: data_area.configure(scrollregion=data_area.bbox("all"))
        )
        data_area.create_window((0, 0), window=scrollable_frame, width=600)
        data_area.grid(row=1, column=1, columnspan=4, sticky=tk.N + tk.S + tk.E + tk.W)
        vscroll.grid(row=1, column=5, sticky=tk.N + tk.S + tk.E + tk.W)

        scrollable_frame.columnconfigure(0, weight=1, minsize=150)
        scrollable_frame.columnconfigure(1, weight=1, minsize=150)
        scrollable_frame.columnconfigure(2, weight=1, minsize=150)
        scrollable_frame.columnconfigure(3, weight=1, minsize=150)

        groups = self.database.groups
        users = self.database.users
        projects = self.database.projects

        group = groups.find_one({"_id": group_id})

        group["members_name"] = [
            users.find_one({"_id": member})["username"] for member in group["members"]
        ]
        # group['projects_name'] = [projects.find_one({'_id': project}) for project in group['projects']]

        member_buttons = []
        for member in group["members_name"]:
            if member == group["owner"]:
                member_buttons.append("")
            else:
                member_buttons.append(
                    tk.Button(
                        scrollable_frame,
                        text="REMOVE\nMEMBER",
                        fg="white",
                        bg="#F21112",
                        activebackground="white",
                        activeforeground="#F21112",
                    )
                )
        for i in range(len(member_buttons)):
            if member_buttons[i] != "":
                member_buttons[i]["command"] = lambda pos=i: self.remove_member(
                    group["members"][pos], group["_id"], group["name"]
                )
                self._add_hover(member_buttons[i])
                member_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                member_buttons[i].grid(row=i + 1, column=1, pady=10)

                label_member = tk.Label(
                    scrollable_frame, text=group["members_name"][i], bg="white", borderwidth=0
                )
                label_member["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                label_member.grid(row=i + 1, column=0, pady=10)
            else:
                label_member = tk.Label(
                    scrollable_frame,
                    text=group["members_name"][i] + " (owner)",
                    bg="white",
                    borderwidth=0,
                )
                label_member["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
                label_member.grid(row=i + 1, column=0, pady=10)

        project_buttons = []
        for projet in group["projects"]:
            project_buttons.append(
                tk.Button(
                    scrollable_frame,
                    text="REMOVE\nPROJECT",
                    fg="white",
                    bg="#F21112",
                    activebackground="white",
                    activeforeground="#F21112",
                )
            )
        for i in range(len(project_buttons)):
            project_buttons[i]["command"] = lambda pos=i: self.remove_project(
                group["projects"][pos], group_id, group_name
            )
            self._add_hover(project_buttons[i])
            project_buttons[i]["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            project_buttons[i].grid(row=i + 1, column=3, pady=10)

            label_project = tk.Label(
                scrollable_frame,
                text=projects.find_one({"_id": group["projects"][i]})["name"],
                bg="white",
                borderwidth=0,
            )
            label_project["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
            label_project.grid(row=i + 1, column=2, pady=10)

        self.new_members = [
            connection
            for connection in [
                users.find_one({"_id": _id})["username"] for _id in self.user["connections"]
            ]
            if connection not in group["members_name"]
        ]
        self.new_members_var = tk.StringVar()
        self.members_selector = ttk.Combobox(
            self.group_settings_window,
            textvariable=self.new_members_var,
            values=self.new_members,
            font=("Roboto", 8),
        )
        self.members_selector.grid(row=2, column=2)

        new_member_button = tk.Button(
            self.group_settings_window,
            text="ADD MEMBER",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        new_member_button["command"] = lambda: self.add_member(group_id, group_name)
        new_member_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(new_member_button)
        new_member_button.grid(row=3, column=2)

        delete_group_button = tk.Button(
            self.group_settings_window,
            text="ERASE GROUP",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        delete_group_button["command"] = lambda: self.delete_group(group_id, group_name)
        delete_group_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(delete_group_button)
        delete_group_button.grid(row=3, column=3)

    def add_member(self, group_id, group_name):
        if self.new_members_var.get() == "":
            tk.messagebox.showwarning("USER NOT SELECTED", "Select a user to add as new member.")
            self.group_settings(group_id, group_name)
            return

        groups = self.database.groups
        users = self.database.users
        groups.update_one(
            {"_id": group_id},
            {"$push": {"members": users.find_one({"username": self.new_members_var.get()})["_id"]}},
        )
        self.group_settings(group_id, group_name)

    def remove_member(self, member_id, group_id, group_name):
        groups = self.database.groups
        groups.update_one({"_id": group_id}, {"$pull": {"members": member_id}})
        self.group_settings(group_id, group_name)

    def remove_project(self, project_id, group_id, group_name):
        groups = self.database.groups
        groups.update_one({"_id": group_id}, {"$pull": {" projects": project_id}})
        self.group_settings(group_id, group_name)

    def delete_group(self, group_id, group_name):
        if tk.messagebox.askyesno(
            f"DELETE GROUP {group_name}",
            "Are you sure you want to delete this group? This action is immediate and irreversible.",
        ):
            groups = self.database.groups
            groups.delete_one({"_id": group_id})
            self.erase_all_windows()

    def logout(self):
        del self.user
        self.database.close()
        del self.database

        tk.messagebox.showinfo("LOGOUT SUCCESSFUL", "You have been successfully logged out.")
        self.online.delete("Logout")
        self.online.delete("Manage Account")
        self.online.delete("Manage Connections")
        self.online.delete("Manage Projects")
        self.online.delete("Manage Groups")
        self.online.add_command(label="Login", command=self.create_login, accelerator="Ctrl+L")
        self.master.bind("<Control-L>", self.create_login)
        self.master.bind("<Control-l>", self.create_login)
        self.online.add_command(label="Create Account", command=self.setup_account)
        self.file_options.delete("Save to Database")
        self.master.unbind("<Control-D>")
        self.master.unbind("<Control-d>")

    def setup_account(self, event=None):
        self.erase_all_windows()

        self.new_account_window = tk.Toplevel(self.master)
        self.new_account_window.title("Create CHIMERA Account")
        self.new_account_window.geometry("500x300")
        self.new_account_window.configure(background="#E4E4E4")
        self.new_account_window.resizable(False, False)
        self.focus_window(self.new_account_window)

        text = """
        Welcome to CHIMERA Online! In order to access the database where you can
        store your projects you first need to create an account.
        Please fill in the fields below.
        """
        intro = tk.Label(self.new_account_window, text=text, bg="#E4E4E4", justify="left")
        intro["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        intro.place(relwidth=0.9, relx=0.05, rely=0.02)

        frame_username = tk.Frame(self.new_account_window, bg="#E4E4E4")
        label_username = tk.Label(frame_username, text="Username:", bg="#E4E4E4", anchor="w")
        label_username["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_username.place(relx=0.32, rely=0.0)
        self.username_entry = tk.Entry(frame_username, width=20, justify="left")
        self.username_entry.place(relx=0.48, rely=0.0)
        frame_username.place(relwidth=1, relheight=0.15, relx=0, rely=0.25)

        frame_email = tk.Frame(self.new_account_window, bg="#E4E4E4")
        label_email = tk.Label(frame_email, text="Email:", bg="#E4E4E4", anchor="w")
        label_email["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_email.place(relx=0.32, rely=0)
        self.email_entry = tk.Entry(frame_email, width=20, justify="left")
        self.email_entry.place(relx=0.48, rely=0)
        frame_email.place(relwidth=1, relheight=0.15, relx=0, rely=0.4)

        frame_password = tk.Frame(self.new_account_window, bg="#E4E4E4")
        label_password = tk.Label(frame_password, text="Password:", bg="#E4E4E4", anchor="w")
        label_password["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_password.place(relx=0.32, rely=0)
        self.password_entry = tk.Entry(frame_password, show="*", width=20, justify="left")
        self.password_entry.place(relx=0.48, rely=0)
        self.button_show = tk.Button(
            frame_password,
            text="Show",
            bg="#E4E4E4",
            activebackground="#E4E4E4",
            highlightthickness=0,
            borderwidth=0,
            command=self.toggle_pass,
            cursor="hand2",
            takefocus=0,
        )
        self.button_show["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        self.button_show.place(relx=0.75, rely=0)
        frame_password.place(relwidth=1, relheight=0.15, relx=0, rely=0.55)

        create_account_button = tk.Button(
            self.new_account_window,
            text="CREATE ACCOUNT",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        create_account_button["command"] = self.save_account
        create_account_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(create_account_button)
        create_account_button.place(rely=0.7, relx=0.36)

    def save_account(self, event=None):
        if not self.load_db_credentials():
            return

        # first we need to do some tests
        username = self.username_entry.get()
        password = self.password_entry.get()
        email = self.email_entry.get()

        # regular expression to validate email
        regex = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"

        # tests on the username
        if " " in username or "\t" in username:
            tk.messagebox.showwarning(
                "INVALID USERNAME", "Username cannot contain whitespace (spaces, tabs,...)."
            )
            if not hasattr(self, "user"):
                self.setup_account()
            else:
                self.edit_account()
            return
        elif len(username) == 0:
            tk.messagebox.showwarning(
                "INVALID USERNAME", "Username needs to have at least one character."
            )
            if not hasattr(self, "user"):
                self.setup_account()
            else:
                self.edit_account()
            return

        # tests on the password
        elif " " in password or "\t" in password:
            tk.messagebox.showwarning(
                "INVALID PASSWORD", "Password cannot contain whitespace (spaces, tabs,...)."
            )
            if not hasattr(self, "user"):
                self.setup_account()
            else:
                self.edit_account()
            return
        elif len(password) < 8:
            tk.messagebox.showwarning(
                "INVALID PASSWORD", "Password needs to have at least 8 characters."
            )
            if not hasattr(self, "user"):
                self.setup_account()
            else:
                self.edit_account()
            return

        # tests on the email
        elif not re.fullmatch(regex, email):
            tk.messagebox.showwarning("INVALID EMAIL", "Please provide a valid email address.")
            if not hasattr(self, "user"):
                self.setup_account()
            else:
                self.edit_account()
            return

        update = hasattr(self, "user")

        # Hash the (new) password for storage: 32-byte salt followed by the key.
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        hashed_pass = salt + key

        if update:
            # Preserve the existing connection code, connections and projects.
            user = {
                "username": username,
                "password": hashed_pass,  # first 32 bytes are the salt, rest is the key
                "email": email,
                "connect_code": self.user["connect_code"],
                "connections": self.user.get("connections", []),
                "projects": self.user.get("projects", []),
            }
        else:
            # New account: generate a unique connection code.
            characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
            connect_code = "".join(secrets.choice(characters) for _ in range(10))
            user = {
                "username": username,
                "password": hashed_pass,  # first 32 bytes are the salt, rest is the key
                "email": email,
                "connect_code": connect_code,
                "connections": [],
                "projects": [],
            }

        if not hasattr(self, "database"):
            try:
                self.database = ChimeraDB.connect(self.database_username, self.database_password)
            except pymongo.errors.PyMongoError:
                tk.messagebox.showwarning(
                    "CONNECTION ERROR",
                    "Connection timed out after 5 seconds. Make sure you have a stable internet connection.",
                )
                self.new_account_window.destroy()
                return

        # finally we just check for repeated usernames
        try:
            temp = self.database.find_user(user["username"])
        except pymongo.errors.PyMongoError:
            tk.messagebox.showwarning(
                "CONNECTION ERROR",
                "Connection timed out. Make sure you have a stable internet connection.",
            )
            self.new_account_window.destroy()
            return
        if temp is not None and not (update and temp["_id"] == self.user["_id"]):
            tk.messagebox.showwarning(
                "INVALID USERNAME",
                "The username provided is already connected to an existing account. Please select a different, unique username.",
            )
            if update:
                self.edit_account()
            else:
                self.setup_account()
            return

        if update:
            try:
                self.database.replace_user_fields(self.user["username"], user)
                self.user = self.database.find_user(self.user["username"])
            except pymongo.errors.PyMongoError:
                tk.messagebox.showwarning(
                    "CONNECTION ERROR",
                    "Connection timed out. Make sure you have a stable internet connection.",
                )
                self.edit_account_window.destroy()
                return

            tk.messagebox.showinfo("ACCOUNT EDITED", "The account has been edited successfully!")
            self.edit_account_window.destroy()
            self.logout()
        else:
            try:
                self.database.insert_user(user)
            except pymongo.errors.PyMongoError:
                tk.messagebox.showwarning(
                    "CONNECTION ERROR",
                    "Connection timed out. Make sure you have a stable internet connection.",
                )
                self.new_account_window.destroy()
                return
            tk.messagebox.showinfo("ACCOUNT CREATED", "The account has been created successfully!")
            self.new_account_window.destroy()

    def edit_account(self, event=None):
        self.erase_all_windows()

        self.edit_account_window = tk.Toplevel(self.master)
        self.edit_account_window.title("Edit CHIMERA Account")
        self.edit_account_window.geometry("600x300")
        self.edit_account_window.configure(background="#E4E4E4")
        self.edit_account_window.resizable(False, False)
        self.focus_window(self.edit_account_window)

        text = """
        Here you can manage your account. All changes are immediate and
        after performing them you will have to login again. Just correct
        the entries below to the updated values to edit your account.
        """
        intro = tk.Label(self.edit_account_window, text=text, bg="#E4E4E4", justify="left")
        intro["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        intro.place(relwidth=0.9, relx=0.05, rely=0.01)

        frame_username = tk.Frame(self.edit_account_window, bg="#E4E4E4")
        label_username = tk.Label(frame_username, text="Username:", bg="#E4E4E4", anchor="w")
        label_username["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_username.place(relx=0.30, rely=0.0)
        self.username_entry = tk.Entry(frame_username, width=20, justify="left")
        self.username_entry.place(relx=0.50, rely=0.0)
        self.username_entry.insert(0, self.user["username"])
        frame_username.place(relwidth=1, relheight=0.15, relx=0, rely=0.25)

        frame_email = tk.Frame(self.edit_account_window, bg="#E4E4E4")
        label_email = tk.Label(frame_email, text="Email:", bg="#E4E4E4", anchor="w")
        label_email["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_email.place(relx=0.30, rely=0)
        self.email_entry = tk.Entry(frame_email, width=20, justify="left")
        self.email_entry.place(relx=0.50, rely=0)
        self.email_entry.insert(0, self.user["email"])
        frame_email.place(relwidth=1, relheight=0.15, relx=0, rely=0.4)

        frame_password = tk.Frame(self.edit_account_window, bg="#E4E4E4")
        label_password = tk.Label(frame_password, text="Password:", bg="#E4E4E4", anchor="w")
        label_password["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_password.place(relx=0.30, rely=0)
        self.password_entry = tk.Entry(frame_password, show="*", width=20, justify="left")
        self.password_entry.place(relx=0.50, rely=0)
        # The plaintext password is never stored, so the field starts empty; the
        # user must re-enter a password (min 8 chars) to save account changes.
        self.button_show = tk.Button(
            frame_password,
            text="Show",
            bg="#E4E4E4",
            activebackground="#E4E4E4",
            highlightthickness=0,
            borderwidth=0,
            command=self.toggle_pass,
            cursor="hand2",
        )
        self.button_show["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        self.button_show.place(relx=0.75, rely=0)
        frame_password.place(relwidth=1, relheight=0.15, relx=0, rely=0.55)

        frame_connection = tk.Frame(self.edit_account_window, bg="#E4E4E4")
        label_connection = tk.Label(
            frame_connection, text="Connection Code:", bg="#E4E4E4", anchor="w"
        )
        label_connection["font"] = ("Roboto", int(15 * self.master.winfo_width() / 2350))
        label_connection.place(relx=0.30, rely=0)
        connection_entry = tk.Entry(
            frame_connection, width=20, justify="left", cursor="arrow", takefocus=0
        )
        connection_entry.place(relx=0.50, rely=0)
        connection_entry.insert(0, self.user["connect_code"])
        connection_entry.config(state="readonly")
        frame_connection.place(relwidth=1, relheight=0.15, relx=0, rely=0.7)

        create_account_button = tk.Button(
            self.edit_account_window,
            text="EDIT ACCOUNT",
            fg="white",
            bg="#F21112",
            activebackground="white",
            activeforeground="#F21112",
        )
        create_account_button["command"] = self.save_account
        create_account_button["font"] = ("Roboto", int(20 * self.master.winfo_width() / 2350))
        # Change the colors on enter and leave
        self._add_hover(create_account_button)
        create_account_button.place(rely=0.85, relx=0.40)
