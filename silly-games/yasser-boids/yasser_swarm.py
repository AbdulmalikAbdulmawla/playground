import math
import random
import tkinter as tk

# ---- Tuning constants ---------------------------------------------------
DWELL_S = 3.0          # simulated seconds spent "on" a letter
FREE_MIN_S = 2.0       # simulated seconds "free" (min)
FREE_MAX_S = 5.0       # simulated seconds "free" (max)
P_NEXT_LETTER = 0.5    # prob. of going seek->(different letter) after leaving
W_SEP = 0.3            # weak separation weight (relative to main force)
W_ALIGN = 0.15         # weak alignment weight (relative to main force)
W_WANDER = 0.2         # wander jitter strength
MAX_SPEED = 3.0
MAX_FORCE = 0.15

# ---- Letter definitions -------------------------------------------------
# Each letter is a list of strokes; each stroke is a polyline of (x, y)
# points inside a 0..1 box with y increasing downward.

def build_letters():
    def bezier(p0, ctrl, p1, n):
        # dense sampling of a quadratic bezier (smooth curve)
        pts = []
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            x = mt * mt * p0[0] + 2 * mt * t * ctrl[0] + t * t * p1[0]
            y = mt * mt * p0[1] + 2 * mt * t * ctrl[1] + t * t * p1[1]
            pts.append((x, y))
        return pts

    letters = []

    # Y: two upper diagonals meet at a stem
    letters.append([
        [(0.05, 0.12), (0.5, 0.55)],
        [(0.95, 0.12), (0.5, 0.55)],
        [(0.5, 0.55), (0.5, 0.95)],
    ])

    # A: two legs + crossbar
    letters.append([
        [(0.1, 0.95), (0.5, 0.08)],
        [(0.9, 0.95), (0.5, 0.08)],
        [(0.28, 0.6), (0.72, 0.6)],
    ])

    # S: real S built from four arcs joined with *matching tangents*
    # so the whole stroke is C1-continuous (no sharp corners at the joins).
    # top arc: top-right -> over the top -> top-left (arrives heading down-left)
    s_top = bezier((0.80, 0.20), (0.50, 0.08), (0.22, 0.28), 12)
    # mid1: top-left -> centre, control kept collinear with s_top's arrival
    #       tangent so the join is smooth (curve continues down-right).
    s_mid1 = bezier((0.22, 0.28), (0.30, 0.40), (0.50, 0.50), 10)
    # mid2: centre -> bottom-right (mirror of mid1 through the centre)
    s_mid2 = bezier((0.50, 0.50), (0.70, 0.60), (0.79, 0.72), 10)
    # bottom arc: right -> round the bottom -> bottom-left
    s_bot = bezier((0.79, 0.72), (0.50, 0.90), (0.21, 0.80), 12)
    # join, dropping the duplicated join points
    s = s_top + s_mid1[1:] + s_mid2[1:] + s_bot[1:]
    letters.append([s])
    letters.append([s])

    # E: stem + three bars
    letters.append([
        [(0.15, 0.1), (0.15, 0.9)],
        [(0.15, 0.1), (0.82, 0.1)],
        [(0.15, 0.5), (0.7, 0.5)],
        [(0.15, 0.9), (0.82, 0.9)],
    ])

    # R: stem + bowl (half-circle bulging RIGHT) + leg
    # bowl: straight from stem top (0.15,0.10) to (0.50,0.10), then a
    # half-circle centred at (0.50,0.30) r=0.20 out to (0.50,0.50),
    # then straight back left to the stem at (0.15,0.50).
    bowl_top = [(0.15, 0.10), (0.50, 0.10)]
    bowl = []
    for i in range(17):
        t = -math.pi / 2 + math.pi * i / 16     # t from -pi/2 to +pi/2
        bowl.append((0.50 + 0.20 * math.cos(t), 0.30 + 0.20 * math.sin(t)))
    bowl_bot = [(0.50, 0.50), (0.15, 0.50)]
    letters.append([
        [(0.15, 0.1), (0.15, 0.9)],   # stem
        bowl_top + bowl,              # straight top + half-circle bowl
        bowl_bot,                     # straight back left to stem
        [(0.40, 0.50), (0.85, 0.90)], # leg
    ])

    return letters


# ---- Geometry helpers (arc-length parameterisation in pixels) ----------

def stroke_len(stroke):
    return sum(math.hypot(stroke[i][0] - stroke[i - 1][0],
                          stroke[i][1] - stroke[i - 1][1])
               for i in range(1, len(stroke)))


