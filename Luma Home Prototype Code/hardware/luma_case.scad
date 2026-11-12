// Luma Home: the lamp. A frosted dome on a short white base, with a warm glow low in the middle (prototype, "EVT").
//
// Three printed sections, bottom to top:
//   base : the computer (a Jetson Orin Nano Super developer kit by default), the speaker firing down, the microphone
//          switch and its hard-wired light. Air comes in underneath and leaves through the port window at the back.
//   deck : the lid of the base. The microphone ring and the glow sit on it, under the dome.
//   dome : the frosted shade. It twists onto the deck and stands 2 mm above it: that ring of air is how sound reaches
//          the microphones.
// plus small parts: a tag for the switch, and test pieces to print first.
//
// Everything is a number you can change. Measure your own parts before you print: the defaults are from the makers'
// published sizes. Print `part = "fit"` and `part = "rim"` first (under an hour together).
//
//   openscad -o base.stl -D 'part="base"' luma_case.scad      (and "deck", "dome", "tag", "fit", "rim")
//
// Base and deck: white PETG. Dome: natural (clear) PETG, which prints frosted. 0.2 mm layers, no supports: the base
// and the deck stand as drawn, the dome prints standing on its flat top.
// Units are millimetres. License: MIT.

part = "assembly";   // base | deck | dome | tag | fit | rim | assembly | exploded | cut

/* [The body] */
body_d = 168;        // across
body_h = 260;        // top to bottom (1.55 times as tall as wide, as in the picture)
wall = 2.4;          // base and deck
dome_wall = 1.6;     // the dome: thin enough to glow, thick enough to hold
edge_r = 20;         // the rounding under the base
shoulder_r = 42;     // the rounding at the top of the dome
start_a = 40;        // how steeply a rounding starts, from flat (40 prints cleanly with no supports)
base_h = 54;         // the base section
deck_h = 7;          // the deck above it; base and deck together are the white band
seam = 2;            // the ring of air between deck and dome
lip = 3;             // how far the deck steps into the base
gap = 0.25;          // slack between sections

/* [The computer] */
// Jetson Orin Nano Super developer kit: the board is 100 x 79; with connectors and the fan it fills about 103 x 90.5 x 35.
board_w = 103;
board_d = 90.5;
board_h = 35;
board_lift = 4;      // the board sits on its own feet; this is room under it for air
board_y = 11.75;     // how far back of centre the board sits (back is +y)
port_w = 98;         // window in the back wall for power, network, display and USB
port_up = 2;         // bottom of the window above the board's underside
// A Raspberry Pi 5 instead (the smaller device): set pi5 = true for four M2.5 posts on its 58 x 49 hole pattern.
pi5 = false;

/* [The speaker] */
// A small speaker that comes sealed in its own box (70 x 30 x 17, 4 ohm, 3 W). It lies face down over slots in the floor.
spk_w = 71.5;
spk_d = 32;
spk_h = 17;
spk_lift = 3;        // how far above the floor it rests
spk_y = -52.5;       // its middle, in front of the board

/* [The microphones and the glow] */
mic_d = 70;          // ReSpeaker Mic Array v2.0: a round board, 70 across
mic_up = 6;          // how far above the deck the board lies (room for its plug)

/* [The switch and its light] */
sw_d = 6.3;          // hole for a mini toggle switch's threaded neck
sw_at = 75;          // where it is, in degrees round from the back
sw_z = 31;           // how high
led_d = 3.1;         // a 3 mm LED pressed in from inside
led_at = 120;        // round to the front, where it can be seen
led_z = 31;

/* [How the dome holds on] */
lugs = 3;            // bumps inside the dome's rim that twist under three towers on the deck
lug_w = 7;           // degrees
lug_in = 2;          // how far a bump stands in from the dome's wall
tower_h = 14;
tower_at = 60;       // where the first tower is, in degrees round from the back

$fn = 96;
R = body_d / 2;
dome_h = body_h - base_h - deck_h - seam;
floor_t = wall;
boss = 9;            // posts for the M3 screws that hold the deck down
ins = 4.0;           // hole for an M3 heat-set insert
post_at = [90, 135, 225, 270];   // where the posts are, in degrees round from the back
post_r = R - wall - boss / 2 + 0.6;

