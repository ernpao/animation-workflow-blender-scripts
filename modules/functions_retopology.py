# Quad remesher in the spirit of ZBrush's ZRemesher.
#
# Rather than wrapping QuadriFlow (which can hang on dense or non-manifold
# input), this builds the quad mesh itself, following the approach of
# "Instant Field-Aligned Meshes" (Jakob et al., 2015):
#
#   1. Build an evenly sampled, cleaned-up triangle proxy of the mesh.
#   2. Smooth a 4-way orientation field, then a square-lattice position field,
#      over the proxy, coarse to fine on a clustering hierarchy. Smoothing in
#      3D (extrinsically) makes the edge flow follow curvature, and boundaries
#      and sharp edges constrain the fields so edge loops run along them.
#   3. Snap every proxy vertex to its nearest lattice point and read off a
#      quad-dominant mesh from how neighbouring lattice points connect.
#   4. Subdivide once so every face is a quad, mirror if symmetric, then relax
#      the result and project it back onto the original surface.
#
# Every loop is bounded, so the operation finishes in predictable time.

import math
import time

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

# Proxy vertices sampled along each edge of the extracted (pre-subdivision)
# quad mesh. Higher is more robust but slower.
PROXY_SAMPLES_PER_EDGE = 3.0
# Upper bound on the proxy size, which bounds runtime and memory.
MAX_PROXY_VERTICES = 250_000
# Field smoothing iterations per hierarchy level.
SMOOTHING_ITERATIONS = 15
RELAX_ITERATIONS = 6
SHARP_ANGLE = math.radians(40.0)
# Gaps in the extracted mesh bounded by up to this many edges are filled.
MAX_FILL_SIDES = 12
# Edges processed per batch in the lattice searches, to bound memory use.
_CHUNK = 1 << 17
_CELL_CORNERS = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float64)


class _RetopologyError(Exception):
    pass


def retopologize_selected(
    target_face_count=4000,
    use_mesh_symmetry=True,
    preserve_sharp=False,
    seed=0,
    operator=None,
):
    """
    Quad-remeshes the active mesh object into a new object named
    "<name>_Retopo" and hides the original.

    Args:
        target_face_count (int): Approximate number of quads in the result.
        use_mesh_symmetry (bool): Mirror the result across the axes enabled in
            the mesh's own symmetry settings (the X/Y/Z butterfly toggles in
            the Edit/Sculpt mode header).
        preserve_sharp (bool): Make edge loops follow edges sharper than
            SHARP_ANGLE and edges marked sharp.
        seed (int): Seed for the random field initialisation. Change it for a
            different layout.
        operator (bpy.types.Operator): Optional, used to report to the UI.

    Returns:
        set: {"FINISHED"} on success, {"CANCELLED"} otherwise.
    """
    context = bpy.context
    if context.mode != "OBJECT":
        _report(operator, "ERROR", "Switch to Object Mode to retopologize.")
        return {"CANCELLED"}

    source = context.view_layer.objects.active
    if source is None or source.type != "MESH":
        meshes = [o for o in context.selected_objects if o.type == "MESH"]
        if not meshes:
            _report(operator, "ERROR", "Select a mesh object to retopologize.")
            return {"CANCELLED"}
        source = meshes[0]

    print(f"--- Retopologizing '{source.name}' ---")
    print(
        f"Settings: Target Faces={target_face_count}, Symmetry={use_mesh_symmetry}, "
        f"PreserveSharp={preserve_sharp}, Seed={seed}"
    )

    wm = context.window_manager
    wm.progress_begin(0, 100)
    start_time = time.time()
    try:
        result = _retopologize(
            source,
            max(int(target_face_count), 10),
            use_mesh_symmetry,
            preserve_sharp,
            seed,
            operator,
            wm.progress_update,
        )
    except _RetopologyError as e:
        _report(operator, "ERROR", f"Retopology failed: {e}")
        return {"CANCELLED"}
    finally:
        wm.progress_end()

    source.hide_set(True)
    for obj in context.selected_objects:
        obj.select_set(False)
    result.select_set(True)
    context.view_layer.objects.active = result

    _report(
        operator,
        "INFO",
        f"Retopologized '{source.name}' into '{result.name}': "
        f"{len(result.data.polygons)} quads in {time.time() - start_time:.1f}s.",
    )
    return {"FINISHED"}


def _report(operator, level, message):
    print(message)
    if operator is not None:
        operator.report({level}, message)


