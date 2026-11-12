// Luma Home: the first case you can print (prototype, "EVT").
//
// A soft-cornered tower in three printed sections, bottom to top:
//   base : the computer (a Jetson Orin Nano Super developer kit by default), air in from below, ports out the back
//   mid  : a sealed box for the speaker, which fires out the front
//   top  : the microphone ring, the hardware microphone switch and its hard-wired light at the back
//   lid  : an open lattice over the microphones
// plus two small parts: a ring that clamps the speaker from inside, and a cover plate for the switch.
//
// Everything is a number you can change. Measure your own parts before you print: the defaults are from the makers' published
// sizes, and a speaker or a switch from another maker will differ by a millimetre or two. Print `part = "fit"` first (ten
// minutes): thin test rings for the board, the speaker and the microphone ring.
//
//   openscad -o base.stl -D 'part="base"' luma_case.scad      (and "mid", "top", "lid", "ring", "plate", "fit")
//
// Print in PETG, 0.2 mm layers, 3 walls, 20% infill, no supports: base, mid and top stand as drawn, the lid lies on its face.
// Units are millimetres. License: MIT.

part = "assembly";   // base | mid | top | lid | ring | plate | fit | assembly | exploded | cut

/* [The body] */
body_w = 136;        // width, side to side
body_d = 124;        // depth, front to back (the back is +y: ports, switch)
corner_r = 18;       // corner radius
wall = 2.4;          // wall thickness (3 lines of a 0.4 mm nozzle at 0.8 extra)
floor_t = 2.4;
lip = 3;             // how far one section steps into the next
gap = 0.25;          // slack between sections

/* [The computer] */
// Jetson Orin Nano Super developer kit: the board is 100 x 79; with connectors and the fan it fills about 103 x 90.5 x 35.
board_w = 103;
board_d = 90.5;
board_h = 35;
board_lift = 3;      // the board sits on its own feet; this is extra room under it for air
cable_room = 8;      // above the fan, for the USB plugs and wires
port_w = 98;         // window in the back wall for USB, network, display and power; open to the rim, so nothing bridges
port_up = 2;         // bottom of the window above the board's underside
// A Raspberry Pi 5 instead (the $250 tier): set pi5 = true for four M2.5 posts on its 58 x 49 hole pattern.
pi5 = false;

/* [The speaker] */
spk_cone = 70;       // opening for the cone (a 3 inch driver)
spk_frame = 78;      // outside of the driver's frame
spk_screw = 62;      // side of the square the four mounting holes sit on (measure yours)
chamber_h = 86;      // inside height of the sealed box

/* [The microphones] */
mic_d = 70;          // ReSpeaker Mic Array v2.0: a round board, 70 across
mic_drop = 9;        // how far below the top surface the board sits
top_h = 28;          // the top section with its lid on
lid_t = 2;           // the lid's thickness

/* [The switch and its light] */
sw_slot = [13, 6.5]; // opening for the slide switch's lever
sw_holes = 19;       // distance between its two mounting screws
led_d = 5.1;         // a 5 mm LED pressed in from inside

$fn = 72;
bay_h = floor_t + board_lift + board_h + cable_room;   // inside height of the base
mid_h = floor_t + chamber_h;
boss = 9;            // corner posts for the M3 screws that hold the sections together
ins = 4.0;           // hole for an M3 heat-set insert (4.0 for the common 4.6 mm brass ones)
iw = body_w - 2 * wall;
id = body_d - 2 * wall;
ir = corner_r - wall;

module slab(w, d, r, h) {       // a rounded rectangle, standing on z = 0
    hull() for (x = [-1, 1], y = [-1, 1]) translate([x * (w / 2 - r), y * (d / 2 - r), 0]) cylinder(r = r, h = h);
}

module shell(h) {               // the outer wall of one section, open top and bottom
    difference() {
        slab(body_w, body_d, corner_r, h);
        translate([0, 0, -1]) slab(iw, id, ir, h + 2);
    }
}

// Two sets of screws, so a screwdriver always has a straight way in. The mid section screws down into the base's four corner
// posts (through its own floor, from above, before the top goes on). The top screws down into four ribs on the mid section's
// side walls (through wells in the lid). Posts and ribs are fused into the wall and print without supports.
module corners() {
    off = (ir - boss / 2 + 0.6) * 0.7071;
    for (x = [-1, 1], y = [-1, 1]) translate([x * (iw / 2 - ir + off), y * (id / 2 - ir + off), 0]) children();
}

