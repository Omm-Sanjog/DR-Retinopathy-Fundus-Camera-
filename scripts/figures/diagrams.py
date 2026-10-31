import subprocess, os
OUT = "/home/claude/rep/figs/"
F = 'fontname="DejaVu Sans"'
HEAD = f'''graph [{F}, fontsize=12, bgcolor="white", pad=0.15, nodesep=0.35, ranksep=0.42];
node [{F}, fontsize=11, shape=box, style="rounded,filled", fillcolor="#eef3fb", color="#1f3864", penwidth=1.3, margin="0.14,0.07"];
edge [{F}, fontsize=9.5, color="#52514e", arrowsize=0.75, penwidth=1.1];
'''
C = dict(blue=("#e3eefc", "#2a78d6"), orange=("#fdeadf", "#d9541f"), aqua=("#dff5ec", "#14936a"), yellow=("#fdf3d6", "#b88200"),
         violet=("#ebe8fb", "#6250d6"), red=("#fbe3e3", "#c43c3b"), grey=("#f2f2f0", "#8a8984"), navy=("#1f3864", "#1f3864"))


def st(c, extra=""):
    f, b = C[c]
    return f'fillcolor="{f}", color="{b}"' + (", " + extra if extra else "")


def render(name, body, directed=True):
    src = ("digraph G {\n" if directed else "graph G {\n") + HEAD + body + "\n}"
    open(f"/home/claude/rep/src/{name}.dot", "w").write(src)
    subprocess.run(["dot", "-Tpng", "-Gdpi=220", f"/home/claude/rep/src/{name}.dot", "-o", OUT + name + ".png"], check=True)
    print("saved", name)


# 1. Literature map -----------------------------------------------------------
render("g_litmap", f'''
rankdir=LR; ranksep=0.5;
a [label="Classical image\\nprocessing", {st("grey")}]; b [label="Machine learning on\\nhand-crafted features", {st("grey")}];
c [label="Deep learning\\n(CNN grading)", {st("blue")}]; d [label="Edge / offline\\ninference", {st("aqua")}]; e [label="Low-cost fundus\\nimaging hardware", {st("orange")}];
{{rank=same; a; b; c; d; e}} a -> b -> c -> d -> e [style=invis];
a1 [label="Vessel segmentation, MA &\\nexudate detection (morphology,\\nmatched filters, thresholding)", {st("grey")}];
b1 [label="SVM / Random Forest on\\nlesion counts & texture", {st("grey")}];
c1 [label="Gulshan 2016, Ting 2017,\\nKrause 2018 (ensembles,\\nInception-v3, VGG)", {st("blue")}];
c2 [label="Regulated products:\\nIDx-DR / LumineticsCore,\\nEyeArt, Google ARDA", {st("blue")}];
d1 [label="Medios on smartphone,\\nMobileNet / EfficientNet,\\nINT8 quantisation", {st("aqua")}];
e1 [label="Smartphone adapters:\\nPeek, Remidio FOP,\\nD-Eye, 20 D + phone", {st("orange")}];
e2 [label="Raspberry Pi camera with\\n20 D lens & IR/white LEDs\\n(Shen & Mukai 2017)", {st("orange")}];
a -> a1; b -> b1; c -> c1; c -> c2; d -> d1; e -> e1; e -> e2;
gap [label="Gap addressed by this project:\\nopen, low-cost device that captures\\nAND grades on-device, offline,\\nwith an image-quality gate", {st("red")}, penwidth=2];
{{c2 d1 e2}} -> gap [style=dashed, color="#c43c3b"];
''')