function arc(R, Rs, zc, n = 24) = [for (i = [0 : n]) let (t = -(90 - start_a) * (1 - i / n)) [R - Rs + Rs * cos(t), zc + Rs * sin(t)]];
function flat_r(R, Rs) = R - Rs * (1 - cos(90 - start_a));   // how wide the flat is before a rounding starts

module half(R, h, Rs) {          // half the outline of a cup: flat underneath, a rounded edge, straight sides
    polygon(concat([[0, 0], [flat_r(R, Rs), 0]], arc(R, Rs, Rs * sin(90 - start_a)), [[R, h], [0, h]]));
}

module cup2d(R, h, Rs, t) {      // the same outline, hollowed to a wall t thick and open at the top
    difference() {
        half(R, h, Rs);
        intersection() {
            offset(delta = -t) union() { half(R, h + 10, Rs); mirror([1, 0]) half(R, h + 10, Rs); }
            translate([0, -1]) square([R, h + 12]);
        }
    }
}

module cup(R, h, Rs, t) { rotate_extrude($fn = 180) cup2d(R, h, Rs, t); }
module solid(R, h, Rs) { rotate_extrude($fn = 180) half(R, h, Rs); }

module at(a) { rotate([0, 0, 90 - a]) children(); }             // a degrees round from the back (+y), towards +x
module ring_piece(r1, r2, a, w, h) { at(a + w / 2) rotate_extrude(angle = w, $fn = 180) translate([r1, 0]) square([r2 - r1, h]); }

module slots(n, len, w, pitch) { // a row of slots, centred
    for (i = [0 : n - 1]) translate([(i - (n - 1) / 2) * pitch, 0, 0]) hull() {
        translate([0, -len / 2 + w / 2, 0]) cylinder(d = w, h = 20, center = true, $fn = 24);
        translate([0, len / 2 - w / 2, 0]) cylinder(d = w, h = 20, center = true, $fn = 24);
    }
}

// ---- base: the computer, the speaker, the switch ------------------------------------------------------------------------
module base() {
    post_top = base_h - lip - 0.3;
    difference() {
        union() {
            cup(R, base_h, edge_r, wall);
            intersection() {       // everything inside is trimmed to the cup's own outline
                solid(R, base_h, edge_r);
                union() {
                    for (a = post_at) at(a) translate([post_r, 0, 0]) cylinder(d = boss, h = post_top);
                    if (pi5) {      // four M2.5 posts on the Pi 5's hole pattern (58 x 49)
                        translate([0, board_y, floor_t]) for (x = [-29, 29], y = [-24.5, 24.5]) translate([x, y, 0])
                            difference() { cylinder(d = 6, h = board_lift + 3); cylinder(d = 2.2, h = board_lift + 4); }
                    } else {        // four guides: the kit stands on its own feet between them
                        translate([0, board_y, floor_t]) for (x = [-1, 1], y = [-1, 1])
                            translate([x * (board_w / 2 + 1.5), y * (board_d / 2 - 10), 4.5]) cube([2, 14, 9], center = true);
                    }
                    // the speaker's cradle: two rests it lies on and a low wall at each end
                    for (x = [-1, 1]) translate([x * (spk_w / 2 - 3), spk_y, floor_t + spk_lift / 2]) cube([6, spk_d, spk_lift], center = true);
                    for (x = [-1, 1]) translate([x * (spk_w / 2 + 1.2), spk_y, floor_t + (spk_lift + 7) / 2]) cube([1.6, spk_d - 8, spk_lift + 7], center = true);
                    // a thicker patch of wall around the switch, so its nut has something flat to pull against
                    at(sw_at) translate([R - wall - 1.2, 0, sw_z]) rotate([0, 90, 0]) cylinder(d1 = 13, d2 = 22, h = 2.6);
                }
            }
        }
        for (a = post_at) at(a) translate([post_r, 0, post_top - 10]) cylinder(d = ins, h = 11);   // heat-set inserts
        // air in from below, under the board
        translate([0, board_y, 0]) slots(9, 60, 4, 9);
        // the speaker's sound out, under the base (it stands on feet)
        translate([0, spk_y, 0]) slots(7, 22, 3, 8.5);
        // the back: one window for every port on the board's rear edge, open to the rim so nothing bridges
        translate([-port_w / 2, board_y + board_d / 2 - 1, floor_t + board_lift + port_up]) cube([port_w, R, base_h]);
        // the switch: a round hole, and a shallow flat outside for its tag
        at(sw_at) translate([R - 12, 0, sw_z]) rotate([0, 90, 0]) cylinder(d = sw_d, h = 20, $fn = 32);
        at(sw_at) translate([R - 0.9, -13.5, sw_z - 10]) cube([3, 27, 20]);
        // its light, hard-wired to the microphones' power: lit means they can hear
        at(led_at) translate([R - 12, 0, led_z]) rotate([0, 90, 0]) cylinder(d = led_d, h = 20, $fn = 32);
        // four recesses for stick-on rubber feet
        for (a = [45, 135, 225, 315]) at(a) translate([R - 26, 0, -0.01]) cylinder(d = 13, h = 0.8);
    }
}