def closest_point(stroke, x, y):
    """Return (distance, s) where s is arc length in pixels along stroke."""
    best_d2 = float('inf')
    best_s = 0.0
    cum = 0.0
    x1, y1 = stroke[0]
    for i in range(1, len(stroke)):
        x2, y2 = stroke[i]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        L2 = seg_len * seg_len
        if L2 == 0:
            t = 0.0
        else:
            t = ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / L2
            t = max(0.0, min(1.0, t))
        px = x1 + t * (x2 - x1)
        py = y1 + t * (y2 - y1)
        d2 = (x - px) ** 2 + (y - py) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_s = cum + t * seg_len
        cum += seg_len
        x1, y1 = x2, y2
    return math.sqrt(best_d2), best_s


def point_at_arc(stroke, s):
    """Point at arc length s along stroke (clamped to [0, stroke_len])."""
    L = stroke_len(stroke)
    if s <= 0:
        return stroke[0]
    if s >= L:
        return stroke[-1]
    cum = 0.0
    x1, y1 = stroke[0]
    for i in range(1, len(stroke)):
        x2, y2 = stroke[i]
        seg_len = math.hypot(x2 - x1, y2 - y1)
        if s <= cum + seg_len:
            t = (s - cum) / seg_len if seg_len else 0.0
            return (x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)
        cum += seg_len
        x1, y1 = x2, y2
    return stroke[-1]


# ---- Boid ---------------------------------------------------------------

class Boid:
    def __init__(self, flock, stroke, letter_idx, direction):
        self.flock = flock
        self.stroke = stroke
        self.letter_idx = letter_idx
        self.dir = direction                 # +1 or -1 along the stroke
        L = stroke_len(stroke)
        self.s = random.random() * L         # arc length position (px)
        self.x, self.y = point_at_arc(stroke, self.s)
        # small velocity aligned with the stroke
        px, py = point_at_arc(stroke, self.s + 0.05 * direction)
        self.vx, self.vy = (px - self.x) * 6, (py - self.y) * 6
        self.item = None                     # canvas polygon, created later

    def steer(self, target_vx, target_vy, maxforce):
        sw = target_vx - self.vx
        tw = target_vy - self.vy
        m = math.hypot(sw, tw)
        if m > maxforce:
            sw, tw = sw / m * maxforce, tw / m * maxforce
        return sw, tw

    def update(self):
        self.vx += self.ax
        self.vy += self.ay
        sp = math.hypot(self.vx, self.vy)
        if sp > self.flock.max_speed:
            self.vx, self.vy = self.vx / sp * self.flock.max_speed, \
                               self.vy / sp * self.flock.max_speed
        self.x += self.vx
        self.y += self.vy
        # keep inside window (clamped to 0..W, 0..H - never leaves window)
        W, H = self.flock.W, self.flock.H
        if self.x < 0: self.x, self.vx = 0, abs(self.vx)
        if self.x > W: self.x, self.vx = W, -abs(self.vx)
        if self.y < 0: self.y, self.vy = 0, abs(self.vy)
        if self.y > H: self.y, self.vy = H, -abs(self.vy)


# ---- Flock --------------------------------------------------------------

