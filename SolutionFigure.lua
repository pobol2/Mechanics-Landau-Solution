-- SPDX-License-Identifier: MIT
-- Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
--
-- Numerical fields for the figures of the Solution Manual (used by SolutionFigure.cls).
--
-- A field is the sum of attractive sources of three kinds, all given in the
-- co-ordinates (a,b) of the drawn cross-section:
--   * 2D sources: infinite lines perpendicular to the cross-section,
--     potential m*ln(r) (used for bodies infinite in one direction);
--   * 3D sources: points, potential -m/r; the cross-section is the plane y = 0
--     (a,b) -> (x,y,z) = (a,0,b) by default, or a plane z = c with
--     (a,b) -> (a,b,c) (SF.sectionz), and the field drawn is its component in
--     the cross-section;
--   * a uniform field towards the line b = 0 (infinite plane), potential m*|b|.
-- Field lines are traced from seed points along the field, until they reach a
-- solid (the section of the body) or leave the drawn region. Equipotentials are
-- contours of the potential, found on a grid with the marching squares method.

SF = {}

local sqrt, log, abs, floor = math.sqrt, math.log, math.abs, math.floor

local function fmt(x) return string.format("%.3f", x) end

-- ============ Field ============ --

function SF.reset()
    SF.src2, SF.src3, SF.uniform = {}, {}, 0
    SF.solids, SF.solids3 = {}, {} -- functions of (a,b) and of (x,y,z)
    SF.grid = nil
    SF.box = { -3, 3, -2, 2 }
    SF.zsection = nil -- nil: plane y = 0, otherwise c for the plane z = c
end

-- Cross-section z = c for the 3D sources (instead of y = 0)
function SF.sectionz(c)
    SF.zsection = c
    SF.grid = nil
end

local function to3d(a, b)
    if SF.zsection then return a, b, SF.zsection end
    return a, 0, b
end

-- Drawn region (the field is only computed there)
function SF.bounds(a1, a2, b1, b2)
    SF.box = { a1, a2, b1, b2 }
    SF.grid = nil
end

function SF.potential(a, b)
    local u = SF.uniform * abs(b)
    for _, p in ipairs(SF.src2) do
        local da, db = a - p[1], b - p[2]
        u = u + p[3] * 0.5 * log(da * da + db * db + 1e-9)
    end
    local x, y, z = to3d(a, b)
    for _, p in ipairs(SF.src3) do
        local dx, dy, dz = x - p[1], y - p[2], z - p[3]
        u = u - p[4] / sqrt(dx * dx + dy * dy + dz * dz + 1e-9)
    end
    return u
end

-- Field E = -grad(U), projected on the cross-section
function SF.field(a, b)
    local ea, eb = 0, 0
    if b > 0 then eb = -SF.uniform elseif b < 0 then eb = SF.uniform end
    for _, p in ipairs(SF.src2) do
        local da, db = a - p[1], b - p[2]
        local r2 = da * da + db * db + 1e-9
        ea, eb = ea - p[3] * da / r2, eb - p[3] * db / r2
    end
    local x, y, z = to3d(a, b)
    for _, p in ipairs(SF.src3) do
        local dx, dy, dz = x - p[1], y - p[2], z - p[3]
        local r2 = dx * dx + dy * dy + dz * dz + 1e-9
        local r3 = r2 * sqrt(r2)
        -- component in the cross-section: (x,z) for y = 0, (x,y) for z = c
        ea = ea - p[4] * dx / r3
        if SF.zsection then eb = eb - p[4] * dy / r3 else eb = eb - p[4] * dz / r3 end
    end
    return ea, eb
end

local function inside_solid(a, b)
    for _, f in ipairs(SF.solids) do
        if f(a, b) then return true end
    end
    local x, y, z = to3d(a, b)
    for _, f in ipairs(SF.solids3) do
        if f(x, y, z) then return true end
    end
    return false
end

local function inside_box(a, b, margin)
    local m = margin or 0
    return a >= SF.box[1] - m and a <= SF.box[2] + m and b >= SF.box[3] - m and b <= SF.box[4] + m
end

-- ============ Sources (each also defines its solid section) ============ --