# 2. System block diagram ------------------------------------------------------
render("g_block", f'''
rankdir=LR; nodesep=0.22; ranksep=0.42; newrank=true;
node [width=1.6];
subgraph cluster_opt {{ label="OPTICAL HEAD"; style="rounded,filled"; fillcolor="#fff8f3"; color="#d9541f"; fontcolor="#d9541f"; fontsize=11;
  eye [label="Patient eye\\n(undilated pupil)", {st("grey")}];
  led [label="IR 850 nm (align)\\n+ white LED (flash)", {st("red")}];
  lens [label="20 D condensing\\nlens (f = 50 mm)", {st("orange")}];
  cam [label="Camera Module 3\\nNoIR · IMX708", {st("orange")}]; }}
subgraph cluster_pi {{ label="RASPBERRY PI 5 — PROCESSING"; style="rounded,filled"; fillcolor="#f3f8ff"; color="#2a78d6"; fontcolor="#2a78d6"; fontsize=11;
  cap [label="Capture control\\n(Picamera2 / libcamera)", {st("blue")}];
  q [label="Quality & fundus\\ngate", {st("yellow")}];
  pre [label="Pre-processing\\n(OpenCV)", {st("blue")}];
  inf [label="EfficientNet-B0\\n(ONNX Runtime)", {st("navy", 'fontcolor="white"')}];
  rep [label="Grade + referral\\ndecision", {st("blue")}]; }}
subgraph cluster_ui {{ label="USER INTERFACE & POWER"; style="rounded,filled"; fillcolor="#f8f6fe"; color="#6250d6"; fontcolor="#6250d6"; fontsize=11;
  ui [label="5″ touch display\\n+ capture button", {st("violet")}];
  sd [label="microSD storage\\n(OS, model, records)", {st("grey")}];
  out [label="Report\\n(screen / JSON / PDF)", {st("violet")}];
  pwr [label="USB-C PD 27 W\\nor power bank", {st("grey")}]; }}
{{rank=same; eye; led; lens; cam}} {{rank=same; cap; q; pre; inf; rep}} {{rank=same; ui; sd; out; pwr}}
cam -> lens -> led -> eye [style=invis]; pwr -> out -> sd -> ui [style=invis];
lens -> led [dir=back, label="illuminate", style=dashed, color="#c43c3b", fontcolor="#c43c3b"];
eye -> lens [dir=both, constraint=false];
cam -> lens [dir=back, label="aerial image"];
rep -> inf -> pre -> q -> cap [dir=back];
cam -> cap [label="CSI-2"]; q -> ui [label="retake prompt", style=dashed, color="#b88200", fontcolor="#b88200"];
rep -> out; inf -> sd [style=dotted, label="model"]; ui -> cap [style=dashed, label="capture", constraint=false];
''')

# 3. Interfacing / circuit -----------------------------------------------------
render("g_circuit", f'''
rankdir=LR; nodesep=0.22; ranksep=0.9;
node [shape=box];
camn [label="Camera Module 3 NoIR\\nIMX708 · 12 MP · AF", {st("orange")}];
ir [label="IR LED string (5 V)\\n4 × 850 nm @ 50 mA\\nR = 68 Ω each", {st("red")}];
wl [label="White LED flash (5 V)\\n2 × 3000 K @ 20 mA\\nR = 100 Ω each", {st("yellow")}];
q1 [label="N-MOSFET Q1\\nAO3400", {st("grey")}]; q2 [label="N-MOSFET Q2\\nAO3400", {st("grey")}];
btn [label="Capture button\\nto GND, 10 kΩ pull-up", {st("aqua")}];
pi [shape=record, {st("blue")}, label="<t> Raspberry Pi 5 (4 GB)\\nBCM2712, 4× Cortex-A76|<csi> CSI-0 (22-pin FPC)|<g18> GPIO18 / PWM0|<g19> GPIO19 / PWM1|<g17> GPIO17 (input)|<dsi> DSI-1 / HDMI-0|<usb> USB-C power in|<fan> Fan header"];
disp [label="5″ touch display\\n800 × 480", {st("violet")}];
psu [label="27 W USB-C PD supply\\nor 10 000 mAh PD bank", {st("grey")}];
fan [label="Active cooler", {st("grey")}];
camn -> pi:csi [dir=none, color="#d9541f", penwidth=2];
q1 -> pi:g18 [dir=back]; q2 -> pi:g19 [dir=back];
q1 -> ir [dir=none]; q2 -> wl [dir=none];
btn -> pi:g17;
pi:dsi -> disp [dir=none, color="#6250d6", penwidth=2]; psu -> pi:usb [penwidth=2]; pi:fan -> fan [dir=none];
{{rank=same; camn; ir; q1; wl; q2; btn}}
camn -> ir -> q1 -> wl -> q2 -> btn [style=invis];
''')