def _retopologize(
    source, target_faces, use_mesh_symmetry, preserve_sharp, seed, operator, progress
):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    rng = np.random.default_rng(seed)
    timer = time.time()

    def stage(name, percent):
        nonlocal timer
        now = time.time()
        print(f"  {name}: {now - timer:.2f}s")
        timer = now
        progress(percent)

    # ----- MEASURE ----- #
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph))
    try:
        verts, tris = _mesh_arrays(mesh)
    finally:
        bpy.data.meshes.remove(mesh)
    if len(tris) == 0:
        raise _RetopologyError(f"'{source.name}' has no faces.")
    print(f"Original face count: {len(source.data.polygons)}")

    area = _triangle_areas(verts, tris).sum()
    diagonal = np.linalg.norm(verts.max(0) - verts.min(0))
    merge_distance = 1e-5 * diagonal
    symmetry_axes = (
        _symmetry_axes(source.data, verts, merge_distance, operator)
        if use_mesh_symmetry
        else []
    )

    # Quads are extracted at twice the final edge length, then subdivided.
    edge_length = 2.0 * math.sqrt(area / target_faces)
    proxy_area = area / 2 ** len(symmetry_axes)
    proxy_edge = max(
        edge_length / PROXY_SAMPLES_PER_EDGE,
        math.sqrt(1.155 * proxy_area / MAX_PROXY_VERTICES),
    )
    max_proxy_faces = int(2.31 * proxy_area / proxy_edge**2)

    # ----- PROXY ----- #
    verts, tris, marked_sharp = _build_proxy(
        source, depsgraph, proxy_edge, max_proxy_faces, symmetry_axes, merge_distance
    )
    if len(tris) == 0:
        raise _RetopologyError("Nothing left to remesh after cleaning up the mesh.")
    surface, constraints, flags, feature_segments = _proxy_surface(
        verts, tris, preserve_sharp, marked_sharp, symmetry_axes, merge_distance
    )
    print(f"Proxy: {surface.n} vertices")
    stage("Proxy", 15)

    # ----- FIELDS ----- #
    levels, level_constraints = _build_hierarchy(surface, constraints, proxy_edge)
    orientations = _orientation_field(levels, rng, level_constraints)
    stage("Orientation field", 35)
    positions = _position_field(levels, orientations, edge_length, rng, level_constraints)
    stage("Position field", 60)

    # ----- EXTRACT ----- #
    # Per-vertex flags: one column per symmetry seam, then feature, then corner.
    points, faces, flags = _extract_faces(
        surface, orientations[0], positions, edge_length, flags, constraints
    )
    if len(faces) < 2:
        raise _RetopologyError(
            "Could not extract a quad mesh. Try a higher target face count."
        )
    projector = _Projector(
        BVHTree.FromObject(source, depsgraph), *feature_segments, symmetry_axes, proxy_edge
    )
    points = projector.project(points, flags[:, -2], flags[:, -1])
    for k, axis in enumerate(symmetry_axes):
        points[flags[:, k], axis] = 0.0
    stage("Extraction", 75)

    # ----- QUADS ----- #
    coarse_count = len(points)
    verts, quads, flags = _subdivide(points, faces, flags)
    flags[coarse_count:, -1] = False  # midpoints and centres are never corners
    verts, quads, flags, mirror_maps = _mirror(verts, quads, flags, symmetry_axes)
    verts = _relax(verts, quads, projector, flags[:, -2], flags[:, -1], mirror_maps)
    quads = _match_source_winding(verts, quads, projector.bvh)
    stage("Relax", 95)

    sharp_edges = _sharp_edge_keys(verts, quads) if preserve_sharp else None
    return _create_object(source, verts, quads, sharp_edges)


# ----- MESH I/O ----- #


def _mesh_arrays(mesh):
    mesh.calc_loop_triangles()
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)
    tris = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", tris)
    return co.reshape(-1, 3).astype(np.float64), tris.reshape(-1, 3).astype(np.int64)


def _triangle_areas(verts, tris):
    edge1 = verts[tris[:, 1]] - verts[tris[:, 0]]
    edge2 = verts[tris[:, 2]] - verts[tris[:, 0]]
    return 0.5 * np.linalg.norm(np.cross(edge1, edge2), axis=1)


def _symmetry_axes(mesh, verts, tolerance, operator):
    enabled = [
        axis
        for axis, flag in enumerate(
            (mesh.use_mirror_x, mesh.use_mirror_y, mesh.use_mirror_z)
        )
        if flag
    ]
    if not enabled:
        _report(
            operator,
            "INFO",
            "No symmetry axes enabled on the mesh; remeshing without symmetry.",
        )
    axes = []
    for axis in enabled:
        if verts[:, axis].min() < -tolerance and verts[:, axis].max() > tolerance:
            axes.append(axis)
        else:
            _report(
                operator,
                "WARNING",
                f"Mesh doesn't straddle the {'XYZ'[axis]} symmetry plane; ignoring it.",
            )
    return axes


def _build_proxy(source, depsgraph, edge_length, max_faces, symmetry_axes, merge_distance):
    """Returns a clean, evenly sampled triangle version of the evaluated mesh,
    cut down to the positive side of each symmetry plane."""
    mesh = bpy.data.meshes.new_from_object(source.evaluated_get(depsgraph))
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
    finally:
        bpy.data.meshes.remove(mesh)

    try:
        # Weld UV/normal splits so the surface is connected.
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge_distance)
        bmesh.ops.dissolve_degenerate(bm, dist=merge_distance, edges=bm.edges[:])
        _delete_loose(bm)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

        if len(bm.faces) > 1.5 * max_faces:
            _decimate(bm, max_faces / len(bm.faces))

        for axis in symmetry_axes:
            normal = [0.0, 0.0, 0.0]
            normal[axis] = 1.0
            bmesh.ops.bisect_plane(
                bm,
                geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                dist=merge_distance,
                plane_co=(0.0, 0.0, 0.0),
                plane_no=normal,
                clear_inner=True,
            )
            for v in bm.verts:
                if abs(v.co[axis]) <= merge_distance:
                    v.co[axis] = 0.0
        _delete_loose(bm)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

        _split_long_edges(bm, 1.5 * edge_length)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        bm.verts.index_update()
        marked_sharp = np.array(
            [(e.verts[0].index, e.verts[1].index) for e in bm.edges if not e.smooth],
            dtype=np.int64,
        ).reshape(-1, 2)

        mesh = bpy.data.meshes.new("_retopo_proxy")
        bm.to_mesh(mesh)
    finally:
        bm.free()

    try:
        verts, tris = _mesh_arrays(mesh)
    finally:
        bpy.data.meshes.remove(mesh)

    # bmesh element order can vary between runs; sort it so a seed always
    # gives the same result.
    order = np.lexsort(verts.T[::-1])
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    tris = rank[tris]
    tris = np.take_along_axis(tris, (tris.argmin(1)[:, None] + np.arange(3)) % 3, 1)
    tris = tris[np.lexsort(tris.T[::-1])]
    return verts[order], tris, rank[marked_sharp]