-- Uniform infinite plane b = 0 (seen edge on)
function SF.plane(thickness)
    SF.uniform = 1
    local t = (thickness or 0.08) / 2
    table.insert(SF.solids, function(a, b) return abs(b) <= t end)
end

-- Point mass at (x0,y0,z0) (3D), with a small ball as solid
function SF.point(x0, y0, z0, m, r)
    table.insert(SF.src3, { x0, y0, z0, m or 1 })
    local rr = r or 0.12
    table.insert(SF.solids3, function(x, y, z) return (x - x0) ^ 2 + (y - y0) ^ 2 + (z - z0) ^ 2 <= rr * rr end)
end

-- Disc of radius R centred at (a,b) in the cross-section of an infinite
-- cylinder (2D): its field outside is the one of a line at its centre
function SF.disc2(ca, cb, R)
    table.insert(SF.src2, { ca, cb, 1 })
    table.insert(SF.solids, function(a, b) return (a - ca) ^ 2 + (b - cb) ^ 2 <= R * R end)
end

-- Uniform polygon in the cross-section of an infinite prism (2D), sampled on
-- a grid of step h. pts = { {a1,b1}, {a2,b2}, ... }
local function in_polygon(pts, a, b)
    local c, n = false, #pts
    local j = n
    for i = 1, n do
        local ai, bi, aj, bj = pts[i][1], pts[i][2], pts[j][1], pts[j][2]
        if ((bi > b) ~= (bj > b)) and (a < (aj - ai) * (b - bi) / (bj - bi) + ai) then c = not c end
        j = i
    end
    return c
end

function SF.polygon2(pts, h)
    h = h or 0.05
    local a1, a2, b1, b2 = math.huge, -math.huge, math.huge, -math.huge
    for _, p in ipairs(pts) do
        a1, a2 = math.min(a1, p[1]), math.max(a2, p[1])
        b1, b2 = math.min(b1, p[2]), math.max(b2, p[2])
    end
    for a = a1 + h / 2, a2, h do
        for b = b1 + h / 2, b2, h do
            if in_polygon(pts, a, b) then table.insert(SF.src2, { a, b, h * h }) end
        end
    end
    table.insert(SF.solids, function(a, b) return in_polygon(pts, a, b) end)
end

-- Same, with the vertices given as "a1/b1, a2/b2, ..."
function SF.polygon(str, h)
    local pts = {}
    for a, b in string.gmatch(str, "([%-%d%.]+)%s*/%s*([%-%d%.]+)") do
        table.insert(pts, { tonumber(a), tonumber(b) })
    end
    SF.polygon2(pts, h)
end

-- Uniform half-plane b = 0, a < 0, seen edge on (2D), sampled from -L to 0.
-- The pull along the half-plane grows like ln(L), so the half-plane of an
-- infinite length is replaced by one a little longer than the drawn region.
function SF.halfplane(L, thickness)
    L = L or 4.5
    local n = 2000
    for i = 1, n do
        table.insert(SF.src2, { -L * (i - 0.5) / n, 0, L / n })
    end
    local t = (thickness or 0.08) / 2
    table.insert(SF.solids, function(a, b) return a <= 0 and abs(b) <= t end)
end

-- Solid cone of base radius R (base at z = 0) and height H, axis z (3D),
-- sampled by rings of points
function SF.cone(R, H, n)
    n = n or 10
    for i = 1, n do
        local z = H * (i - 0.5) / n
        local rmax = R * (1 - z / H)
        local nr = math.max(1, floor(n * rmax / R + 0.5))
        for j = 1, nr do
            local r = rmax * (j - 0.5) / nr
            local k = math.max(6, floor(24 * r / R))
            for l = 1, k do
                local t = 2 * math.pi * (l - 0.5) / k
                table.insert(SF.src3, { r * math.cos(t), r * math.sin(t), z, r / k })
            end
        end
    end
    table.insert(SF.solids3, function(x, y, z) return z >= 0 and z <= H and sqrt(x * x + y * y) <= R * (1 - z / H) end)
end