# 4. Software architecture -----------------------------------------------------
render("g_sw", f'''
rankdir=TB; nodesep=0.18; ranksep=0.18;
node [width=1.55, height=0.5, fixedsize=false];
subgraph cluster_p {{ label="Presentation layer"; style="rounded,filled"; fillcolor="#f6f2fd"; color="#6250d6";
  p1 [label="Touch-screen UI", {st("violet")}]; p2 [label="CLI\\npi_inference.py", {st("violet")}]; p3 [label="JSON / PDF report", {st("violet")}]; }}
subgraph cluster_a {{ label="Application layer"; style="rounded,filled"; fillcolor="#f1f7ff"; color="#2a78d6";
  a1 [label="Capture controller\\n(IR preview → flash)", {st("blue")}]; a2 [label="DRModel.predict()", {st("blue")}]; a3 [label="Record store\\n(local, anonymised)", {st("blue")}]; }}
subgraph cluster_i {{ label="Inference & vision layer"; style="rounded,filled"; fillcolor="#eefaf5"; color="#14936a";
  i1 [label="Quality metrics\\n+ fundus gate", {st("aqua")}]; i2 [label="preprocess_fundus()\\nOpenCV", {st("aqua")}]; i3 [label="ONNX Runtime 1.x\\nCPU EP, INT8/FP32", {st("aqua")}]; }}
subgraph cluster_o {{ label="Platform layer"; style="rounded,filled"; fillcolor="#f7f7f5"; color="#8a8984";
  o1 [label="Raspberry Pi OS\\nBookworm 64-bit", {st("grey")}]; o2 [label="libcamera /\\nrpicam-apps", {st("grey")}]; o3 [label="Python 3.11 +\\nNumPy", {st("grey")}]; }}
p1 -> a1 [style=invis]; p2 -> a2 [style=invis]; p3 -> a3 [style=invis];
a1 -> i1 [style=invis]; a2 -> i2 [style=invis]; a3 -> i3 [style=invis];
i1 -> o1 [style=invis]; i2 -> o2 [style=invis]; i3 -> o3 [style=invis];
''')

# 5. Device workflow flowchart ------------------------------------------------
D = st("yellow", 'shape=diamond, style="filled", margin="0.04,0.02"')
render("g_workflow", f'''
rankdir=TB; nodesep=0.35; ranksep=0.32;
s [label="Start", shape=oval, {st("navy", 'fontcolor="white"')}];
a [label="Dim room; patient fixates;\\noperator aligns under IR preview", {st("blue")}];
b [label="Press capture → white LED flash\\n(≤ 200 ms) + 12 MP still", {st("blue")}];
c [label="Compute brightness &\\nsharpness (green channel)", {st("blue")}];
d1 [label="Quality\\nOK?", {D}];
d2 [label="Fundus-like?\\n(R/G ≥ 1.6)", {D}];
e [label="Crop → square → 384 px →\\nBen Graham → mask", {st("aqua")}];
f [label="EfficientNet-B0 (ONNX)\\n→ severity score ŷ", {st("navy", 'fontcolor="white"')}];
g [label="Grade = Σ [ŷ > tᵢ]\\nReferable if grade ≥ 2", {st("aqua")}];
h [label="Display grade, referral advice,\\nsave anonymised record", {st("violet")}];
r [label="Show reason:\\nblur / dark / not retina\\n→ RETAKE", {st("red")}];
x [label="End", shape=oval, {st("navy", 'fontcolor="white"')}];
s -> a -> b -> c -> d1; d1 -> d2 [label=" yes"]; d1 -> r [label=" no"]; d2 -> e [label=" yes"]; d2 -> r [label=" no"];
e -> f -> g -> h -> x; r -> a [constraint=false, style=dashed, label=" ≤ 3 attempts"];
{{rank=same; d1; r}}
''')