def _delete_loose(bm):
    loose_edges = [e for e in bm.edges if not e.link_faces]
    if loose_edges:
        bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")


def _decimate(bm, ratio):
    """Collapse-decimates bm in place using a temporary Decimate modifier."""
    mesh = bpy.data.meshes.new("_retopo_decimate")
    bm.to_mesh(mesh)
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    try:
        modifier = obj.modifiers.new("Decimate", "DECIMATE")
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        depsgraph = bpy.context.evaluated_depsgraph_get()
        result = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
    bm.clear()
    bm.from_mesh(result)
    bpy.data.meshes.remove(result)


def _split_long_edges(bm, max_length, max_passes=12):
    for _ in range(max_passes):
        long_edges = [e for e in bm.edges if e.calc_length() > max_length]
        if not long_edges:
            return
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])


def _create_object(source, verts, quads, sharp_edges=None):
    """sharp_edges: optional edge keys (min * vertex count + max) to mark sharp."""
    mesh = bpy.data.meshes.new(f"{source.data.name}_Retopo")
    mesh.from_pydata(verts.tolist(), [], quads.tolist())
    mesh.validate()
    for material in source.data.materials:
        mesh.materials.append(material)
    if hasattr(mesh, "shade_smooth"):
        mesh.shade_smooth()
    else:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

    if sharp_edges is not None and len(sharp_edges):
        edges = np.empty(len(mesh.edges) * 2, dtype=np.int32)
        mesh.edges.foreach_get("vertices", edges)
        edges = edges.reshape(-1, 2).astype(np.int64)
        keys = edges.min(1) * len(verts) + edges.max(1)
        mesh.edges.foreach_set("use_edge_sharp", np.isin(keys, sharp_edges).tolist())
        if hasattr(mesh, "use_auto_smooth"):  # Blender < 4.1
            mesh.use_auto_smooth = True
            mesh.auto_smooth_angle = math.pi
    mesh.update()

    obj = bpy.data.objects.new(f"{source.name}_Retopo", mesh)
    for collection in source.users_collection or [bpy.context.scene.collection]:
        collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    return obj


# ----- VECTOR HELPERS ----- #


def _dot(a, b):
    return np.einsum("ij,ij->i", a, b)


def _normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=1), 1e-30)[:, None]


def _project_to_tangent(v, normals):
    return v - normals * _dot(v, normals)[:, None]


def _scatter_add(index, values, n):
    """Sums the rows of values into n buckets given by index."""
    return np.stack(
        [np.bincount(index, weights=values[:, c], minlength=n) for c in range(3)],
        axis=1,
    )


def _random_tangents(rng, normals):
    tangents = _project_to_tangent(rng.standard_normal(normals.shape), normals)
    return _normalize(tangents)


def _any_tangent(normals):
    tangents = np.cross(normals, [1.0, 0.0, 0.0])
    weak = np.linalg.norm(tangents, axis=1) < 0.1
    tangents[weak] = np.cross(normals[weak], [0.0, 1.0, 0.0])
    return _normalize(tangents)


# ----- PROXY SURFACE ----- #


class _Level:
    """One level of the field hierarchy: a point graph with normals."""

    def __init__(self, verts, normals, areas, a, b):
        self.V = verts
        self.N = normals
        self.A = areas
        self.a = a  # undirected edges
        self.b = b
        self.n = len(verts)
        self.src = np.concatenate([a, b])
        self.dst = np.concatenate([b, a])
        self.parent = None  # vertex index in the next coarser level
        self.groups = None  # independent vertex sets, see _color_groups


def _color_groups(level, rng):
    """Splits the vertices into independent sets (no two in a set share an
    edge) so each set can be updated in one vectorised Gauss-Seidel step.
    Returns (vertices, outgoing edges, slot of each edge's source vertex)."""
    color = np.full(level.n, -1)
    priority = rng.random(level.n)
    colors = 0
    while (color < 0).any():
        open_vertex = color < 0
        live = open_vertex[level.src] & open_vertex[level.dst]
        best_neighbour = np.full(level.n, -1.0)
        np.maximum.at(best_neighbour, level.src[live], priority[level.dst[live]])
        picked = open_vertex & (priority > best_neighbour)
        color[picked] = colors
        colors += 1

    order = np.argsort(color[level.src], kind="stable")
    edge_groups = np.split(
        order, np.cumsum(np.bincount(color[level.src], minlength=colors))[:-1]
    )
    slot = np.empty(level.n, dtype=np.int64)
    groups = []
    for k in range(colors):
        vertices = np.flatnonzero(color == k)
        slot[vertices] = np.arange(len(vertices))
        edges = edge_groups[k]
        groups.append((vertices, edges, slot[level.src[edges]]))
    return groups


