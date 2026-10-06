import os
import tempfile
import unittest

from app import CatalogApp
from catalog_manager import CatalogError, CatalogManager


class CatalogManagerGuideTests(unittest.TestCase):
    def test_validate_optional_explanatory_guides(self):
        data = {
            "ordenColecciones": ["jaulas"],
            "guiasVisuales": {
                "jaulas": [{"src": "/images/explicaciones/jaulas/modelo.webp", "alt": "Modelo de canil"}],
                "lista-personalizada": [],
            },
            "jaulas": [{"id": 1, "nombre": "Canil", "galeria": []}],
        }

        CatalogManager.validate(data)

    def test_validate_mixed_explanatory_guides_with_youtube(self):
        data = {
            "guiasVisuales": {
                "jaulas": [
                    {"src": "/images/explicaciones/jaulas/modelo.webp", "alt": "Modelo de canil"},
                    {"tipo": "video", "src": "https://youtu.be/dQw4w9WgXcQ", "alt": "Video del modelo"},
                ],
            },
        }

        CatalogManager.validate(data)

    def test_reject_invalid_explanatory_guide_item(self):
        with self.assertRaises(CatalogError):
            CatalogManager.validate({"guiasVisuales": {"jaulas": [{"src": "/images/guide.webp"}]}})

    def test_reject_invalid_explanatory_guide_video_url(self):
        with self.assertRaises(CatalogError):
            CatalogManager.validate({"guiasVisuales": {"jaulas": [{"tipo": "video", "src": "https://vimeo.com/123456", "alt": "Video"}]}})

    def test_load_assigns_uids_to_existing_products_and_rows(self):
        data = {
            "jaulas": [{"id": 1, "nombre": "Canil", "galeria": []}],
            "listasPersonalizadas": [{
                "clave": "especial",
                "titulo": "Especial",
                "columnas": [{"clave": "producto", "nombre": "Producto"}],
                "filas": [{"id": 1, "celdas": {"producto": "Fila"}, "galeria": []}],
            }],
        }

        project_root = tempfile.mkdtemp(prefix="catalog_test_")
        json_path = os.path.join(project_root, "src", "data", "productos.json")
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as handle:
            import json
            json.dump(data, handle)

        loaded = CatalogManager(project_root).load()

        self.assertRegex(loaded["jaulas"][0]["uid"], r"^[A-Za-z0-9_-]{16,64}$")
        self.assertRegex(loaded["listasPersonalizadas"][0]["filas"][0]["uid"], r"^[A-Za-z0-9_-]{16,64}$")

    def test_rejects_duplicate_uids_in_one_collection(self):
        data = {
            "jaulas": [
                {"id": 1, "uid": "producto-estable-001", "nombre": "A", "galeria": []},
                {"id": 2, "uid": "producto-estable-001", "nombre": "B", "galeria": []},
            ],
        }

        with self.assertRaises(CatalogError):
            CatalogManager.validate(data)


class CatalogManagerPriceExcelTests(unittest.TestCase):
    def test_import_prices_accepts_missing_price_marker(self):
        data = {
            "jaulas": [{"id": 10, "nombre": "Jaula A", "precio": 1000, "galeria": []}],
        }

        project_root = tempfile.mkdtemp(prefix="catalog_test_")
        json_path = os.path.join(project_root, "src", "data", "productos.json")
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as handle:
            import json
            json.dump(data, handle)

        manager = CatalogManager(project_root)
        excel_path = os.path.join(project_root, "precios.xlsx")
        manager.export_prices_excel(excel_path)
        workbook = manager.load_workbook(excel_path)
        workbook.active.cell(row=2, column=4).value = "----"
        workbook.save(excel_path)

        result = manager.import_prices_excel(excel_path)

        self.assertEqual(result["updated"], 1)
        self.assertEqual(manager.data["jaulas"][0]["precio"], "----")

    def test_export_and_import_prices_by_id(self):
        data = {
            "ordenColecciones": ["jaulas", "mallas"],
            "jaulas": [
                {"id": 10, "nombre": "Jaula A", "precio": 1000, "galeria": []},
                {"id": 20, "nombre": "Jaula B", "precio": 2000, "galeria": []},
            ],
            "mallas": [
                {"id": 7, "nombre": "Malla", "precio": 777, "precioZincado": 800, "precioCrudo": 700, "galeria": []},
            ],
        }

        project_root = tempfile.mkdtemp(prefix="catalog_test_")
        json_path = os.path.join(project_root, "src", "data", "productos.json")
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as handle:
            import json
            json.dump(data, handle)

        manager = CatalogManager(project_root)
        excel_path = os.path.join(project_root, "precios.xlsx")
        manager.export_prices_excel(excel_path)

        # Reorder rows and change values in the workbook to verify it updates by ID, not by position.
        workbook = manager.load_workbook(excel_path)
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
        sheet.delete_rows(2, len(rows) - 1)
        sheet.append(["jaulas", 20, "Jaula B", 9999])
        sheet.append(["jaulas", 10, "Jaula A", 1234])
        sheet.append(["mallas", 7, "Malla", 4567])
        workbook.save(excel_path)

        result = manager.import_prices_excel(excel_path)

        self.assertEqual(result["updated"], 3)
        self.assertEqual(manager.data["jaulas"][1]["precio"], 9999)
        self.assertEqual(manager.data["jaulas"][0]["precio"], 1234)
        self.assertEqual(manager.data["mallas"][0]["precio"], 4567)