# 6. Training pipeline ----------------------------------------------------------
render("g_train", f'''
rankdir=TB; nodesep=0.3; ranksep=0.3;
a [label="Download APTOS 2019 from\\nHugging Face (3,662 images)", {st("blue")}];
b [label="Pre-process once & cache\\n(crop, 384 px, Ben Graham, mask)\\n+ record quality metrics", {st("blue")}];
c [label="Stratified split 70/15/15\\n(seed 42)", {st("blue")}];
subgraph cluster_t {{ label="Training loop (20 epochs, T4 GPU, AMP)"; style="rounded,dashed"; color="#14936a"; fontcolor="#14936a";
 d [label="Augment: flips, ±180° rotation,\\nscale crop, colour jitter, blur", {st("aqua")}];
 e [label="EfficientNet-B0 (ImageNet init)\\n→ 1 regression output", {st("aqua")}];
 f [label="Smooth-L1 loss, AdamW\\nOne-cycle LR (3e-4)", {st("aqua")}];
 g [label="Validation QWK each epoch\\nsave best checkpoint", {st("aqua")}]; }}
h [label="Tune thresholds t₁–t₄ on\\nvalidation set (maximise QWK)", {st("yellow")}];
i [label="Evaluate once on held-out test:\\nQWK, accuracy, sens/spec, AUC", {st("orange")}];
j [label="Grad-CAM explanations", {st("orange")}];
k [label="Export ONNX FP32 → INT8 (QDQ)\\nparity & accuracy check", {st("violet")}];
l [label="dr_pi_bundle.zip\\n(model, config, script, README)", {st("navy", 'fontcolor="white"')}];
a -> b -> c -> d -> e -> f -> g; g -> d [label=" next epoch", style=dashed, constraint=false];
g -> h -> i -> j -> k -> l;
''')

# 7. MBConv block --------------------------------------------------------------
render("g_mbconv", f'''
rankdir=TB; nodesep=0.35; ranksep=0.45;
x [label="Input\\nH×W×C", {st("grey")}];
e [label="1×1 Conv\\nexpand ×6\\nBN + SiLU", {st("blue")}];
d [label="k×k depthwise\\nConv\\nBN + SiLU", {st("blue")}];
s [label="Squeeze-and-\\nExcitation\\n(GAP→FC→σ)", {st("yellow")}];
p [label="1×1 Conv\\nproject\\nBN", {st("blue")}];
a [label="⊕", shape=circle, {st("aqua")}, fontsize=16];
y [label="Output\\nH×W×C", {st("grey")}];
{{rank=same; x; e; d; s}} {{rank=same; y; a; p}} x -> e -> d -> s; s -> p; y -> a -> p [dir=back]; x -> a [label=" skip connection", style=dashed];
''')

# 8. State machine -----------------------------------------------------------------
render("g_states", f'''
rankdir=TB; nodesep=0.5; ranksep=0.55;
node [shape=box, style="rounded,filled"];
boot [label="BOOT\\nload model\\n& config", {st("grey")}];
idle [label="IDLE\\nhome screen", {st("blue")}];
align [label="ALIGN\\nIR preview\\n30 fps", {st("blue")}];
flash [label="CAPTURE\\nwhite flash\\n+ still", {st("orange")}];
check [label="CHECK\\nquality &\\nfundus gate", {st("yellow")}];
anal [label="ANALYSE\\npre-process\\n+ inference", {st("navy", 'fontcolor="white"')}];
res [label="RESULT\\ngrade &\\nreferral", {st("aqua")}];
{{rank=same; boot; idle; align; flash}} {{rank=same; res; anal; check}} boot -> idle; idle -> align [label="new\\npatient"]; align -> flash [label="button"]; flash -> check;
check -> align [label="fail → retake", style=dashed, color="#c43c3b", fontcolor="#c43c3b"];
res -> anal [dir=back]; anal -> check [dir=back, label="pass"]; res -> idle [label=" save / next"];
''')

