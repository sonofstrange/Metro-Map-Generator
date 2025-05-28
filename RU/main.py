import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import json

from PIL import Image, ImageDraw, ImageTk, ImageFont
import math


class MetroMapGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Генератор карты метро")

        # Данные карты
        self.lines = []
        self.stations = []
        self.selected_line = None
        self.selected_station = None
        self.edit_mode = "add"  # Режим: 'add' или 'edit'
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.drag_start = None

        # Основные фреймы
        self.control_frame = ttk.Frame(root, padding="10")
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas_frame = ttk.Frame(root, padding="10")
        self.canvas_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # Холст для рисования
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", width=800, height=600)
        self.canvas.pack(expand=True, fill=tk.BOTH)

        # Привязка событий
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Button-2>", self.start_drag)  # Средняя кнопка мыши
        self.canvas.bind("<B2-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-2>", self.end_drag)

        # Элементы управления
        self.setup_controls()

        # Отрисовка начального состояния
        self.redraw_map()

    def setup_controls(self):
        # Кнопки управления
        ttk.Button(self.control_frame, text="Добавить линию", command=self.add_line).pack(fill=tk.X, pady=2)
        ttk.Button(self.control_frame, text="Экспорт PNG", command=self.export_png).pack(fill=tk.X, pady=2)
        ttk.Button(self.control_frame, text="Экспорт JSON", command=self.export_json).pack(fill=tk.X, pady=2)
        ttk.Button(self.control_frame, text="Импорт JSON", command=self.import_json).pack(fill=tk.X, pady=2)

        # Выбор режима
        self.mode_var = tk.StringVar(value="add")
        ttk.Label(self.control_frame, text="Режим:").pack(anchor=tk.W)
        ttk.Radiobutton(self.control_frame, text="Добавление", variable=self.mode_var, value="add",
                        command=self.set_mode).pack(anchor=tk.W)
        ttk.Radiobutton(self.control_frame, text="Редактирование", variable=self.mode_var, value="edit",
                        command=self.set_mode).pack(anchor=tk.W)

        # Настройки линии
        ttk.Label(self.control_frame, text="Настройки линии:").pack()
        ttk.Label(self.control_frame, text="Толщина:").pack(anchor=tk.W)
        self.line_width_var = tk.IntVar(value=6)
        ttk.Spinbox(self.control_frame, from_=1, to=20, textvariable=self.line_width_var, width=5).pack(anchor=tk.W)

        ttk.Label(self.control_frame, text="Сглаживание:").pack(anchor=tk.W)
        self.smoothing_var = tk.StringVar(value="straight")
        ttk.Combobox(self.control_frame, textvariable=self.smoothing_var,
                     values=["straight", "smooth", "metro"], state="readonly", width=8).pack(anchor=tk.W)

        # Список линий
        ttk.Label(self.control_frame, text="Линии:").pack()
        self.lines_listbox = tk.Listbox(self.control_frame, height=5)
        self.lines_listbox.pack(fill=tk.X)
        self.lines_listbox.bind("<<ListboxSelect>>", self.on_line_select)

        # Кнопки для линии
        ttk.Button(self.control_frame, text="Изменить цвет", command=self.change_line_color).pack(fill=tk.X, pady=2)
        ttk.Button(self.control_frame, text="Применить настройки", command=self.apply_line_settings).pack(fill=tk.X,
                                                                                                          pady=2)

        # Список станций
        ttk.Label(self.control_frame, text="Станции:").pack()
        self.stations_listbox = tk.Listbox(self.control_frame, height=10)
        self.stations_listbox.pack(fill=tk.X)
        self.stations_listbox.bind("<<ListboxSelect>>", self.on_station_select)

        # Настройки станции
        ttk.Label(self.control_frame, text="Стиль станции:").pack()
        self.station_style_var = tk.StringVar(value="circle")
        ttk.Combobox(self.control_frame, textvariable=self.station_style_var,
                     values=["circle", "square", "horizontal rect", "vertical rect", "triangle", "label", "empty"],
                     state="readonly").pack()

        # Координаты станции
        ttk.Label(self.control_frame, text="Координаты:").pack()
        self.coord_frame = ttk.Frame(self.control_frame)
        self.coord_frame.pack(fill=tk.X)

        ttk.Label(self.coord_frame, text="X:").pack(side=tk.LEFT)
        self.x_var = tk.DoubleVar()
        ttk.Entry(self.coord_frame, textvariable=self.x_var, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Label(self.coord_frame, text="Y:").pack(side=tk.LEFT)
        self.y_var = tk.DoubleVar()
        ttk.Entry(self.coord_frame, textvariable=self.y_var, width=8).pack(side=tk.LEFT, padx=2)

        ttk.Button(self.control_frame, text="Применить к станции", command=self.apply_station_settings).pack(fill=tk.X,
                                                                                                             pady=2)

        # Кнопка удаления
        ttk.Button(self.control_frame, text="Удалить выбранное", command=self.delete_selected).pack(fill=tk.X, pady=2)

        # Масштаб и перемещение
        ttk.Label(self.control_frame, text="Масштаб:").pack()
        self.scale_slider = ttk.Scale(self.control_frame, from_=0.025, to=6.0, value=1.0, command=self.on_scale_change)
        self.scale_slider.pack(fill=tk.X)

        ttk.Button(self.control_frame, text="Сбросить вид", command=self.reset_view).pack(fill=tk.X, pady=2)

        # Информация
        ttk.Label(self.control_frame, text="Инструкция:").pack()
        ttk.Label(self.control_frame, text="ЛКМ - добавить/переместить").pack(anchor=tk.W)
        ttk.Label(self.control_frame, text="ПКМ - выбрать станцию").pack(anchor=tk.W)
        ttk.Label(self.control_frame, text="Колесо - масштаб").pack(anchor=tk.W)
        ttk.Label(self.control_frame, text="Средняя кнопка - перемещение").pack(anchor=tk.W)

    def set_mode(self):
        self.edit_mode = self.mode_var.get()

    def add_line(self):
        color = colorchooser.askcolor(title="Выберите цвет линии")[1]
        if color:
            line_id = len(self.lines) + 1
            self.lines.append({
                "id": line_id,
                "name": f"Линия {line_id}",
                "color": color,
                "width": self.line_width_var.get(),
                "smoothing": self.smoothing_var.get(),
                "stations": []
            })
            self.update_lines_list()
            self.selected_line = len(self.lines) - 1
            self.lines_listbox.selection_clear(0, tk.END)
            self.lines_listbox.selection_set(self.selected_line)
            self.redraw_map()

    def change_line_color(self):
        if self.selected_line is not None:
            color = \
                colorchooser.askcolor(title="Выберите цвет линии",
                                      initialcolor=self.lines[self.selected_line]["color"])[1]
            if color:
                self.lines[self.selected_line]["color"] = color
                self.redraw_map()

    def apply_line_settings(self):
        if self.selected_line is not None:
            self.lines[self.selected_line]["width"] = self.line_width_var.get()
            self.lines[self.selected_line]["smoothing"] = self.smoothing_var.get()
            self.redraw_map()

    def apply_station_settings(self):
        if self.selected_station is not None and self.selected_line is not None:
            station_id = self.lines[self.selected_line]["stations"][self.selected_station]
            station = next(s for s in self.stations if s["id"] == station_id)
            station["style"] = self.station_style_var.get()

            try:
                station["x"] = float(self.x_var.get())
                station["y"] = float(self.y_var.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Координаты должны быть числами")

            self.redraw_map()

    def on_line_select(self, event):
        selection = self.lines_listbox.curselection()
        if selection:
            self.selected_line = selection[0]
            self.update_stations_list()
            # Обновляем настройки линии в интерфейсе
            self.line_width_var.set(self.lines[self.selected_line]["width"])
            self.smoothing_var.set(self.lines[self.selected_line]["smoothing"])

    def on_station_select(self, event):
        selection = self.stations_listbox.curselection()
        if selection and self.selected_line is not None:
            self.selected_station = selection[0]
            station_id = self.lines[self.selected_line]["stations"][self.selected_station]
            station = next(s for s in self.stations if s["id"] == station_id)
            self.station_style_var.set(station.get("style", "circle"))
            self.x_var.set(station["x"])
            self.y_var.set(station["y"])

    def delete_selected(self):
        if self.selected_line is not None and self.selected_station is not None:
            # Удаление станции
            station_id = self.lines[self.selected_line]["stations"][self.selected_station]
            station = next(s for s in self.stations if s["id"] == station_id)

            # Удаляем станцию из всех линий
            for line in self.lines:
                if station_id in line["stations"]:
                    line["stations"].remove(station_id)

            # Удаляем саму станцию
            self.stations = [s for s in self.stations if s["id"] != station_id]

            self.selected_station = None
            self.update_stations_list()
            self.redraw_map()
        elif self.selected_line is not None:
            # Удаление линии
            # Сначала удаляем все станции этой линии
            station_ids = self.lines[self.selected_line]["stations"]
            self.stations = [s for s in self.stations if s["id"] not in station_ids]

            # Затем удаляем саму линию
            del self.lines[self.selected_line]

            self.selected_line = None
            self.selected_station = None
            self.update_lines_list()
            self.update_stations_list()
            self.redraw_map()

    def update_lines_list(self):
        self.lines_listbox.delete(0, tk.END)
        for line in self.lines:
            self.lines_listbox.insert(tk.END, line["name"])

    def update_stations_list(self):
        self.stations_listbox.delete(0, tk.END)
        if self.selected_line is not None:
            for station_id in self.lines[self.selected_line]["stations"]:
                station = next(s for s in self.stations if s["id"] == station_id)
                self.stations_listbox.insert(tk.END, station["name"])

    def on_canvas_click(self, event):
        x, y = self.get_unscaled_coords(event.x, event.y)

        if self.edit_mode == "add" and self.selected_line is not None:
            # Добавление новой станции
            station_id = len(self.stations) + 1
            self.stations.append({
                "id": station_id,
                "name": f"Станция {station_id}",
                "x": x,
                "y": y,
                "style": self.station_style_var.get()
            })
            self.lines[self.selected_line]["stations"].append(station_id)
            self.update_stations_list()
            self.redraw_map()
        elif self.edit_mode == "edit":
            # Проверяем, кликнули ли мы на станцию
            for station in self.stations:
                sx, sy = self.get_scaled_coords(station["x"], station["y"])
                distance = math.sqrt((sx - event.x) ** 2 + (sy - event.y) ** 2)
                if distance < 10:  # Радиус выбора
                    self.dragged_station = station
                    return

    def on_canvas_drag(self, event):
        if hasattr(self, 'dragged_station') and self.dragged_station:
            x, y = self.get_unscaled_coords(event.x, event.y)
            self.dragged_station["x"] = x
            self.dragged_station["y"] = y
            self.x_var.set(x)
            self.y_var.set(y)
            self.redraw_map()

    def on_canvas_release(self, event):
        if hasattr(self, 'dragged_station'):
            del self.dragged_station

    def on_right_click(self, event):
        x, y = event.x, event.y

        # Проверяем, кликнули ли мы на станцию
        for station in self.stations:
            sx, sy = self.get_scaled_coords(station["x"], station["y"])
            distance = math.sqrt((sx - x) ** 2 + (sy - y) ** 2)
            if distance < 10:  # Радиус выбора
                # Показываем диалог редактирования
                self.edit_station(station)
                return

    def edit_station(self, station):
        dialog = tk.Toplevel(self.root)
        dialog.title("Редактирование станции")

        ttk.Label(dialog, text="Название:").grid(row=0, column=0, padx=5, pady=5)
        name_entry = ttk.Entry(dialog)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        name_entry.insert(0, station["name"])

        ttk.Label(dialog, text="Стиль:").grid(row=1, column=0, padx=5, pady=5)
        style_var = tk.StringVar(value=station.get("style", "circle"))
        ttk.Combobox(dialog, textvariable=style_var,
                     values=["circle", "square", "horizontal rect", "vertical rect", "triangle", "label", "empty"],
                     state="readonly").grid(row=1, column=1, padx=5,
                                            pady=5)

        ttk.Label(dialog, text="Координата X:").grid(row=2, column=0, padx=5, pady=5)
        x_entry = ttk.Entry(dialog)
        x_entry.grid(row=2, column=1, padx=5, pady=5)
        x_entry.insert(0, str(station["x"]))

        ttk.Label(dialog, text="Координата Y:").grid(row=3, column=0, padx=5, pady=5)
        y_entry = ttk.Entry(dialog)
        y_entry.grid(row=3, column=1, padx=5, pady=5)
        y_entry.insert(0, str(station["y"]))

        def save_changes():
            station["name"] = name_entry.get()
            station["style"] = style_var.get()
            try:
                station["x"] = float(x_entry.get())
                station["y"] = float(y_entry.get())
            except ValueError:
                messagebox.showerror("Ошибка", "Координаты должны быть числами")
                return

            self.update_stations_list()
            self.redraw_map()
            dialog.destroy()

        ttk.Button(dialog, text="Сохранить", command=save_changes).grid(row=4, column=0, columnspan=2, pady=5)

    def start_drag(self, event):
        self.drag_start = (event.x, event.y)

    def on_drag(self, event):
        if self.drag_start:
            dx = event.x - self.drag_start[0]
            dy = event.y - self.drag_start[1]
            self.offset_x += dx
            self.offset_y += dy
            self.drag_start = (event.x, event.y)
            self.redraw_map()

    def end_drag(self, event):
        self.drag_start = None

    def on_mouse_wheel(self, event):
        # Масштабирование колесиком мыши
        scale_factor = 1.1 if event.delta > 0 else 0.9
        self.scale *= scale_factor
        self.scale = max(0.025, min(6.0, self.scale))  # Ограничиваем масштаб
        self.scale_slider.set(self.scale)
        self.redraw_map()

    def on_scale_change(self, value):
        self.scale = float(value)
        self.redraw_map()

    def reset_view(self):
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.scale_slider.set(self.scale)
        self.redraw_map()

    def get_scaled_coords(self, x, y):
        return x * self.scale + self.offset_x, y * self.scale + self.offset_y

    def get_unscaled_coords(self, x, y):
        return (x - self.offset_x) / self.scale, (y - self.offset_y) / self.scale

    def calculate_metro_path(self, points):
        """Строит путь между станциями с углами строго 45 градусов, гарантированно проходя через все точки"""
        if len(points) < 2:
            return points

        path = [points[0]]

        for i in range(1, len(points)):
            prev_x, prev_y = path[-1]
            curr_x, curr_y = points[i]

            dx = curr_x - prev_x
            dy = curr_y - prev_y

            # Определяем основные направления движения
            if dx == 0:  # Вертикальное движение
                path.append((prev_x, curr_y))
            elif dy == 0:  # Горизонтальное движение
                path.append((curr_x, prev_y))
            else:
                # Движение под углом 45 градусов
                distance = min(abs(dx), abs(dy))
                step_x = distance if dx > 0 else -distance
                step_y = distance if dy > 0 else -distance

                # Промежуточная точка
                mid_x = prev_x + step_x
                mid_y = prev_y + step_y

                # Проверяем, не проходим ли мы уже через целевую точку
                if (abs(mid_x - curr_x) < 1 and abs(mid_y - curr_y) < 1):
                    path.append((curr_x, curr_y))
                else:
                    path.append((mid_x, mid_y))

                    # Добираемся до конечной точки
                    if mid_x != curr_x:
                        path.append((curr_x, mid_y))
                    if mid_y != curr_y:
                        path.append((curr_x, curr_y))

        # Оптимизация: удаляем лишние точки на одной прямой
        optimized_path = [path[0]]
        for i in range(1, len(path) - 1):
            x0, y0 = optimized_path[-1]
            x1, y1 = path[i]
            x2, y2 = path[i + 1]

            # Если три точки лежат на одной прямой, среднюю можно удалить
            if (x1 - x0) * (y2 - y0) != (x2 - x0) * (y1 - y0):
                optimized_path.append((x1, y1))

        optimized_path.append(path[-1])
        return optimized_path

    def redraw_map(self):
        self.canvas.delete("all")

        # Рисуем линии
        for line in self.lines:
            if len(line["stations"]) < 2:
                continue

            points = []
            for station_id in line["stations"]:
                station = next(s for s in self.stations if s["id"] == station_id)
                points.append(self.get_scaled_coords(station["x"], station["y"]))

            if line["smoothing"] == "straight":
                self.canvas.create_line(points, fill=line["color"], width=line["width"])
            elif line["smoothing"] == "smooth":
                # Сглаживание с использованием кубических кривых Безье
                smooth_points = []
                for i in range(len(points) - 1):
                    x1, y1 = points[i]
                    x2, y2 = points[i + 1]

                    if i == 0:  # Первая точка
                        x0, y0 = x1, y1
                    else:
                        x0, y0 = points[i - 1]

                    if i == len(points) - 2:  # Последняя точка
                        x3, y3 = x2, y2
                    else:
                        x3, y3 = points[i + 2]

                    # Контрольные точки для плавного перехода
                    cp1x = x1 + (x2 - x0) * 0.2
                    cp1y = y1 + (y2 - y0) * 0.2
                    cp2x = x2 - (x3 - x1) * 0.2
                    cp2y = y2 - (y3 - y1) * 0.2

                    # Генерируем точки вдоль кривой Безье
                    for t in [i / 10 for i in range(11)]:
                        t2 = t * t
                        t3 = t2 * t
                        mt = 1 - t
                        mt2 = mt * mt
                        mt3 = mt2 * mt

                        x = mt3 * x1 + 3 * mt2 * t * cp1x + 3 * mt * t2 * cp2x + t3 * x2
                        y = mt3 * y1 + 3 * mt2 * t * cp1y + 3 * mt * t2 * cp2y + t3 * y2
                        smooth_points.extend([x, y])

                self.canvas.create_line(smooth_points, fill=line["color"], width=line["width"], smooth=True)
            elif line["smoothing"] == "metro":
                metro_path = self.calculate_metro_path(points)
                self.canvas.create_line(metro_path, fill=line["color"], width=line["width"],
                                        smooth=False, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        # Рисуем станции
        for station in self.stations:
            x, y = self.get_scaled_coords(station["x"], station["y"])
            style = station.get("style", "circle")
            line_width = 2
            for line in self.lines:
                if station["id"] in line["stations"]:
                    line_width = line["width"]
                    break

            size_mult = max(1.4, line_width / 8 + 0.5)

            if style == "circle":
                self.canvas.create_oval(x - 5 * size_mult, y - 5 * size_mult, x + 5 * size_mult, y + 5 * size_mult,
                                        fill="white", outline="black")
            elif style == "square":
                self.canvas.create_rectangle(x - 5 * size_mult, y - 5 * size_mult, x + 5 * size_mult, y + 5 * size_mult,
                                             fill="white", outline="black")
            elif style == "horizontal rect":
                self.canvas.create_rectangle(x - 15 * size_mult, y - 5 * size_mult, x + 5 * size_mult,
                                             y + 5 * size_mult,
                                             fill="white", outline="black")
            elif style == "vertical rect":
                self.canvas.create_rectangle(x - 5 * size_mult, y - 15 * size_mult, x + 5 * size_mult,
                                             y + 5 * size_mult,
                                             fill="white", outline="black")
            elif style == "triangle":
                self.canvas.create_polygon(x, y - 6 * size_mult, x - 6 * size_mult, y + 6 * size_mult,
                                           x + 6 * size_mult, y + 6 * size_mult, fill="white", outline="black")
            elif style == "label":
                # Сначала чёрный текст (как "обводка") со смещением во все стороны
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    self.canvas.create_text(
                        x + dx,
                        y + dy,
                        text=station["name"],
                        anchor=tk.N,
                        font=("Minecraftia", 10),
                        fill="black"
                    )
                # Затем основной белый текст поверх
                self.canvas.create_text(
                    x,
                    y,
                    text=station["name"],
                    anchor=tk.N,
                    font=("Minecraftia", 10),
                    fill="white"
                )
            else:  # empty
                pass

            if style != "label" and style != "empty":
                if style == "horizontal rect":
                    x -= int(6 * size_mult)
                # Сначала чёрный текст (как "обводка") со смещением во все стороны
                for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    self.canvas.create_text(
                        x + dx,
                        y + dy + 14 * ((size_mult - 0.4) / 2),
                        text=station["name"],
                        anchor=tk.N,
                        font=("Minecraftia", 10),
                        fill="black"
                    )
                # Затем основной белый текст поверх
                self.canvas.create_text(
                    x,
                    y + 14 * ((size_mult - 0.4) / 2),
                    text=station["name"],
                    anchor=tk.N,
                    font=("Minecraftia", 10),
                    fill="white"
                )

    def export_png(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            # Создаем изображение с учетом масштаба
            padding = 40
            size = 1 / self.scale

            all_points = [(s["x"], s["y"]) for s in self.stations]
            if not all_points:
                messagebox.showerror("Ошибка", "Нет станций для экспорта")
                return

            min_x = min(p[0] // size for p in all_points) - padding
            max_x = max(p[0] // size for p in all_points) + padding
            min_y = min(p[1] // size for p in all_points) - padding
            max_y = max(p[1] // size for p in all_points) + padding

            width = int(max_x - min_x)
            height = int(max_y - min_y)

            img = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(img)

            # Рисуем линии
            for line in self.lines:
                if len(line["stations"]) < 2:
                    continue

                points = []
                for station_id in line["stations"]:
                    station = next(s for s in self.stations if s["id"] == station_id)
                    points.append((station["x"] // size - min_x, station["y"] // size - min_y))

                if line["smoothing"] == "straight":
                    draw.line(points, fill=line["color"], width=line["width"], joint="curve")
                elif line["smoothing"] == "smooth":
                    smooth_points = []
                    for i in range(len(points) - 1):
                        x1, y1 = points[i]
                        x2, y2 = points[i + 1]

                        if i == 0:  # Первая точка
                            x0, y0 = x1, y1
                        else:
                            x0, y0 = points[i - 1]

                        if i == len(points) - 2:  # Последняя точка
                            x3, y3 = x2, y2
                        else:
                            x3, y3 = points[i + 2]

                        cp1x = x1 + (x2 - x0) * 0.2
                        cp1y = y1 + (y2 - y0) * 0.2
                        cp2x = x2 - (x3 - x1) * 0.2
                        cp2y = y2 - (y3 - y1) * 0.2

                        for t in [i / 10 for i in range(11)]:
                            t2 = t * t
                            t3 = t2 * t
                            mt = 1 - t
                            mt2 = mt * mt
                            mt3 = mt2 * mt

                            x = mt3 * x1 + 3 * mt2 * t * cp1x + 3 * mt * t2 * cp2x + t3 * x2
                            y = mt3 * y1 + 3 * mt2 * t * cp1y + 3 * mt * t2 * cp2y + t3 * y2
                            smooth_points.append((x, y))

                    draw.line(smooth_points, fill=line["color"], width=line["width"])
                elif line["smoothing"] == "metro":
                    metro_path = self.calculate_metro_path(points)
                    draw.line(metro_path, fill=line["color"], width=line["width"], joint="curve")

            # Рисуем станции
            font = ImageFont.truetype(r"assets/Minecraft.ttf", 10)
            for station in self.stations:
                x, y = station["x"] // size - min_x, station["y"] // size - min_y
                style = station.get("style", "circle")

                line_width = 2
                for line in self.lines:
                    if station["id"] in line["stations"]:
                        line_width = line["width"]
                        break

                size_mult = max(1.4, line_width / 8 + 0.5)

                if style == "circle":
                    draw.ellipse([x - 5 * size_mult, y - 5 * size_mult, x + 5 * size_mult, y + 5 * size_mult],
                                 fill="white", outline="black")
                elif style == "square":
                    draw.rectangle([x - 5 * size_mult, y - 5 * size_mult, x + 5 * size_mult, y + 5 * size_mult],
                                   fill="white", outline="black")
                elif style == "horizontal rect":
                    draw.rectangle([x - 15 * size_mult, y - 5 * size_mult, x + 5 * size_mult, y + 5 * size_mult],
                                   fill="white", outline="black")
                elif style == "vertical rect":
                    draw.rectangle([x - 5 * size_mult, y - 15 * size_mult, x + 5 * size_mult, y + 5 * size_mult],
                                   fill="white", outline="black")
                elif style == "triangle":
                    draw.polygon([x, y - 6 * size_mult, x - 6 * size_mult, y + 6 * size_mult, x + 6 * size_mult,
                                  y + 6 * size_mult], fill="white", outline="black")
                elif style == "label":
                    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        draw.text((x + dx, y + dy),
                                  station["name"], fill="black", anchor="ma", font=font)
                    # Затем основной чёрный текст
                    draw.text((x, y),
                              station["name"], fill="white", anchor="ma", font=font)
                else:  # empty
                    pass

                if style != "label" and style != "empty":
                    if style == "horizontal rect":
                        x -= int(6 * size_mult)
                    for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                        draw.text((x + dx, y + 14 * ((size_mult - 0.4) / 2) + dy),
                                  station["name"], fill="black", anchor="ma", font=font)
                    # Затем основной чёрный текст
                    draw.text((x, y + 14 * ((size_mult - 0.4) / 2)),
                              station["name"], fill="white", anchor="ma", font=font)

            img.save(file_path)

    def export_json(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            data = {
                "lines": self.lines,
                "stations": self.stations,
                "scale": self.scale,
                "offset_x": self.offset_x,
                "offset_y": self.offset_y
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Успех", f"Данные сохранены как {file_path}")

    def import_json(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.lines = data.get("lines", [])
                self.stations = data.get("stations", [])
                self.scale = data.get("scale", 1.0)
                self.offset_x = data.get("offset_x", 0)
                self.offset_y = data.get("offset_y", 0)
                self.scale_slider.set(self.scale)

                self.selected_line = None
                self.selected_station = None
                self.update_lines_list()
                self.update_stations_list()
                self.redraw_map()

                messagebox.showinfo("Успех", f"Данные загружены из {file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = MetroMapGenerator(root)
    root.mainloop()