def _proxy_surface(verts, tris, preserve_sharp, marked_sharp, symmetry_axes, tolerance):
    n = len(verts)
    face_normals = np.cross(
        verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]
    )
    double_area = np.linalg.norm(face_normals, axis=1)
    normals = np.zeros((n, 3))
    areas = np.zeros(n)
    for k in range(3):
        normals += _scatter_add(tris[:, k], face_normals, n)
        areas += np.bincount(tris[:, k], weights=double_area / 6.0, minlength=n)
    normals = _normalize(normals)
    face_normals /= np.maximum(double_area, 1e-30)[:, None]

    corner_edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    face_of = np.tile(np.arange(len(tris)), 3)
    keys = corner_edges.min(1) * n + corner_edges.max(1)
    keys, edge_of, face_count = np.unique(keys, return_inverse=True, return_counts=True)
    edge_of = edge_of.reshape(-1)
    a, b = keys // n, keys % n

    # Open boundaries (including symmetry seams) always guide the edge flow.
    boundary = face_count == 1
    feature = boundary.copy()
    if preserve_sharp:
        order = np.argsort(edge_of, kind="stable")
        first = np.cumsum(face_count) - face_count
        f0 = face_of[order[first]]
        f1 = face_of[order[np.minimum(first + 1, len(order) - 1)]]
        cos = _dot(face_normals[f0], face_normals[f1])
        feature |= (face_count == 2) & (cos < math.cos(SHARP_ANGLE))
        if len(marked_sharp):
            marked_keys = marked_sharp.min(1) * n + marked_sharp.max(1)
            feature |= (face_count == 2) & np.isin(keys, marked_keys)

    constraints = _feature_constraints(verts, normals, a[feature], b[feature])

    on_boundary = np.zeros(n, dtype=bool)
    on_boundary[a[boundary]] = True
    on_boundary[b[boundary]] = True
    seams = [on_boundary & (np.abs(verts[:, axis]) <= tolerance) for axis in symmetry_axes]
    flags = np.stack(seams + [constraints.mask, constraints.corner], axis=1)

    feature_segments = (verts[a[feature]], verts[b[feature]])
    surface = _Level(verts, normals, areas, a, b)
    return surface, constraints, flags, feature_segments


class _Constraints:
    """Feature constraints for one hierarchy level. Vertices on a feature line
    get the line's direction and a lattice line through their anchor point;
    corners also get a lattice point on their anchor."""

    def __init__(self, directions, line, corner, anchors):
        self.dir = directions
        self.line = line
        self.corner = corner
        self.mask = line | corner
        self.anchor = anchors
        self._line_index = np.flatnonzero(line)
        self._corner_index = np.flatnonzero(corner)

    def coarsen(self, fine, coarse):
        """Each coarse vertex takes on the constraint of one of its children."""
        directions = np.zeros((coarse.n, 3))
        anchors = np.zeros((coarse.n, 3))
        line = np.zeros(coarse.n, dtype=bool)
        corner = np.zeros(coarse.n, dtype=bool)
        for children, flags in ((self._line_index, line), (self._corner_index, corner)):
            parents = fine.parent[children]
            directions[parents] = self.dir[children]
            anchors[parents] = self.anchor[children]
            flags[parents] = True
        directions = _project_to_tangent(directions, coarse.N)
        valid = np.linalg.norm(directions, axis=1) > 1e-6
        return _Constraints(
            _normalize(directions), line & valid & ~corner, corner & valid, anchors
        )

    def constrain_positions(self, o, normals, h):
        i = self._line_index
        d, anchor = self.dir[i], self.anchor[i]
        across = np.cross(normals[i], d)
        snapped = o[i] - across * _dot(o[i] - anchor, across)[:, None]
        snapped += d * (np.round(_dot(anchor - snapped, d) / h) * h)[:, None]
        o[i] = snapped
        o[self._corner_index] = self.anchor[self._corner_index]


def _feature_constraints(verts, normals, fa, fb):
    """Vertices on feature edges follow the feature's direction. Where feature
    lines meet at an angle, the vertex is a corner."""
    n = len(verts)
    directions = _normalize(verts[fb] - verts[fa])
    count = np.bincount(fa, minlength=n) + np.bincount(fb, minlength=n)

    constraint_dir = np.zeros((n, 3))
    constraint_dir[fa] = directions
    constraint_dir[fb] = directions
    straightness = np.ones(n)
    np.minimum.at(straightness, fa, np.abs(_dot(constraint_dir[fa], directions)))
    np.minimum.at(straightness, fb, np.abs(_dot(constraint_dir[fb], directions)))

    constraint_dir = _project_to_tangent(constraint_dir, normals)
    valid = np.linalg.norm(constraint_dir, axis=1) > 1e-6
    constraint_dir = _normalize(constraint_dir)

    corner = valid & ((count >= 3) | ((count == 2) & (straightness < 0.7)))
    line = valid & (count > 0) & ~corner
    return _Constraints(constraint_dir, line, corner, verts)