# 9. Methodology ---------------------------------------------------------------------
render("g_method", f'''
rankdir=TB; nodesep=0.5; ranksep=0.4;
node [width=1.6];
p1 [label="1. Study\\nliterature,\\ndatasets,\\nstandards", {st("blue")}];
p2 [label="2. Specify\\nrequirements\\n& constraints", {st("blue")}];
p3 [label="3. Design\\noptics, circuit,\\nsoftware", {st("aqua")}];
p4 [label="4. Build\\nmodel (Colab)\\n& Pi bundle", {st("aqua")}];
p5 [label="5. Verify\\nmetrics,\\nparity, gates", {st("yellow")}];
p6 [label="6. Validate\\nown camera vs\\nophthalmologist", {st("orange")}];
{{rank=same; p1; p2; p3}} {{rank=same; p6; p5; p4}} p1 -> p2 -> p3; p3 -> p4; p6 -> p5 -> p4 [dir=back]; p5 -> p3 [style=dashed, label=" iterate"];
''')

# 10. DFD level 1 -------------------------------------------------------------------
render("g_dfd", f'''
rankdir=TB; nodesep=0.3; ranksep=0.5;
op [label="Operator /\\nhealth worker", shape=box, style="filled", {st("grey")}];
pt [label="Patient", shape=box, style="filled", {st("grey")}];
p1 [label="1.0\\nCapture\\nimage", shape=circle, {st("blue")}, width=1.0];
p2 [label="2.0\\nAssess\\nquality", shape=circle, {st("yellow")}, width=1.0];
p3 [label="3.0\\nGrade\\nDR", shape=circle, {st("navy", 'fontcolor="white"')}, width=1.0];
p4 [label="4.0\\nReport &\\nstore", shape=circle, {st("aqua")}, width=1.0];
d1 [label="D1  Model & config", shape=box, style="filled", {st("grey")}];
d2 [label="D2  Screening records", shape=box, style="filled", {st("grey")}];
pt -> p1 [label="retinal\\nreflection"]; op -> p1 [label="capture\\ncommand"];
p1 -> p2 [label="raw image"]; p2 -> op [label="retake\\nprompt", style=dashed];
p2 -> p3 [label="gradable\\nimage"]; d1 -> p3 [label="weights,\\nthresholds"];
p3 -> p4 [label="grade,\\nscore"]; {{rank=same; p1; p2; p3; p4}} {{rank=same; op; pt}} {{rank=same; d1; d2}} p4 -> op [label="result &\\nreferral"]; p4 -> d2 [label="record"];
''')

# 11. Export pipeline ---------------------------------------------------------------
render("g_export", f'''
nodesep=0.3; ranksep=0.4;
a [label="best_model.pt\\n(PyTorch)", {st("blue")}];
b [label="Wrapper +\\nnormalisation", {st("blue")}];
c [label="ONNX export\\nopset 17", {st("aqua")}];
d [label="FP32 ONNX\\n15.9 MB", {st("aqua")}];
e [label="Static INT8\\nquantisation", {st("yellow")}];
f [label="INT8 ONNX\\n4.5 MB", {st("orange")}];
g [label="Parity & QWK\\ncheck → select", {st("violet")}];
rankdir=TB; {{rank=same; a; b; c; d}} {{rank=same; g; f; e}} a -> b -> c -> d; d -> e; e -> f -> g [dir=back]; f -> e [style=invis];
''')