module sides() {
    for (x = [-1, 1], y = [-1, 1]) translate([x * (iw / 2 - boss / 2 + 0.6), y * id / 4, 0]) children();
}

module plug(clear = "corners") {   // the step under a section that drops into the one below: solid, so the floor above it prints on it
    difference() {
        translate([0, 0, -lip]) slab(iw - 2 * gap, id - 2 * gap, ir - gap, lip + 0.01);
        if (clear == "corners") corners() translate([0, 0, -lip - 1]) cylinder(d = boss + 1, h = lip + 2);
        else sides() translate([0, 0, -lip - 1]) cylinder(d = boss + 1, h = lip + 2);
    }
}

module seam(h) {   // the space a section may fill: its plug, then a 45 degree step out to the full width (no overhang to print, and a neat shadow line)
    bevel = wall + gap;
    translate([0, 0, -lip - 1]) slab(iw - 2 * gap, id - 2 * gap, ir - gap, lip + 1.01);
    hull() { slab(iw - 2 * gap, id - 2 * gap, ir - gap, 0.01); translate([0, 0, bevel]) slab(body_w, body_d, corner_r, 0.01); }
    translate([0, 0, bevel]) slab(body_w, body_d, corner_r, h);
}

module slots(n, len, w, pitch) { // a row of air slots, centred
    for (i = [0 : n - 1]) translate([(i - (n - 1) / 2) * pitch, 0, 0]) hull() {
        translate([0, -len / 2 + w / 2, 0]) cylinder(d = w, h = 20, center = true);
        translate([0, len / 2 - w / 2, 0]) cylinder(d = w, h = 20, center = true);
    }
}

// ---- base: the computer -------------------------------------------------------------------------------------------------
module base() {
    difference() {
        union() {
            slab(body_w, body_d, corner_r, floor_t);
            shell(bay_h);
            corners() translate([0, 0, floor_t]) cylinder(d = boss, h = bay_h - floor_t);
            if (pi5) {  // four M2.5 posts on the Pi 5's hole pattern (58 x 49), board against the back wall
                translate([0, id / 2 - 56 / 2 - 3, floor_t]) for (x = [-29, 29], y = [-24.5, 24.5]) translate([x, y, 0])
                    difference() { cylinder(d = 6, h = board_lift + 3); cylinder(d = 2.2, h = board_lift + 4); }
            } else {    // four corner guides: the kit stands on its own feet between them
                translate([0, id / 2 - board_d / 2 - 0.5, floor_t]) for (x = [-1, 1], y = [-1, 1])
                    translate([x * (board_w / 2 + 1.5), y * (board_d / 2 - 8), 4.5]) cube([2, 14, 9], center = true);
            }
        }
        corners() translate([0, 0, bay_h - 10]) cylinder(d = ins, h = 11);        // heat-set inserts for the mid section's screws
        // air in from below, under the board
        translate([0, 6, 0]) slots(9, 62, 4, 9);
        // air out both sides, level with the fan
        for (x = [-1, 1]) translate([x * body_w / 2, 0, floor_t + board_lift + board_h * 0.62]) rotate([0, 90, 0]) rotate([0, 0, 90]) slots(8, 14, 3.2, 8);
        // the back: one window for every port on the board's rear edge
        translate([-port_w / 2, body_d / 2 - 2 * wall, floor_t + board_lift + port_up]) cube([port_w, 4 * wall, bay_h]);
        // four recesses for stick-on rubber feet
        for (x = [-1, 1], y = [-1, 1]) translate([x * (body_w / 2 - 20), y * (body_d / 2 - 20), -0.01]) cylinder(d = 13, h = 0.8);
    }
}