-- Torus of radius R (axis z, centre at the origin) and tube radius r (3D),
-- sampled by points on circles of the tube
function SF.torus(R, r, n)
    n = n or 72
    for _, q in ipairs({ { 0, 0 }, { 0.5, 0 }, { -0.5, 0 }, { 0, 0.5 }, { 0, -0.5 } }) do
        local rho, z = R + q[1] * r, q[2] * r
        for l = 1, n do
            local t = 2 * math.pi * (l - 0.5) / n
            table.insert(SF.src3, { rho * math.cos(t), rho * math.sin(t), z, rho / n })
        end
    end
    table.insert(SF.solids3, function(x, y, z) return (sqrt(x * x + y * y) - R) ^ 2 + z * z <= r * r end)
end

-- Helix of radius R and pitch h, axis z (3D), turns above and below z = 0,
-- sampled by points; the solid is a wire of radius r around it
function SF.helix(R, h, turns, r)
    turns = turns or 8
    local n = 48
    for i = -turns * n, turns * n do
        local t = 2 * math.pi * i / n
        table.insert(SF.src3, { R * math.cos(t), R * math.sin(t), h * i / n, 1 / n })
    end
    local rr = r or 0.1
    table.insert(SF.solids3, function(x, y, z)
        -- nearest turn: the angle of the point, plus the whole turns that bring
        -- the helix closest to its height
        local phi = math.atan(y, x)
        local k = floor((2 * math.pi * z / h - phi) / (2 * math.pi) + 0.5)
        local t = phi + 2 * math.pi * k
        local dx, dy, dz = x - R * math.cos(t), y - R * math.sin(t), z - h * t / (2 * math.pi)
        return dx * dx + dy * dy + dz * dz <= rr * rr
    end)
end

-- ============ Field lines ============ --

local function direction(a, b)
    local ea, eb = SF.field(a, b)
    local n = sqrt(ea * ea + eb * eb)
    if n < 1e-12 then return 0, 0, 0 end
    return ea / n, eb / n, n
end

-- Field line from (a,b), along the field, as a TikZ path
local function trace(a, b, style)
    local h, maxsteps = 0.01, 3000
    local pts = { { a, b } }
    local last = { a, b }
    local entered = inside_box(a, b, 0.05) -- seeds may be outside the drawn region
    for _ = 1, maxsteps do
        local da, db, n = direction(a, b)
        if n == 0 then break end
        local ma, mb = direction(a + h / 2 * da, b + h / 2 * db)
        a, b = a + h * ma, b + h * mb
        if (a - last[1]) ^ 2 + (b - last[2]) ^ 2 >= 0.04 ^ 2 then
            table.insert(pts, { a, b }); last = { a, b }
        end
        if inside_solid(a, b) then break end
        if inside_box(a, b, 0.05) then
            -- keep only the part in the drawn region (for the arrow in its middle)
            if not entered then pts = { { a, b } }; last = { a, b }; entered = true end
        elseif entered then break end
    end
    if last[1] ~= a or last[2] ~= b then table.insert(pts, { a, b }) end
    if #pts < 3 then return end
    local s = {}
    for i, p in ipairs(pts) do s[i] = "(" .. fmt(p[1]) .. "," .. fmt(p[2]) .. ")" end
    tex.sprint("\\draw[" .. style .. "] " .. table.concat(s, " -- ") .. ";")
end

-- Seeds given as "a1/b1, a2/b2, ..."
function SF.lines(seeds, style)
    for a, b in string.gmatch(seeds, "([%-%d%.]+)%s*/%s*([%-%d%.]+)") do
        trace(tonumber(a), tonumber(b), style or "field line")
    end
end

-- n seeds evenly spaced on a circle of centre (ca,cb) and radius r
function SF.linescircle(ca, cb, r, n, phase, style)
    for i = 0, n - 1 do
        local t = math.rad(phase or 0) + 2 * math.pi * i / n
        trace(ca + r * math.cos(t), cb + r * math.sin(t), style or "field line")
    end
end

-- n seeds evenly spaced on the segment from (a1,b1) to (a2,b2)
function SF.linessegment(a1, b1, a2, b2, n, style)
    for i = 1, n do
        local t = (i - 0.5) / n
        trace(a1 + t * (a2 - a1), b1 + t * (b2 - b1), style or "field line")
    end
end

-- ============ Equipotentials ============ --

local NX, NY = 240, 180

