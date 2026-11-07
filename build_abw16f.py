import base64
import math
from pathlib import Path

import bpy


OUTPUT = Path(__file__).resolve().parent
MESHES = {}
MATERIALS = {}
WORKSTATIONS = []


def material(name, color, metallic=0.0, roughness=0.7):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1.0)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    MATERIALS[name] = mat
    return mat


def mesh_for(shape, mat):
    key = (shape, mat.name)
    if key in MESHES:
        return MESHES[key]

    mesh = bpy.data.meshes.new(f"{shape}_{mat.name}")
    if shape == "cube":
        vertices = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
        ]
        faces = [
            (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
            (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
        ]
    elif shape == "sphere":
        golden = (1 + math.sqrt(5)) / 2
        vertices = [
            (-1, golden, 0), (1, golden, 0), (-1, -golden, 0), (1, -golden, 0),
            (0, -1, golden), (0, 1, golden), (0, -1, -golden), (0, 1, -golden),
            (golden, 0, -1), (golden, 0, 1), (-golden, 0, -1), (-golden, 0, 1),
        ]
        vertices = [tuple(value / golden for value in vertex) for vertex in vertices]
        faces = [
            (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
            (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
            (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
            (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1),
        ]
    else:
        segments = 20
        vertices = []
        faces = []
        for z in (-1.0, 1.0):
            for index in range(segments):
                angle = 2 * math.pi * index / segments
                vertices.append((math.cos(angle), math.sin(angle), z))
        for index in range(segments):
            next_index = (index + 1) % segments
            faces.append((index, next_index, next_index + segments, index + segments))
        faces.append(tuple(reversed(range(segments))))
        if shape == "cone":
            vertices.append((0, 0, 1.35))
            tip = len(vertices) - 1
            for index in range(segments):
                faces.append((index + segments, (index + 1) % segments + segments, tip))
        else:
            faces.append(tuple(range(segments, segments * 2)))

    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    mesh.update()
    MESHES[key] = mesh
    return mesh


def shape(name, position, dimensions, mat, primitive="cube", rotation=0.0):
    obj = bpy.data.objects.new(name, mesh_for(primitive, mat))
    bpy.context.collection.objects.link(obj)
    obj.location = position
    obj.scale = (dimensions[0] / 2, dimensions[1] / 2, dimensions[2] / 2)
    obj.rotation_euler[2] = rotation
    return obj


def box(name, x, y, z, width, depth, height, mat, rotation=0.0):
    return shape(name, (x, y, z), (width, depth, height), mat, rotation=rotation)


def cylinder(name, x, y, z, radius, height, mat):
    return shape(name, (x, y, z), (radius * 2, radius * 2, height), mat, "cylinder")


def cone(name, x, y, z, radius, height, mat, rotation=0.0):
    return shape(name, (x, y, z), (radius * 2, radius * 2, height / 1.175), mat, "cone", rotation)


def rotated_offset(x, y, dx, dy, angle):
    return (
        x + dx * math.cos(angle) - dy * math.sin(angle),
        y + dx * math.sin(angle) + dy * math.cos(angle),
    )


def chair(x, y, angle=0.0, prefix="Chair"):
    def part(label, dx, dy, z, width, depth, height, mat):
        px, py = rotated_offset(x, y, dx, dy, angle)
        return box(f"{prefix} {label}", px, py, z, width, depth, height, mat, angle)

    part("seat", 0, 0, 0.49, 0.56, 0.54, 0.13, MATERIALS["chair_seat"])
    part("back", 0, -0.22, 0.83, 0.54, 0.12, 0.57, MATERIALS["chair_back"])
    part("stem", 0, 0, 0.27, 0.1, 0.1, 0.35, MATERIALS["metal"])
    for dx, dy in ((-0.19, -0.19), (0.19, -0.19), (-0.19, 0.19), (0.19, 0.19)):
        part("foot", dx, dy, 0.09, 0.32, 0.07, 0.07, MATERIALS["metal"])


def avatar_part(parent, name, position, dimensions, mat, primitive="cube"):
    obj = bpy.data.objects.new(name, mesh_for(primitive, mat))
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = position
    obj.scale = (dimensions[0] / 2, dimensions[1] / 2, dimensions[2] / 2)
    return obj


def person(name, x, y, angle=0.0, pose="seated", shirt_name="shirt_teal"):
    root = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(root)
    root.location = (x, y, 0)
    root.rotation_euler[2] = angle
    shirt = MATERIALS[shirt_name]
    skin = MATERIALS["skin_dark"] if sum(name.encode("utf-8")) % 2 else MATERIALS["skin_light"]

    avatar_part(root, f"{name}_torso", (0, 0, 1.1), (0.42, 0.28, 0.48), shirt)
    avatar_part(root, f"{name}_head", (0, 0.01, 1.53), (0.28, 0.29, 0.31), skin, "sphere")
    avatar_part(root, f"{name}_hair", (0, -0.015, 1.66), (0.27, 0.28, 0.11), MATERIALS["hair"])

    if pose == "seated":
        for side in (-1, 1):
            avatar_part(root, f"{name}_thigh_{side}", (side * 0.12, 0.18, 0.63),
                        (0.16, 0.44, 0.15), MATERIALS["pants"])
            avatar_part(root, f"{name}_shin_{side}", (side * 0.12, 0.42, 0.31),
                        (0.13, 0.14, 0.38), MATERIALS["pants"])
            avatar_part(root, f"{name}_shoe_{side}", (side * 0.12, 0.53, 0.09),
                        (0.16, 0.28, 0.12), MATERIALS["shoes"])
            avatar_part(root, f"{name}_upper_arm_{side}", (side * 0.25, 0.02, 1.08),
                        (0.13, 0.15, 0.3), shirt)
            avatar_part(root, f"{name}_forearm_{side}", (side * 0.25, 0.23, 0.91),
                        (0.11, 0.34, 0.11), shirt)
            avatar_part(root, f"{name}_hand_{side}", (side * 0.25, 0.41, 0.9),
                        (0.11, 0.12, 0.1), skin)
    else:
        for side, label in ((-1, "left"), (1, "right")):
            leg = bpy.data.objects.new(f"{name}_leg_{label}", None)
            bpy.context.collection.objects.link(leg)
            leg.parent = root
            leg.location = (side * 0.12, 0, 0.82)
            avatar_part(leg, f"{name}_thigh_{label}", (0, 0, -0.18),
                        (0.16, 0.16, 0.38), MATERIALS["pants"])
            avatar_part(leg, f"{name}_shin_{label}", (0, 0, -0.55),
                        (0.13, 0.14, 0.37), MATERIALS["pants"])
            avatar_part(leg, f"{name}_shoe_{label}", (0, 0.08, -0.77),
                        (0.16, 0.28, 0.12), MATERIALS["shoes"])

            arm = bpy.data.objects.new(f"{name}_arm_{label}", None)
            bpy.context.collection.objects.link(arm)
            arm.parent = root
            arm.location = (side * 0.23, 0, 1.28)
            avatar_part(arm, f"{name}_upper_arm_{label}", (side * 0.04, 0, -0.13),
                        (0.13, 0.15, 0.3), shirt)
            avatar_part(arm, f"{name}_forearm_{label}", (side * 0.05, 0.12, -0.3),
                        (0.11, 0.29, 0.11), shirt)
            avatar_part(arm, f"{name}_hand_{label}", (side * 0.05, 0.27, -0.3),
                        (0.11, 0.11, 0.1), skin)
    return root


def animate_walker(root, route, start_index):
    points = route[start_index:] + route[:start_index]
    frames = (1, 49, 97, 145)
    previous_angle = None
    headings = []
    for index, (x, y) in enumerate(points):
        next_x, next_y = points[(index + 1) % len(points)]
        angle = math.atan2(-(next_x - x), next_y - y)
        if previous_angle is not None:
            while angle < previous_angle:
                angle += 2 * math.pi
        headings.append(angle)
        previous_angle = angle

    for frame, point, angle in zip(frames, points, headings):
        root.location = (point[0], point[1], 0)
        root.rotation_euler[2] = angle
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)

    root.location = (points[0][0], points[0][1], 0)
    root.rotation_euler[2] = headings[0] + 2 * math.pi
    root.keyframe_insert(data_path="location", frame=193)
    root.keyframe_insert(data_path="rotation_euler", frame=193)
    action = root.animation_data.action
    action.name = f"{root.name}_WalkingLoop"
    channelbag = action.layers[0].strips[0].channelbag(action.slots[0])
    for curve in channelbag.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
        curve.modifiers.new(type="CYCLES")


def workstation(x, y, prefix="Desk"):
    box(f"{prefix} top", x, y, 0.76, 1.22, 0.68, 0.11, MATERIALS["wood"])
    for dx in (-0.51, 0.51):
        for dy in (-0.25, 0.25):
            box(f"{prefix} leg", x + dx, y + dy, 0.37, 0.07, 0.07, 0.72, MATERIALS["metal"])
    box(f"{prefix} monitor", x, y + 0.16, 1.12, 0.72, 0.075, 0.43, MATERIALS["screen"])
    box(f"{prefix} stand", x, y + 0.15, 0.91, 0.09, 0.09, 0.24, MATERIALS["metal"])
    chair(x, y - 0.83, prefix=f"{prefix} chair")
    WORKSTATIONS.append((x, y, prefix))


def meeting_table(x, y, width, depth, count, prefix, round_table=False):
    attendance = {
        "North conference": {0, 3, 4},
        "Design review": {1, 3, 5},
        "East meeting": {0, 2, 4},
        "South meeting": {1, 2, 5},
        "Team cafe": {1},
        "Collaboration cafe": {3},
    }
    attendees = attendance.get(prefix, set())
    if round_table:
        cylinder(f"{prefix} top", x, y, 0.78, width / 2, 0.11, MATERIALS["wood"])
        cylinder(f"{prefix} pedestal", x, y, 0.4, 0.12, 0.68, MATERIALS["metal"])
        for index in range(count):
            angle = 2 * math.pi * index / count
            px = x + math.cos(angle) * (width / 2 + 0.52)
            py = y + math.sin(angle) * (width / 2 + 0.52)
            facing = angle - math.pi / 2
            chair(px, py, facing, f"{prefix} chair")
            if index in attendees:
                person(f"Meeting_{prefix.replace(' ', '_')}_{index}", px, py, facing,
                       shirt_name="shirt_coral" if index % 2 else "shirt_mustard")
        return

    box(f"{prefix} top", x, y, 0.78, width, depth, 0.12, MATERIALS["wood"])
    for dx in (-width * 0.4, width * 0.4):
        for dy in (-depth * 0.32, depth * 0.32):
            box(f"{prefix} leg", x + dx, y + dy, 0.39, 0.09, 0.09, 0.73, MATERIALS["metal"])
    side_count = count // 2
    seat_index = 0
    for index in range(side_count):
        px = x - width * 0.36 + index * width * 0.72 / max(1, side_count - 1)
        for seat_y, facing in ((y - depth / 2 - 0.48, 0), (y + depth / 2 + 0.48, math.pi)):
            chair(px, seat_y, facing, f"{prefix} chair")
            if seat_index in attendees:
                person(f"Meeting_{prefix.replace(' ', '_')}_{seat_index}", px, seat_y, facing,
                       shirt_name="shirt_coral" if seat_index % 2 else "shirt_mustard")
            seat_index += 1


def plant(x, y, prefix="Plant"):
    cylinder(f"{prefix} pot", x, y, 0.33, 0.3, 0.62, MATERIALS["terracotta"])
    cylinder(f"{prefix} soil", x, y, 0.66, 0.25, 0.04, MATERIALS["soil"])
    for index in range(5):
        angle = index * 2.0 * math.pi / 5
        px = x + math.cos(angle) * 0.13
        py = y + math.sin(angle) * 0.13
        cone(f"{prefix} leaf", px, py, 1.22 + (index % 2) * 0.1, 0.17, 1.2, MATERIALS["leaf"], angle)


def build_scene():
    WORKSTATIONS.clear()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    colors = {
        "floor": ((0.69, 0.72, 0.69), 0.0, 0.9),
        "rug": ((0.31, 0.48, 0.46), 0.0, 0.9),
        "wood": ((0.63, 0.4, 0.22), 0.0, 0.72),
        "metal": ((0.25, 0.3, 0.31), 0.45, 0.36),
        "screen": ((0.075, 0.15, 0.17), 0.1, 0.32),
        "chair_seat": ((0.12, 0.4, 0.39), 0.0, 0.68),
        "chair_back": ((0.83, 0.35, 0.2), 0.0, 0.7),
        "core": ((0.2, 0.24, 0.25), 0.12, 0.54),
        "lift": ((0.47, 0.53, 0.52), 0.2, 0.38),
        "terracotta": ((0.65, 0.28, 0.18), 0.0, 0.78),
        "soil": ((0.19, 0.14, 0.1), 0.0, 1.0),
        "leaf": ((0.2, 0.4, 0.22), 0.0, 0.82),
        "white": ((0.82, 0.83, 0.78), 0.0, 0.72),
        "skin_light": ((0.77, 0.53, 0.37), 0.0, 0.85),
        "skin_dark": ((0.42, 0.25, 0.17), 0.0, 0.85),
        "hair": ((0.12, 0.11, 0.1), 0.0, 0.9),
        "pants": ((0.17, 0.24, 0.31), 0.0, 0.8),
        "shoes": ((0.16, 0.17, 0.16), 0.0, 0.75),
        "shirt_teal": ((0.1, 0.42, 0.4), 0.0, 0.8),
        "shirt_coral": ((0.83, 0.31, 0.2), 0.0, 0.8),
        "shirt_mustard": ((0.82, 0.57, 0.17), 0.0, 0.8),
        "shirt_blue": ((0.24, 0.38, 0.55), 0.0, 0.8),
    }
    for name, (color, metallic, roughness) in colors.items():
        material(name, color, metallic, roughness)

    box("Open floor slab", 0, 0, -0.16, 34, 23, 0.32, MATERIALS["floor"])
    box("Left work zone rug", -12, 0.1, 0.012, 8.3, 10.2, 0.025, MATERIALS["rug"])
    box("Upper work zone rug", -1, 8.25, 0.012, 12.2, 4.2, 0.025, MATERIALS["rug"])
    box("Right training zone rug", 11.6, 2.6, 0.012, 8.8, 8.5, 0.025, MATERIALS["rug"])

    for row, y in enumerate((-9.0, -7.1, -5.2)):
        for column, x in enumerate((-14, -10, -6, -2, 2, 6, 10, 14)):
            workstation(x, y, f"Open office {row + 1}-{column + 1}")

    for row, y in enumerate((-3.2, 0.0, 3.2)):
        for column, x in enumerate((-14.4, -11.2, -8.0)):
            workstation(x, y, f"West wing {row + 1}-{column + 1}")

    for column, x in enumerate((-13, -9, -5, 4.2, 8.2)):
        workstation(x, 9.15, f"North wing {column + 1}")

    box("Central core base", 0.2, 1.45, 0.23, 7.2, 5.4, 0.46, MATERIALS["core"])
    for index, (x, y) in enumerate(((-1.6, 0.3), (0.2, 0.3), (2.0, 0.3), (-0.7, 2.5), (1.1, 2.5))):
        box(f"Lift core {index + 1}", x, y, 1.5, 1.35, 1.55, 2.45, MATERIALS["lift"])
        box(f"Lift door {index + 1}", x, y - 0.79, 1.35, 0.76, 0.045, 1.8, MATERIALS["screen"])

    meeting_table(-5.0, 5.9, 3.5, 1.35, 6, "North conference")
    meeting_table(4.0, 6.1, 3.0, 1.25, 6, "Design review")
    meeting_table(11.5, 6.5, 2.4, 1.2, 6, "East meeting")
    meeting_table(11.2, -5.5, 2.5, 1.2, 6, "South meeting")
    meeting_table(-6.7, -1.5, 1.7, 1.7, 4, "Team cafe", True)
    meeting_table(6.7, -1.8, 1.7, 1.7, 4, "Collaboration cafe", True)

    for row, y in enumerate((0.2, -2.0, -4.2)):
        for column, x in enumerate((9.4, 13.3)):
            workstation(x, y, f"East studio {row + 1}-{column + 1}")

    shirts = ("shirt_teal", "shirt_coral", "shirt_mustard", "shirt_blue")
    for index, (x, y, _) in enumerate(WORKSTATIONS):
        if index % 4 == 0:
            person(f"Worker_{index + 1:02d}", x, y - 0.83, shirt_name=shirts[index % len(shirts)])

    route = [(-5.3, -4.3), (5.3, -4.3), (5.3, 4.35), (-5.3, 4.35)]
    for index in range(3):
        start = route[index]
        walker = person(f"Walker_{index + 1:02d}", start[0], start[1], pose="walking",
                        shirt_name=shirts[(index + 1) % len(shirts)])
        animate_walker(walker, route, index)

    for x, y in ((-16, 8.8), (-16, 4.7), (-16, -5.0), (-8.2, 7.2),
                 (3.0, 8.9), (8.5, 8.8), (16, 4.2), (16, -0.5),
                 (16, -7.0), (7.5, -8.6), (-3.5, -9.8)):
        plant(x, y)

    bpy.ops.object.camera_add(location=(32, -38, 38))
    camera = bpy.context.object
    camera.name = "Presentation camera"
    direction = -camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 43
    bpy.context.scene.camera = camera

    for name, location, energy, size in (
        ("Key light", (1, -10, 28), 5200, 18),
        ("Fill light", (-18, 8, 22), 3600, 16),
        ("Rim light", (18, 12, 24), 2800, 14),
    ):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (-light.location).to_track_quat("-Z", "Y").to_euler()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.72, 0.75, 0.72)
    scene.render.filepath = str(OUTPUT / "ABW16F_preview.png")
    scene.view_settings.view_transform = "AgX"
    scene.unit_settings.system = "METRIC"
    scene.frame_start = 1
    scene.frame_end = 193
    scene.render.fps = 24
    scene.frame_set(1)


HTML = r'''<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f2f1ec">
  <title>ABW16F | 3D 辦公室配置</title>
  <style>
    :root{color-scheme:light;--paper:#f2f1ec;--ink:#252d2b;--muted:#697370;--line:#d5d9d3;--teal:#176b66;--coral:#c95038;--lime:#d8e887}
    *{box-sizing:border-box}
    html,body{height:100%;margin:0;overflow:hidden}
    body{background:var(--paper);color:var(--ink);font-family:"Aptos","Microsoft JhengHei",sans-serif}
    .stage{position:fixed;inset:0;background-color:#eeefea;background-image:linear-gradient(rgba(42,66,61,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(42,66,61,.045) 1px,transparent 1px);background-size:28px 28px}
    canvas{display:block;width:100%;height:100%;outline:none}
    .masthead{position:absolute;top:24px;left:28px;display:flex;align-items:flex-start;gap:14px;pointer-events:none}
    .mark{display:grid;place-items:center;width:42px;height:42px;background:var(--teal);color:white;font-size:12px;font-weight:800;border-radius:4px}
    .title h1{font-size:20px;line-height:1.15;margin:0;font-weight:750}
    .title p{margin:5px 0 0;color:var(--muted);font-size:12px}
    .badge{position:absolute;top:27px;right:28px;padding:8px 11px;border:1px solid var(--line);border-radius:3px;background:rgba(248,248,244,.82);font-size:11px;color:var(--muted);letter-spacing:.04em}
    .panel{position:absolute;left:28px;bottom:26px;width:min(280px,calc(100vw - 32px));padding:16px 17px 14px;border:1px solid var(--line);border-radius:4px;background:rgba(248,248,244,.92);box-shadow:0 10px 28px rgba(27,38,34,.08);backdrop-filter:blur(10px)}
    .panel h2{margin:0 0 12px;font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
    .legend{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px;font-size:12px}
    .legend span{display:flex;align-items:center;gap:8px;white-space:nowrap}
    .swatch{width:9px;height:9px;border-radius:2px;background:var(--teal)}
    .swatch.wood{background:#a16638}.swatch.coral{background:var(--coral)}.swatch.green{background:#578044}
    .note{border-top:1px solid var(--line);margin:13px 0 0;padding-top:10px;font-size:11px;color:var(--muted);line-height:1.5}
    .controls{position:absolute;right:28px;bottom:26px;display:flex;align-items:center;gap:6px;padding:7px;border:1px solid var(--line);border-radius:4px;background:rgba(248,248,244,.94);box-shadow:0 8px 22px rgba(27,38,34,.08)}
    button{height:36px;min-width:36px;border:1px solid transparent;border-radius:3px;background:transparent;color:var(--ink);font:inherit;font-size:17px;cursor:pointer}
    button:hover{background:#e5e9e1;border-color:#cdd5cb}
    button:focus-visible{outline:2px solid var(--teal);outline-offset:2px}
    button.reset{width:auto;padding:0 12px;border-left:1px solid var(--line);font-size:12px;font-weight:650}
    .status{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);padding:10px 14px;border-radius:3px;background:#fff;color:var(--muted);font-size:13px;box-shadow:0 4px 18px #25312c20}
    .status[hidden]{display:none}
    @media(max-width:600px){.masthead{top:15px;left:15px}.badge{top:17px;right:15px}.title h1{font-size:17px}.panel{left:12px;bottom:12px;width:calc(100vw - 24px);padding:12px 13px}.panel h2{margin-bottom:8px}.legend{gap:7px 10px}.note{margin-top:9px;padding-top:8px}.controls{top:74px;right:12px;bottom:auto;padding:5px;gap:2px}.controls button{min-width:34px;height:34px}.controls button.reset{padding:0 8px}.badge{font-size:10px}}
  </style>
</head>
<body>
  <main class="stage" aria-label="ABW16F 互動式 3D 辦公室模型">
    <div class="masthead"><div class="mark">16F</div><div class="title"><h1>ABW16F 空間配置</h1><p>Infineon Taiwan · Taipei Office</p></div></div>
    <div class="badge">ACTIVE OFFICE / 3D VIEW</div>
    <div class="panel"><h2>空間圖例</h2><div class="legend"><span><i class="swatch"></i>開放工位</span><span><i class="swatch wood"></i>會議桌</span><span><i class="swatch coral"></i>協作座椅</span><span><i class="swatch green"></i>植栽休憩</span></div><p class="note">依參考圖重建之示意模型；未提供工程尺寸，比例與家具位置僅供空間檢視。</p></div>
    <div class="controls" aria-label="視角控制">
      <button type="button" data-turn="left" title="向左旋轉" aria-label="向左旋轉">←</button>
      <button type="button" data-turn="up" title="向上旋轉" aria-label="向上旋轉">↑</button>
      <button type="button" data-turn="down" title="向下旋轉" aria-label="向下旋轉">↓</button>
      <button type="button" data-turn="right" title="向右旋轉" aria-label="向右旋轉">→</button>
      <button type="button" class="reset" id="reset" title="重設視角">重設</button>
    </div>
    <div id="status" class="status">正在載入 3D 模型…</div>
  </main>
  <script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}</script>
  <script type="module">
    import * as THREE from 'three';
    import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
    import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

    const stage = document.querySelector('.stage');
    const status = document.querySelector('#status');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#eeefea');
    const basePosition = new THREE.Vector3(34, 31, 38);
    const isMobile = innerWidth < 600;
    const camera = new THREE.PerspectiveCamera(isMobile ? 64 : 42, innerWidth / innerHeight, 0.1, 200);
    const initialPosition = basePosition.clone().multiplyScalar(isMobile ? 1.15 : 0.88);
    camera.position.copy(initialPosition);
    const renderer = new THREE.WebGLRenderer({antialias:true, alpha:false});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(innerWidth, innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    stage.prepend(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xfff8ed, 0x87938b, 2.15));
    const sun = new THREE.DirectionalLight(0xfff5e8, 3.3);
    sun.position.set(-14, 25, 18);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.left = -23;
    sun.shadow.camera.right = 23;
    sun.shadow.camera.top = 19;
    sun.shadow.camera.bottom = -19;
    scene.add(sun);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 1.2, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 20;
    controls.maxDistance = 75;
    controls.minPolarAngle = 0.12;
    controls.maxPolarAngle = Math.PI / 2.02;
    controls.update();
        const clock = new THREE.Clock();
        let mixer = null;
        const walkers = [];

    const encodedModel = '__MODEL_GLB_BASE64__';
    const binary = Uint8Array.from(atob(encodedModel), character => character.charCodeAt(0)).buffer;
    new GLTFLoader().parse(binary, '', gltf => {
            mixer = new THREE.AnimationMixer(gltf.scene);
            gltf.animations.forEach(clip => {
                mixer.clipAction(clip).setLoop(THREE.LoopRepeat, Infinity).play();
            });
      gltf.scene.traverse(object => {
        if (object.isMesh) {
          object.castShadow = true;
          object.receiveShadow = true;
        }
                if (/^Walker_\d+$/.test(object.name)) {
                    walkers.push({
                        leftLeg: object.getObjectByName(`${object.name}_leg_left`),
                        rightLeg: object.getObjectByName(`${object.name}_leg_right`),
                        leftArm: object.getObjectByName(`${object.name}_arm_left`),
                        rightArm: object.getObjectByName(`${object.name}_arm_right`),
                        phase: walkers.length * 1.7
                    });
                }
      });
      scene.add(gltf.scene);
      status.hidden = true;
    }, error => {
      status.textContent = `模型載入失敗：${error.message}`;
    });

    function turn(horizontal, vertical) {
      const offset = camera.position.clone().sub(controls.target);
      const spherical = new THREE.Spherical().setFromVector3(offset);
      spherical.theta -= horizontal;
      spherical.phi = THREE.MathUtils.clamp(spherical.phi + vertical, 0.12, Math.PI / 2.02);
      camera.position.setFromSpherical(spherical).add(controls.target);
      camera.lookAt(controls.target);
      controls.update();
    }
    const step = Math.PI / 18;
    document.querySelectorAll('[data-turn]').forEach(button => button.addEventListener('click', () => {
      const direction = button.dataset.turn;
      turn(direction === 'left' ? step : direction === 'right' ? -step : 0,
           direction === 'up' ? -step : direction === 'down' ? step : 0);
    }));
    document.querySelector('#reset').addEventListener('click', () => {
      camera.position.copy(initialPosition);
      controls.target.set(0, 1.2, 0);
      controls.update();
    });
    addEventListener('keydown', event => {
      if (event.key.startsWith('Arrow')) {
        event.preventDefault();
        if (event.key === 'ArrowLeft') turn(step, 0);
        if (event.key === 'ArrowRight') turn(-step, 0);
        if (event.key === 'ArrowUp') turn(0, -step);
        if (event.key === 'ArrowDown') turn(0, step);
      }
    });
    addEventListener('resize', () => {
            const mobile = innerWidth < 600;
            const modeChanged = mobile !== (camera.fov > 50);
            camera.fov = mobile ? 64 : 42;
            if (modeChanged) {
                const direction = camera.position.clone().sub(controls.target).normalize();
                initialPosition.copy(basePosition).multiplyScalar(mobile ? 1.15 : 0.88);
                camera.position.copy(controls.target).add(direction.multiplyScalar(initialPosition.length()));
                controls.update();
            }
      camera.aspect = innerWidth / innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(innerWidth, innerHeight);
      renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    });
        renderer.setAnimationLoop(() => {
            const delta = clock.getDelta();
            mixer?.update(delta);
            const gait = clock.elapsedTime * 8;
            walkers.forEach(walker => {
                const swing = Math.sin(gait + walker.phase) * 0.32;
                walker.leftLeg.rotation.x = swing;
                walker.rightLeg.rotation.x = -swing;
                walker.leftArm.rotation.x = -swing * 0.65;
                walker.rightArm.rotation.x = swing * 0.65;
            });
      controls.update();
      renderer.render(scene, camera);
    });
  </script>
</body>
</html>
'''


def main():
    build_scene()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT / "ABW16F.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "EMPTY"}:
            obj.select_set(True)
    bpy.context.view_layer.objects.active = next(
        obj for obj in bpy.context.scene.objects if obj.type == "MESH"
    )
    glb_path = OUTPUT / "ABW16F.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path), export_format="GLB", use_selection=True, export_animations=True
    )
    encoded = base64.b64encode(glb_path.read_bytes()).decode("ascii")
    html = HTML.replace("__MODEL_GLB_BASE64__", encoded)
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")
    print(f"Created {OUTPUT / 'ABW16F.blend'}")
    print(f"Created {glb_path} ({glb_path.stat().st_size:,} bytes)")
    print(f"Created {OUTPUT / 'index.html'}")


if __name__ == "__main__":
    main()