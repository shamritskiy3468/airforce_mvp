import math
import csv

start = (53.8825, 28.0325) # start point (Minsk)
end = (25.2528, 55.3644) # end point (Dubai)

distance_km = 3540 # distance between Minsk and Dubai - или считать руками или взять готовое
steps = distance_km

lat_step = (end[0] - start[0]) / steps
lon_step = (end[1] - start[1]) / steps

points = []

for i in range(steps + 1):
    lat = start[0] + lat_step * i
    lon = start[1] + lon_step * i
    points.append((lat, lon, 10000))

with open("./input/dubai_minst_linear_route.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["lat", "lon", "altitude"])
    writer.writerows(points)