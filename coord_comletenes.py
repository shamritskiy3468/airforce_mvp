import argparse
import csv
from pyproj import Transformer

def gk_to_epsg3857(x_gk, y_gk):
    """
    Переводит координаты из 5-й зоны Гаусса-Крюгера (СК-42, EPSG:28405)
    в географические WGS84 (EPSG:4326) и прямоугольные Web Mercator (EPSG:3857).
    """
    # Коррекция Y, если передано 6-значное число без номера зоны насале (например, 435000 вместо 5435000)
    if y_gk < 1000000:
        y_gk_corrected = y_gk + 5000000
        print(f"-> Координата Y скорректирована под 5-ю зону: {y_gk} -> {y_gk_corrected}")
    else:
        y_gk_corrected = y_gk

    # 1. Шаг: Из Гаусса-Крюгера (Зона 5) в стандартную Широту/Долготу (WGS84)
    # Исходная СК: EPSG:28405 (Pulkovo 1942 / Gauss-Kruger zone 5)
    # Порядок XY в pyproj для этих СК: True Easting (Y), True Northing (X)
    to_wgs84 = Transformer.from_crs("EPSG:28405", "EPSG:4326", always_xy=True)
    lon, lat = to_wgs84.transform(y_gk_corrected, x_gk)

    # 2. Шаг: Из WGS84 в Web Mercator (EPSG:3857) для карт
    to_3857 = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    x_3857, y_3857 = to_3857.transform(lon, lat)

    return lat, lon, x_3857, y_3857

def save_to_qgis_csv(filename, x_gk, y_gk, lat, lon, x_3857, y_3857):
    """Сохраняет данные в формате CSV, идеально подходящем для QGIS"""
    headers = ["id", "src_X_GK", "src_Y_GK", "lat", "lon", "X_3857", "Y_3857"]
    
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow([1, x_gk, y_gk, f"{lat:.8f}", f"{lon:.8f}", f"{x_3857:.2f}", f"{y_3857:.2f}"])
    
    print(f"\n[Успешно] Файл для QGIS создан: {filename}")
    print("Содержимое CSV:")
    print(f"{', '.join(headers)}")
    print(f"1, {x_gk}, {y_gk}, {lat:.8f}, {lon:.8f}, {x_3857:.2f}, {y_3857:.2f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Конвертер Гаусса-Крюгера (5 зона) в EPSG:3857 и WGS84 с выводом CSV для QGIS")
    parser.add_argument("--xcoord", type=float, required=True, help="Координата X (Северное смещение, обычно 7 знаков, например 5971485)")
    parser.add_argument("--ycoord", type=float, required=True, help="Координата Y (Восточное смещение, 6 или 7 знаков, например 5354228)")
    parser.add_argument("--output", type=str, default="qgis_layer.csv", help="Имя выходного CSV файла (по умолчанию: qgis_layer.csv)")

    args = parser.parse_args()

    # Конвертация
    lat, lon, x_3857, y_3857 = gk_to_epsg3857(args.xcoord, args.ycoord)
    
    # Сохранение
    save_to_qgis_csv(args.output, args.xcoord, args.ycoord, lat, lon, x_3857, y_3857)