def _build_hierarchy(surface, constraints, spacing):
    """Clusters vertices on successively coarser grids. Vertices whose normals
    point different ways (e.g. two sides of a thin wall) stay apart, as do
    constrained and free vertices so features don't blur at coarse levels.
    Returns the levels and their constraints."""
    levels = [surface]
    level_constraints = [constraints]
    cell = 2.0 * spacing
    for _ in range(64):
        fine = levels[-1]
        if fine.n <= 30:
            break
        grid = np.floor((fine.V - fine.V.min(0)) / cell).astype(np.int64)
        dims = grid.max(0) + 1
        axis = np.abs(fine.N).argmax(1)
        positive = fine.N[np.arange(fine.n), axis] > 0
        keys = ((grid[:, 0] * dims[1] + grid[:, 1]) * dims[2] + grid[:, 2]) * 12
        keys += (axis * 2 + positive) * 2 + level_constraints[-1].mask
        _, parent = np.unique(keys, return_inverse=True)
        parent = parent.reshape(-1)
        n = int(parent.max()) + 1
        cell *= 2.0
        if n > 0.8 * fine.n:
            continue

        weights = fine.A + 1e-30
        areas = np.bincount(parent, weights=weights, minlength=n)
        verts = _scatter_add(parent, fine.V * weights[:, None], n) / areas[:, None]
        normals = _normalize(_scatter_add(parent, fine.N * weights[:, None], n))
        pa, pb = parent[fine.a], parent[fine.b]
        keep = pa != pb
        keys = np.unique(np.minimum(pa, pb)[keep] * n + np.maximum(pa, pb)[keep])

        fine.parent = parent
        levels.append(_Level(verts, normals, areas, keys // n, keys % n))
        level_constraints.append(level_constraints[-1].coarsen(fine, levels[-1]))
    return levels, level_constraints


# ----- ORIENTATION FIELD ----- #


def _compat_orientation(qi, qj, nj):
    """Of the four 90-degree rotations of qj about nj, returns the one closest
    to qi."""
    tj = np.cross(nj, qj)
    dq = _dot(qi, qj)
    dt = _dot(qi, tj)
    use_t = np.abs(dt) > np.abs(dq)
    sign = np.where(use_t, np.sign(dt), np.sign(dq))
    sign[sign == 0] = 1.0
    return np.where(use_t[:, None], tj, qj) * sign[:, None]


def _orientation_sweep(level, q, directions, mask):
    for vertices, edges, slot in level.groups:
        s, d = level.src[edges], level.dst[edges]
        matched = _compat_orientation(q[s], q[d], level.N[d])
        total = q[vertices] + _scatter_add(slot, matched, len(vertices))
        total = _project_to_tangent(total, level.N[vertices])
        length = np.linalg.norm(total, axis=1)
        ok = length > 1e-12
        q[vertices[ok]] = total[ok] / length[ok, None]
        q[mask] = directions[mask]


def _orientation_field(levels, rng, constraints):
    fields = [None] * len(levels)
    q = _random_tangents(rng, levels[-1].N)
    for i in reversed(range(len(levels))):
        level = levels[i]
        if i < len(levels) - 1:
            q = _project_to_tangent(fields[i + 1][level.parent], level.N)
            weak = np.linalg.norm(q, axis=1) < 1e-6
            q[weak] = _random_tangents(rng, level.N[weak])
            q = _normalize(q)
        if level.groups is None:
            level.groups = _color_groups(level, rng)
        directions, mask = constraints[i].dir, constraints[i].mask
        q[mask] = directions[mask]
        for _ in range(SMOOTHING_ITERATIONS):
            _orientation_sweep(level, q, directions, mask)
        fields[i] = q
    return fields


# ----- POSITION FIELD ----- #


def _middle_point(p0, n0, p1, n1):
    """Point closest to both p0 and p1 that lies on both tangent planes."""
    n0p0, n0p1 = _dot(n0, p0), _dot(n0, p1)
    n1p0, n1p1 = _dot(n1, p0), _dot(n1, p1)
    n0n1 = _dot(n0, n1)
    denom = 1.0 / (1.0 - n0n1 * n0n1 + 1e-4)
    lambda0 = 2.0 * (n0p1 - n0p0 - n0n1 * (n1p0 - n1p1)) * denom
    lambda1 = 2.0 * (n1p0 - n1p1 - n0n1 * (n0p1 - n0p0)) * denom
    return 0.5 * (p0 + p1) - 0.25 * (n0 * lambda0[:, None] + n1 * lambda1[:, None])


def _closest_lattice_points(o0, q0, t0, o1, q1, t1, target, h):
    """Of the corners of the two lattice cells containing target, finds the
    closest pair (one corner from each lattice). Returns their integer lattice
    coordinates and their positions."""

    def cell_corners(o, q, t):
        d = target - o
        cell = np.floor(np.stack([_dot(d, q), _dot(d, t)], axis=1) / h)
        coords = cell[:, None, :] + _CELL_CORNERS
        points = o[:, None, :] + h * (
            coords[..., :1] * q[:, None, :] + coords[..., 1:] * t[:, None, :]
        )
        return coords, points

    c0, p0 = cell_corners(o0, q0, t0)
    c1, p1 = cell_corners(o1, q1, t1)
    distance = ((p0[:, :, None, :] - p1[:, None, :, :]) ** 2).sum(-1)
    best = distance.reshape(len(target), 16).argmin(1)
    rows = np.arange(len(target))
    i0, i1 = best // 4, best % 4
    return c0[rows, i0], c1[rows, i1], p0[rows, i0], p1[rows, i1]


def _round_to_lattice(o, q, normals, verts, h):
    """Moves each lattice origin to the lattice point closest to its vertex."""
    t = np.cross(normals, q)
    d = verts - o
    return o + h * (
        np.round(_dot(d, q) / h)[:, None] * q + np.round(_dot(d, t) / h)[:, None] * t
    )


def _lattice_shift(level, q, o, s, d, h):
    """For each edge s->d, how far s's lattice must move to line up with d's."""
    shift = np.empty((len(s), 3))
    for c in range(0, len(s), _CHUNK):
        ia, ib = s[c : c + _CHUNK], d[c : c + _CHUNK]
        n0, n1 = level.N[ia], level.N[ib]
        q0, q1 = q[ia], q[ib]
        middle = _middle_point(level.V[ia], n0, level.V[ib], n1)
        _, _, p0, p1 = _closest_lattice_points(
            o[ia], q0, np.cross(n0, q0), o[ib], q1, np.cross(n1, q1), middle, h
        )
        shift[c : c + _CHUNK] = p1 - p0
    return shift


def _position_sweep(level, q, o, h, constraints):
    for vertices, edges, slot in level.groups:
        shift = _lattice_shift(level, q, o, level.src[edges], level.dst[edges], h)
        count = np.maximum(np.bincount(slot, minlength=len(vertices)), 1)
        moved = o[vertices] + _scatter_add(slot, shift, len(vertices)) / count[:, None]
        verts, normals = level.V[vertices], level.N[vertices]
        moved = verts + _project_to_tangent(moved - verts, normals)
        o[vertices] = _round_to_lattice(moved, q[vertices], normals, verts, h)
        constraints.constrain_positions(o, level.N, h)


def _position_field(levels, orientations, h, rng, constraints):
    top, q = levels[-1], orientations[-1]
    offset = rng.uniform(-0.5, 0.5, (top.n, 2)) * h
    o = top.V + q * offset[:, :1] + np.cross(top.N, q) * offset[:, 1:]
    for i in reversed(range(len(levels))):
        level, q = levels[i], orientations[i]
        if i < len(levels) - 1:
            o = o[level.parent]
            o = level.V + _project_to_tangent(o - level.V, level.N)
        o = _round_to_lattice(o, q, level.N, level.V, h)
        for _ in range(SMOOTHING_ITERATIONS):
            _position_sweep(level, q, o, h, constraints[i])
    return o


# ----- EXTRACTION ----- #


def _connected_components(n, a, b):
    labels = np.arange(n)
    while True:
        la, lb = labels[a], labels[b]
        differ = la != lb
        if not differ.any():
            return labels
        np.minimum.at(
            labels,
            np.maximum(la[differ], lb[differ]),
            np.minimum(la[differ], lb[differ]),
        )
        while True:
            jumped = labels[labels]
            if np.array_equal(jumped, labels):
                break
            labels = jumped


def _extract_faces(level, q, o, h, flags, constraints):
    """Merges proxy vertices that snapped to the same lattice point, connects
    lattice neighbours, and traces the faces of the resulting graph. A merged
    point gets each flag that any of its proxy vertices has."""
    offset = np.empty((len(level.a), 2), dtype=np.int64)
    for s in range(0, len(level.a), _CHUNK):
        ia, ib = level.a[s : s + _CHUNK], level.b[s : s + _CHUNK]
        n0, n1 = level.N[ia], level.N[ib]
        q0 = q[ia]
        q1 = _compat_orientation(q0, q[ib], n1)
        middle = _middle_point(level.V[ia], n0, level.V[ib], n1)
        c0, c1, _, _ = _closest_lattice_points(
            o[ia], q0, np.cross(n0, q0), o[ib], q1, np.cross(n1, q1), middle, h
        )
        offset[s : s + _CHUNK] = c0 - c1
    steps = np.abs(offset).sum(1)

    same = steps == 0
    labels = _connected_components(level.n, level.a[same], level.b[same])
    _, cluster = np.unique(labels, return_inverse=True)
    cluster = cluster.reshape(-1)
    n = int(cluster.max()) + 1
    count = np.bincount(cluster, minlength=n)
    points = _scatter_add(cluster, o, n) / count[:, None]
    normals = _normalize(_scatter_add(cluster, level.N * level.A[:, None], n))
    point_flags = np.zeros((n, flags.shape[1]), dtype=bool)
    for k in range(flags.shape[1]):
        point_flags[cluster[flags[:, k]], k] = True
    corners = constraints.corner
    points[cluster[corners]] = constraints.anchor[corners]

    adjacent = steps == 1
    ea, eb = cluster[level.a[adjacent]], cluster[level.b[adjacent]]
    keep = ea != eb
    keys = np.unique(np.minimum(ea, eb)[keep] * n + np.maximum(ea, eb)[keep])
    ea, eb = _prune_dangling(n, keys // n, keys % n)

    faces = _trace_faces(points, normals, ea, eb, h)
    faces = _dissolve_two_face_vertices(points, faces, keep=point_flags[:, -1])
    if not faces:
        return points[:0], faces, point_flags[:0]

    used, remap = np.unique(np.concatenate(faces), return_inverse=True)
    sizes = [len(f) for f in faces]
    remap = np.split(remap.reshape(-1), np.cumsum(sizes)[:-1])
    return points[used], [r.tolist() for r in remap], point_flags[used]


def _prune_dangling(n, ea, eb):
    while True:
        degree = np.bincount(ea, minlength=n) + np.bincount(eb, minlength=n)
        keep = (degree[ea] >= 2) & (degree[eb] >= 2)
        if keep.all():
            return ea, eb
        ea, eb = ea[keep], eb[keep]


def _trace_faces(points, normals, ea, eb, h):
    """Walks the faces of the graph, embedded on the surface by sorting each
    vertex's edges by angle around its normal. h is the lattice spacing."""
    n = len(points)
    u = np.concatenate([ea, eb])
    v = np.concatenate([eb, ea])
    ref = _any_tangent(normals)
    ref2 = np.cross(normals, ref)
    d = points[v] - points[u]
    angle = np.arctan2(_dot(d, ref2[u]), _dot(d, ref[u]))
    order = np.lexsort((angle, u))
    u, v = u[order], v[order]

    degree = np.bincount(u, minlength=n)
    start = np.cumsum(degree) - degree
    position = np.arange(len(u)) - start[u]
    keys = u * n + v
    by_key = np.argsort(keys)
    reverse = by_key[np.searchsorted(keys[by_key], v * n + u)]
    # The face to the left of u->v continues along the edge from v that comes
    # just before v->u in counter-clockwise order.
    following = (start[v] + (position[reverse] - 1) % degree[v]).tolist()

    u_list = u.tolist()
    visited = [False] * len(u_list)
    faces = []
    for first in range(len(u_list)):
        if visited[first]:
            continue
        loop = []
        e = first
        while not visited[e]:
            visited[e] = True
            loop.append(u_list[e])
            e = following[e]
        for simple in _split_pinched_loop(loop):
            if not 3 <= len(simple) <= MAX_FILL_SIDES:
                continue
            # Loops wound against the surface normal are open boundaries. Ones
            # with next to no area are folded faces, which relaxing untangles.
            corners = points[simple]
            newell = np.cross(corners, np.roll(corners, -1, axis=0)).sum(0)
            normal = normals[simple].sum(0)
            signed_area = 0.5 * newell @ normal / max(np.linalg.norm(normal), 1e-30)
            if signed_area > -0.25 * h * h:
                faces.append(simple)
    return faces


def _dissolve_two_face_vertices(points, faces, keep):
    """Removes interior vertices that only two faces share, by merging those
    faces. Two quads merged this way are re-split along their shortest
    diagonal. Vertices flagged in keep are left alone."""
    for _ in range(8):
        incident = {}
        for f, face in enumerate(faces):
            for v in face:
                incident.setdefault(v, []).append(f)
        merged = set()
        result = []
        for v, (f1, f2) in ((v, fs) for v, fs in incident.items() if len(fs) == 2):
            if keep[v] or f1 in merged or f2 in merged:
                continue
            first, second = faces[f1], faces[f2]
            i, j = first.index(v), second.index(v)
            a, b = first[i - 1], first[(i + 1) % len(first)]
            # Interior only if both faces wrap around v through a and b.
            if second[j - 1] != b or second[(j + 1) % len(second)] != a:
                continue
            path1 = first[i + 1 :] + first[:i]  # b ... a
            path2 = second[j + 1 :] + second[:j]  # a ... b
            polygon = path1 + path2[1:-1]
            if len(set(polygon)) != len(polygon) or len(polygon) < 3:
                continue
            merged.update((f1, f2))
            if len(polygon) == 6:
                p = points[polygon]
                k = int(np.argmin([np.linalg.norm(p[k] - p[k + 3]) for k in range(3)]))
                polygon = polygon[k:] + polygon[:k]
                result += [polygon[:4], polygon[3:] + polygon[:1]]
            else:
                result.append(polygon)
        if not merged:
            return faces
        faces = [f for k, f in enumerate(faces) if k not in merged] + result
    return faces


def _split_pinched_loop(loop):
    """Splits a loop that passes through the same vertex more than once into
    loops that don't."""
    loops = []
    path = []
    position = {}
    for v in loop:
        if v in position:
            start = position[v]
            loops.append(path[start:])
            for w in path[start + 1 :]:
                del position[w]
            del path[start + 1 :]
        else:
            position[v] = len(path)
            path.append(v)
    loops.append(path)
    return loops


# ----- QUAD MESH ----- #


def _subdivide(points, faces, flags):
    """Splits every n-sided face into n quads. Edge midpoints keep the flags
    both ends share; face centres get none."""
    n = len(points)
    sizes = np.array([len(f) for f in faces])
    corners = np.concatenate([np.asarray(f) for f in faces])
    face_of = np.repeat(np.arange(len(faces)), sizes)
    first = (np.cumsum(sizes) - sizes)[face_of]
    local = np.arange(len(corners)) - first
    following = corners[first + (local + 1) % sizes[face_of]]
    previous = first + (local - 1) % sizes[face_of]

    keys, edge_of = np.unique(
        np.minimum(corners, following) * n + np.maximum(corners, following),
        return_inverse=True,
    )
    edge_of = edge_of.reshape(-1)
    ea, eb = keys // n, keys % n
    midpoints = 0.5 * (points[ea] + points[eb])
    centers = _scatter_add(face_of, points[corners], len(faces)) / sizes[:, None]

    verts = np.concatenate([points, midpoints, centers])
    midpoint = n + edge_of
    center = n + len(keys) + face_of
    quads = np.stack([corners, midpoint, center, midpoint[previous]], axis=1)
    flags = np.concatenate(
        [flags, flags[ea] & flags[eb], np.zeros((len(faces), flags.shape[1]), bool)]
    )
    return verts, quads, flags


def _mirror(verts, quads, flags, symmetry_axes):
    """Mirrors the half mesh across each symmetry plane, sharing the vertices
    on the seam (flag column k for the k-th axis). Also returns, per axis, the
    index of each vertex's mirror image."""
    mirror_maps = []
    for k, axis in enumerate(symmetry_axes):
        n = len(verts)
        copies = np.flatnonzero(~flags[:, k])
        mirror = np.arange(n)
        mirror[copies] = n + np.arange(len(copies))
        mirror_maps = [
            (other, np.concatenate([m, mirror[m[copies]]])) for other, m in mirror_maps
        ]
        reflected = verts[copies].copy()
        reflected[:, axis] *= -1.0
        verts = np.concatenate([verts, reflected])
        flags = np.concatenate([flags, flags[copies]])
        quads = np.concatenate([quads, mirror[quads][:, ::-1]])
        mirror_maps.append((axis, np.concatenate([mirror, copies])))
    return verts, quads, flags, mirror_maps


class _Projector:
    """Projects points onto the source surface, or onto its feature lines
    (sharp edges, open boundaries and symmetry seams)."""

    def __init__(self, bvh, segment_a, segment_b, symmetry_axes, spacing):
        self.bvh = bvh
        # Mirrored vertices need the mirrored features to snap to.
        for axis in symmetry_axes:
            flip = np.ones(3)
            flip[axis] = -1.0
            segment_a = np.concatenate([segment_a, segment_a * flip])
            segment_b = np.concatenate([segment_b, segment_b * flip])
        self.segment_a = segment_a
        self.segment_b = segment_b

        # Index the segments by points sampled along them.
        lengths = np.linalg.norm(segment_b - segment_a, axis=1)
        steps = np.maximum(np.ceil(lengths / (0.5 * spacing)), 1).astype(np.int64)
        self.segment_of = np.repeat(np.arange(len(segment_a)), steps)
        t = np.arange(steps.sum()) - np.repeat(np.cumsum(steps) - steps, steps)
        t = (t + 0.5) / steps[self.segment_of]
        samples = segment_a[self.segment_of] + t[:, None] * (
            segment_b - segment_a
        )[self.segment_of]
        self.tree = KDTree(len(samples))
        for i, co in enumerate(samples.tolist()):
            self.tree.insert(co, i)
        self.tree.balance()

    def project(self, verts, on_feature, fixed):
        projected = verts.copy()
        for i in np.flatnonzero(~on_feature & ~fixed).tolist():
            location = self.bvh.find_nearest(verts[i].tolist())[0]
            if location is not None:
                projected[i] = location
        for i in np.flatnonzero(on_feature & ~fixed).tolist():
            projected[i] = self._nearest_on_features(verts[i])
        return projected

    def _nearest_on_features(self, point):
        best, best_distance = point, math.inf
        for _, index, _ in self.tree.find_n(point.tolist(), 4):
            s = self.segment_of[index]
            a, ab = self.segment_a[s], self.segment_b[s] - self.segment_a[s]
            t = min(max(np.dot(point - a, ab) / max(np.dot(ab, ab), 1e-30), 0.0), 1.0)
            candidate = a + t * ab
            distance = np.dot(point - candidate, point - candidate)
            if distance < best_distance:
                best, best_distance = candidate, distance
        return best


def _quad_vertex_normals(verts, quads):
    face_normals = np.cross(
        verts[quads[:, 2]] - verts[quads[:, 0]], verts[quads[:, 3]] - verts[quads[:, 1]]
    )
    normals = np.zeros_like(verts)
    for k in range(4):
        normals += _scatter_add(quads[:, k], face_normals, len(verts))
    return _normalize(normals)


def _symmetrize(verts, mirror_maps):
    for axis, mirror in mirror_maps:
        reflected = verts[mirror]
        reflected[:, axis] *= -1.0
        verts = 0.5 * (verts + reflected)
    return verts


def _relax(verts, quads, projector, feature, corner, mirror_maps):
    """Evens out the quads with tangential smoothing while keeping them on the
    source surface. Vertices on features and open boundaries only slide along
    them, and corners stay put."""
    n = len(verts)
    corner_edges = quads[:, [0, 1, 1, 2, 2, 3, 3, 0]].reshape(-1, 2)
    keys, face_count = np.unique(
        corner_edges.min(1) * n + corner_edges.max(1), return_counts=True
    )
    ea, eb = keys // n, keys % n
    boundary_edge = face_count == 1
    guided = feature.copy()
    guided[ea[boundary_edge]] = True
    guided[eb[boundary_edge]] = True
    along = boundary_edge | (feature[ea] & feature[eb])

    to_a = along | ~guided[ea]
    to_b = along | ~guided[eb]
    src = np.concatenate([ea[to_a], eb[to_b]])
    dst = np.concatenate([eb[to_a], ea[to_b]])
    count = np.bincount(src, minlength=n)
    moving = (count > 0) & ~corner
    interior = moving & ~guided

    verts = _symmetrize(projector.project(verts, feature, corner), mirror_maps)
    for _ in range(RELAX_ITERATIONS):
        average = _scatter_add(src, verts[dst], n)[moving] / count[moving, None]
        delta = np.zeros_like(verts)
        delta[moving] = average - verts[moving]
        normals = _quad_vertex_normals(verts, quads)
        delta[interior] = _project_to_tangent(delta[interior], normals[interior])
        verts = verts + 0.5 * delta
        verts = _symmetrize(projector.project(verts, feature, corner), mirror_maps)
    return verts


def _sharp_edge_keys(verts, quads):
    """Keys (min * vertex count + max) of edges whose faces meet at more than
    SHARP_ANGLE."""
    n = len(verts)
    normals = _normalize(
        np.cross(
            verts[quads[:, 2]] - verts[quads[:, 0]],
            verts[quads[:, 3]] - verts[quads[:, 1]],
        )
    )
    corner_edges = quads[:, [0, 1, 1, 2, 2, 3, 3, 0]].reshape(-1, 2)
    keys = corner_edges.min(1) * n + corner_edges.max(1)
    face_of = np.repeat(np.arange(len(quads)), 4)
    order = np.argsort(keys, kind="stable")
    keys, face_of = keys[order], face_of[order]
    shared = keys[1:] == keys[:-1]
    cos = _dot(normals[face_of[:-1][shared]], normals[face_of[1:][shared]])
    return keys[:-1][shared][cos < math.cos(SHARP_ANGLE)]


def _match_source_winding(verts, quads, bvh, samples=2000):
    """Flips the result if its faces point the opposite way to the source's."""
    picked = quads[:: max(1, len(quads) // samples)]
    centers = verts[picked].mean(1)
    normals = np.cross(
        verts[picked[:, 2]] - verts[picked[:, 0]],
        verts[picked[:, 3]] - verts[picked[:, 1]],
    )
    agreement = 0.0
    for center, normal in zip(centers.tolist(), normals):
        source_normal = bvh.find_nearest(center)[1]
        if source_normal is not None:
            agreement += float(np.dot(normal, source_normal))
    return quads[:, ::-1] if agreement < 0 else quads
