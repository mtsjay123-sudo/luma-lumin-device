# The pitch film, in code

A 38-second film drawn by a web page and photographed frame by frame. No video editor.

- `film.html` is the whole film: every scene, and one function, `seek(t)`, that puts everything where it belongs at second `t`.
- `render.cjs` opens it in a browser, takes 1,140 pictures (30 a second), and ffmpeg joins them.

To make it again (needs node with Playwright, and ffmpeg):

```
cp /path/to/your/photo.png pitch/founder.png     # your own picture; it isn't kept in the repository
mkdir -p pitch/frames
node pitch/render.cjs check                      # six stills to look at first
node pitch/render.cjs                            # every frame
ffmpeg -framerate 30 -i pitch/frames/f%05d.jpg -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart pitch/luma-pitch.mp4
```

To change a line, change it in `film.html`. Times are in seconds, in `seek`.

What's true in it: the 2023 Surgeon General's figure, the three facts (the brain is in the lamp, the switch cuts the
microphones' power, 988 comes before the brain), the test count on the day it was made, and the lines of code, which are
copied from this repository. The man in the third scene is a drawing, and the film says so. The lamp is a design; the
film's last card says that too.
