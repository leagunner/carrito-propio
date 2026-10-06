from __future__ import annotations

import copy
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from catalog_manager import COLLECTION_ORDER_KEY, EXPLANATORY_GUIDES_KEY, CatalogError, CatalogManager, CUSTOM_LISTS_KEY


class CatalogApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Administrador de listas | Metalúrgica Exhibe")
        self.geometry("1280x760")
        self.minsize(980, 620)
        self.manager: CatalogManager | None = None
        self.data: dict = {}
        self.current_collection = ""
        self.current_index: int | None = None
        self.custom_list_draft: dict | None = None
        self.custom_list_window: tk.Toplevel | None = None
        self.custom_list_editor: ttk.Frame | None = None
        self._editor_commit = None
        self._build_ui()
        self.after_idle(self._load_default_project)

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self, padding=12)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.rowconfigure(1, weight=1)
        ttk.Label(sidebar, text="Colecciones", font=("Segoe UI", 12, "bold")).grid(sticky="w")
        self.collections = tk.Listbox(sidebar, width=28, exportselection=False)
        self.collections.grid(row=1, sticky="nsew", pady=(8, 8))
        self.collections.bind("<<ListboxSelect>>", self._select_collection)
        collection_order_buttons = ttk.Frame(sidebar)
        collection_order_buttons.grid(row=2, sticky="ew")
        collection_order_buttons.columnconfigure(0, weight=1)
        collection_order_buttons.columnconfigure(1, weight=1)
        ttk.Button(collection_order_buttons, text="Subir", command=lambda: self._move_selected_collection(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(collection_order_buttons, text="Bajar", command=lambda: self._move_selected_collection(1)).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        ttk.Button(sidebar, text="Editar lista", command=self._edit_selected_list).grid(sticky="ew", pady=(8, 0))
        ttk.Button(sidebar, text="Nueva lista personalizada", command=self._new_custom_list).grid(sticky="ew")
        ttk.Button(sidebar, text="Exportar precios Excel", command=self._export_prices_excel).grid(sticky="ew", pady=(6, 0))
        ttk.Button(sidebar, text="Importar precios Excel", command=self._import_prices_excel).grid(sticky="ew")
        ttk.Button(sidebar, text="Elegir lista JSON", command=self._choose_project).grid(sticky="ew", pady=(6, 0))
        ttk.Button(sidebar, text="Eliminar lista seleccionada", command=self._delete_selected_collection).grid(sticky="ew", pady=(6, 0))

        main = ttk.Frame(self, padding=(0, 12, 12, 12))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        self.collection_title = ttk.Label(main, text="Selecciona una colección", font=("Segoe UI", 15, "bold"))
        self.collection_title.grid(row=0, column=0, sticky="w", pady=(0, 8))

        content = ttk.PanedWindow(main, orient="horizontal")
        content.grid(row=1, column=0, sticky="nsew")
        left = ttk.Frame(content, padding=(0, 0, 10, 0))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text="Elementos").grid(sticky="w")
        self.items = tk.Listbox(left, exportselection=False)
        self.items.grid(row=1, sticky="nsew", pady=(6, 8))
        self.items.bind("<<ListboxSelect>>", self._select_item)
        item_order_buttons = ttk.Frame(left)
        item_order_buttons.grid(row=2, sticky="ew", pady=(0, 4))
        item_order_buttons.columnconfigure(0, weight=1)
        item_order_buttons.columnconfigure(1, weight=1)
        ttk.Button(item_order_buttons, text="Subir", command=lambda: self._move_selected_item(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(item_order_buttons, text="Bajar", command=lambda: self._move_selected_item(1)).grid(row=0, column=1, sticky="ew", padx=(3, 0))
        item_buttons = ttk.Frame(left)
        item_buttons.grid(row=3, sticky="ew")
        for column in range(4):
            item_buttons.columnconfigure(column, weight=1)
        ttk.Button(item_buttons, text="Nuevo", command=self._new_item).grid(row=0, column=0, sticky="ew")
        ttk.Button(item_buttons, text="Duplicar", command=self._duplicate_item).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(item_buttons, text="Eliminar", command=self._delete_item).grid(row=0, column=2, sticky="ew")
        ttk.Button(item_buttons, text="Guardar", command=self._save).grid(row=0, column=3, sticky="ew", padx=(4, 0))
        content.add(left, weight=1)

        self.editor = ttk.Frame(content, padding=(10, 0, 0, 0))
        self.editor.columnconfigure(1, weight=1)
        content.add(self.editor, weight=3)
        self.status = ttk.Label(self, text="", relief="sunken", anchor="w", padding=5)
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _choose_project(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecciona el archivo JSON del catálogo",
            filetypes=[("Archivo JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if not selected:
            return
        self._load_project(selected)

    def _load_default_project(self) -> None:
        default_path = Path(__file__).resolve().parent.parent / "src" / "data" / "productos.json"
        if default_path.is_file():
            self._load_project(default_path)
            return
        self._choose_project()

    def _load_project(self, selected: str | Path) -> None:
        manager = CatalogManager(selected)
        try:
            data = manager.load()
        except CatalogError as error:
            messagebox.showerror("Catálogo no válido", str(error))
            return
        self.manager, self.data = manager, data
        self._ensure_collection_order()
        self._refresh_collections()
        self.status.config(text=f"JSON: {manager.json_path}")

    def _edit_selected_list(self) -> None:
        selected = self._selected_collection()
        if not selected:
            messagebox.showinfo("Editar lista", "Selecciona una lista personalizada primero.")
            return
        key, custom_list = selected
        if key != CUSTOM_LISTS_KEY:
            messagebox.showwarning("Lista protegida", "Solo se puede editar la estructura de listas personalizadas.")
            return
        self._open_custom_list_editor(custom_list)

    def _open_custom_list_editor(self, custom_list: dict | None = None) -> None:
        if not self.manager:
            return
        if self.custom_list_window and self.custom_list_window.winfo_exists():
            self.custom_list_window.deiconify()
            self.custom_list_window.lift()
            self.custom_list_window.focus_force()
            return
        self.custom_list_window = tk.Toplevel(self)
        self.custom_list_window.title("Editar lista" if custom_list else "Nueva lista personalizada")
        self.custom_list_window.geometry("1050x680")
        self.custom_list_window.minsize(780, 500)
        self.custom_list_window.columnconfigure(0, weight=1)
        self.custom_list_window.rowconfigure(0, weight=1)
        self.custom_list_editor = ttk.Frame(self.custom_list_window, padding=16)
        self.custom_list_editor.grid(row=0, column=0, sticky="nsew")
        self.custom_list_editor.columnconfigure(1, weight=1)
        self.custom_list_editor.rowconfigure(3, weight=1)
        self.custom_list_window.protocol("WM_DELETE_WINDOW", self._cancel_custom_list)
        self.custom_list_draft = {
            "mode": "edit" if custom_list else "create",
            "target": custom_list,
            "title": tk.StringVar(self.custom_list_window, value=custom_list["titulo"] if custom_list else "Nueva lista"),
            "columns": [],
            "rows": [],
        }
        if custom_list:
            for column in custom_list["columnas"]:
                self.custom_list_draft["columns"].append({
                    "clave": column["clave"],
                    "nombre": tk.StringVar(self.custom_list_window, value=column["nombre"]),
                })
        else:
            for index in range(1, 4):
                self._draft_add_column(f"Columna {index}")
            self._draft_add_row()
        self._show_custom_list_builder()

    def _refresh_collections(self) -> None:
        self.collections.delete(0, tk.END)
        for collection_key, label, _value in self._collection_entries():
            self.collections.insert(tk.END, label)
        if self.collections.size():
            self.collections.selection_clear(0, tk.END)
            self.collections.selection_set(0)
            self.collections.activate(0)
            self._select_collection()

    def _ensure_collection_order(self) -> None:
        original_keys = [key for key in self.data if key not in {CUSTOM_LISTS_KEY, COLLECTION_ORDER_KEY, EXPLANATORY_GUIDES_KEY}]
        custom_keys = [f"lista:{item['clave']}" for item in self.data.get(CUSTOM_LISTS_KEY, [])]
        available = original_keys + custom_keys
        current = self.data.get(COLLECTION_ORDER_KEY, [])
        self.data[COLLECTION_ORDER_KEY] = [key for key in current if key in available]
        self.data[COLLECTION_ORDER_KEY].extend(key for key in available if key not in self.data[COLLECTION_ORDER_KEY])

    def _collection_entries(self) -> list[tuple[str, str, list | dict]]:
        entries = []
        custom_by_key = {f"lista:{item['clave']}": item for item in self.data.get(CUSTOM_LISTS_KEY, [])}
        for key in self.data.get(COLLECTION_ORDER_KEY, []):
            if key in custom_by_key:
                custom_list = custom_by_key[key]
                entries.append((key, f"{custom_list['titulo']}  [{custom_list['clave']}]", custom_list))
            elif key in self.data and key not in {CUSTOM_LISTS_KEY, COLLECTION_ORDER_KEY, EXPLANATORY_GUIDES_KEY}:
                entries.append((key, key, self.data[key]))
        return entries

    def _selected_collection(self) -> tuple[str, list] | None:
        selection = self.collections.curselection()
        if not selection:
            return None
        position = selection[0]
        entries = self._collection_entries()
        if position < len(entries):
            key, _label, value = entries[position]
            return (CUSTOM_LISTS_KEY, value) if key.startswith("lista:") else (key, value)
        return None

    def _move_selected_collection(self, direction: int) -> None:
        selection = self.collections.curselection()
        if not selection:
            return
        current = selection[0]
        target = current + direction
        order = self.data.get(COLLECTION_ORDER_KEY, [])
        if target < 0 or target >= len(order):
            return
        order[current], order[target] = order[target], order[current]
        self._refresh_collections()
        self.collections.selection_set(target)
        self.collections.activate(target)
        self._select_collection()
        self.status.config(text="Orden actualizado en memoria. Pulsa Guardar para escribir el JSON.")

    def _select_collection(self, _event: object | None = None) -> None:
        self._commit_active_editor()
        selected = self._selected_collection()
        if not selected:
            return
        key, value = selected
        self.current_collection, self.current_index = key, None
        if key == CUSTOM_LISTS_KEY:
            self.collection_title.config(text=value["titulo"])
            self._fill_items(value["filas"], lambda _row, index: f"Fila {index}")
        else:
            self.collection_title.config(text=key)
            self._fill_items(value, lambda product, _index: f"{product.get('id', '?')} - {product.get('nombre', 'Sin nombre')}")
        self._clear_editor()
        self._show_collection_guide_button()

    def _selected_collection_key(self) -> str | None:
        selection = self.collections.curselection()
        if not selection:
            return None
        entries = self._collection_entries()
        position = selection[0]
        return entries[position][0] if position < len(entries) else None

    def _show_collection_guide_button(self) -> None:
        if not self.manager:
            return
        ttk.Label(self.editor, text="Material explicativo de la lista", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, sticky="w", pady=(18, 4))
        ttk.Button(self.editor, text="Administrar imágenes explicativas", command=self._show_collection_guide).grid(row=1, column=1, sticky="w", pady=(18, 4))

    def _show_collection_guide(self) -> None:
        if not self.manager:
            return
        collection_key = self._selected_collection_key()
        if not collection_key:
            return
        self._clear_editor()
        ttk.Label(self.editor, text=f"Material explicativo: {collection_key}", font=("Segoe UI", 12, "bold")).grid(columnspan=2, sticky="w")
        guides = self.data.setdefault(EXPLANATORY_GUIDES_KEY, {}).setdefault(collection_key, [])
        guide = tk.Listbox(self.editor, height=10, selectmode=tk.SINGLE, exportselection=False)
        guide.grid(row=1, column=1, sticky="ew", pady=(14, 4))
        for media in guides:
            media_type = media.get("tipo", "imagen")
            guide.insert(tk.END, f"{media_type}: {media['src']} | {media['alt']}")
        preview = self._create_gallery_preview(guide, {"galeria": guides})
        preview.grid(row=1, column=0, sticky="nsew", padx=(0, 12), pady=(14, 4))
        self.editor.rowconfigure(1, minsize=220, weight=0)
        buttons = ttk.Frame(self.editor)
        buttons.grid(row=2, column=1, sticky="w")
        ttk.Button(buttons, text="Agregar imágenes", command=lambda: self._add_explanatory_images(collection_key, guide)).pack(side="left")
        ttk.Button(buttons, text="Agregar YouTube", command=lambda: self._add_explanatory_youtube(collection_key, guide)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Subir", command=lambda: self._move_guide(collection_key, guide, -1)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Bajar", command=lambda: self._move_guide(collection_key, guide, 1)).pack(side="left")
        ttk.Button(buttons, text="Editar texto descriptivo", command=lambda: self._edit_guide_description(collection_key, guide)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Quitar seleccionado", command=lambda: self._remove_guide(collection_key, guide)).pack(side="left", padx=6)
        ttk.Button(self.editor, text="Volver a la lista", command=self._select_collection).grid(row=3, column=1, sticky="e", pady=14)

    def _add_explanatory_images(self, collection_key: str, guide: tk.Listbox) -> None:
        if not self.manager:
            return
        sources = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.gif"), ("Todos", "*.*")])
        if not sources:
            return
        guides = self.data.setdefault(EXPLANATORY_GUIDES_KEY, {}).setdefault(collection_key, [])
        added = 0
        errors: list[str] = []
        for source in sources:
            try:
                route = self.manager.copy_explanatory_image(source, collection_key)
            except CatalogError as error:
                errors.append(f"{Path(source).name}: {error}")
                continue
            image = {"tipo": "imagen", "src": route, "alt": Path(source).stem}
            guides.append(image)
            guide.insert(tk.END, f"{route} | {image['alt']}")
            guide.selection_clear(0, tk.END)
            guide.selection_set(guide.size() - 1)
            guide.activate(guide.size() - 1)
            guide.event_generate("<<ListboxSelect>>")
            added += 1
        if errors:
            messagebox.showwarning("Algunas imágenes no se agregaron", "\n".join(errors))
        if added:
            self.status.config(text=f"{added} imagen(es) explicativa(s) agregada(s) en memoria. Pulsa Guardar para escribir el JSON.")

    def _add_explanatory_youtube(self, collection_key: str, guide: tk.Listbox) -> None:
        if not self.manager:
            return
        url = simpledialog.askstring("Video explicativo de YouTube", "Pega la URL del video:")
        if not url:
            return
        try:
            valid_url = self.manager.youtube_url(url)
        except CatalogError as error:
            messagebox.showerror("URL no válida", str(error))
            return
        alt = simpledialog.askstring("Descripción del video", "Texto para la guía:", initialvalue="Video explicativo")
        if alt is None:
            return
        alt = alt.strip() or "Video explicativo"
        media = {"tipo": "video", "src": valid_url, "alt": alt}
        guides = self.data.setdefault(EXPLANATORY_GUIDES_KEY, {}).setdefault(collection_key, [])
        guides.append(media)
        guide.insert(tk.END, f"video: {valid_url} | {alt}")
        self.status.config(text="Video explicativo agregado en memoria. Pulsa Guardar para escribir el JSON.")

    def _edit_guide_description(self, collection_key: str, guide: tk.Listbox) -> None:
        selection = guide.curselection()
        if not selection:
            messagebox.showinfo("Editar texto descriptivo", "Selecciona una imagen o video primero.")
            return
        selected_index = selection[0]
        guides = self.data[EXPLANATORY_GUIDES_KEY][collection_key]
        media = guides[selected_index]
        description = simpledialog.askstring(
            "Editar texto descriptivo",
            "Texto descriptivo accesible:",
            initialvalue=media.get("alt", ""),
        )
        if description is None:
            return
        description = description.strip()
        if not description:
            messagebox.showerror("Texto no válido", "El texto descriptivo no puede estar vacío.")
            return
        media["alt"] = description
        media_type = media.get("tipo", "imagen")
        guide.delete(selected_index)
        guide.insert(selected_index, f"{media_type}: {media['src']} | {description}")
        guide.selection_set(selected_index)
        guide.activate(selected_index)
        self.status.config(text="Texto descriptivo actualizado en memoria. Pulsa Guardar para escribir el JSON.")

    def _move_guide(self, collection_key: str, guide: tk.Listbox, direction: int) -> None:
        selection = guide.curselection()
        if not selection:
            return
        current_index = selection[0]
        guides = self.data[EXPLANATORY_GUIDES_KEY][collection_key]
        target_index = current_index + direction
        if target_index < 0 or target_index >= len(guides):
            return
        guides[current_index], guides[target_index] = guides[target_index], guides[current_index]
        self._show_collection_guide()
        self.status.config(text="Orden de la guía actualizado en memoria. Pulsa Guardar para escribir el JSON.")

    def _remove_guide(self, collection_key: str, guide: tk.Listbox) -> None:
        selection = guide.curselection()
        if not selection:
            return
        del self.data[EXPLANATORY_GUIDES_KEY][collection_key][selection[0]]
        self._show_collection_guide()
        self.status.config(text="Imagen explicativa quitada en memoria. Pulsa Guardar para escribir el JSON.")

    def _fill_items(self, values: list, label) -> None:
        self.items.delete(0, tk.END)
        for index, value in enumerate(values, start=1):
            self.items.insert(tk.END, label(value, index))

    @staticmethod
    def _move_item(values: list, current_index: int, direction: int) -> int | None:
        target_index = current_index + direction
        if target_index < 0 or target_index >= len(values):
            return None
        values[current_index], values[target_index] = values[target_index], values[current_index]
        return target_index

    def _move_selected_item(self, direction: int) -> None:
        selection = self.items.curselection()
        selected = self._selected_collection()
        if not selection or not selected:
            return
        self._commit_active_editor()
        key, values = selected
        items = values["filas"] if key == CUSTOM_LISTS_KEY else values
        target_index = self._move_item(items, selection[0], direction)
        if target_index is None:
            return
        if key == CUSTOM_LISTS_KEY:
            self._fill_items(items, lambda _row, index: f"Fila {index}")
        else:
            self._fill_items(items, lambda product, _index: f"{product.get('id', '?')} - {product.get('nombre', 'Sin nombre')}")
        self.items.selection_set(target_index)
        self.items.activate(target_index)
        self.items.see(target_index)
        self._select_item()
        self.status.config(text="Orden actualizado en memoria. Pulsa Guardar para escribir el JSON.")

    def _select_item(self, _event: object | None = None) -> None:
        selection = self.items.curselection()
        if not selection:
            return
        self._commit_active_editor()
        self.current_index = selection[0]
        selected = self._selected_collection()
        if selected:
            key, value = selected
            self._show_custom_row(value["filas"][self.current_index]) if key == CUSTOM_LISTS_KEY else self._show_product(value[self.current_index])

    def _clear_editor(self) -> None:
        self._commit_active_editor()
        for child in self.editor.winfo_children():
            child.destroy()
        for row in range(80):
            self.editor.rowconfigure(row, weight=0, minsize=0, pad=0)
        ttk.Label(self.editor, text="Selecciona un elemento para editarlo", foreground="#666").grid(pady=30)

    def _commit_active_editor(self) -> None:
        if self._editor_commit:
            commit = self._editor_commit
            self._editor_commit = None
            commit()

    def _show_product(self, product: dict) -> None:
        self._clear_editor()
        self.editor.columnconfigure(1, weight=1)
        fields = [(key, value) for key, value in product.items() if key not in {"galeria", "media"}]
        variables: dict[str, tk.StringVar] = {}
        field_types: dict[str, object] = {}
        for row, (key, value) in enumerate(fields):
            self.editor.rowconfigure(row, weight=0, minsize=0, pad=0)
            ttk.Label(self.editor, text=key).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=4)
            variable = tk.StringVar(value="" if value is None else str(value))
            variables[key] = variable
            field_types[key] = value
            entry = ttk.Entry(self.editor, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            sync = lambda _event=None, field=key, source=value, current=variable: self._update_product_field(product, field, current, source)
            variable.trace_add("write", lambda *_args, callback=sync: callback())
            entry.bind("<KeyRelease>", sync)
            entry.bind("<FocusOut>", sync)
        ttk.Label(self.editor, text="Galería multimedia").grid(row=len(fields), column=0, sticky="nw", pady=(14, 4))
        gallery = tk.Listbox(self.editor, height=7, selectmode=tk.SINGLE, exportselection=False)
        gallery.grid(row=len(fields), column=1, sticky="ew", pady=(14, 4))
        self.editor.rowconfigure(len(fields), minsize=220, weight=0)
        for media in product.get("galeria", []):
            gallery.insert(tk.END, f"{media['tipo']}: {media['src']}")
        preview = self._create_gallery_preview(gallery, product)
        preview.grid(row=len(fields), column=0, sticky="nsew", padx=(0, 12), pady=(14, 4))
        buttons = ttk.Frame(self.editor)
        buttons.grid(row=len(fields) + 1, column=1, sticky="w")
        ttk.Button(buttons, text="Agregar imágenes", command=lambda: self._add_image(product, gallery)).pack(side="left")
        ttk.Button(buttons, text="Agregar YouTube", command=lambda: self._add_youtube(product, gallery)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Subir", command=lambda: self._move_media(product, gallery, -1)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Bajar", command=lambda: self._move_media(product, gallery, 1)).pack(side="left")
        ttk.Button(buttons, text="Quitar seleccionado", command=lambda: self._remove_media(product, gallery)).pack(side="left")
        self._editor_commit = lambda: self._commit_product_fields(product, variables, field_types)

    def _update_product_field(self, product: dict, key: str, variable: tk.StringVar, original: object) -> None:
        valid, converted = self._convert_editor_value(variable.get(), original, key)
        if not valid:
            return
        product[key] = converted
        if key == "nombre" and self.current_index is not None:
            self.items.delete(self.current_index)
            self.items.insert(self.current_index, f"{product.get('id', '?')} - {product.get('nombre', 'Sin nombre')}")
            self.items.selection_set(self.current_index)
            self.items.activate(self.current_index)

    @staticmethod
    def _integer_or_none(value: str) -> int | object:
        try:
            return int(value)
        except ValueError:
            return ...

    @staticmethod
    def _convert_editor_value(value: str, original: object, key: str) -> tuple[bool, object]:
        if key in {"precio", "precioZincado", "precioCrudo"} and value.strip() == "----":
            return True, "----"
        if isinstance(original, int) and not isinstance(original, bool):
            try:
                return True, int(value)
            except ValueError:
                return False, original
        if isinstance(original, float):
            try:
                return True, float(value)
            except ValueError:
                return False, original
        if original is None and key in {"precio", "precioZincado", "precioCrudo"}:
            if not value.strip():
                return True, None
            try:
                return True, int(value)
            except ValueError:
                return False, original
        return True, value

    def _commit_product_fields(self, product: dict, variables: dict[str, tk.StringVar], field_types: dict[str, object]) -> None:
        for key, variable in variables.items():
            valid, converted = self._convert_editor_value(variable.get(), field_types[key], key)
            if valid:
                product[key] = converted

    def _show_custom_row(self, row: dict) -> None:
        self._clear_editor()
        selected = self._selected_collection()
        if not selected:
            return
        custom_list = selected[1]
        row_number = (self.current_index or 0) + 1
        ttk.Label(self.editor, text=f"Fila {row_number}", font=("Segoe UI", 12, "bold")).grid(columnspan=2, sticky="w")
        variables: dict[str, tk.StringVar] = {}
        description = tk.StringVar(self, value=row.get("descripcion", ""))
        self.editor.rowconfigure(0, weight=0, minsize=0, pad=0)
        self.editor.rowconfigure(1, weight=0, minsize=0, pad=0)
        ttk.Label(self.editor, text="Descripción").grid(row=1, column=0, sticky="w", pady=4)
        description_entry = ttk.Entry(self.editor, textvariable=description)
        description_entry.grid(row=1, column=1, sticky="ew", pady=4)
        description_sync = lambda _event=None: row.__setitem__("descripcion", description.get())
        description.trace_add("write", lambda *_args: description_sync())
        description_entry.bind("<KeyRelease>", description_sync)
        description_entry.bind("<FocusOut>", description_sync)
        for index, column in enumerate(custom_list["columnas"], start=2):
            self.editor.rowconfigure(index, weight=0, minsize=0, pad=0)
            ttk.Label(self.editor, text=column["nombre"]).grid(row=index, column=0, sticky="w", pady=4)
            column_key = column["clave"]
            variable = tk.StringVar(value=row["celdas"].get(column_key, ""))
            variables[column_key] = variable
            entry = ttk.Entry(self.editor, textvariable=variable)
            entry.grid(row=index, column=1, sticky="ew", pady=4)
            variable.trace_add(
                "write",
                lambda *_args, row_data=row, key=column_key, source=variable: self._update_row_cell(row_data, key, source),
            )
            entry.bind(
                "<KeyRelease>",
                lambda _event, row_data=row, key=column_key, source=variable: self._update_row_cell(row_data, key, source),
            )
        media_row = len(variables) + 2
        ttk.Label(self.editor, text="Galería multimedia").grid(row=media_row, column=0, sticky="nw", pady=(14, 4))
        gallery = tk.Listbox(self.editor, height=6, selectmode=tk.SINGLE, exportselection=False)
        gallery.grid(row=media_row, column=1, sticky="ew", pady=(14, 4))
        self.editor.rowconfigure(media_row, minsize=220, weight=0)
        for media in row.get("galeria", []):
            gallery.insert(tk.END, f"{media['tipo']}: {media['src']}")
        preview = self._create_gallery_preview(gallery, row)
        preview.grid(row=media_row, column=0, sticky="nsew", padx=(0, 12), pady=(14, 4))
        buttons = ttk.Frame(self.editor)
        buttons.grid(row=media_row + 1, column=1, sticky="w")
        ttk.Button(buttons, text="Agregar imágenes", command=lambda: self._add_image(row, gallery)).pack(side="left")
        ttk.Button(buttons, text="Agregar YouTube", command=lambda: self._add_youtube(row, gallery)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Subir", command=lambda: self._move_media(row, gallery, -1)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Bajar", command=lambda: self._move_media(row, gallery, 1)).pack(side="left")
        ttk.Button(buttons, text="Quitar seleccionado", command=lambda: self._remove_media(row, gallery)).pack(side="left")
        self._editor_commit = lambda: self._commit_row_fields(row, variables, description)

    @staticmethod
    def _update_row_cell(row: dict, key: str, variable: tk.StringVar) -> None:
        value = variable.get()
        if value:
            row.setdefault("celdas", {})[key] = value
        else:
            row.setdefault("celdas", {}).pop(key, None)

    def _commit_row_fields(self, row: dict, variables: dict[str, tk.StringVar], description: tk.StringVar) -> None:
        row["descripcion"] = description.get().strip()
        for key, variable in variables.items():
            self._update_row_cell(row, key, variable)

    def _create_gallery_preview(self, gallery: tk.Listbox, item: dict) -> tk.Frame:
        preview = tk.Frame(
            self.editor,
            width=320,
            height=220,
            bg="#f3f3f3",
            relief="sunken",
            bd=1,
        )
        preview.grid_propagate(False)
        preview_label = tk.Label(
            preview,
            text="Selecciona una imagen",
            anchor="center",
            justify="center",
            bg="#f3f3f3",
            fg="#666666",
        )
        preview_label.pack(fill="both", expand=True)
        preview.preview_label = preview_label
        gallery.bind(
            "<<ListboxSelect>>",
            lambda _event: self._update_gallery_preview(gallery, item, preview),
        )
        gallery.bind("<Up>", lambda _event: self._move_gallery_selection(gallery, -1), add="+")
        gallery.bind("<Down>", lambda _event: self._move_gallery_selection(gallery, 1), add="+")
        if gallery.size():
            gallery.selection_set(0)
            gallery.activate(0)
            self._update_gallery_preview(gallery, item, preview)
        return preview

    @staticmethod
    def _move_gallery_selection(gallery: tk.Listbox, direction: int) -> str:
        if not gallery.size():
            return "break"
        selection = gallery.curselection()
        current_index = selection[0] if selection else 0
        target_index = max(0, min(gallery.size() - 1, current_index + direction))
        gallery.selection_clear(0, tk.END)
        gallery.selection_set(target_index)
        gallery.activate(target_index)
        gallery.see(target_index)
        gallery.focus_set()
        gallery.event_generate("<<ListboxSelect>>")
        return "break"

    def _update_gallery_preview(self, gallery: tk.Listbox, item: dict, preview: tk.Frame) -> None:
        preview_label = preview.preview_label
        selection = gallery.curselection()
        media_items = item.get("galeria", [])
        if not selection or selection[0] >= len(media_items):
            preview_label.configure(image="", text="Selecciona una imagen")
            preview_label.image = None
            return

        media = media_items[selection[0]]
        if media.get("tipo", "imagen") != "imagen":
            preview_label.configure(image="", text="El elemento seleccionado\nes un video de YouTube")
            preview_label.image = None
            return
        if not self.manager:
            return
        source = self.manager.project_root / "public" / media.get("src", "").lstrip("/")
        try:
            from PIL import Image, ImageTk

            with Image.open(source) as image:
                image = image.convert("RGB")
                image.thumbnail((280, 190), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image.copy())
        except (FileNotFoundError, OSError, ImportError):
            preview_label.configure(image="", text="No se pudo cargar\nla imagen seleccionada")
            preview_label.image = None
            return
        preview_label.configure(image=photo, text="")
        preview_label.image = photo

    def _add_image(self, item: dict, gallery: tk.Listbox) -> None:
        if not self.manager:
            return
        sources = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.gif"), ("Todos", "*.*")])
        if not sources:
            return
        folder = self.current_collection if self.current_collection != CUSTOM_LISTS_KEY else "listas"
        added = 0
        errors: list[str] = []
        for source in sources:
            try:
                route = self.manager.copy_image(source, folder)
            except CatalogError as error:
                errors.append(f"{Path(source).name}: {error}")
                continue
            item.setdefault("galeria", []).append({"tipo": "imagen", "src": route, "alt": Path(source).stem})
            gallery.insert(tk.END, f"imagen: {route}")
            gallery.selection_clear(0, tk.END)
            gallery.selection_set(gallery.size() - 1)
            gallery.activate(gallery.size() - 1)
            gallery.event_generate("<<ListboxSelect>>")
            added += 1
        if errors:
            messagebox.showwarning("Algunas imágenes no se agregaron", "\n".join(errors))
        if added:
            optimization = self.manager.last_image_optimization or {}
            original_size = int(optimization.get("original_bytes", 0))
            optimized_size = int(optimization.get("optimized_bytes", 0))
            reduction = round((1 - optimized_size / original_size) * 100) if original_size else 0
            self.status.config(text=f"{added} imagen(es) agregada(s). Última optimización: {original_size // 1024} KB -> {optimized_size // 1024} KB ({reduction}% menos)")

    def _add_youtube(self, item: dict, gallery: tk.Listbox) -> None:
        if not self.manager:
            return
        url = simpledialog.askstring("Video de YouTube", "Pega la URL del video:")
        if not url:
            return
        try:
            valid_url = self.manager.youtube_url(url)
        except CatalogError as error:
            messagebox.showerror("URL no válida", str(error))
            return
        item.setdefault("galeria", []).append({"tipo": "video", "src": valid_url, "alt": "Video del producto"})
        gallery.insert(tk.END, f"video: {valid_url}")
        gallery.selection_clear(0, tk.END)
        gallery.selection_set(gallery.size() - 1)
        gallery.activate(gallery.size() - 1)
        gallery.event_generate("<<ListboxSelect>>")

    @staticmethod
    def _move_media(item: dict, gallery: tk.Listbox, direction: int) -> None:
        selection = gallery.curselection()
        if not selection:
            return
        current_index = selection[0]
        target_index = current_index + direction
        media = item.setdefault("galeria", [])
        if target_index < 0 or target_index >= len(media):
            return
        media[current_index], media[target_index] = media[target_index], media[current_index]
        gallery.delete(0, tk.END)
        for element in media:
            gallery.insert(tk.END, f"{element['tipo']}: {element['src']}")
        gallery.selection_set(target_index)
        gallery.activate(target_index)
        gallery.see(target_index)
        gallery.event_generate("<<ListboxSelect>>")

    @staticmethod
    def _remove_media(item: dict, gallery: tk.Listbox) -> None:
        selection = gallery.curselection()
        if selection:
            del item["galeria"][selection[0]]
            gallery.delete(selection[0])
            if gallery.size():
                next_index = min(selection[0], gallery.size() - 1)
                gallery.selection_clear(0, tk.END)
                gallery.selection_set(next_index)
                gallery.activate(next_index)
            gallery.event_generate("<<ListboxSelect>>")

    def _new_custom_list(self) -> None:
        self._open_custom_list_editor()

    def _draft_add_column(self, name: str | None = None) -> None:
        if not self.custom_list_draft:
            return
        used_keys = {column["clave"] for column in self.custom_list_draft["columns"]}
        index = 1
        while f"columna-{index}" in used_keys:
            index += 1
        key = f"columna-{index}"
        master = self.custom_list_window or self
        column = {"clave": key, "nombre": tk.StringVar(master, value=name or f"Columna {index}")}
        self.custom_list_draft["columns"].append(column)
        for row in self.custom_list_draft["rows"]:
            row["celdas"][key] = tk.StringVar(master)

    def _draft_add_row(self) -> None:
        if not self.custom_list_draft:
            return
        row_id = max((row["id"] for row in self.custom_list_draft["rows"]), default=0) + 1
        master = self.custom_list_window or self
        cells = {column["clave"]: tk.StringVar(master) for column in self.custom_list_draft["columns"]}
        self.custom_list_draft["rows"].append({"id": row_id, "descripcion": tk.StringVar(master), "celdas": cells, "galeria": []})

    def _clear_custom_list_editor(self) -> None:
        if not self.custom_list_editor:
            return
        for child in self.custom_list_editor.winfo_children():
            child.destroy()

    def _show_custom_list_builder(self) -> None:
        draft = self.custom_list_draft
        if not draft:
            return
        self._clear_custom_list_editor()
        editor = self.custom_list_editor
        if not editor:
            return
        editor.columnconfigure(1, weight=1)

        is_editing = draft["mode"] == "edit"
        ttk.Label(editor, text="Editar lista" if is_editing else "Nueva lista", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(editor, text="Título visible").grid(row=1, column=0, sticky="w", pady=(12, 6))
        ttk.Entry(editor, textvariable=draft["title"]).grid(row=1, column=1, sticky="ew", pady=(12, 6))

        columns_frame = ttk.LabelFrame(editor, text="Columnas")
        columns_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        columns_frame.columnconfigure(0, weight=1)
        draft["column_controls"] = {}
        for index, column in enumerate(draft["columns"]):
            ttk.Entry(columns_frame, textvariable=column["nombre"]).grid(row=index, column=0, sticky="ew", padx=6, pady=3)
            move_up = ttk.Button(
                columns_frame,
                text="Subir",
                state="disabled" if index == 0 else "normal",
                command=lambda item=column: self._draft_move_column(item, -1),
            )
            move_up.grid(row=index, column=1, padx=(6, 2), pady=3)
            move_down = ttk.Button(
                columns_frame,
                text="Bajar",
                state="disabled" if index == len(draft["columns"]) - 1 else "normal",
                command=lambda item=column: self._draft_move_column(item, 1),
            )
            move_down.grid(row=index, column=2, padx=2, pady=3)
            ttk.Button(columns_frame, text="Quitar", command=lambda item=column: self._draft_remove_column(item)).grid(row=index, column=3, padx=(2, 6), pady=3)
            draft["column_controls"][column["clave"]] = {"up": move_up, "down": move_down}
        ttk.Button(columns_frame, text="+ Agregar columna", command=self._draft_add_column_and_refresh).grid(row=len(draft["columns"]), column=0, sticky="w", padx=6, pady=6)

        if not is_editing:
            rows_container = ttk.Frame(editor)
            rows_container.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=8)
            rows_container.columnconfigure(0, weight=1)
            rows_container.rowconfigure(0, weight=1)
            rows_canvas = tk.Canvas(rows_container, highlightthickness=0)
            rows_canvas.grid(row=0, column=0, sticky="nsew")
            rows_scrollbar = ttk.Scrollbar(rows_container, orient="horizontal", command=rows_canvas.xview)
            rows_scrollbar.grid(row=1, column=0, sticky="ew")
            rows_canvas.configure(xscrollcommand=rows_scrollbar.set)
            table_frame = ttk.LabelFrame(rows_canvas, text="Filas")
            table_window = rows_canvas.create_window((0, 0), window=table_frame, anchor="nw")
            table_frame.bind(
                "<Configure>",
                lambda _event: rows_canvas.configure(scrollregion=rows_canvas.bbox("all")),
            )
            rows_canvas.bind(
                "<Configure>",
                lambda event: rows_canvas.itemconfigure(table_window, height=max(event.height, table_frame.winfo_reqheight())),
            )
            editor.rowconfigure(3, weight=1)
            for column_index, column in enumerate(draft["columns"], start=1):
                ttk.Label(table_frame, text=column["nombre"].get()).grid(row=0, column=column_index + 1, padx=5, pady=4)
            ttk.Label(table_frame, text="Descripción").grid(row=0, column=1, padx=5, pady=4)
            ttk.Label(table_frame, text="Multimedia").grid(row=0, column=len(draft["columns"]) + 2, padx=5, pady=4)
            for row_index, row in enumerate(draft["rows"], start=1):
                ttk.Label(table_frame, text=f"Fila {row_index}").grid(row=row_index, column=0, padx=5, pady=3)
                ttk.Entry(table_frame, textvariable=row["descripcion"], width=28).grid(row=row_index, column=1, padx=3, pady=3)
                for column_index, column in enumerate(draft["columns"], start=1):
                    ttk.Entry(table_frame, textvariable=row["celdas"][column["clave"]], width=18).grid(row=row_index, column=column_index + 1, padx=3, pady=3)
                ttk.Button(table_frame, text="Fotos / videos", command=lambda item=row: self._show_draft_media(item)).grid(row=row_index, column=len(draft["columns"]) + 2, padx=5, pady=3)
                ttk.Button(table_frame, text="Quitar", command=lambda item=row: self._draft_remove_row(item)).grid(row=row_index, column=len(draft["columns"]) + 3, padx=5, pady=3)

        actions = ttk.Frame(editor)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        if not is_editing:
            ttk.Button(actions, text="+ Agregar fila", command=self._draft_add_row_and_refresh).pack(side="left")
        ttk.Button(actions, text="Cancelar", command=self._cancel_custom_list).pack(side="right", padx=(6, 0))
        save_command = self._save_custom_list_edit if is_editing else self._create_custom_list_from_draft
        ttk.Button(actions, text="Guardar cambios" if is_editing else "Crear lista", command=save_command).pack(side="right")

    def _draft_add_column_and_refresh(self) -> None:
        self._draft_add_column()
        self._show_custom_list_builder()

    def _draft_move_column(self, column: dict, direction: int) -> None:
        draft = self.custom_list_draft
        if not draft:
            return
        current_index = next((index for index, item in enumerate(draft["columns"]) if item is column), None)
        if current_index is None:
            return
        target_index = self._move_item(draft["columns"], current_index, direction)
        if target_index is None:
            return
        self._show_custom_list_builder()
        control_name = "up" if direction < 0 else "down"
        draft["column_controls"][column["clave"]][control_name].focus_set()

    def _draft_add_row_and_refresh(self) -> None:
        self._draft_add_row()
        self._show_custom_list_builder()

    def _draft_remove_column(self, column: dict) -> None:
        draft = self.custom_list_draft
        if not draft:
            return
        if len(draft["columns"]) <= 1:
            messagebox.showinfo("Quitar columna", "La lista debe conservar al menos una columna.")
            return
        column_key = column["clave"]
        target = draft.get("target")
        if target:
            populated_rows = sum(bool(row.get("celdas", {}).get(column_key)) for row in target["filas"])
        else:
            populated_rows = sum(bool(row["celdas"][column_key].get()) for row in draft["rows"])
        if populated_rows and not messagebox.askyesno(
            "Quitar columna",
            f"La columna tiene datos en {populated_rows} fila(s). Se eliminarán esos datos. ¿Continuar?",
        ):
            return
        draft["columns"].remove(column)
        for row in draft["rows"]:
            row["celdas"].pop(column_key, None)
        self._show_custom_list_builder()

    def _draft_remove_row(self, row: dict) -> None:
        draft = self.custom_list_draft
        if not draft:
            return
        draft["rows"].remove(row)
        self._show_custom_list_builder()

    def _show_draft_media(self, row: dict) -> None:
        self._clear_custom_list_editor()
        editor = self.custom_list_editor
        if not editor:
            return
        draft_rows = self.custom_list_draft["rows"] if self.custom_list_draft else []
        row_number = next((index for index, draft_row in enumerate(draft_rows, start=1) if draft_row is row), 0)
        ttk.Label(editor, text=f"Multimedia de la fila {row_number}", font=("Segoe UI", 12, "bold")).grid(columnspan=2, sticky="w")
        gallery = tk.Listbox(editor, height=10)
        gallery.grid(row=1, column=0, columnspan=2, sticky="ew", pady=12)
        for media in row["galeria"]:
            gallery.insert(tk.END, f"{media['tipo']}: {media['src']}")
        buttons = ttk.Frame(editor)
        buttons.grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Button(buttons, text="Agregar imagen", command=lambda: self._add_image(row, gallery)).pack(side="left")
        ttk.Button(buttons, text="Agregar YouTube", command=lambda: self._add_youtube(row, gallery)).pack(side="left", padx=6)
        ttk.Button(buttons, text="Quitar seleccionado", command=lambda: self._remove_media(row, gallery)).pack(side="left")
        ttk.Button(editor, text="Volver a la lista", command=self._show_custom_list_builder).grid(row=3, column=1, sticky="e", pady=14)

    def _cancel_custom_list(self) -> None:
        self.custom_list_draft = None
        if self.custom_list_window and self.custom_list_window.winfo_exists():
            self.custom_list_window.destroy()
        self.custom_list_window = None
        self.custom_list_editor = None

    def _delete_selected_collection(self) -> None:
        selected = self._selected_collection()
        if not selected:
            messagebox.showinfo("Eliminar lista", "Selecciona una lista personalizada primero.")
            return
        key, custom_list = selected
        if key != CUSTOM_LISTS_KEY:
            messagebox.showwarning(
                "Lista protegida",
                "Las categorías originales del catálogo no se pueden eliminar desde este botón.",
            )
            return
        title = custom_list.get("titulo", custom_list.get("clave", "lista"))
        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Eliminar definitivamente la lista personalizada '{title}'?\n\nEsta acción no se puede deshacer.",
        ):
            return
        lists = self.data.get(CUSTOM_LISTS_KEY, [])
        lists.remove(custom_list)
        self.data[COLLECTION_ORDER_KEY] = [key for key in self.data.get(COLLECTION_ORDER_KEY, []) if key != f"lista:{custom_list['clave']}"]
        if not lists:
            self.data.pop(CUSTOM_LISTS_KEY, None)
        self.current_collection = ""
        self.current_index = None
        self._refresh_collections()
        self.status.config(text=f"Lista '{title}' eliminada en memoria. Pulsa Guardar para escribir el JSON.")

    def _create_custom_list_from_draft(self) -> None:
        draft = self.custom_list_draft
        if not self.manager or not draft:
            return
        title = draft["title"].get().strip()
        if not title:
            messagebox.showerror("Lista no válida", "Escribe un título para la lista.")
            return
        existing = {item["clave"] for item in self.data.get(CUSTOM_LISTS_KEY, [])}
        try:
            key = self.manager.custom_list_key(title, existing)
            custom_list = self.manager.new_custom_list(key, title, len(draft["columns"]), len(draft["rows"]))
            custom_list["columnas"] = [{"clave": column["clave"], "nombre": column["nombre"].get().strip() or f"Columna {index + 1}"} for index, column in enumerate(draft["columns"])]
            custom_list["filas"] = [{"id": row["id"], "uid": row.get("uid") or self.manager.new_uid(), "descripcion": row["descripcion"].get().strip(), "celdas": {key: value.get() for key, value in row["celdas"].items() if value.get()}, "galeria": copy.deepcopy(row["galeria"])} for row in draft["rows"]]
            self.manager.add_custom_list(self.data, custom_list)
            self._ensure_collection_order()
        except CatalogError as error:
            messagebox.showerror("Lista no válida", str(error))
            return
        self.custom_list_draft = None
        if self.custom_list_window and self.custom_list_window.winfo_exists():
            self.custom_list_window.destroy()
        self.custom_list_window = None
        self.custom_list_editor = None
        self._refresh_collections()
        self.status.config(text=f"Lista '{title}' creada. Pulsa Guardar para escribir el JSON.")

    @staticmethod
    def _apply_custom_list_structure(custom_list: dict, title: str, columns: list[dict]) -> None:
        allowed_keys = {column["clave"] for column in columns}
        custom_list["titulo"] = title
        custom_list["columnas"] = columns
        for row in custom_list["filas"]:
            row["celdas"] = {key: value for key, value in row["celdas"].items() if key in allowed_keys}

    def _save_custom_list_edit(self) -> None:
        draft = self.custom_list_draft
        if not draft or not self.manager:
            return
        title = draft["title"].get().strip()
        if not title:
            messagebox.showerror("Título no válido", "El título no puede estar vacío.")
            return
        if not draft["columns"]:
            messagebox.showerror("Lista no válida", "La lista debe tener al menos una columna.")
            return
        custom_list = draft["target"]
        columns = [
            {"clave": column["clave"], "nombre": column["nombre"].get().strip() or f"Columna {index + 1}"}
            for index, column in enumerate(draft["columns"])
        ]
        self._apply_custom_list_structure(custom_list, title, columns)
        selected_key = f"lista:{custom_list['clave']}"
        self._cancel_custom_list()
        self._refresh_collections()
        selected_index = next(
            (index for index, (key, _label, _value) in enumerate(self._collection_entries()) if key == selected_key),
            None,
        )
        if selected_index is not None:
            self.collections.selection_clear(0, tk.END)
            self.collections.selection_set(selected_index)
            self.collections.activate(selected_index)
            self._select_collection()
        self.status.config(text=f"Lista '{title}' actualizada en memoria. Pulsa Guardar para escribir el JSON.")

    def _new_item(self) -> None:
        selected = self._selected_collection()
        if not selected:
            return
        key, values = selected
        if key == CUSTOM_LISTS_KEY:
            rows = values["filas"]
            next_id = max((row["id"] for row in rows), default=0) + 1
            rows.append({"id": next_id, "uid": self.manager.new_uid(), "descripcion": "", "celdas": {}, "galeria": []})
            self._select_collection()
        else:
            next_id = max((item.get("id", 0) for item in values), default=0) + 1
            values.append({"id": next_id, "uid": self.manager.new_uid(), "nombre": "Nuevo producto", "descripcion": "", "precio": None, "galeria": []})
            self._select_collection()

    def _duplicate_item(self) -> None:
        selected = self._selected_collection()
        if not selected or self.current_index is None:
            return
        key, values = selected
        source = values["filas"][self.current_index] if key == CUSTOM_LISTS_KEY else values[self.current_index]
        duplicate = copy.deepcopy(source)
        duplicate["id"] = max((item.get("id", 0) for item in (values["filas"] if key == CUSTOM_LISTS_KEY else values)), default=0) + 1
        duplicate["uid"] = self.manager.new_uid()
        (values["filas"] if key == CUSTOM_LISTS_KEY else values).append(duplicate)
        self._select_collection()

    def _delete_item(self) -> None:
        selected = self._selected_collection()
        if not selected or self.current_index is None:
            return
        if not messagebox.askyesno("Confirmar eliminación", "¿Eliminar el elemento seleccionado?"):
            return
        key, values = selected
        target = values["filas"] if key == CUSTOM_LISTS_KEY else values
        del target[self.current_index]
        self._select_collection()

    def _export_prices_excel(self) -> None:
        if not self.manager:
            return
        output = filedialog.asksaveasfilename(
            title="Guardar precios en Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")],
            initialfile="precios-exhibe.xlsx",
        )
        if not output:
            return
        try:
            self.manager.data = self.data
            path = self.manager.export_prices_excel(output)
        except CatalogError as error:
            messagebox.showerror("No se pudo exportar", str(error))
            return
        self.status.config(text=f"Archivo Excel exportado: {path}")

    def _import_prices_excel(self) -> None:
        if not self.manager:
            return
        selected = filedialog.askopenfilename(
            title="Selecciona el archivo Excel con precios",
            filetypes=[("Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if not selected:
            return
        try:
            self.manager.data = self.data
            result = self.manager.import_prices_excel(selected)
        except (CatalogError, OSError) as error:
            messagebox.showerror("No se pudo importar", str(error))
            return
        updated = result.get("updated", 0)
        skipped = result.get("skipped", 0)
        self.status.config(text=f"Precios importados: {updated} actualizados, {skipped} omitidos.")
        self._refresh_collections()

    def _save(self) -> None:
        if not self.manager:
            return
        self._commit_active_editor()
        try:
            self.manager.save(self.data)
        except (CatalogError, OSError) as error:
            messagebox.showerror("No se pudo guardar", str(error))
            return
        self.status.config(text=f"Guardado correcto: {self.manager.json_path}")


if __name__ == "__main__":
    CatalogApp().mainloop()
