"""Fenêtre de réglages des règles de nettoyage des titres."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import customtkinter as ctk


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master: ctk.CTk, settings: dict[str, Any], on_save: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(master)
        self.title("Réglages — Sonore")
        self.geometry("760x580")
        self.minsize(650, 480)
        self.transient(master)
        self.grab_set()
        self.settings = settings
        self.on_save = on_save
        self.removals = list(settings.get("removals", []))
        self.replacements = list(settings.get("replacements", []))
        self._build()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        tabs = ctk.CTkTabview(self)
        tabs.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 8))
        remove_tab = tabs.add("Suppression")
        replace_tab = tabs.add("Remplacement")
        self._build_removals(remove_tab)
        self._build_replacements(replace_tab)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 16))
        ctk.CTkButton(footer, text="Fermer", width=100, fg_color="#30353d", hover_color="#414752", command=self.destroy).pack(side="right", padx=(8, 0))
        ctk.CTkButton(footer, text="Enregistrer", width=125, command=self._save).pack(side="right")

    def _build_removals(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(parent, text="Retirer des séquences des titres", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 10))
        self.remove_list = ctk.CTkScrollableFrame(parent, label_text="Séquences enregistrées")
        self.remove_list.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self._render_removals()
        add = ctk.CTkFrame(parent, fg_color="transparent")
        add.grid(row=2, column=0, sticky="ew", padx=16, pady=16)
        self.remove_entry = ctk.CTkEntry(add, placeholder_text="Ex. (clip officiel)")
        self.remove_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.remove_entry.bind("<Return>", lambda _: self._add_removal())
        ctk.CTkButton(add, text="Ajouter", width=90, command=self._add_removal).pack(side="right")

    def _render_removals(self) -> None:
        for widget in self.remove_list.winfo_children():
            widget.destroy()
        if not self.removals:
            ctk.CTkLabel(self.remove_list, text="Aucune séquence — les titres restent inchangés.", text_color="#8a929d").pack(anchor="w", padx=12, pady=10)
        for index, value in enumerate(self.removals):
            row = ctk.CTkFrame(self.remove_list, fg_color="#1c2025")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=value, anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkButton(row, text="Supprimer", width=82, height=28, fg_color="#30353d", hover_color="#664247", command=lambda i=index: self._delete_removal(i)).pack(side="right", padx=8, pady=6)

    def _add_removal(self) -> None:
        value = self.remove_entry.get().strip()
        if value and value not in self.removals:
            self.removals.append(value)
            self._render_removals()
        self.remove_entry.delete(0, tk.END)

    def _delete_removal(self, index: int) -> None:
        del self.removals[index]
        self._render_removals()

    def _build_replacements(self, parent: ctk.CTkFrame) -> None:
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        self.replace_list = ctk.CTkScrollableFrame(parent, label_text="Règles de remplacement")
        self.replace_list.grid(row=0, column=0, sticky="nsew", padx=16, pady=(16, 8))
        self._render_replacements()
        form = ctk.CTkFrame(parent, fg_color="#1c2025", corner_radius=12)
        form.grid(row=1, column=0, sticky="ew", padx=16, pady=(8, 16))
        form.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(form, text="Séquence recherchée").grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(form, text="Remplacer par").grid(row=0, column=1, sticky="w", padx=12, pady=(12, 4))
        self.find_entry = ctk.CTkEntry(form, placeholder_text="Ex. Official Video")
        self.find_entry.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.replace_entry = ctk.CTkEntry(form, placeholder_text="Ex. Audio")
        self.replace_entry.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 8))
        self.append_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(form, text="Ajouter le remplacement à la fin du titre", variable=self.append_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))
        ctk.CTkButton(form, text="Ajouter la règle", width=130, command=self._add_replacement).grid(row=3, column=1, sticky="e", padx=12, pady=(0, 12))
        self.find_entry.bind("<Return>", lambda _: self._add_replacement())
        self.replace_entry.bind("<Return>", lambda _: self._add_replacement())

    def _render_replacements(self) -> None:
        for widget in self.replace_list.winfo_children():
            widget.destroy()
        if not self.replacements:
            ctk.CTkLabel(self.replace_list, text="Aucune règle de remplacement enregistrée.", text_color="#8a929d").pack(anchor="w", padx=12, pady=10)
        for index, rule in enumerate(self.replacements):
            row = ctk.CTkFrame(self.replace_list, fg_color="#1c2025")
            row.pack(fill="x", pady=3)
            mode = "ajouté à la fin" if rule.get("append") else "remplacé sur place"
            label = f"{rule['find']}  →  {rule['replace'] or '∅'}  ·  {mode}"
            ctk.CTkLabel(row, text=label, anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=8)
            ctk.CTkButton(row, text="Supprimer", width=82, height=28, fg_color="#30353d", hover_color="#664247", command=lambda i=index: self._delete_replacement(i)).pack(side="right", padx=8, pady=6)

    def _add_replacement(self) -> None:
        find = self.find_entry.get().strip()
        if find:
            self.replacements.append({"find": find, "replace": self.replace_entry.get(), "append": self.append_var.get()})
            self._render_replacements()
            self.find_entry.delete(0, tk.END)
            self.replace_entry.delete(0, tk.END)
            self.append_var.set(False)

    def _delete_replacement(self, index: int) -> None:
        del self.replacements[index]
        self._render_replacements()

    def _save(self) -> None:
        self.on_save({"removals": self.removals, "replacements": self.replacements})
        self.destroy()