local function make_grid()
    local a1, a2, b1, b2 = SF.box[1], SF.box[2], SF.box[3], SF.box[4]
    local g = { a1 = a1, b1 = b1, da = (a2 - a1) / NX, db = (b2 - b1) / NY }
    for i = 0, NX do
        g[i] = {}
        for j = 0, NY do g[i][j] = SF.potential(a1 + i * g.da, b1 + j * g.db) end
    end
    SF.grid = g
end

-- Contour of the potential at the level it has at (a,b)
local function contour(a, b, style)
    if not SF.grid then make_grid() end
    local g, level = SF.grid, SF.potential(a, b)
    -- Points on the edges of the grid where the potential crosses the level,
    -- keyed by edge: "h,i,j" from (i,j) to (i+1,j) and "v,i,j" from (i,j) to (i,j+1)
    local function point(key)
        local kind, i, j = key:match("(%a),(%d+),(%d+)")
        i, j = tonumber(i), tonumber(j)
        local i2, j2 = i, j
        if kind == "h" then i2 = i + 1 else j2 = j + 1 end
        local f1, f2 = g[i][j] - level, g[i2][j2] - level
        local t = f1 / (f1 - f2)
        return g.a1 + (i + t * (i2 - i)) * g.da, g.b1 + (j + t * (j2 - j)) * g.db
    end
    local adj = {}
    local function link(k1, k2)
        adj[k1] = adj[k1] or {}; adj[k2] = adj[k2] or {}
        table.insert(adj[k1], k2); table.insert(adj[k2], k1)
    end
    for i = 0, NX - 1 do
        for j = 0, NY - 1 do
            local c = {}
            local v = { g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1] }
            local e = { "h," .. i .. "," .. j, "v," .. (i + 1) .. "," .. j, "h," .. i .. "," .. (j + 1), "v," .. i .. "," .. j }
            for k = 1, 4 do
                local f1, f2 = v[k] - level, v[k % 4 + 1] - level
                if (f1 < 0) ~= (f2 < 0) then table.insert(c, e[k]) end
            end
            if #c == 2 then
                link(c[1], c[2])
            elseif #c == 4 then
                -- saddle: decide with the value at the centre of the cell
                local centre = (v[1] + v[2] + v[3] + v[4]) / 4 - level
                if (centre < 0) == (v[1] - level < 0) then
                    link(c[1], c[2]); link(c[3], c[4])
                else
                    link(c[1], c[4]); link(c[2], c[3])
                end
            end
        end
    end
    -- Join the segments into polylines
    local used = {}
    local function walk(start)
        local chain, prev, cur = { start }, nil, start
        used[start] = true
        while true do
            local nxt = nil
            for _, k in ipairs(adj[cur]) do
                if k ~= prev and not used[k] then nxt = k; break end
            end
            if not nxt then
                for _, k in ipairs(adj[cur]) do
                    if k == start and prev ~= nil and #chain > 2 then return chain, true end
                end
                return chain, false
            end
            used[nxt] = true
            table.insert(chain, nxt)
            prev, cur = cur, nxt
        end
    end
    local function emit(chain, closed)
        if #chain < 3 then return end
        local s, last = {}, nil
        for idx, k in ipairs(chain) do
            local x, y = point(k)
            if idx == 1 or idx == #chain or (x - last[1]) ^ 2 + (y - last[2]) ^ 2 >= 0.03 ^ 2 then
                table.insert(s, "(" .. fmt(x) .. "," .. fmt(y) .. ")"); last = { x, y }
            end
        end
        tex.sprint("\\draw[" .. style .. "] " .. table.concat(s, " -- ") .. (closed and " -- cycle" or "") .. ";")
    end
    -- open chains start at an end (an edge with a single neighbour)
    for k, l in pairs(adj) do
        if #l == 1 and not used[k] then emit(walk(k)) end
    end
    for k, _ in pairs(adj) do
        if not used[k] then emit(walk(k)) end
    end
end

-- Equipotentials through the points "a1/b1, a2/b2, ..."
function SF.equipotentials(seeds, style)
    for a, b in string.gmatch(seeds, "([%-%d%.]+)%s*/%s*([%-%d%.]+)") do
        contour(tonumber(a), tonumber(b), style or "equipotential")
    end
end

SF.reset()