class CatalogAppPriceEditorTests(unittest.TestCase):
    def test_price_editor_accepts_missing_price_marker(self):
        for key in ("precio", "precioZincado", "precioCrudo"):
            valid, converted = CatalogApp._convert_editor_value("----", 1000, key)

            self.assertTrue(valid)
            self.assertEqual(converted, "----")

    def test_price_editor_still_accepts_numbers(self):
        valid, converted = CatalogApp._convert_editor_value("1250", 1000, "precio")

        self.assertTrue(valid)
        self.assertEqual(converted, 1250)


class CatalogAppItemOrderTests(unittest.TestCase):
    def test_move_item_reorders_original_products_and_custom_rows(self):
        original_products = [{"id": 1}, {"id": 2}, {"id": 3}]
        custom_rows = [{"id": 10}, {"id": 20}, {"id": 30}]

        original_selection = CatalogApp._move_item(original_products, 1, 1)
        custom_selection = CatalogApp._move_item(custom_rows, 1, -1)

        self.assertEqual(original_selection, 2)
        self.assertEqual([item["id"] for item in original_products], [1, 3, 2])
        self.assertEqual(custom_selection, 0)
        self.assertEqual([row["id"] for row in custom_rows], [20, 10, 30])

    def test_move_item_keeps_order_at_list_boundaries(self):
        items = [{"id": 1}, {"id": 2}]

        self.assertIsNone(CatalogApp._move_item(items, 0, -1))
        self.assertIsNone(CatalogApp._move_item(items, 1, 1))
        self.assertEqual([item["id"] for item in items], [1, 2])


class CatalogAppCustomListStructureTests(unittest.TestCase):
    def test_apply_structure_keeps_renamed_column_data_and_removes_deleted_column(self):
        custom_list = {
            "titulo": "Anterior",
            "columnas": [
                {"clave": "producto", "nombre": "Producto"},
                {"clave": "medida", "nombre": "Medida"},
            ],
            "filas": [
                {"celdas": {"producto": "Canil", "medida": "60 cm"}},
                {"celdas": {"producto": "Reja", "medida": "90 cm"}},
            ],
        }
        columns = [
            {"clave": "producto", "nombre": "Artículo"},
            {"clave": "precio", "nombre": "Precio"},
        ]

        CatalogApp._apply_custom_list_structure(custom_list, "Nueva", columns)

        self.assertEqual(custom_list["titulo"], "Nueva")
        self.assertEqual(custom_list["columnas"], columns)
        self.assertEqual(custom_list["filas"][0]["celdas"], {"producto": "Canil"})
        self.assertEqual(custom_list["filas"][1]["celdas"], {"producto": "Reja"})

    def test_reordering_columns_preserves_keys_and_row_values(self):
        columns = [
            {"clave": "producto", "nombre": "Producto"},
            {"clave": "medida", "nombre": "Medida"},
            {"clave": "precio", "nombre": "Precio"},
        ]
        rows = [{"celdas": {"producto": "Canil", "medida": "60 cm", "precio": "1200"}}]
        original_cells = rows[0]["celdas"].copy()

        target_index = CatalogApp._move_item(columns, 0, 1)

        self.assertEqual(target_index, 1)
        self.assertEqual([column["clave"] for column in columns], ["medida", "producto", "precio"])
        self.assertEqual(rows[0]["celdas"], original_cells)


if __name__ == "__main__":
    unittest.main()
