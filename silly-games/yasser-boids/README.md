# YASSER boids

300 little triangles roam the window as a loose swarm. Every few seconds one is drawn to a
letter of the name YASSER, rides along its lines for 3 seconds, then flies off, either to
another letter or back to roaming. They keep a little distance from each other and loosely
line up with their neighbours.

Grey = roaming · colour = heading to, or riding, the letter of that colour.

## Run

```
python yasser_swarm.py
```

Plain Python, nothing to install (uses tkinter). **Space** pauses, **click** scatters nearby boids.
The tuning knobs (time on a letter, roaming time, chance of going to another letter,
separation and alignment strength) are the constants at the top of the file.

## How it was made

Written by a local model (Ornith-1.5 35B on a home GPU box) over five rounds. After each
round Claude Code ran the program without a window, measured it (crashes, how far each
boid sits from its letter, how long a visit lasts) and sent the faults back. The model
wrote every line; the measurements found every bug.