class Flock:
    def __init__(self, root, letters):
        self.root = root
        self.W, self.H = 1200, 450
        self.max_speed = MAX_SPEED
        self.max_force = MAX_FORCE
        self.grid = 28
        self.paused = False
        self.sim_time = 0.0

        # layout: letter boxes across the window
        self.margin_x = 45
        self.spacing = 14
        self.letter_w = (self.W - 2 * self.margin_x - self.spacing * 5) / 6
        self.letter_h = self.H - 40
        self.origin_y = 20
        # precompute each stroke in pixel coords
        self.strokes = []      # list of (stroke_pixels, letter_idx)
        for li, letter in enumerate(letters):
            for stroke in letter:
                px = [(self.margin_x + li * (self.letter_w + self.spacing) + p[0] * self.letter_w,
                       self.origin_y + p[1] * self.letter_h) for p in stroke]
                self.strokes.append((px, li))

        # colour per letter
        self.colours = ["#FF6B6B", "#FFD93D", "#6BCB77",
                        "#4D96FF", "#C77BFF", "#FF9F45"]
        self.grey = "#c8ccd2"

        # spatial grid
        self.cells = {}

        # distribute 300 boids, all starting "free"
        target = 300
        counts = [target // len(self.strokes)] * len(self.strokes)
        for i in range(target - sum(counts)):
            counts[i] += 1
        self.boids = []
        for (stroke, li), count in zip(self.strokes, counts):
            for _ in range(count):
                b = Boid(self, stroke, li, 1 if random.random() < 0.5 else -1)
                # start free at a random position with random velocity
                b.x = random.uniform(0, self.W)
                b.y = random.uniform(0, self.H)
                ang = random.uniform(0, 2 * math.pi)
                b.vx = math.cos(ang) * self.max_speed * 0.5
                b.vy = math.sin(ang) * self.max_speed * 0.5
                b.state = "free"
                b.letter = None
                b.last_letter = None
                b.free_time = random.uniform(0, 3.0)   # staggered timers
                b.wander_angle = random.uniform(0, 2 * math.pi)
                b.start_time = 0.0
                self.boids.append(b)

        for b in self.boids:
            self._add_to_grid(b)

        # canvas
        self.canvas = tk.Canvas(root, width=self.W, height=self.H,
                                bg="#101418", highlightthickness=0)
        self.canvas.pack()
        self._draw_letters()
        self._make_boids()

        self.canvas.focus_set()
        self.canvas.bind("<space>", lambda e: self.toggle_pause())
        self.canvas.bind("<Button-1>", self.on_click)

    def _draw_letters(self):
        for stroke, li in self.strokes:
            pts = []
            for p in stroke:
                pts += [p[0], p[1]]
            self.canvas.create_line(pts, fill="#3a3f47", width=1.5,
                                    smooth=False)

    def _make_boids(self):
        for b in self.boids:
            b.item = self.canvas.create_polygon(
                0, 0, 0, 0, 0, 0, fill=self.grey,
                outline="")

    def _cell(self, x, y):
        return (int(x // self.grid), int(y // self.grid))

    def _add_to_grid(self, b):
        key = self._cell(b.x, b.y)
        self.cells.setdefault(key, []).append(b)

    def _rehash(self):
        self.cells = {}
        for b in self.boids:
            self._add_to_grid(b)

    def neighbours(self, b):
        cx, cy = self._cell(b.x, b.y)
        res = []
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                cell = self.cells.get((cx + i, cy + j))
                if cell:
                    res.extend(cell)
        return res

    def _pick_letter(self, exclude=None):
        idxs = [li for li in range(len(self.colours)) if li != exclude]
        if not idxs:
            idxs = list(range(len(self.colours)))
        return random.choice(idxs)

    def _nearest_stroke(self, li, b):
        """Nearest stroke of letter li -> (stroke, dist, s)."""
        best_d = float('inf')
        best_stroke = None
        best_s = 0.0
        for stroke, l in self.strokes:
            if l != li:
                continue
            d, s = closest_point(stroke, b.x, b.y)
            if d < best_d:
                best_d = d
                best_stroke = stroke
                best_s = s
        return best_stroke, best_d, best_s

    def _attach(self, b):
        stroke, d, s = self._nearest_stroke(b.letter, b)
        b.stroke = stroke
        b.s = s
        b.dir = 1 if random.random() < 0.5 else -1
        b.x, b.y = point_at_arc(stroke, s)
        px, py = point_at_arc(stroke, s + 0.05 * b.dir)
        b.vx, b.vy = (px - b.x) * 6, (py - b.y) * 6

    def _reassign(self, b):
        # move boid to another stroke of the SAME letter, snapping to nearest
        others = [s for (s, li) in self.strokes if li == b.letter and s is not b.stroke]
        if not others:
            return
        b.stroke = random.choice(others)
        dist, s = closest_point(b.stroke, b.x, b.y)
        b.s = s
        b.x, b.y = point_at_arc(b.stroke, s)
        px, py = point_at_arc(b.stroke, s + 0.05 * b.dir)
        b.vx, b.vy = (px - b.x) * 6, (py - b.y) * 6

    def _recolor(self, b):
        col = self.grey if b.state == "free" else self.colours[b.letter]
        self.canvas.itemconfig(b.item, fill=col)

    def _sep_align(self, b):
        """Weak separation + alignment steering forces (max_force capped)."""
        sep_x = sep_y = 0.0
        al_x = al_y = 0.0
        n_al = 0
        sep_r2 = 10 * 10
        align_r2 = 28 * 28
        for o in self.neighbours(b):
            if o is b:
                continue
            dx, dy = b.x - o.x, b.y - o.y
            d2 = dx * dx + dy * dy
            if 0.0001 < d2 < sep_r2:
                d = math.sqrt(d2)
                w = 1.0 - d / 10.0
                sep_x += (dx / d) * w
                sep_y += (dy / d) * w
            if d2 < align_r2:
                al_x += o.vx
                al_y += o.vy
                n_al += 1
        sm = math.hypot(sep_x, sep_y)
        if sm > 0:
            sep_x, sep_y = sep_x / sm * self.max_speed, sep_y / sm * self.max_speed
            sx, sy = b.steer(sep_x, sep_y, self.max_force)
        else:
            sx, sy = 0.0, 0.0
        if n_al > 0:
            al_x /= n_al
            al_y /= n_al
            am = math.hypot(al_x, al_y)
            if am > 0:
                al_x, al_y = al_x / am * self.max_speed, al_y / am * self.max_speed
                ax, ay = b.steer(al_x, al_y, self.max_force)
            else:
                ax, ay = 0.0, 0.0
        else:
            ax, ay = 0.0, 0.0
        return sx, sy, ax, ay

    def _edge_avoid(self, b):
        """Soft inward steering within 40 px of a window edge."""
        margin = 40.0
        ex = 0.0
        if b.x < margin:
            ex = (margin - b.x) / margin
        elif b.x > self.W - margin:
            ex = -(b.x - (self.W - margin)) / margin
        ey = 0.0
        if b.y < margin:
            ey = (margin - b.y) / margin
        elif b.y > self.H - margin:
            ey = -(b.y - (self.H - margin)) / margin
        return ex, ey

    def _leave(self, b):
        # push away from the letter (random outward direction, ~max_speed)
        ang = random.uniform(0, 2 * math.pi)
        b.vx = math.cos(ang) * self.max_speed
        b.vy = math.sin(ang) * self.max_speed
        b.last_letter = b.letter                 # remember before re-targeting
        if random.random() < P_NEXT_LETTER:
            b.letter = self._pick_letter(exclude=b.last_letter)
            b.state = "seek"
        else:
            b.letter = None
            b.state = "free"
            b.free_time = random.uniform(FREE_MIN_S, FREE_MAX_S)
        self._recolor(b)

    def on_click(self, event):
        for b in self.boids:
            dx, dy = b.x - event.x, b.y - event.y
            d = math.hypot(dx, dy)
            if d < 80 and d > 0.001:
                push = (80 - d) / 80
                b.vx += dx / d * push * 12
                b.vy += dy / d * push * 12

    def toggle_pause(self):
        self.paused = not self.paused

    def step(self):
        if self.paused:
            return

        self.sim_time += 1.0 / 60.0
        self._rehash()

        LOOK = 12.0            # shortened look-ahead on curves (px)
        ARRIVE_R = 25.0        # arrive band near stroke ends (px)

        for b in self.boids:
            if b.state == "free":
                # wander (smoothly changing heading)
                b.wander_angle += random.uniform(-1, 1) * W_WANDER
                wx = math.cos(b.wander_angle)
                wy = math.sin(b.wander_angle)
                ax, ay = b.steer(wx * self.max_speed, wy * self.max_speed, self.max_force)
                sx, sy, ax2, ay2 = self._sep_align(b)
                ax += W_SEP * sx + W_ALIGN * ax2
                ay += W_SEP * sy + W_ALIGN * ay2
                ex, ey = self._edge_avoid(b)
                ax += ex
                ay += ey
                b.ax, b.ay = ax, ay
                b.update()
                b.free_time -= 1.0 / 60.0
                if b.free_time <= 0:
                    b.letter = self._pick_letter(exclude=b.last_letter)
                    b.state = "seek"
                    self._recolor(b)

            elif b.state == "seek":
                # steer toward nearest point on any stroke of target letter
                stroke, d, s = self._nearest_stroke(b.letter, b)
                tx, ty = point_at_arc(stroke, s)
                dx, dy = tx - b.x, ty - b.y
                m = math.hypot(dx, dy)
                if m > 0:
                    dx, dy = dx / m * self.max_speed, dy / m * self.max_speed
                    ax, ay = b.steer(dx, dy, self.max_force)
                else:
                    ax, ay = 0.0, 0.0
                sx, sy, ax2, ay2 = self._sep_align(b)
                ax += W_SEP * sx + W_ALIGN * ax2
                ay += W_SEP * sy + W_ALIGN * ay2
                b.ax, b.ay = ax, ay
                b.update()
                if d <= 8.0:
                    b.state = "on"
                    b.start_time = self.sim_time
                    self._attach(b)
                    self._recolor(b)

            else:  # "on"
                if self.sim_time - b.start_time >= DWELL_S:
                    self._leave(b)
                    continue

                sx, sy, ax, ay = self._sep_align(b)

                # (1) look-ahead target
                sp = math.hypot(b.vx, b.vy)
                if sp > 0:
                    predict_x = b.x + b.vx / sp * LOOK
                    predict_y = b.y + b.vy / sp * LOOK
                else:
                    predict_x, predict_y = b.x, b.y
                _, s_pred = closest_point(b.stroke, predict_x, predict_y)

                # (2) forward (progression) steering
                s_target = s_pred + LOOK * b.dir
                tx, ty = point_at_arc(b.stroke, s_target)
                dx, dy = tx - b.x, ty - b.y
                m = math.hypot(dx, dy)
                if m > 0:
                    dx, dy = dx / m * self.max_speed, dy / m * self.max_speed
                    path_x, path_y = b.steer(dx, dy, self.max_force)
                else:
                    path_x, path_y = 0.0, 0.0

                # (3) lateral correction toward closest point on stroke
                _, s_curr = closest_point(b.stroke, b.x, b.y)
                cpx, cpy = point_at_arc(b.stroke, s_curr)
                lx, ly = cpx - b.x, cpy - b.y
                lm = math.hypot(lx, ly)
                if lm > 0.0001:
                    lx, ly = lx / lm, ly / lm
                    mag = min(self.max_speed, lm * 0.35)
                    lx, ly = lx * mag, ly * mag
                    lat_x, lat_y = b.steer(lx, ly, self.max_force)
                else:
                    lat_x, lat_y = 0.0, 0.0

                b.ax = path_x * 1.4 + 1.4 * lat_x + W_SEP * sx + W_ALIGN * ax
                b.ay = path_y * 1.4 + 1.4 * lat_y + W_SEP * sy + W_ALIGN * ay

                # stroke-end / arrive behaviour
                L = stroke_len(b.stroke)
                _, s_actual = closest_point(b.stroke, b.x, b.y)
                at_end = (b.dir > 0 and s_actual >= L - ARRIVE_R) or \
                         (b.dir < 0 and s_actual <= ARRIVE_R)
                if at_end:
                    if random.random() < 0.2:
                        self._reassign(b)
                        b.ax = b.ay = 0.0
                        b.update()
                        continue
                    b.dir = -b.dir
                    if b.dir > 0:
                        back_s = min(s_actual - ARRIVE_R, L)
                    else:
                        back_s = max(s_actual + ARRIVE_R, 0)
                    bx, by = point_at_arc(b.stroke, back_s)
                    dx, dy = bx - b.x, by - b.y
                    m = math.hypot(dx, dy)
                    if m > 0:
                        dx, dy = dx / m * self.max_speed, dy / m * self.max_speed
                        path_x, path_y = b.steer(dx, dy, self.max_force)
                        b.ax = path_x * 1.4 + 1.4 * lat_x
                        b.ay = path_y * 1.4 + 1.4 * lat_y
                else:
                    end_s = L if b.dir > 0 else 0.0
                    rem = abs(end_s - s_pred)
                    if rem < ARRIVE_R and rem > 0.001:
                        factor = rem / ARRIVE_R
                        b.vx *= 0.4 + 0.6 * factor
                        b.vy *= 0.4 + 0.6 * factor

                b.update()

        # redraw reusing canvas items (coords() updates)
        for b in self.boids:
            ang = math.atan2(b.vy, b.vx)
            r = 4.5
            nx, ny = math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)
            nose = (b.x + math.cos(ang) * r, b.y + math.sin(ang) * r)
            bl = (b.x - math.cos(ang) * r * 0.5 + nx * r * 0.5,
                  b.y - math.sin(ang) * r * 0.5 + ny * r * 0.5)
            br = (b.x - math.cos(ang) * r * 0.5 - nx * r * 0.5,
                  b.y - math.sin(ang) * r * 0.5 - ny * r * 0.5)
            self.canvas.coords(b.item,
                                nose[0], nose[1], bl[0], bl[1], br[0], br[1])


def main():
    random.seed(7)
    root = tk.Tk()
    root.title("YASSER boids")
    root.resizable(False, False)
    letters = build_letters()
    flock = Flock(root, letters)
    def loop():
        flock.step()
        root.after(16, loop)
    loop()
    root.mainloop()


if __name__ == "__main__":
    main()