// ---- mid: the speaker's sealed box ----------------------------------------------------------------------------------------
module mid() {
    intersection() {
        seam(mid_h + 1);
        difference() {
            union() {
                slab(body_w, body_d, corner_r, floor_t);       // the deck between the computer and the speaker
                shell(mid_h);
                plug("corners");
                sides() translate([0, 0, floor_t]) cylinder(d = boss, h = mid_h - floor_t);
                // a flat pad inside the front wall for the driver's frame
                translate([-(spk_frame + 6) / 2, -id / 2 - 0.5, floor_t]) cube([spk_frame + 6, 3.5, chamber_h - lip - 1]);
                // the cable chimney's wall keeps the speaker's box sealed
                translate([0, id / 2 - 9, floor_t]) hull() { translate([-9, 0, 0]) cylinder(d = 9 + 2 * wall, h = chamber_h); translate([9, 0, 0]) cylinder(d = 9 + 2 * wall, h = chamber_h); }
            }
            corners() translate([0, 0, -lip - 1]) cylinder(d = 3.4, h = lip + floor_t + 2);          // M3 x 12 screws down into the base
            sides() translate([0, 0, mid_h - 10]) cylinder(d = ins, h = 11);                         // heat-set inserts for the top's screws
            // the cone looks out through nine slots; no finger reaches it
            translate([0, -body_d / 2, floor_t + chamber_h / 2]) rotate([90, 0, 0]) intersection() {
                cylinder(d = spk_cone, h = 20, center = true);
                slots(9, spk_cone, 4.2, 7.6);
            }
            // four screws for the driver
            for (x = [-1, 1], z = [-1, 1]) translate([x * spk_screw / 2, -id / 2, floor_t + chamber_h / 2 + z * spk_screw / 2])
                rotate([90, 0, 0]) cylinder(d = 2.8, h = 12, center = true);
            // one hole in the deck for the speaker wire (seal it with a dab of hot glue), and the chimney for the cables going up
            translate([iw / 2 - 16, 0, -lip - 1]) cylinder(d = 5, h = lip + floor_t + 2);
            translate([0, id / 2 - 9, -lip - 1]) hull() { translate([-9, 0, 0]) cylinder(d = 9, h = mid_h + lip + 2); translate([9, 0, 0]) cylinder(d = 9, h = mid_h + lip + 2); }
        }
    }
}

// ---- top: the microphones, the switch and its light -----------------------------------------------------------------------
// A tub with a solid floor. The floor is the speaker box's ceiling (a strip of 1 mm foam tape on the rim below seals it), so the
// microphones sit outside the box the speaker pushes air into. Cables come up the chimney at the back.
ledge = top_h - lid_t - mic_drop - 1.6;   // the microphone board lies on a ring this high

module top() {
    intersection() {
        seam(top_h);
        difference() {
            union() {
                slab(body_w, body_d, corner_r, floor_t);
                shell(top_h - lid_t);
                plug("sides");
                // a ring the round board lies on, and a low rim around it that centres it
                difference() {
                    union() { cylinder(d = mic_d - 2, h = ledge); cylinder(d = mic_d + 4.4, h = ledge + 2.2); }
                    translate([0, 0, floor_t]) cylinder(d = mic_d - 8, h = ledge + 5);
                    translate([0, 0, ledge]) cylinder(d = mic_d + 0.8, h = 5);
                    translate([0, mic_d / 2, floor_t + (ledge + 4) / 2]) cube([30, 22, ledge + 4], center = true);   // its USB plug and audio jack, at the back
                }
            }
            sides() translate([0, 0, -lip - 1]) cylinder(d = 3.4, h = lip + floor_t + 2);             // M3 x 12 screws down into the mid section's ribs
            // the cables' way up from the chimney
            translate([0, id / 2 - 9, -lip - 1]) hull() { translate([-9, 0, 0]) cylinder(d = 9, h = lip + floor_t + 2); translate([9, 0, 0]) cylinder(d = 9, h = lip + floor_t + 2); }
            // the switch: a slot for its lever and two screws, on the back, where a thumb finds it
            translate([-22, body_d / 2, (top_h - lid_t + floor_t) / 2]) rotate([90, 0, 0]) {
                cube([sw_slot[0], sw_slot[1], 3 * wall], center = true);
                for (x = [-1, 1]) translate([x * sw_holes / 2, 0, 0]) cylinder(d = 2.3, h = 3 * wall, center = true);
            }
            // its light, hard-wired to the microphones' power: lit means they can hear
            translate([10, body_d / 2, (top_h - lid_t + floor_t) / 2]) rotate([90, 0, 0]) cylinder(d = led_d, h = 3 * wall, center = true);
        }
    }
}

// ---- lid: an open lattice over the microphones and their ring of lights ---------------------------------------------------
// Prints flat, upside down. Stretch speaker cloth under it if you like. It presses into the top; two dabs of glue if it's loose.
module lid() {
    difference() {
        union() {
            slab(body_w, body_d, corner_r, lid_t);
            translate([0, 0, -lip]) difference() {
                slab(iw - 2 * gap, id - 2 * gap, ir - gap, lip);
                translate([0, 0, -1]) slab(iw - 2 * gap - 2 * 1.6, id - 2 * gap - 2 * 1.6, max(ir - gap - 1.6, 1), lip + 2);
            }
        }
        translate([0, 0, -lip - 1]) cylinder(d = mic_d + 18, h = lid_t + lip + 2);
    }
    intersection() {
        cylinder(d = mic_d + 19, h = lid_t);
        union() {
            for (a = [0 : 30 : 150]) rotate([0, 0, a]) translate([0, 0, lid_t / 2]) cube([mic_d + 20, 1.6, lid_t], center = true);
            for (d = [22, 46, 70]) difference() { cylinder(d = d + 1.6, h = lid_t); translate([0, 0, -1]) cylinder(d = d - 1.6, h = lid_t + 2); }
        }
    }
}