// ---- deck: the lid of the base; the microphones and the glow stand on it --------------------------------------------------
// Solid, so the base is closed under the microphones: the speaker and the fan are in a different room from them.
ledge = mic_up;
tower_out = R - dome_wall - 0.35;
tower_in = tower_out - 5.2;
lug_low = 4.5;       // a bump's underside, above the dome's rim
lug_tall = 3;        // its straight part; a 45 degree ramp above it makes it printable
slot_low = seam + lug_low - 0.5;
slot_high = seam + lug_low + lug_tall + lug_in + 0.4;

module deck() {
    bevel = wall + gap;
    difference() {
        union() {
            translate([0, 0, -lip]) cylinder(r = R - wall - gap, h = lip + 0.01, $fn = 180);        // the step down into the base
            cylinder(r1 = R - wall - gap, r2 = R, h = bevel, $fn = 180);                            // out to full width at 45 degrees
            translate([0, 0, bevel]) cylinder(r = R, h = deck_h - bevel, $fn = 180);
            translate([0, 0, deck_h]) {
                // the ring the microphone board lies on, and a low rim that centres it
                difference() {
                    union() { cylinder(d = mic_d - 2, h = ledge); cylinder(d = mic_d + 4.4, h = ledge + 2.2); }
                    translate([0, 0, -1]) cylinder(d = mic_d - 8, h = ledge + 6);
                    translate([0, 0, ledge]) cylinder(d = mic_d + 0.8, h = 5);
                    translate([0, mic_d / 2, (ledge + 4) / 2]) cube([30, 22, ledge + 5], center = true);   // its USB plug, at the back
                }
                // three towers the dome twists onto, and three small rests that hold its rim up off the deck
                for (i = [0 : lugs - 1]) {
                    difference() {
                        ring_piece(tower_in, tower_out, tower_at + i * 360 / lugs, 40, tower_h);
                        ring_piece(tower_out - lug_in - 0.9, tower_out + 1, tower_at + i * 360 / lugs - 12, lug_w + 5, tower_h + 1);                      // the way in, from above
                        translate([0, 0, slot_low]) ring_piece(tower_out - lug_in - 0.9, tower_out + 1, tower_at + i * 360 / lugs, 30, slot_high - slot_low);   // then round, under the roof
                    }
                    ring_piece(R - dome_wall - 1.4, R - 0.4, i * 360 / lugs, 8, seam);
                }
            }
        }
        // four M3 screws down into the base's posts; their heads are under the dome
        for (a = post_at) at(a) translate([post_r, 0, -lip - 1]) { cylinder(d = 3.4, h = lip + deck_h + 2, $fn = 24); translate([0, 0, lip + deck_h + 1 - 3.5]) cylinder(d = 6.4, h = 4, $fn = 24); }
        // the cables' way up: the microphones' USB plug and the glow's two wires
        translate([0, mic_d / 2 + 2, 0]) cube([17, 10, 40], center = true);
        // room for the posts' tops
        for (a = post_at) at(a) translate([post_r, 0, -lip - 1]) cylinder(d = boss + 1.2, h = 1.31);
    }
}

