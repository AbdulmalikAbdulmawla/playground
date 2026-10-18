# YASSER boids — a test of the local AI box

This is a **test of my local AI box**: can a model running on my own hardware, with no cloud,
write a working small program? The task was a boids swarm on the word YASSER.

300 little triangles roam the window as a loose swarm. Every few seconds one is drawn to a
letter of YASSER, rides along its lines for 3 seconds, then flies off, either to another
letter or back to roaming. They keep a little distance from each other and loosely line up
with their neighbours. Grey = roaming · colour = heading to, or riding, the letter of that colour.

## Run

```
python yasser_swarm.py     # the free swarm (rounds 4–5)
python yasser_boids.py     # the first version: boids that stay on the letters (rounds 1–3)
```

Plain Python, nothing to install (uses tkinter). **Space** pauses, **click** scatters nearby boids.
The tuning knobs (time on a letter, roaming time, chance of going to another letter,
separation and alignment strength) are the constants at the top of the file.

## The test set-up

- **Writer:** Ornith-1.5 35B-A3B (Q4_K_M) on llama.cpp, on a desktop with an RTX 3060 12 GB.
  Thinking capped at 8,000 tokens, about 46–51 tokens/s.
- **Checker:** Claude Code. After each round it ran the program without a window for
  600–1,500 frames and measured it: crashes, how far each boid sits from its letter, how long
  a letter visit lasts, speed per frame. It then sent the faults back as a numbered list.
- **Rule:** the local model wrote every line of the code. The checker only described what was
  wrong. It patched a throw-away copy only to find the next bug, never the delivered file.

## The trials

Rounds 1–3 built the first version, `yasser_boids.py` (boids that stay on the letters all the
time). Rounds 4–5 changed the behaviour to the free swarm, `yasser_swarm.py`. Before round 4, the checker wrote its
8-point acceptance test before the model saw the task.

| Round | Task | Box time | Errors the local model made (found by running it) | What we sent back | Result |
|---|---|---|---|---|---|
| 1 | Boids ride the letter lines | 4.3 min | Crashed before the window opened: an invalid drawing option (`dash=(1, 0)`) and a wrong key name (`<Space>` instead of `<space>`). Crashed on frame 1: a function used as a number. Called a method that did not exist. Mixed up two units (pixels vs. point numbers), so 296 of 300 boids started about 12,000 px away from their letter. Drew the S as a loop and the R's bowl as a U. Bounced boids outwards at the left and top edges. | 11-point bug list + an executable test: 600 frames, at least 90 % of boids within 8 px of their line | ✗ did not start |
| 2 | same | 5.3 min | Ran smoothly (5.4 ms per frame), but the R was **still a U**, and 17 % of boids left the lines: 39 cut the corners on the curves, 14 overshot the ends of a line. | Exact geometry for the R; a constant pull back to the line; a shorter look-ahead on curves; smooth joins inside the S; slowing down before the end of a line | ✗ 83 % on the lines |
| 3 | same | 7.6 min | None the test could find. Every boid stayed on its line at frames 60, 300 and 600; the R was correct; 8 ms per frame. Weak spot left: a click scatters boids only about 5 px. | — | ✓ passed |
| 4 | Free swarm: roam, ride a letter 3 s, leave for another letter or roam | 5.7 min | Crashed on frame 1: picked a target from the 18 strokes instead of the 6 letters, and used a variable that did not exist. Once patched: **every movement was divided by 60**, so boids crawled at 0.05 px per frame; after 25 s, 288 of 300 were still on their way and only 61 letter visits had happened. Also: "go to a *different* letter" was never enforced, a boid could jump to a stroke of the wrong letter, and alignment counted boids up to 84 px away. | 6-point bug list, with the measured numbers | ✗ crashed, then far too slow |
| 5 | same | 5.8 min | None. All 8 checks passed: 929 letter visits, each 3.00–3.02 s; 100 % of riders on their line; 33–64 % of boids on a letter at any moment; every boid visited at least 2 letters; 0 of 750 repeat visits to the same letter; nobody left the window; 6.2 ms per frame. | — | ✓ passed |

**Totals:** 5 rounds, about 29 minutes of box time, 2 passing programs, no cloud model writing code.

**What the test showed:** the local model got the overall design right every time. But every
failing round hid silent bugs (wrong units, wrong scale, wrong shape) that only running the
program revealed. The model never found one of its own bugs. Once told precisely what was
wrong, with numbers, it fixed it. So the local box is a usable coder when something checks its
work by running it, not when it works alone.