// ---- small parts -----------------------------------------------------------------------------------------------------------
module ring() {   // clamps the speaker's frame against the front wall from inside
    difference() {
        cube([spk_frame + 6, spk_frame + 6, 3], center = true);
        cylinder(d = spk_cone + 2, h = 5, center = true);
        for (x = [-1, 1], y = [-1, 1]) translate([x * spk_screw / 2, y * spk_screw / 2, 0]) cylinder(d = 3.3, h = 5, center = true);
    }
}

module plate() {  // goes over the switch from outside: a slot and the two words that matter
    difference() {
        hull() for (x = [-1, 1]) translate([x * 16, 0, 0]) cylinder(d = 14, h = 1.6);
        translate([0, 0, -1]) hull() for (x = [-1, 1]) translate([x * (sw_slot[0] / 2 - 2), 0, 0]) cylinder(d = 4.5, h = 4);
        for (x = [-1, 1]) translate([x * sw_holes / 2, 0, -1]) cylinder(d = 2.4, h = 4);
        translate([-19.5, -6.2, 1.1]) linear_extrude(1) text("MIC", size = 3.2, font = "Liberation Sans:style=Bold");
        translate([12.5, -6.2, 1.1]) linear_extrude(1) text("OFF", size = 3.2, font = "Liberation Sans:style=Bold");
    }
}

module fit() {    // print this first: three thin rings to try your parts in (it fits a 220 mm bed)
    difference() { cube([board_w + 6, board_d + 6, 2], center = true); cube([board_w + 1, board_d + 1, 4], center = true); }
    translate([-(spk_frame + 6) / 2 - 3, (board_d + 6) / 2 + (spk_frame + 6) / 2 + 6, 0.5]) ring();
    translate([(mic_d + 5) / 2 + 3, (board_d + 6) / 2 + (mic_d + 5) / 2 + 6, 0])
        difference() { cylinder(d = mic_d + 5, h = 2, center = true); cylinder(d = mic_d + 0.8, h = 4, center = true); }
}

// ---- what to draw ----------------------------------------------------------------------------------------------------------
module computer_ghost() {  // the board's envelope, to see how it sits
    color([0.25, 0.6, 0.3, 0.6]) translate([0, id / 2 - board_d / 2 - 0.5, floor_t + board_lift + board_h / 2]) cube([board_w, board_d, board_h], center = true);
}

module whole(spread = 0) {
    color([0.93, 0.92, 0.89]) base();
    computer_ghost();
    translate([0, 0, bay_h + spread]) color([0.93, 0.92, 0.89]) mid();
    translate([0, 0, bay_h + mid_h + 2 * spread]) color([0.93, 0.92, 0.89]) top();
    // the speaker's clamp ring and its cone, the microphone board
    translate([0, -id / 2 + 4.5 + spread * 0.4, bay_h + spread + floor_t + chamber_h / 2]) rotate([90, 0, 0]) color([0.2, 0.2, 0.22]) ring();
    translate([0, -id / 2 + 24 + spread * 0.4, bay_h + spread + floor_t + chamber_h / 2]) rotate([90, 0, 0]) color([0.12, 0.12, 0.13]) cylinder(d1 = 30, d2 = spk_cone - 4, h = 14);
    translate([0, 0, bay_h + mid_h + 2 * spread + ledge + spread * 0.9]) color([0.1, 0.42, 0.36]) cylinder(d = mic_d, h = 1.6);
    translate([0, 0, bay_h + mid_h + 2 * spread + top_h - lid_t + spread * 1.9]) color([0.93, 0.92, 0.89]) lid();
}

if (part == "base") base();
else if (part == "mid") mid();
else if (part == "top") top();
else if (part == "lid") rotate([180, 0, 0]) lid();
else if (part == "ring") ring();
else if (part == "plate") plate();
else if (part == "fit") fit();
else if (part == "exploded") whole(36);
else if (part == "cut") difference() { whole(0); translate([0, -150, -10]) cube([300, 300, 400]); }
else whole(0);