// ---- dome: the frosted shade ----------------------------------------------------------------------------------------------
// Drawn the way it prints: standing on its flat top. The bumps are near the rim, which prints last.
module lug(a) {
    hull() {
        ring_piece(R - dome_wall - lug_in, R - dome_wall + 0.2, a, lug_w, lug_tall);
        translate([0, 0, -lug_in]) ring_piece(R - dome_wall - 0.05, R - dome_wall + 0.2, a, lug_w, 0.1);
    }
}

module dome() {
    cup(R, dome_h, shoulder_r, dome_wall);
    for (i = [0 : lugs - 1]) translate([0, 0, dome_h - lug_low - lug_tall]) lug(tower_at + i * 360 / lugs - 12);
}

module rim() {   // the last 16 mm of the dome, to try the twist on the deck before printing the whole dome
    intersection() { dome(); translate([0, 0, dome_h - 16]) cylinder(r = R + 1, h = 17); }
}

// ---- small parts -----------------------------------------------------------------------------------------------------------
module tag() {   // goes under the switch's nut: the two words that matter
    difference() {
        translate([-13, -9.5, 0]) cube([26, 19, 1.2]);
        translate([0, 0, -1]) cylinder(d = sw_d, h = 4, $fn = 32);
        translate([0, 5, 0.7]) linear_extrude(1) text("MIC", size = 3.4, font = "Liberation Sans:style=Bold", halign = "center");
        translate([0, -8.6, 0.7]) linear_extrude(1) text("OFF", size = 3.4, font = "Liberation Sans:style=Bold", halign = "center");
    }
}

module fit() {    // print this first: thin frames to try your computer, your speaker and your microphone board in
    difference() { cube([board_w + 6, board_d + 6, 2], center = true); cube([board_w + 1, board_d + 1, 4], center = true); }
    translate([0, (board_d + 6) / 2 + (spk_d + 5) / 2 + 4, 0]) difference() { cube([spk_w + 5, spk_d + 5, 2], center = true); cube([spk_w, spk_d, 4], center = true); }
    translate([0, -(board_d + 6) / 2 - (mic_d + 5) / 2 - 4, 0])
        difference() { cylinder(d = mic_d + 5, h = 2, center = true); cylinder(d = mic_d + 0.8, h = 4, center = true); }
}

// ---- what to draw ----------------------------------------------------------------------------------------------------------
white = [0.96, 0.96, 0.94];

module insides() {  // the bought parts, to see how they sit
    color([0.25, 0.6, 0.3, 0.7]) translate([0, board_y, floor_t + board_lift + board_h / 2]) cube([board_w, board_d, board_h], center = true);
    color([0.15, 0.15, 0.16]) translate([0, spk_y, floor_t + spk_lift + spk_h / 2]) cube([spk_w - 1.5, spk_d - 1, spk_h], center = true);
}

module whole(spread = 0) {
    color(white) base();
    insides();
    translate([0, 0, base_h + spread]) color(white) deck();
    translate([0, 0, base_h + deck_h + ledge + spread * 1.5]) color([0.1, 0.42, 0.36]) cylinder(d = mic_d, h = 1.6);                       // the microphone board
    translate([0, 0, base_h + deck_h + spread * 1.5]) color([1, 0.72, 0.35]) difference() { cylinder(d = mic_d + 9, h = 5); translate([0, 0, -1]) cylinder(d = mic_d + 6.5, h = 7); }   // the glow
    translate([0, 0, base_h + deck_h + seam + dome_h + spread * 3]) mirror([0, 0, 1]) color([1, 1, 1, 0.42]) dome();
}

if (part == "base") base();
else if (part == "deck") deck();
else if (part == "dome") dome();
else if (part == "rim") translate([0, 0, -(dome_h - 16)]) rim();
else if (part == "tag") tag();
else if (part == "fit") fit();
else if (part == "exploded") whole(46);
else if (part == "cut") difference() { whole(0); translate([0, -200, -10]) cube([300, 400, 400]); }
else whole(0);
